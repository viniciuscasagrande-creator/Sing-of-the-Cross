import sqlite3, datetime, json, re, shutil, subprocess, concurrent.futures, time, os, threading, sys
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent
BACKEND_DIR=ROOT/'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
from discovery import aliases
import guardian
import reaper
import oracle
import devcentral_bridge

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
DB=ROOT/'database'/'history.sqlite3'
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
    out=dict(vm,ssh_status='unknown',server_status='unknown',detail='',checked=time.strftime('%H:%M:%S'),checked_epoch=int(time.time()))
    if not shutil.which('ssh'):
        out['detail']='Cliente OpenSSH não encontrado'; return out
    # Detecta processos remotos e mede latência SSH (descontando o sleep 1 da amostragem de CPU).
    command="printf 'SOTC_HOST '; hostname; printf 'SOTC_UP '; cut -d. -f1 /proc/uptime; printf 'SOTC_CORES '; getconf _NPROCESSORS_ONLN; printf 'SOTC_CPU '; awk '/^cpu / {print $2+$3+$4+$5+$6+$7+$8, $5+$6}' /proc/stat; sleep 1; printf 'SOTC_CPU '; awk '/^cpu / {print $2+$3+$4+$5+$6+$7+$8, $5+$6}' /proc/stat; printf 'SOTC_RAM '; free -m | awk '/^Mem:/ {print $3, $2}'; printf 'SOTC_SWAP '; free -m | awk '/^Swap:/ {print $3, $2}'; printf 'SOTC_DISK '; df -P / | awk 'NR==2 {print $5, $3, $2}'; printf 'SOTC_LOAD '; cat /proc/loadavg; printf 'SOTC_NET '; awk '/:/ && $1!~\"lo:\" {rx+=$2; tx+=$10} END {print rx+0, tx+0}' /proc/net/dev; printf 'SOTC_PROCS '; ps -e --no-headers | wc -l; ps -eo args | grep -E '[.]vscode-server|[.]vscode-remote|[.]vscode-server-insiders' >/dev/null && echo SOTC_SERVER_PRESENT || echo SOTC_SERVER_NOT_DETECTED"
    t0=time.monotonic()
    try:
        p=subprocess.run(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','-o','ConnectionAttempts=1','-o','ClearAllForwardings=yes','-o','RequestTTY=no',vm['ssh'],command],capture_output=True,text=True,timeout=12)
        elapsed_ms=max(1,round((time.monotonic()-t0-1.0)*1000))
        if p.returncode==0:
            out['ssh_status']='ok'
            out['latency_ms']=elapsed_ms
            cpu=[]
            for line in p.stdout.splitlines():
                if line.startswith('SOTC_CPU '):
                    try: cpu.append(tuple(map(float,line.split()[1:3])))
                    except ValueError: pass
                for key,field in [('HOST','hostname'),('UP','uptime'),('CORES','cores'),('PROCS','proc_count')]:
                    if line.startswith('SOTC_'+key+' '): out[field]=line.split(' ',1)[1].strip()

                if line.startswith('SOTC_RAM '):
                    try:
                        used,total=map(int,line.split()[1:3]); out['ram_pct']=round(100*used/total,1); out['ram_used_mb']=used; out['ram_total_mb']=total
                    except (ValueError,ZeroDivisionError): pass
                elif line.startswith('SOTC_SWAP '):
                    try:
                        s_used,s_total=map(int,line.split()[1:3]); out['swap_pct']=round(100*s_used/s_total,1) if s_total>0 else 0.0; out['swap_used_mb']=s_used; out['swap_total_mb']=s_total
                    except (ValueError,ZeroDivisionError): pass
                elif line.startswith('SOTC_DISK '):
                    parts=line.split()
                    if len(parts)>=2: out['disk_pct']=parts[1]
                    if len(parts)>=4:
                        try:
                            out['disk_used_gb']=round(int(parts[2])/1048576,2)
                            out['disk_total_gb']=round(int(parts[3])/1048576,2)
                        except ValueError: pass
                elif line.startswith('SOTC_LOAD '):
                    lparts=line.split()
                    if len(lparts)>=4:
                        out['load1']=lparts[1]; out['load5']=lparts[2]; out['load15']=lparts[3]; out['load']=lparts[1]
                elif line.startswith('SOTC_NET '):
                    try:
                        rx_b,tx_b=map(int,line.split()[1:3]); out['net_rx_mb']=round(rx_b/1048576,1); out['net_tx_mb']=round(tx_b/1048576,1)
                    except ValueError: pass
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
        if self.path not in ('/api/inventory','/api/guardian','/api/reaper','/api/abyss','/api/devcentral/health','/api/sentinel/run') or self.headers.get('Host') not in ('127.0.0.1:8765','localhost:8765') or self.headers.get('Origin') not in ('http://127.0.0.1:8765','http://localhost:8765') or self.headers.get('Content-Type') != 'application/json':
            self.send_error(403); return
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<=n<8192: raise ValueError('Tamanho inválido')
            item=json.loads(self.rfile.read(n)) if n>0 else {}
            if self.path == '/api/sentinel/run':
                from agent import sentinel
                self.send_data(json.dumps(sentinel.run_cycle(),ensure_ascii=False).encode()); return
            if self.path == '/api/devcentral/health':
                self.send_data(json.dumps(devcentral_bridge.check_http_health(item.get('url','')),ensure_ascii=False).encode()); return
            if self.path in ('/api/guardian','/api/reaper','/api/abyss'):
                vm=next((v for v in inventory() if v['ssh']==item.get('ssh')),None)
                if vm is None: raise ValueError('VM não cadastrada')
                if self.path == '/api/abyss':
                    result=oracle.execute_abyss(vm,item)
                elif self.path == '/api/reaper':
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
            if path=='/': self.send_data((ROOT/'frontend'/'index.html').read_bytes(),'text/html; charset=utf-8')
            elif path=='/gothic.css': self.send_data((ROOT/'frontend'/'gothic.css').read_bytes(),'text/css; charset=utf-8')
            elif path=='/background.jpg': self.send_data((ROOT/'frontend'/'assets'/'background.jpg').read_bytes(),'image/jpeg')
            elif path=='/logo.png': self.send_data((ROOT/'frontend'/'assets'/'logo.png').read_bytes(),'image/png')
            elif path=='/sotc.ico': self.send_data((ROOT/'frontend'/'assets'/'sotc.ico').read_bytes(),'image/x-icon')
            elif path in ('/SingOfTheCross.apk','/SOTC-Monitor-v1.0.0.apk'):
                apk_f = ROOT/'frontend'/'assets'/'SOTC-Monitor-v1.0.0.apk'
                if not apk_f.exists(): apk_f = ROOT/'frontend'/'assets'/'SingOfTheCross.apk'
                self.send_data(apk_f.read_bytes(),'application/vnd.android.package-archive')
            elif path=='/api/guardian/events': self.send_data(json.dumps(guardian.events()).encode())
            elif path=='/api/devcentral': self.send_data(json.dumps(devcentral_bridge.fetch_overview(),ensure_ascii=False).encode())
            elif path in ('/api/sentinel/heartbeat','/api/sentinel/alerts','/api/sentinel/telemetry'):
                self.send_data(json.dumps(devcentral_bridge.fetch_sentinel_status(),ensure_ascii=False).encode())
            elif path=='/api/oracle':
                self.send_data(json.dumps(oracle.analyze_infrastructure(status()),ensure_ascii=False).encode())
            elif path=='/api/command-center':
                vms_st = status()
                try: dc_ov = devcentral_bridge.fetch_overview()
                except Exception: dc_ov = {}
                try: sent_st = devcentral_bridge.fetch_sentinel_status()
                except Exception: sent_st = {}
                suite = oracle.build_command_center_suite(vms_st, dc_ov, sent_st, guardian.events())
                self.send_data(json.dumps(suite,ensure_ascii=False).encode())
            elif path=='/api/history': self.send_data(json.dumps(history(),ensure_ascii=False).encode())
            elif path=='/api/aliases': self.send_data(json.dumps(aliases()).encode())
            elif path=='/api/status':
                results=status()
                self.send_data(json.dumps(results,ensure_ascii=False).encode())
            else: self.send_error(404)
        except Exception as e: self.send_data(json.dumps({'error':str(e)}).encode(),status=500)

def _background_collector_worker():
    """Worker independente do navegador: coleta telemetria e sincroniza com SQLite + Neon a cada 30s."""
    while True:
        try:
            status()
        except Exception:
            pass
        time.sleep(30)

if __name__=='__main__':
    threading.Thread(target=_background_collector_worker, daemon=True).start()
    print('Sing Of The Cross V1.0 Multi-Cloud Command Center (Worker 24/7 Ativo): http://127.0.0.1:8765')
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
