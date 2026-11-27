import subprocess, shutil, os, re, json, sqlite3, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def run(args, timeout=25):
    exe=shutil.which(args[0])
    if not exe: raise ValueError('CLI não instalado: '+args[0])
    # Windows CLI launchers may be .cmd; only validated identifiers are passed.
    p=subprocess.run([exe,*args[1:]],capture_output=True,text=True,errors='replace',timeout=timeout,stdin=subprocess.DEVNULL)
    return {'ok':p.returncode==0,'output':(p.stdout+'\n'+p.stderr).strip()[:16000],'code':p.returncode}

def field(vm,key,pattern=r'[A-Za-z0-9][A-Za-z0-9_.-]*'):
    v=vm.get(key,'')
    if not isinstance(v,str) or not re.fullmatch(pattern,v): raise ValueError('Configure '+key+' em vms.json')
    return v

def cloud_args(vm, action):
    c=vm['cloud']; name=field(vm,'name')
    if c=='Google Cloud':
        return ['gcloud','compute','instances','describe',name,'--project='+field(vm,'project'),'--zone='+field(vm,'zone'),'--format=value(status)','--quiet']
    if c=='AWS':
        return ['aws','ec2','describe-instances','--instance-ids',field(vm,'instance_id',r'i-[0-9a-f]+'),'--region',field(vm,'region'),'--query','Reservations[].Instances[].State.Name','--output','text','--no-cli-pager']
    if c=='Azure':
        return ['az','vm','get-instance-view','--name',name,'--resource-group',field(vm,'resource_group'),'--subscription',field(vm,'subscription'),'--query','instanceView.statuses[].code','--output','tsv']
    if c=='Oracle Cloud':
        return ['oci','compute','instance','get','--instance-id',field(vm,'instance_id',r'ocid1\.instance\.[A-Za-z0-9_.-]+'),'--region',field(vm,'region'),'--query','data."lifecycle-state"','--raw-output']
    raise ValueError('Cloud não suportada')

DIAG={'processes':'ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -26','services':'systemctl list-units --type=service --state=running --no-pager --plain','network':'ip -s link; ss -s','storage':'df -hT; lsblk','logs':'journalctl -n 60 --no-pager -p warning','system':'uname -a; uptime; free -h'}
_LAST_ACTION_TS = {}

def check_rate_limit(key, cooldown_sec=10):
    now = time.monotonic()
    last = _LAST_ACTION_TS.get(key, 0)
    if now - last < cooldown_sec:
        rem = round(cooldown_sec - (now - last), 1)
        raise ValueError(f'Proteção anti-repetição (Cooldown RBAC): aguarde {rem}s antes de repetir esta operação crítica.')
    _LAST_ACTION_TS[key] = now

def ssh(vm,cmd):
    return run(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','-o','ClearAllForwardings=yes','-o','RequestTTY=no',field(vm,'ssh'),cmd])

def audit(alias,action,result):
    with sqlite3.connect(ROOT/'history.sqlite3') as db:
        db.execute('CREATE TABLE IF NOT EXISTS interventions(ts INTEGER, alias TEXT, action TEXT, ok INTEGER)')
        db.execute('INSERT INTO interventions VALUES(?,?,?,?)',(int(time.time()),alias,action,int(result['ok'])))
    try:
        import devcentral_bridge
        devcentral_bridge.push_audit_to_neon(alias,action,bool(result['ok']))
    except Exception:
        pass

def execute(vm,item):
    action=item.get('action'); alias=field(vm,'ssh')
    if action=='cloud': result=run(cloud_args(vm,action))
    elif action in DIAG: result=ssh(vm,DIAG[action])
    elif action=='restart_service':
        service=item.get('service','')
        if not isinstance(service,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@-]{0,100}\.service',service): raise ValueError('Informe unidade systemd terminada em .service')
        if item.get('confirm')!=alias+' '+service: raise ValueError('Confirmação incorreta')
        check_rate_limit(f'{alias}:restart:{service}', cooldown_sec=12)
        result=ssh(vm,'sudo -n systemctl restart -- '+service+' && systemctl is-active -- '+service)
    else: raise ValueError('Ação desconhecida')
    audit(alias,action,result); return result

def events():
    with sqlite3.connect(ROOT/'history.sqlite3') as db:
        db.execute('CREATE TABLE IF NOT EXISTS interventions(ts INTEGER, alias TEXT, action TEXT, ok INTEGER)')
        return [dict(ts=t,alias=a,action=b,ok=bool(c)) for t,a,b,c in db.execute('SELECT * FROM interventions ORDER BY rowid DESC LIMIT 100')]
