import sqlite3, datetime, json, re, shutil, subprocess, concurrent.futures, time, os, threading
from pathlib import Path
from discovery import aliases
import guardian
import reaper
import devcentral_bridge
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent

def inventory():
    data=json.loads((ROOT/'vms.json').read_text(encoding='utf-8'))
    if not isinstance(data,list): raise ValueError('vms.json deve conter uma lista')
    for vm in data:
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*',vm['ssh']): raise ValueError('Alias SSH inválido: '+vm['ssh'])
        if vm['cloud'] not in ('Google Cloud','AWS','Azure','Oracle Cloud'): raise ValueError('Cloud inválida')
    return data

def local_processes():
    if os.name != 'nt': return None
    script = "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    try:
        p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,timeout=8)
        if p.returncode: return None
        data=json.loads(p.stdout)
        return data if isinstance(data,list) else [data]
    except (OSError,ValueError,subprocess.TimeoutExpired): return None

def local_evidence(alias, processes):
    if processes is None: return 'unknown'
    byid={p['ProcessId']:p for p in processes}
    for p in processes:
        if p.get('Name','').lower() != 'ssh.exe': continue
        if not re.search(r'(?<![\w.-])'+re.escape(alias)+r'(?![\w.-])',p.get('CommandLine') or '',re.I): continue
        seen=set(); parent=p.get('ParentProcessId')
        while parent in byid and parent not in seen:
            seen.add(parent); q=byid[parent]
            if q.get('Name','').lower() in ('code.exe','code - insiders.exe'): return 'detected'
            parent=q.get('ParentProcessId')
    return 'not_detected'

LOCK=threading.Lock()
CACHE=None
LAST=0
DB=ROOT/'history.sqlite3'
def record(rows):
    with sqlite3.connect(DB) as db:
        db.execute('CREATE TABLE IF NOT EXISTS samples (ts INTEGER, alias TEXT, payload TEXT)')
        db.execute('CREATE INDEX IF NOT EXISTS sample_alias ON samples(alias,ts)')
        now=int(time.time())
        db.executemany('INSERT INTO samples VALUES (?,?,?)',[(now,r['ssh'],json.dumps(r)) for r in rows])
        db.execute('DELETE FROM samples WHERE ts < ?', (now-30*86400,))
    threading.Thread(target=devcentral_bridge.push_vm_telemetry_to_neon, args=(rows,), daemon=True).start()
def history():
    with sqlite3.connect(DB) as db:
        db.execute('CREATE TABLE IF NOT EXISTS samples (ts INTEGER, alias TEXT, payload TEXT)')
        return [dict(ts=t,**json.loads(p)) for t,p in db.execute('SELECT ts,payload FROM samples ORDER BY ts DESC LIMIT 10000')]


def status():
    global CACHE,LAST
    with LOCK:
        if CACHE is not None and time.monotonic()-LAST<15: return CACHE
        processes=local_processes()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(probe,inventory()))
        for vm in results: vm['local_evidence']=local_evidence(vm['ssh'],processes)
        record(results); CACHE=results; LAST=time.monotonic(); return results

def probe(vm):
    out=dict(vm,ssh_status='unknown',server_status='unknown',detail='',checked=time.strftime('%H:%M:%S'))
    if not shutil.which('ssh'):
        out['detail']='Cliente OpenSSH não encontrado'; return out
    # Detecta processos remotos, não confirma uma sessão de editor ativa.
    command="printf 'SOTC_HOST '; hostname; printf 'SOTC_UP '; cut -d. -f1 /proc/uptime; printf 'SOTC_CORES '; getconf _NPROCESSORS_ONLN; printf 'SOTC_CPU '; awk '/^cpu / {print $2+$3+$4+$5+$6+$7+$8, $5+$6}' /proc/stat; sleep 1; printf 'SOTC_CPU '; awk '/^cpu / {print $2+$3+$4+$5+$6+$7+$8, $5+$6}' /proc/stat; printf 'SOTC_RAM '; free -m | awk '/^Mem:/ {print $3, $2}'; printf 'SOTC_DISK '; df -P / | awk 'NR==2 {print $5}'; printf 'SOTC_LOAD '; cat /proc/loadavg; ps -eo args | grep -E '[.]vscode-server|[.]vscode-remote|[.]vscode-server-insiders' >/dev/null && echo SOTC_SERVER_PRESENT || echo SOTC_SERVER_NOT_DETECTED"
    try:
        p=subprocess.run(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','-o','ConnectionAttempts=1','-o','ClearAllForwardings=yes','-o','RequestTTY=no',vm['ssh'],command],capture_output=True,text=True,timeout=12)
        if p.returncode==0:
            out['ssh_status']='ok'
            cpu=[]
            for line in p.stdout.splitlines():
                if line.startswith('SOTC_CPU '):
                    try: cpu.append(tuple(map(float,line.split()[1:3])))
                    except ValueError: pass
                for key,field in [('HOST','hostname'),('UP','uptime'),('CORES','cores')]:
                    if line.startswith('SOTC_'+key+' '): out[field]=line.split(' ',1)[1]

                if line.startswith('SOTC_RAM '):
                    try:
                        used,total=map(int,line.split()[1:3]); out['ram_pct']=round(100*used/total,1)
                    except (ValueError,ZeroDivisionError): pass
                elif line.startswith('SOTC_DISK '): out['disk_pct']=line.split()[-1]
                elif line.startswith('SOTC_LOAD '): out['load']=line.split()[1] if len(line.split())>1 else None
            if 'SOTC_SERVER_PRESENT' in p.stdout.splitlines(): out['server_status']='present'
            elif 'SOTC_SERVER_NOT_DETECTED' in p.stdout.splitlines(): out['server_status']='not_detected'
            if len(cpu)==2 and cpu[1][0]>cpu[0][0]: out['cpu_pct']=round(max(0,min(100,100*(1-(cpu[1][1]-cpu[0][1])/(cpu[1][0]-cpu[0][0])))),1)
            out['detail']='Sessão ativa do editor não verificada'
        else:
            out['ssh_status']='failed'; out['detail']='SSH não confirmado: '+(p.stderr.strip().splitlines()[-1][:180] if p.stderr.strip() else 'falha no comando remoto')
    except (subprocess.TimeoutExpired,OSError) as e:
        out['ssh_status']='failed'; out['detail']='Tempo limite ou erro ao executar SSH'
    return out

class Handler(BaseHTTPRequestHandler):
    def send_data(self, data, kind='application/json',status=200):
        self.send_response(status); self.send_header('Content-Type',kind); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self'; frame-ancestors 'none'"); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        if self.path not in ('/api/inventory','/api/guardian','/api/reaper','/api/devcentral/health') or self.headers.get('Host') not in ('127.0.0.1:8765','localhost:8765') or self.headers.get('Origin') not in ('http://127.0.0.1:8765','http://localhost:8765') or self.headers.get('Content-Type') != 'application/json':
            self.send_error(403); return
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<4096: raise ValueError('Tamanho inválido')
            item=json.loads(self.rfile.read(n))
            if self.path == '/api/devcentral/health':
                self.send_data(json.dumps(devcentral_bridge.check_http_health(item.get('url','')),ensure_ascii=False).encode()); return
            if self.path in ('/api/guardian','/api/reaper'):
                vm=next((v for v in inventory() if v['ssh']==item.get('ssh')),None)
                if vm is None: raise ValueError('VM não cadastrada')
                if self.path == '/api/reaper':
                    try:
                        result=reaper.execute(vm,item)
                    except (ValueError,OSError,subprocess.TimeoutExpired) as e:
                        guardian.audit(vm['ssh'],'reaper:'+str(item.get('action'))[:60],{'ok':False})
                        raise
                    guardian.audit(vm['ssh'],'reaper:'+str(item.get('action'))[:60],result)
                else: result=guardian.execute(vm,item)
                self.send_data(json.dumps(result,ensure_ascii=False).encode()); return
            alias=item['ssh']; cloud=item['cloud']
            if alias not in aliases() or cloud not in ('Google Cloud','AWS','Azure','Oracle Cloud'): raise ValueError('Selecione um alias e uma cloud válidos')
            global CACHE
            with LOCK:
                rows=inventory()
                if any(v['ssh']==alias for v in rows): raise ValueError('Alias já cadastrado')
                rows.append(dict(name=alias,ssh=alias,cloud=cloud,folder='/'))
                tmp=ROOT/'vms.tmp'; tmp.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(ROOT/'vms.json'); CACHE=None
            self.send_data(b'{"ok":true}')
        except (ValueError,KeyError,TypeError,OSError,subprocess.TimeoutExpired) as e: self.send_data(json.dumps({'error':str(e)}).encode(),status=400)
    def do_GET(self):
        if self.headers.get('Host','') not in ('127.0.0.1:8765','localhost:8765'):
            self.send_error(403); return
        path=urlparse(self.path).path
        try:
            if path=='/': self.send_data((ROOT/'index.html').read_bytes(),'text/html; charset=utf-8')
            elif path=='/gothic.css': self.send_data((ROOT/'gothic.css').read_bytes(),'text/css; charset=utf-8')
            elif path=='/background.jpg': self.send_data((ROOT/'background.jpg').read_bytes(),'image/jpeg')
            elif path=='/logo.png': self.send_data((ROOT/'logo.png').read_bytes(),'image/png')
            elif path=='/api/guardian/events': self.send_data(json.dumps(guardian.events()).encode())
            elif path=='/api/devcentral': self.send_data(json.dumps(devcentral_bridge.fetch_overview(),ensure_ascii=False).encode())
            elif path=='/api/history': self.send_data(json.dumps(history(),ensure_ascii=False).encode())
            elif path=='/api/aliases': self.send_data(json.dumps(aliases()).encode())
            elif path=='/api/status':
                results=status()
                self.send_data(json.dumps(results,ensure_ascii=False).encode())
            else: self.send_error(404)
        except Exception as e: self.send_data(json.dumps({'error':str(e)}).encode(),status=500)

if __name__=='__main__':
    print('Sing Of The Cross: http://127.0.0.1:8765')
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
