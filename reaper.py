"""Controlled operations, no arbitrary remote shell from HTTP."""
import os, shutil, subprocess
import guardian

DIAG = {
    'identity': 'id; hostname; pwd',
    'process_tree': 'ps -eo pid,ppid,user,stat,comm,%cpu,%mem --sort=-%cpu | head -41',
    'listeners': 'ss -lntu',
    'memory': 'free -h; cat /proc/swaps',
    'failed_services': 'systemctl --failed --no-pager',
    'filesystems': 'df -hT; df -i',
    'sessions': 'who; w',
}

def power_args(vm, action):
    f=lambda k,p=r'[A-Za-z0-9][A-Za-z0-9_.-]*': guardian.field(vm,k,p)
    c=vm['cloud']
    if action not in ('start','stop','reboot'): raise ValueError('Ação inválida')
    if c=='Google Cloud':
        verb={'start':'start','stop':'stop','reboot':'reset'}[action]
        return ['gcloud','compute','instances',verb,f('name'),'--project='+f('project'),'--zone='+f('zone'),'--quiet']
    if c=='AWS':
        return ['aws','ec2',action+'-instances','--instance-ids',f('instance_id',r'i-[0-9a-f]+'),'--region',f('region'),'--no-cli-pager']
    if c=='Azure':
        return ['az','vm',{'start':'start','stop':'deallocate','reboot':'restart'}[action],'--name',f('name'),'--resource-group',f('resource_group'),'--subscription',f('subscription')]
    if c=='Oracle Cloud':
        return ['oci','compute','instance','action','--instance-id',f('instance_id',r'ocid1\.instance\.[A-Za-z0-9_.-]+'),'--region',f('region'),'--action',{'start':'START','stop':'SOFTSTOP','reboot':'SOFTRESET'}[action]]
    raise ValueError('Cloud inválida')

def execute(vm,item):
    action=item.get('action'); alias=guardian.field(vm,'ssh')
    if action in DIAG: return guardian.ssh(vm,DIAG[action])
    if action=='terminal':
        if os.name!='nt': raise ValueError('Terminal externo disponível no Windows')
        exe=shutil.which('ssh.exe')
        if not exe: raise ValueError('OpenSSH não encontrado')
        subprocess.Popen([exe,'-o','StrictHostKeyChecking=yes','-o','ClearAllForwardings=yes',alias],creationflags=subprocess.CREATE_NEW_CONSOLE)
        return {'ok':True,'output':'Terminal local solicitado. Autentique-se na janela aberta; conexão não confirmada.'}
    if action in ('start','stop','reboot'):
        if vm.get('allow_power') is not True: raise ValueError('Energia bloqueada: habilite allow_power no inventário local após revisar a VM.')
        if item.get('confirm')!=alias+' '+action: raise ValueError('Confirmação incorreta')
        return guardian.run(power_args(vm,action),timeout=90)
    raise ValueError('Operação desconhecida')
