const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFile, exec } = require('child_process');

const PORT = process.env.PORT || 8501;
const CONFIG_PATH = path.join(__dirname, 'vms.json');
const PUBLIC_DIR = path.join(__dirname, 'public');

function loadConfig() {
  try {
    if (!fs.existsSync(CONFIG_PATH)) {
      return { refreshIntervalSeconds: 10, sshTimeoutSeconds: 4, autoDiscoverSshConfig: true, vms: [] };
    }
    return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  } catch (err) {
    console.error('Erro ao ler vms.json:', err.message);
    return { refreshIntervalSeconds: 10, sshTimeoutSeconds: 4, autoDiscoverSshConfig: true, vms: [] };
  }
}

function saveConfig(cfg) {
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2), 'utf8');
}

function execPromise(cmd, args, timeoutMs = 6000) {
  return new Promise((resolve) => {
    execFile(cmd, args, { timeout: timeoutMs, windowsHide: true }, (error, stdout, stderr) => {
      resolve({
        ok: !error,
        stdout: (stdout || '').toString().trim(),
        stderr: (stderr || '').toString().trim(),
        error: error ? error.message : null
      });
    });
  });
}

function execShellPromise(commandLine, timeoutMs = 8000) {
  return new Promise((resolve) => {
    exec(commandLine, { timeout: timeoutMs, windowsHide: true }, (error, stdout, stderr) => {
      resolve({
        ok: !error,
        stdout: (stdout || '').toString().trim(),
        stderr: (stderr || '').toString().trim(),
        error: error ? error.message : null
      });
    });
  });
}

// Lê ~/.ssh/config para importar hosts automaticamente
function parseSshConfig() {
  const sshConfigFile = path.join(os.homedir(), '.ssh', 'config');
  if (!fs.existsSync(sshConfigFile)) return [];
  try {
    const content = fs.readFileSync(sshConfigFile, 'utf8');
    const lines = content.split(/\r?\n/);
    const hosts = [];
    let current = null;

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line || line.startsWith('#')) continue;
      const match = line.match(/^(\S+)\s+(.+)$/);
      if (!match) continue;
      const key = match[1].toLowerCase();
      const val = match[2].trim().replace(/^"|"$/g, '');

      if (key === 'host') {
        if (current && current.alias && !current.alias.includes('*')) {
          hosts.push(current);
        }
        current = { alias: val, host: val, user: 'root', port: 22, identityFile: '' };
      } else if (current) {
        if (key === 'hostname') current.host = val;
        if (key === 'user') current.user = val;
        if (key === 'port') current.port = parseInt(val, 10) || 22;
        if (key === 'identityfile') current.identityFile = val;
      }
    }
    if (current && current.alias && !current.alias.includes('*')) {
      hosts.push(current);
    }
    return hosts;
  } catch (e) {
    return [];
  }
}

// Comando remoto único via SSH para coletar CPU, RAM, Disco, Uptime e sessões ativas reais do VS Code
const REMOTE_PROBE_SCRIPT = [
  'export LC_ALL=C;',
  'CPU=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk \'{print 100 - $8}\' | cut -d. -f1);',
  'if [ -z "$CPU" ]; then CPU=$(ps -A -o %cpu 2>/dev/null | awk \'{s+=$1} END {print int(s)}\'); fi;',
  'RAM=$(free -m 2>/dev/null | awk \'/Mem:/ { printf("%d", ($3/$2)*100) }\');',
  'DISK=$(df -h / 2>/dev/null | awk \'NR==2 {gsub("%","",$5); print $5}\');',
  'UPTIME=$(uptime -p 2>/dev/null | sed "s/up //");',
  'OS=$(grep -E "^PRETTY_NAME=" /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d \'"\');',
  // Diferenciação importante:
  // 1) SERVER_PROC: processo vscode-server / code-server / tunnel rodando em background
  // 2) ACTIVE_SESSIONS: conexões ativas reais de cliente VS Code (extensionHost ativo ou socket/conexão SSH/tunnel ativa para o vscode-server)
  'SERVER_PROC=$(ps aux 2>/dev/null | grep -E "\\.vscode-server|\\.antigravity-server|code-server|code tunnel|code-tunnel" | grep -v grep | wc -l);',
  'EXT_HOST=$(ps aux 2>/dev/null | grep -E "(vscode-server|antigravity-server).*extensionHost|node.*bootstrap-fork.*--type=extensionHost" | grep -v grep | wc -l);',
  'TUNNEL_CONN=$(ps aux 2>/dev/null | grep -E "code-tunnel|code tunnel" | grep -v grep | wc -l);',
  'echo "CPU=${CPU:-0}|RAM=${RAM:-0}|DISK=${DISK:-0}|UPTIME=${UPTIME:-Online}|OS=${OS:-Linux}|SERVER_PROC=${SERVER_PROC:-0}|EXT_HOST=${EXT_HOST:-0}|TUNNEL_CONN=${TUNNEL_CONN:-0}"'
].join(' ');

async function probeVmViaSsh(vm, timeoutSec = 4) {
  const args = [
    '-o', 'BatchMode=yes',
    '-o', `ConnectTimeout=${timeoutSec}`,
    '-o', 'StrictHostKeyChecking=accept-new'
  ];

  if (vm.port && Number(vm.port) !== 22) {
    args.push('-p', String(vm.port));
  }
  if (vm.identityFile && vm.identityFile.trim() !== '') {
    const resolvedKey = vm.identityFile.replace(/^~/, os.homedir());
    args.push('-i', resolvedKey);
  }

  const target = vm.user ? `${vm.user}@${vm.host}` : vm.host;
  args.push(target, REMOTE_PROBE_SCRIPT);

  const res = await execPromise('ssh', args, (timeoutSec + 2) * 1000);
  if (!res.ok) {
    return {
      vmOnline: false,
      vscodeConnected: false,
      vscodeServerRunning: false,
      activeSessions: 0,
      cpu: 0,
      ram: 0,
      disk: 0,
      uptime: 'Offline',
      os: vm.os || 'Inacessível via SSH',
      error: res.stderr || res.error || 'Falha na conexão SSH',
      checkedAt: new Date().toISOString()
    };
  }

  const map = {};
  const line = res.stdout.split(/\r?\n/).find(l => l.includes('CPU=')) || '';
  line.split('|').forEach(pair => {
    const idx = pair.indexOf('=');
    if (idx > -1) {
      const k = pair.slice(0, idx).trim();
      const v = pair.slice(idx + 1).trim();
      map[k] = v;
    }
  });

  const cpu = Math.min(100, Math.max(0, parseInt(map.CPU, 10) || 0));
  const ram = Math.min(100, Math.max(0, parseInt(map.RAM, 10) || 0));
  const disk = Math.min(100, Math.max(0, parseInt(map.DISK, 10) || 0));
  const serverProc = parseInt(map.SERVER_PROC, 10) || 0;
  const extHost = parseInt(map.EXT_HOST, 10) || 0;

  // Sessão ativa do VS Code exige um extensionHost ativo na máquina remota
  const vscodeConnected = extHost > 0;
  const vscodeServerRunning = serverProc > 0;

  return {
    vmOnline: true,
    vscodeConnected,
    vscodeServerRunning,
    activeSessions: extHost,
    cpu,
    ram,
    disk,
    uptime: map.UPTIME || 'Online',
    os: map.OS || 'Linux',
    error: null,
    checkedAt: new Date().toISOString()
  };
}

function getDemoStatus(vm) {
  const st = vm.demoState || {};
  // Adiciona uma leve variação realista de +/- 2% na CPU em modo demonstração para mostrar o live refresh
  let cpu = st.cpu || 0;
  if (st.vmOnline) {
    const jitter = Math.floor(Math.random() * 5) - 2;
    cpu = Math.min(100, Math.max(1, cpu + jitter));
  }
  return {
    vmOnline: Boolean(st.vmOnline),
    vscodeConnected: Boolean(st.vscodeConnected),
    vscodeServerRunning: st.vscodeServerRunning !== undefined ? Boolean(st.vscodeServerRunning) : Boolean(st.vscodeConnected),
    activeSessions: st.activeSessions !== undefined ? st.activeSessions : (st.vscodeConnected ? 1 : 0),
    cpu,
    ram: st.ram || 0,
    disk: st.disk || 0,
    uptime: st.uptime || (st.vmOnline ? 'Online' : 'Offline'),
    os: st.os || 'Linux VM',
    error: null,
    checkedAt: new Date().toISOString()
  };
}

async function getAllVmStatuses() {
  const cfg = loadConfig();
  const timeoutSec = cfg.sshTimeoutSeconds || 4;

  const results = await Promise.all(
    (cfg.vms || []).map(async (vm) => {
      const status = vm.demoMode ? getDemoStatus(vm) : await probeVmViaSsh(vm, timeoutSec);
      // Determina o indicador semafórico:
      // green: VM ligada e VS Code conectado
      // yellow: VM ligada, mas VS Code desconectado
      // red: VM desligada ou inacessível
      let indicator = 'red';
      let indicatorLabel = 'Offline / Inacessível';
      if (status.vmOnline && status.vscodeConnected) {
        indicator = 'green';
        indicatorLabel = 'Online • VS Code Conectado';
      } else if (status.vmOnline && !status.vscodeConnected) {
        indicator = 'yellow';
        indicatorLabel = status.vscodeServerRunning
          ? 'Online • VS Code Desconectado (Server em espera)'
          : 'Online • VS Code Desconectado';
      }

      return {
        ...vm,
        status: {
          ...status,
          indicator,
          indicatorLabel
        }
      };
    })
  );

  const summary = {
    total: results.length,
    online: results.filter(r => r.status.vmOnline).length,
    connected: results.filter(r => r.status.vmOnline && r.status.vscodeConnected).length,
    disconnected: results.filter(r => !r.status.vscodeConnected).length,
    standby: results.filter(r => r.status.vmOnline && !r.status.vscodeConnected).length,
    offline: results.filter(r => !r.status.vmOnline).length,
    refreshIntervalSeconds: cfg.refreshIntervalSeconds || 10,
    timestamp: new Date().toISOString()
  };

  return { summary, vms: results };
}

// Descoberta via CLIs das clouds instaladas (GCP, AWS, Azure, OCI) e ~/.ssh/config
async function discoverCloudAndSshVms() {
  const discovered = [];

  // 1. ~/.ssh/config
  const sshHosts = parseSshConfig();
  for (const h of sshHosts) {
    discovered.push({
      name: h.alias,
      host: h.host,
      user: h.user,
      port: h.port,
      provider: 'ssh',
      connectionType: 'ssh',
      identityFile: h.identityFile,
      source: '~/.ssh/config'
    });
  }

  // 2. Google Cloud (gcloud)
  const gcpRes = await execShellPromise('gcloud compute instances list --format=json', 7000);
  if (gcpRes.ok && gcpRes.stdout.startsWith('[')) {
    try {
      const gcpList = JSON.parse(gcpRes.stdout);
      for (const inst of gcpList) {
        const net = (inst.networkInterfaces && inst.networkInterfaces[0]) || {};
        const extIp = (net.accessConfigs && net.accessConfigs[0] && net.accessConfigs[0].natIP) || net.networkIP || inst.name;
        discovered.push({
          name: inst.name,
          host: extIp,
          user: os.userInfo().username || 'ubuntu',
          port: 22,
          provider: 'gcp',
          connectionType: 'ssh',
          source: `GCP (${inst.status})`
        });
      }
    } catch (e) {}
  }

  // 3. AWS CLI
  const awsRes = await execShellPromise('aws ec2 describe-instances --output json', 7000);
  if (awsRes.ok && awsRes.stdout.startsWith('{')) {
    try {
      const awsData = JSON.parse(awsRes.stdout);
      for (const r of (awsData.Reservations || [])) {
        for (const inst of (r.Instances || [])) {
          const nameTag = (inst.Tags || []).find(t => t.Key === 'Name');
          discovered.push({
            name: (nameTag && nameTag.Value) || inst.InstanceId,
            host: inst.PublicIpAddress || inst.PrivateIpAddress || inst.InstanceId,
            user: 'ubuntu',
            port: 22,
            provider: 'aws',
            connectionType: 'ssh',
            source: `AWS (${inst.State && inst.State.Name})`
          });
        }
      }
    } catch (e) {}
  }

  // 4. Azure CLI
  const azRes = await execShellPromise('az vm list -d -o json', 7000);
  if (azRes.ok && azRes.stdout.startsWith('[')) {
    try {
      const azList = JSON.parse(azRes.stdout);
      for (const vm of azList) {
        discovered.push({
          name: vm.name,
          host: vm.publicIps || vm.privateIps || vm.name,
          user: 'azureuser',
          port: 22,
          provider: 'azure',
          connectionType: 'ssh',
          source: `Azure (${vm.powerState})`
        });
      }
    } catch (e) {}
  }

  return discovered;
}

function buildVsCodeUri(vm) {
  const wsPath = (vm.workspacePath || `/home/${vm.user || 'ubuntu'}`).replace(/^\/+/, '');
  if (vm.connectionType === 'tunnel' && vm.tunnelName) {
    return `vscode://vscode-remote/tunnel+${vm.tunnelName}/${wsPath}`;
  }
  const target = vm.user ? `${vm.user}@${vm.host}` : vm.host;
  return `vscode://vscode-remote/ssh-remote+${target}/${wsPath}`;
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        reject(e);
      }
    });
    req.on('error', reject);
  });
}

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store'
  });
  res.end(JSON.stringify(payload));
}

const server = http.createServer(async (req, res) => {
  const parsedUrl = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const pathname = parsedUrl.pathname;

  // API: Obter status de todas as VMs
  if (pathname === '/api/status' && req.method === 'GET') {
    const data = await getAllVmStatuses();
    return sendJson(res, 200, data);
  }

  // API: Adicionar ou atualizar VM
  if (pathname === '/api/vms' && req.method === 'POST') {
    try {
      const body = await readJsonBody(req);
      const cfg = loadConfig();
      const id = body.id || `vm-${Date.now()}`;
      const newVm = {
        id,
        name: body.name || 'Nova-VM',
        host: body.host || '127.0.0.1',
        user: body.user || 'ubuntu',
        port: parseInt(body.port, 10) || 22,
        provider: body.provider || 'ssh',
        connectionType: body.connectionType || 'ssh',
        tunnelName: body.tunnelName || '',
        workspacePath: body.workspacePath || `/home/${body.user || 'ubuntu'}`,
        identityFile: body.identityFile || '',
        demoMode: Boolean(body.demoMode),
        demoState: body.demoState || {
          vmOnline: true,
          vscodeConnected: false,
          vscodeServerRunning: false,
          activeSessions: 0,
          cpu: 12,
          ram: 28,
          disk: 40,
          uptime: '1d 02h 15m',
          os: 'Ubuntu 24.04 LTS'
        }
      };

      const existingIdx = cfg.vms.findIndex(v => v.id === id);
      if (existingIdx >= 0) {
        cfg.vms[existingIdx] = { ...cfg.vms[existingIdx], ...newVm };
      } else {
        cfg.vms.push(newVm);
      }
      saveConfig(cfg);
      return sendJson(res, 200, { ok: true, vm: newVm });
    } catch (e) {
      return sendJson(res, 400, { ok: false, error: e.message });
    }
  }

  // API: Alternar modo Demo / Simular conexão VS Code ou estado Online
  if (pathname === '/api/vms/toggle-demo-state' && req.method === 'POST') {
    try {
      const body = await readJsonBody(req);
      const cfg = loadConfig();
      const vm = cfg.vms.find(v => v.id === body.id);
      if (!vm) return sendJson(res, 404, { ok: false, error: 'VM não encontrada' });

      if (body.field === 'demoMode') {
        vm.demoMode = !vm.demoMode;
      } else if (vm.demoState) {
        if (body.field === 'vmOnline') {
          vm.demoState.vmOnline = !vm.demoState.vmOnline;
          if (!vm.demoState.vmOnline) {
            vm.demoState.vscodeConnected = false;
            vm.demoState.activeSessions = 0;
            vm.demoState.cpu = 0;
            vm.demoState.ram = 0;
            vm.demoState.uptime = 'Offline';
          } else {
            vm.demoState.cpu = 18;
            vm.demoState.ram = 35;
            vm.demoState.uptime = '0d 01h 12m';
          }
        } else if (body.field === 'vscodeConnected') {
          if (vm.demoState.vmOnline) {
            vm.demoState.vscodeConnected = !vm.demoState.vscodeConnected;
            vm.demoState.activeSessions = vm.demoState.vscodeConnected ? 1 : 0;
          }
        }
      }
      saveConfig(cfg);
      return sendJson(res, 200, { ok: true, vm });
    } catch (e) {
      return sendJson(res, 400, { ok: false, error: e.message });
    }
  }

  // API: Remover VM
  if (pathname === '/api/vms/delete' && req.method === 'POST') {
    try {
      const body = await readJsonBody(req);
      const cfg = loadConfig();
      cfg.vms = (cfg.vms || []).filter(v => v.id !== body.id);
      saveConfig(cfg);
      return sendJson(res, 200, { ok: true });
    } catch (e) {
      return sendJson(res, 400, { ok: false, error: e.message });
    }
  }

  // API: Abrir VM diretamente no VS Code via CLI (`code --remote`) ou URI
  if (pathname === '/api/open-vscode' && req.method === 'POST') {
    try {
      const body = await readJsonBody(req);
      const cfg = loadConfig();
      const vm = cfg.vms.find(v => v.id === body.id);
      if (!vm) return sendJson(res, 404, { ok: false, error: 'VM não encontrada' });

      const wsPath = vm.workspacePath || `/home/${vm.user || 'ubuntu'}`;
      const remoteAuthority = (vm.connectionType === 'tunnel' && vm.tunnelName)
        ? `tunnel+${vm.tunnelName}`
        : `ssh-remote+${vm.user ? `${vm.user}@${vm.host}` : vm.host}`;

      exec(`code --remote "${remoteAuthority}" "${wsPath}"`, { windowsHide: true });
      return sendJson(res, 200, {
        ok: true,
        uri: buildVsCodeUri(vm),
        command: `code --remote "${remoteAuthority}" "${wsPath}"`
      });
    } catch (e) {
      return sendJson(res, 400, { ok: false, error: e.message });
    }
  }

  // API: Auto-descoberta de VMs (~/.ssh/config, GCP, AWS, Azure)
  if (pathname === '/api/discover' && req.method === 'GET') {
    const list = await discoverCloudAndSshVms();
    return sendJson(res, 200, { ok: true, discovered: list });
  }

  // Servir arquivos estáticos do frontend
  let filePath = pathname === '/' ? path.join(PUBLIC_DIR, 'index.html') : path.join(PUBLIC_DIR, pathname);
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403);
    return res.end('Forbidden');
  }

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      return res.end('Arquivo não encontrado');
    }
    const ext = path.extname(filePath).toLowerCase();
    const mimeTypes = {
      '.html': 'text/html; charset=utf-8',
      '.css': 'text/css; charset=utf-8',
      '.js': 'application/javascript; charset=utf-8',
      '.json': 'application/json; charset=utf-8',
      '.svg': 'image/svg+xml'
    };
    res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
    res.end(content);
  });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Cloud VM Monitor rodando em http://localhost:${PORT}`);
});
