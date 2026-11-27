const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFile, exec } = require('child_process');

const PORT = 8765;
const ROOT = __dirname;
const VMS_FILE = path.join(ROOT, 'vms.json');
const LOGO_FILE = path.join(ROOT, 'logo.png');
const INDEX_FILE = path.join(ROOT, 'index.html');
const VALID_CLOUDS = ['Google Cloud', 'AWS', 'Azure', 'Oracle Cloud'];
const HISTORY_LOG = [];

const REMOTE_PROBE_SCRIPT = [
  "export LC_ALL=C;",
  "if ps -eo args 2>/dev/null | grep -E '[.]vscode-server|[.]vscode-remote|[.]vscode-server-insiders|[.]antigravity-server|code-tunnel' >/dev/null; then SRV='present'; else SRV='not_detected'; fi;",
  "SESS=$(ps -eo args 2>/dev/null | grep -E '(vscode-server|antigravity-server).*extensionHost|bootstrap-fork.*--type=extensionHost' | grep -v grep | wc -l);",
  "CPU=$(top -bn1 2>/dev/null | grep 'Cpu(s)' | awk '{print int(100 - $8)}');",
  "RAM=$(free -m 2>/dev/null | awk '/Mem:/ { printf(\"%d\", ($3/$2)*100) }');",
  "DISK=$(df -h / 2>/dev/null | awk 'NR==2 {gsub(\"%\",\"\",$5); print $5}');",
  "UPT=$(uptime -p 2>/dev/null | sed 's/up //');",
  "echo \"SOTC_SRV=${SRV}|SOTC_SESS=${SESS:-0}|SOTC_CPU=${CPU:-0}|SOTC_RAM=${RAM:-0}|SOTC_DISK=${DISK:-0}|SOTC_UPT=${UPT:-Online}\""
].join(' ');

function inventory() {
  if (!fs.existsSync(VMS_FILE)) return [];
  const data = JSON.parse(fs.readFileSync(VMS_FILE, 'utf8'));
  if (!Array.isArray(data)) throw new Error('vms.json deve conter uma lista');
  return data;
}

function saveInventory(data) {
  fs.writeFileSync(VMS_FILE, JSON.stringify(data, null, 2), 'utf8');
}

function parseSshEnvironment() {
  const sshDir = path.join(os.homedir(), '.ssh');
  const cfgPath = path.join(sshDir, 'config');
  const khPath = path.join(sshDir, 'known_hosts');
  const discovered = [];
  const seen = new Set();

  if (fs.existsSync(cfgPath)) {
    let current = null;
    const lines = fs.readFileSync(cfgPath, 'utf8').split(/\r?\n/);
    for (const raw of lines) {
      const line = raw.trim();
      if (!line || line.startsWith('#')) continue;
      const m = line.match(/^(\S+)\s+(.+)$/);
      if (!m) continue;
      const k = m[1].toLowerCase();
      const v = m[2].trim().replace(/^"|"$/g, '');
      if (k === 'host') {
        if (current && !seen.has(current.ssh) && !current.ssh.includes('*')) {
          seen.add(current.ssh);
          discovered.push(current);
        }
        current = { name: v.toUpperCase(), ssh: v, host: v, user: 'ubuntu', port: 22, identity_file: '', source: '~/.ssh/config' };
      } else if (current) {
        if (k === 'hostname') current.host = v;
        if (k === 'user') current.user = v;
        if (k === 'port') current.port = parseInt(v, 10) || 22;
        if (k === 'identityfile') current.identity_file = v;
      }
    }
    if (current && !seen.has(current.ssh) && !current.ssh.includes('*')) {
      seen.add(current.ssh);
      discovered.push(current);
    }
  }

  if (fs.existsSync(khPath)) {
    const lines = fs.readFileSync(khPath, 'utf8').split(/\r?\n/);
    for (const raw of lines) {
      const line = raw.trim();
      if (!line || line.startsWith('#') || line.startsWith('|')) continue;
      const hostField = line.split(/\s+/)[0].split(',')[0];
      const hostClean = hostField.replace(/^\[([^\]]+)\]:\d+$/, '$1');
      if (['github.com', 'gitlab.com', 'bitbucket.org'].includes(hostClean) || seen.has(hostClean)) continue;
      if (/^[A-Za-z0-9_.-]+$/.test(hostClean)) {
        seen.add(hostClean);
        discovered.push({
          name: `HOST-${hostClean.replace(/\./g, '-')}`,
          ssh: hostClean,
          host: hostClean,
          user: 'root',
          port: 22,
          identity_file: '~/.ssh/id_ed25519',
          source: '~/.ssh/known_hosts'
        });
      }
    }
  }

  let keys = [];
  if (fs.existsSync(sshDir)) {
    keys = fs.readdirSync(sshDir).filter(f => !f.endsWith('.pub') && !f.endsWith('.ppk') && f !== 'known_hosts' && f !== 'config');
  }

  return {
    has_ssh_config: fs.existsSync(cfgPath),
    ssh_config_path: cfgPath,
    keys_found: keys,
    discovered_hosts: discovered
  };
}

function probeVm(vm) {
  return new Promise((resolve) => {
    const checked = new Date().toLocaleTimeString('pt-BR', { hour12: false });
    if (vm.mode === 'preview' && vm.preview_state) {
      const ps = vm.preview_state;
      return resolve({
        ...vm,
        ssh_status: ps.ssh_status || 'ok',
        server_status: ps.server_status || 'present',
        session_status: ps.session_status || 'active',
        active_sessions: ps.active_sessions !== undefined ? ps.active_sessions : 1,
        cpu: ps.cpu || 0,
        ram: ps.ram || 0,
        disk: ps.disk || 0,
        uptime: ps.uptime || 'Online',
        detail: ps.detail || 'Modo Prévia',
        checked
      });
    }

    const out = {
      ...vm,
      ssh_status: 'unknown',
      server_status: 'unknown',
      session_status: 'disconnected',
      active_sessions: 0,
      cpu: 0,
      ram: 0,
      disk: 0,
      uptime: 'Offline',
      detail: '',
      checked
    };

    let target = vm.ssh || vm.host;
    if (vm.user && !target.includes('@') && vm.host) {
      target = `${vm.user}@${vm.host}`;
    }

    const args = [
      '-o', 'BatchMode=yes',
      '-o', 'StrictHostKeyChecking=accept-new',
      '-o', 'ConnectTimeout=5',
      '-o', 'ConnectionAttempts=1',
      '-o', 'ClearAllForwardings=yes',
      '-o', 'RequestTTY=no'
    ];
    if (vm.port && Number(vm.port) !== 22) {
      args.push('-p', String(vm.port));
    }
    if (vm.identity_file) {
      const resolvedKey = vm.identity_file.replace(/^~/, os.homedir());
      if (fs.existsSync(resolvedKey)) args.push('-i', resolvedKey);
    }
    args.push(target, REMOTE_PROBE_SCRIPT);

    execFile('ssh', args, { timeout: 10000, windowsHide: true }, (err, stdout, stderr) => {
      if (!err) {
        out.ssh_status = 'ok';
        const kv = {};
        for (const line of (stdout || '').split(/\r?\n/)) {
          if (line.includes('SOTC_SRV=')) {
            line.split('|').forEach(pair => {
              const idx = pair.indexOf('=');
              if (idx > -1) kv[pair.slice(0, idx).trim()] = pair.slice(idx + 1).trim();
            });
          }
        }
        out.server_status = kv.SOTC_SRV || 'not_detected';
        const sess = parseInt(kv.SOTC_SESS || '0', 10) || 0;
        out.active_sessions = sess;
        out.session_status = sess > 0 ? 'active' : (out.server_status === 'present' ? 'idle' : 'disconnected');
        out.cpu = parseInt(kv.SOTC_CPU || '0', 10) || 0;
        out.ram = parseInt(kv.SOTC_RAM || '0', 10) || 0;
        out.disk = parseInt(kv.SOTC_DISK || '0', 10) || 0;
        out.uptime = kv.SOTC_UPT || 'Online';
        if (sess > 0) out.detail = `SSH confirmado • ${sess} sessão(ões) VS Code ativa(s)`;
        else if (out.server_status === 'present') out.detail = 'VS Code Server ativo em background (sem janela conectada)';
        else out.detail = 'SSH acessível • VS Code Server não detectado';
      } else {
        out.ssh_status = 'failed';
        const lines = (stderr || '').trim().split(/\r?\n/).filter(Boolean);
        out.detail = 'SSH não confirmado: ' + (lines.length ? lines[lines.length - 1].slice(0, 160) : 'falha ou timeout na conexão');
      }
      resolve(out);
    });
  });
}

function sendData(res, buf, type = 'application/json; charset=utf-8', status = 200) {
  res.writeHead(status, {
    'Content-Type': type,
    'Cache-Control': 'no-store',
    'Content-Length': Buffer.byteLength(buf)
  });
  res.end(buf);
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', c => { body += c; });
    req.on('end', () => {
      try { resolve(body ? JSON.parse(body) : {}); } catch (e) { reject(e); }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const parsed = new URL(req.url, `http://${req.headers.host || '127.0.0.1:8765'}`);
  const pathname = parsed.pathname;

  try {
    if (req.method === 'GET') {
      if (pathname === '/') {
        return sendData(res, fs.readFileSync(INDEX_FILE), 'text/html; charset=utf-8');
      }
      if (pathname === '/logo.png') {
        return sendData(res, fs.readFileSync(LOGO_FILE), 'image/png');
      }
      if (pathname === '/api/status') {
        const vms = inventory();
        const results = await Promise.all(vms.map(probeVm));
        HISTORY_LOG.push({
          time: new Date().toLocaleTimeString('pt-BR', { hour12: false }),
          total: results.length,
          ok: results.filter(r => r.ssh_status === 'ok').length,
          server: results.filter(r => r.server_status === 'present').length
        });
        if (HISTORY_LOG.length > 25) HISTORY_LOG.shift();
        return sendData(res, JSON.stringify(results));
      }
      if (pathname === '/api/ssh-discovery') {
        return sendData(res, JSON.stringify(parseSshEnvironment()));
      }
      if (pathname === '/api/history') {
        return sendData(res, JSON.stringify(HISTORY_LOG));
      }
      res.writeHead(404);
      return res.end('Not found');
    }

    if (req.method === 'POST') {
      const body = await readJson(req);
      let vms = inventory();

      if (pathname === '/api/vms') {
        const vmId = body.id || `vm-${Date.now()}`;
        const newVm = {
          id: vmId,
          name: (body.name || 'NOVA-VM').trim(),
          cloud: VALID_CLOUDS.includes(body.cloud) ? body.cloud : 'Google Cloud',
          ssh: (body.ssh || body.host || 'localhost').trim(),
          host: (body.host || body.ssh || 'localhost').trim(),
          user: (body.user || 'ubuntu').trim(),
          port: parseInt(body.port, 10) || 22,
          identity_file: (body.identity_file || '').trim(),
          workspace: (body.workspace || '/home/ubuntu').trim(),
          mode: body.mode || 'real',
          preview_state: body.preview_state || {
            ssh_status: 'ok',
            server_status: 'present',
            session_status: 'active',
            active_sessions: 1,
            cpu: 15,
            ram: 30,
            disk: 25,
            uptime: '1d 00h',
            detail: 'VM adicionada ao SOTC'
          }
        };
        const idx = vms.findIndex(v => v.id === vmId || v.ssh === newVm.ssh);
        if (idx >= 0) vms[idx] = newVm;
        else vms.push(newVm);
        saveInventory(vms);
        return sendData(res, JSON.stringify({ ok: true, vm: newVm }));
      }

      if (pathname === '/api/vms/toggle-mode') {
        const targetId = body.id;
        vms.forEach(item => {
          if (item.id === targetId || item.ssh === targetId) {
            item.mode = item.mode === 'preview' ? 'real' : 'preview';
          }
        });
        saveInventory(vms);
        return sendData(res, JSON.stringify({ ok: true }));
      }

      if (pathname === '/api/vms/delete') {
        const targetId = body.id;
        vms = vms.filter(item => item.id !== targetId && item.ssh !== targetId);
        saveInventory(vms);
        return sendData(res, JSON.stringify({ ok: true }));
      }

      if (pathname === '/api/open-vscode') {
        const target = body.ssh;
        const ws = body.workspace || '/';
        exec(`code --remote "ssh-remote+${target}" "${ws}"`, { windowsHide: true });
        return sendData(res, JSON.stringify({ ok: true }));
      }
    }
  } catch (e) {
    return sendData(res, JSON.stringify({ error: e.message }), 'application/json; charset=utf-8', 500);
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log('Sing Of The Cross: http://127.0.0.1:' + PORT);
});
