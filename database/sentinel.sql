-- ============================================================================
-- SIGN OF THE CROSS (SOTC) — V0.7 THE SENTINEL
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
    actor TEXT NOT NULL DEFAULT 'admin@sotc.local',
    role TEXT NOT NULL DEFAULT 'ADMIN',
    impact_level TEXT NOT NULL DEFAULT 'LOW',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sotc_incidents (
    id SERIAL PRIMARY KEY,
    incident_code TEXT UNIQUE NOT NULL,
    vm_ssh TEXT NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'HIGH',
    status TEXT NOT NULL DEFAULT 'OPEN',
    owner TEXT NOT NULL DEFAULT 'SRE On-Call (Vinicius)',
    sla_minutes INTEGER NOT NULL DEFAULT 60,
    opened_ts BIGINT NOT NULL,
    resolved_ts BIGINT,
    mttr_minutes NUMERIC(10,2),
    root_cause TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sotc_hourly_rollups (
    hour_bucket BIGINT NOT NULL,
    ssh TEXT NOT NULL,
    samples_count INTEGER NOT NULL DEFAULT 1,
    avg_cpu NUMERIC(6,2) NOT NULL DEFAULT 0,
    max_cpu NUMERIC(6,2) NOT NULL DEFAULT 0,
    avg_ram NUMERIC(6,2) NOT NULL DEFAULT 0,
    avg_disk NUMERIC(6,2) NOT NULL DEFAULT 0,
    avg_latency_ms NUMERIC(10,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (hour_bucket, ssh)
);

CREATE TABLE IF NOT EXISTS sotc_ssl_certificates (
    domain TEXT PRIMARY KEY,
    vm_ssh TEXT NOT NULL,
    issuer TEXT NOT NULL DEFAULT 'Let''s Encrypt',
    valid_until TEXT NOT NULL,
    days_remaining INTEGER NOT NULL DEFAULT 90,
    status TEXT NOT NULL DEFAULT 'VALID',
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sotc_backups (
    backup_id TEXT PRIMARY KEY,
    vm_ssh TEXT NOT NULL,
    backup_type TEXT NOT NULL DEFAULT 'GCP Disk Snapshot + Neon PITR',
    size_gb NUMERIC(8,2) NOT NULL DEFAULT 7.9,
    rpo_hours INTEGER NOT NULL DEFAULT 24,
    rto_minutes INTEGER NOT NULL DEFAULT 15,
    status TEXT NOT NULL DEFAULT 'VERIFIED',
    last_tested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
