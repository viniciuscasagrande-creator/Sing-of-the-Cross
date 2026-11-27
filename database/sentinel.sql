-- ============================================================================
-- SING OF THE CROSS (SOTC) — V0.7 THE SENTINEL
-- Schema de Persistência Multi-Cloud & Monitoramento Contínuo (Neon PostgreSQL)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sotc_agents (
    agent_id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    os_name TEXT NOT NULL DEFAULT 'Windows 11',
    version TEXT NOT NULL DEFAULT '0.7.0',
    interval_sec INTEGER NOT NULL DEFAULT 30,
    vms_count INTEGER NOT NULL DEFAULT 0,
    local_projects JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'ONLINE',
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_epoch BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sotc_vm_snapshots (
    ssh TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cloud TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sotc_vm_history (
    id SERIAL PRIMARY KEY,
    ts BIGINT NOT NULL,
    ssh TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sotc_vm_history_ssh_ts ON sotc_vm_history (ssh, ts DESC);

CREATE TABLE IF NOT EXISTS sotc_alerts (
    id SERIAL PRIMARY KEY,
    ts BIGINT NOT NULL,
    vm_ssh TEXT NOT NULL,
    metric TEXT NOT NULL,
    value TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sotc_alerts_ts ON sotc_alerts (ts DESC);

CREATE TABLE IF NOT EXISTS sotc_audit_log (
    id SERIAL PRIMARY KEY,
    ts BIGINT NOT NULL,
    alias TEXT NOT NULL,
    action TEXT NOT NULL,
    ok BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
