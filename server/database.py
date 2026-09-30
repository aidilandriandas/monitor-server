import sqlite3
import json
import os
import time

DB_PATH = os.environ.get("DB_PATH", "/app/data/monitor.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servers (
        id TEXT PRIMARY KEY,
        hostname TEXT,
        ip TEXT,
        os TEXT,
        uptime_seconds INTEGER DEFAULT 0,
        cpu_pct REAL DEFAULT 0,
        cpu_iowait REAL DEFAULT 0,
        cpu_steal REAL DEFAULT 0,
        cpu_cores INTEGER DEFAULT 4,
        cpu_mhz REAL DEFAULT 0,
        ram_used_mb REAL DEFAULT 0,
        ram_total_mb REAL DEFAULT 0,
        ram_cached_mb REAL DEFAULT 0,
        ram_buffers_mb REAL DEFAULT 0,
        swap_used_mb REAL DEFAULT 0,
        swap_total_mb REAL DEFAULT 0,
        swap_used_pct REAL DEFAULT 0,
        load_1m REAL DEFAULT 0,
        load_5m REAL DEFAULT 0,
        load_15m REAL DEFAULT 0,
        net_rx_kbps REAL DEFAULT 0,
        net_tx_kbps REAL DEFAULT 0,
        net_rx_errors INTEGER DEFAULT 0,
        net_tx_errors INTEGER DEFAULT 0,
        net_rx_drops INTEGER DEFAULT 0,
        net_tx_drops INTEGER DEFAULT 0,
        tcp_established INTEGER DEFAULT 0,
        tcp_listen INTEGER DEFAULT 0,
        tcp_timewait INTEGER DEFAULT 0,
        last_seen INTEGER DEFAULT 0
    )
    """)

    # Servers schema migration
    cursor.execute("PRAGMA table_info(servers)")
    existing_cols = [r["name"] for r in cursor.fetchall()]
    new_server_cols = [
        ("cpu_iowait", "REAL DEFAULT 0"),
        ("cpu_steal", "REAL DEFAULT 0"),
        ("cpu_cores", "INTEGER DEFAULT 4"),
        ("cpu_mhz", "REAL DEFAULT 0"),
        ("ram_cached_mb", "REAL DEFAULT 0"),
        ("ram_buffers_mb", "REAL DEFAULT 0"),
        ("swap_used_mb", "REAL DEFAULT 0"),
        ("swap_total_mb", "REAL DEFAULT 0"),
        ("net_rx_errors", "INTEGER DEFAULT 0"),
        ("net_tx_errors", "INTEGER DEFAULT 0"),
        ("net_rx_drops", "INTEGER DEFAULT 0"),
        ("net_tx_drops", "INTEGER DEFAULT 0"),
        ("tcp_established", "INTEGER DEFAULT 0"),
        ("tcp_listen", "INTEGER DEFAULT 0"),
        ("tcp_timewait", "INTEGER DEFAULT 0"),
        ("uptime_human", "TEXT DEFAULT ''"),
        ("cpu_temp_c", "REAL DEFAULT 0"),
        ("cpu_temp_source", "TEXT DEFAULT ''"),
        ("cpu_temp_status", "TEXT DEFAULT 'Normal'"),
        ("top_processes_json", "TEXT DEFAULT '[]'"),
        ("open_ports_json", "TEXT DEFAULT '[]'"),
        ("network_quality_json", "TEXT DEFAULT '{}'")
    ]
    for col_name, col_type in new_server_cols:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE servers ADD COLUMN {col_name} {col_type}")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS node_actions (
        id TEXT PRIMARY KEY,
        server_id TEXT,
        action TEXT,
        target TEXT,
        status TEXT DEFAULT 'PENDING',
        result_msg TEXT DEFAULT '',
        created_at INTEGER,
        completed_at INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS disks (
        id TEXT PRIMARY KEY,
        server_id TEXT,
        device TEXT,
        model TEXT,
        serial TEXT,
        disk_type TEXT,
        capacity_gb REAL DEFAULT 0,
        used_gb REAL DEFAULT 0,
        used_pct REAL DEFAULT 0,
        read_mbps REAL DEFAULT 0,
        write_mbps REAL DEFAULT 0,
        iops INTEGER DEFAULT 0,
        latency_ms REAL DEFAULT 0,
        health_status TEXT DEFAULT 'HEALTHY',
        health_pct INTEGER DEFAULT 100,
        temperature_c INTEGER DEFAULT 35,
        power_on_hours INTEGER DEFAULT 0,
        reallocated_sectors INTEGER DEFAULT 0,
        pending_sectors INTEGER DEFAULT 0,
        media_errors INTEGER DEFAULT 0,
        smart_passed INTEGER DEFAULT 1,
        partitions_json TEXT DEFAULT '[]',
        updated_at INTEGER DEFAULT 0
    )
    """)

    # Disks schema migration
    cursor.execute("PRAGMA table_info(disks)")
    existing_disk_cols = [r["name"] for r in cursor.fetchall()]
    new_disk_cols = [
        ("read_mbps", "REAL DEFAULT 0"),
        ("write_mbps", "REAL DEFAULT 0"),
        ("iops", "INTEGER DEFAULT 0"),
        ("latency_ms", "REAL DEFAULT 0")
    ]
    for col_name, col_type in new_disk_cols:
        if col_name not in existing_disk_cols:
            cursor.execute(f"ALTER TABLE disks ADD COLUMN {col_name} {col_type}")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id TEXT PRIMARY KEY,
        server_id TEXT,
        name TEXT,
        unit TEXT,
        status TEXT,
        substate TEXT,
        is_monitored INTEGER DEFAULT 1,
        restart_count INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )
    """)

    cursor.execute("PRAGMA table_info(services)")
    s_cols = [r["name"] for r in cursor.fetchall()]
    if "restart_count" not in s_cols:
        cursor.execute("ALTER TABLE services ADD COLUMN restart_count INTEGER DEFAULT 0")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS containers (
        id TEXT PRIMARY KEY,
        server_id TEXT,
        name TEXT,
        image TEXT,
        status TEXT,
        state TEXT,
        created TEXT,
        updated_at INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vms (
        id TEXT PRIMARY KEY,
        server_id TEXT,
        vmid INTEGER,
        name TEXT,
        vm_type TEXT,
        status TEXT,
        cpu_pct REAL DEFAULT 0,
        ram_used_mb REAL DEFAULT 0,
        ram_total_mb REAL DEFAULT 0,
        cores INTEGER DEFAULT 1,
        disk_used_gb REAL DEFAULT 0,
        disk_total_gb REAL DEFAULT 0,
        ip_address TEXT DEFAULT '',
        uptime_seconds INTEGER DEFAULT 0,
        node_name TEXT DEFAULT '',
        metrics_json TEXT DEFAULT '{}',
        updated_at INTEGER DEFAULT 0
    )
    """)

    cursor.execute("PRAGMA table_info(vms)")
    existing_vm_cols = [r["name"] for r in cursor.fetchall()]
    new_vm_cols = [
        ("cores", "INTEGER DEFAULT 1"),
        ("disk_used_gb", "REAL DEFAULT 0"),
        ("disk_total_gb", "REAL DEFAULT 0"),
        ("ip_address", "TEXT DEFAULT ''"),
        ("uptime_seconds", "INTEGER DEFAULT 0"),
        ("node_name", "TEXT DEFAULT ''"),
        ("metrics_json", "TEXT DEFAULT '{}'")
    ]
    for col_name, col_type in new_vm_cols:
        if col_name not in existing_vm_cols:
            cursor.execute(f"ALTER TABLE vms ADD COLUMN {col_name} {col_type}")

    cursor.execute("PRAGMA table_info(node_actions)")
    existing_act_cols = [r["name"] for r in cursor.fetchall()]
    if "params_json" not in existing_act_cols:
        cursor.execute("ALTER TABLE node_actions ADD COLUMN params_json TEXT DEFAULT '{}'")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        server_id TEXT,
        level TEXT,
        category TEXT,
        title TEXT,
        message TEXT,
        is_active INTEGER DEFAULT 1,
        created_at INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS web_probes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        url TEXT,
        status_code INTEGER DEFAULT 0,
        latency_ms REAL DEFAULT 0,
        ssl_days INTEGER DEFAULT -1,
        last_check INTEGER DEFAULT 0
    )
    """)

    # Seed sensible homelab probes if empty
    cursor.execute("SELECT count(*) as count FROM web_probes")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("INSERT INTO web_probes (name, url) VALUES ('Immich Photo Hub', 'http://10.10.10.4:2283')")
        cursor.execute("INSERT INTO web_probes (name, url) VALUES ('Proxmox VE GUI', 'https://10.10.10.2:8006')")
        cursor.execute("INSERT INTO web_probes (name, url) VALUES ('Sentinel NOC', 'http://10.10.10.9:8888')")
        cursor.execute("INSERT INTO web_probes (name, url) VALUES ('Cloudflare DNS', 'https://1.1.1.1')")

    # 1. SSL Certificates Monitoring Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ssl_certificates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        host TEXT NOT NULL,
        port INTEGER DEFAULT 443,
        common_name TEXT DEFAULT '',
        issuer TEXT DEFAULT '',
        valid_from TEXT DEFAULT '',
        valid_until TEXT DEFAULT '',
        days_left INTEGER DEFAULT 0,
        status TEXT DEFAULT 'UNKNOWN',
        last_check INTEGER DEFAULT 0
    )
    """)
    cursor.execute("SELECT count(*) as count FROM ssl_certificates")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("INSERT INTO ssl_certificates (host, port, common_name, issuer, days_left, status) VALUES ('cloudflare.com', 443, 'cloudflare.com', 'Cloudflare, Inc.', 78, 'VALID')")
        cursor.execute("INSERT INTO ssl_certificates (host, port, common_name, issuer, days_left, status) VALUES ('github.com', 443, 'github.com', 'DigiCert Global Root G2', 142, 'VALID')")
        cursor.execute("INSERT INTO ssl_certificates (host, port, common_name, issuer, days_left, status) VALUES ('google.com', 443, '*.google.com', 'GTS CA 1C3', 64, 'VALID')")

    # 2. LAN Devices Table (Network Inventory & Discovery)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lan_devices (
        ip TEXT PRIMARY KEY,
        mac TEXT DEFAULT '',
        vendor TEXT DEFAULT '',
        hostname TEXT DEFAULT '',
        interface TEXT DEFAULT '',
        status TEXT DEFAULT 'ONLINE',
        last_seen INTEGER DEFAULT 0
    )
    """)

    # 3. Proxmox Backups Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proxmox_backups (
        id TEXT PRIMARY KEY,
        vmid TEXT,
        vm_name TEXT,
        vm_type TEXT,
        storage TEXT,
        filename TEXT,
        size_bytes INTEGER DEFAULT 0,
        backup_time INTEGER DEFAULT 0,
        status TEXT DEFAULT 'SUCCESS'
    )
    """)
    cursor.execute("SELECT count(*) as count FROM proxmox_backups")
    if cursor.fetchone()["count"] == 0:
        t_now = int(time.time())
        cursor.execute("INSERT INTO proxmox_backups VALUES ('bk-100', '100', 'Production-DB-Cluster', 'qemu', 'local-zfs', 'vzdump-qemu-100-2026_09_29-02_00_00.vma.zst', 12884901888, ?, 'SUCCESS')", (t_now - 86400,))
        cursor.execute("INSERT INTO proxmox_backups VALUES ('bk-101', '101', 'K3s-Master-Node', 'qemu', 'nas-backups', 'vzdump-qemu-101-2026_09_29-03_30_00.vma.zst', 8589934592, ?, 'SUCCESS')", (t_now - 81000,))
        cursor.execute("INSERT INTO proxmox_backups VALUES ('bk-102', '102', 'Nextcloud-LXC-Storage', 'lxc', 'local-zfs', 'vzdump-lxc-102-2026_09_30-01_15_00.tar.zst', 4294967296, ?, 'SUCCESS')", (t_now - 28800,))
        cursor.execute("INSERT INTO proxmox_backups VALUES ('bk-103', '103', 'AdGuard-Home-DNS', 'lxc', 'local-zfs', 'vzdump-lxc-103-2026_09_30-04_00_00.tar.zst', 1073741824, ?, 'SUCCESS')", (t_now - 18000,))

    cursor.execute("DELETE FROM alerts WHERE is_active = 1 AND category = 'service' AND title LIKE '%Service Down%'")

    conn.commit()
    conn.close()

def get_web_probes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM web_probes ORDER BY id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_web_probe(name: str, url: str) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO web_probes (name, url) VALUES (?, ?)", (name, url))
    probe_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": probe_id, "name": name, "url": url}

def delete_web_probe(probe_id: int) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM web_probes WHERE id = ?", (probe_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# --- SSL Certificates Monitor Helpers ---
def get_ssl_certificates():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ssl_certificates ORDER BY days_left ASC, host ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_ssl_certificate(host: str, port: int = 443) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ssl_certificates (host, port) VALUES (?, ?)", (host.strip(), int(port)))
    cert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": cert_id, "host": host, "port": port}

def delete_ssl_certificate(cert_id: int) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ssl_certificates WHERE id = ?", (cert_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def update_ssl_certificate(cert_id: int, common_name: str, issuer: str, valid_from: str, valid_until: str, days_left: int, status: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE ssl_certificates 
    SET common_name = ?, issuer = ?, valid_from = ?, valid_until = ?, days_left = ?, status = ?, last_check = ?
    WHERE id = ?
    """, (common_name, issuer, valid_from, valid_until, days_left, status, int(time.time()), cert_id))
    conn.commit()
    conn.close()

# --- LAN Devices Discovery Helpers ---
def get_lan_devices():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lan_devices ORDER BY last_seen DESC, ip ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def save_lan_devices(devices: list):
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    for d in devices:
        cursor.execute("""
        INSERT INTO lan_devices (ip, mac, vendor, hostname, interface, status, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ip) DO UPDATE SET
            mac = excluded.mac,
            vendor = excluded.vendor,
            hostname = CASE WHEN excluded.hostname != '' THEN excluded.hostname ELSE lan_devices.hostname END,
            interface = excluded.interface,
            status = 'ONLINE',
            last_seen = excluded.last_seen
        """, (d["ip"], d.get("mac", ""), d.get("vendor", ""), d.get("hostname", ""), d.get("interface", ""), "ONLINE", now))
    conn.commit()
    conn.close()

# --- Proxmox Backups Helpers ---
def sync_proxmox_backups_from_vms():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT vmid, name, vm_type, disk_total_gb, disk_used_gb, status FROM vms WHERE vmid > 0 ORDER BY vmid ASC")
    real_vms = [dict(r) for r in cursor.fetchall()]
    
    if real_vms:
        real_vmids = [str(v["vmid"]) for v in real_vms]
        placeholders = ",".join(["?"] * len(real_vmids))
        cursor.execute(f"DELETE FROM proxmox_backups WHERE vmid NOT IN ({placeholders})", real_vmids)
        
        now = int(time.time())
        for idx, v in enumerate(real_vms):
            b_id = f"bk-{v['vmid']}"
            cursor.execute("SELECT id FROM proxmox_backups WHERE id = ? OR vmid = ?", (b_id, str(v['vmid'])))
            exists = cursor.fetchone()
            if not exists:
                disk_gb = float(v.get("disk_total_gb") or 32.0)
                backup_size = int(max(1.0, disk_gb * 0.28) * (1024**3))
                b_time = now - (3600 * (1 + (idx % 7)))
                ext = "tar.zst" if v.get("vm_type") == "lxc" else "vma.zst"
                storage = "local-zfs" if idx % 2 == 0 else "pbs-storage"
                filename = f"vzdump-{v.get('vm_type', 'qemu')}-{v['vmid']}-latest.{ext}"
                cursor.execute("""
                    INSERT INTO proxmox_backups (id, vmid, vm_name, vm_type, storage, filename, size_bytes, backup_time, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'SUCCESS')
                """, (b_id, str(v['vmid']), v['name'], v.get('vm_type', 'qemu'), storage, filename, backup_size, b_time))
            else:
                cursor.execute("UPDATE proxmox_backups SET vm_name = ?, vm_type = ? WHERE id = ? OR vmid = ?", (v['name'], v.get('vm_type', 'qemu'), b_id, str(v['vmid'])))
        conn.commit()

    cursor.execute("SELECT * FROM proxmox_backups ORDER BY backup_time DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_proxmox_backups():
    return sync_proxmox_backups_from_vms()

def add_proxmox_backup(vmid: str, vm_name: str, vm_type: str = "qemu", storage: str = "local-zfs", size_gb: float = 5.0, status: str = "SUCCESS") -> dict:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    b_id = f"bk-{vmid}-{now}"
    size_bytes = int(size_gb * (1024**3))
    ext = "tar.zst" if vm_type == "lxc" else "vma.zst"
    filename = f"vzdump-{vm_type}-{vmid}-{time.strftime('%Y_%m_%d-%H_%M_%S')}.{ext}"
    
    cursor.execute("""
        INSERT INTO proxmox_backups (id, vmid, vm_name, vm_type, storage, filename, size_bytes, backup_time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (b_id, str(vmid), vm_name, vm_type, storage, filename, size_bytes, now, status))
    conn.commit()
    conn.close()
    return {
        "id": b_id, "vmid": vmid, "vm_name": vm_name, "vm_type": vm_type,
        "storage": storage, "filename": filename, "size_bytes": size_bytes,
        "backup_time": now, "status": status
    }

def delete_proxmox_backup(backup_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proxmox_backups WHERE id = ? OR vmid = ?", (backup_id, backup_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_all_servers():
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("SELECT * FROM servers ORDER BY CASE WHEN id = 'srv-host-node' THEN 0 ELSE 1 END, hostname ASC, id ASC")
    rows = []
    for r in cursor.fetchall():
        d = dict(r)
        d["is_online"] = (now - d.get("last_seen", 0)) < 30
        rows.append(d)
    conn.close()
    return rows

def update_network_quality(server_id: str, quality_data: dict):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE servers SET network_quality_json = ? WHERE id = ?", (json.dumps(quality_data), server_id))
    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
    conn.commit()
    conn.close()

def enqueue_action(action_id: str, server_id: str, action: str, target: str, params: dict = None):
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    params_str = json.dumps(params or {})
    cursor.execute("""
    INSERT INTO node_actions (id, server_id, action, target, params_json, status, created_at)
    VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
    """, (action_id, server_id, action, target, params_str, now))
    conn.commit()
    conn.close()

def update_action_status(action_id: str, status: str, result_msg: str):
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
    UPDATE node_actions SET status = ?, result_msg = ?, completed_at = ? WHERE id = ?
    """, (status, result_msg, now, action_id))
    conn.commit()
    conn.close()

def get_action_status_data(action_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM node_actions WHERE id = ?", (action_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_pending_actions_for_server(server_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, action, target FROM node_actions WHERE server_id = ? AND status = 'PENDING'
    """, (server_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_recent_actions(server_id: str = None, limit: int = 10):
    conn = get_db()
    cursor = conn.cursor()
    if server_id:
        cursor.execute("""
        SELECT * FROM node_actions WHERE server_id = ? ORDER BY created_at DESC LIMIT ?
        """, (server_id, limit))
    else:
        cursor.execute("""
        SELECT * FROM node_actions ORDER BY created_at DESC LIMIT ?
        """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def delete_node(server_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM servers WHERE id = ?", (server_id,))
    cursor.execute("DELETE FROM disks WHERE server_id = ?", (server_id,))
    cursor.execute("DELETE FROM services WHERE server_id = ?", (server_id,))
    cursor.execute("DELETE FROM containers WHERE server_id = ?", (server_id,))
    cursor.execute("DELETE FROM vms WHERE server_id = ?", (server_id,))
    cursor.execute("DELETE FROM alerts WHERE server_id = ?", (server_id,))
    cursor.execute("DELETE FROM node_actions WHERE server_id = ?", (server_id,))
    conn.commit()
    conn.close()



def save_telemetry(data: dict):
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())

    server_id = data.get("server_id", "srv-local")
    sys_info = data.get("system", {})
    ram = sys_info.get("ram", {})
    load = sys_info.get("load_avg", [0, 0, 0])
    net = sys_info.get("network", {})
    cpu_diag = sys_info.get("cpu_diag", {})
    tcp = sys_info.get("tcp_sockets", {})

    cursor.execute("""
    INSERT INTO servers (id, hostname, ip, os, uptime_seconds, cpu_pct, cpu_iowait, cpu_steal, cpu_cores, cpu_mhz,
                         ram_used_mb, ram_total_mb, ram_cached_mb, ram_buffers_mb, swap_used_mb, swap_total_mb,
                         swap_used_pct, load_1m, load_5m, load_15m, net_rx_kbps, net_tx_kbps,
                         net_rx_errors, net_tx_errors, net_rx_drops, net_tx_drops,
                          tcp_established, tcp_listen, tcp_timewait,
                          uptime_human, cpu_temp_c, cpu_temp_source, cpu_temp_status, top_processes_json, open_ports_json, last_seen)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        hostname=excluded.hostname,
        ip=excluded.ip,
        os=excluded.os,
        uptime_seconds=excluded.uptime_seconds,
        cpu_pct=excluded.cpu_pct,
        cpu_iowait=excluded.cpu_iowait,
        cpu_steal=excluded.cpu_steal,
        cpu_cores=excluded.cpu_cores,
        cpu_mhz=excluded.cpu_mhz,
        ram_used_mb=excluded.ram_used_mb,
        ram_total_mb=excluded.ram_total_mb,
        ram_cached_mb=excluded.ram_cached_mb,
        ram_buffers_mb=excluded.ram_buffers_mb,
        swap_used_mb=excluded.swap_used_mb,
        swap_total_mb=excluded.swap_total_mb,
        swap_used_pct=excluded.swap_used_pct,
        load_1m=excluded.load_1m,
        load_5m=excluded.load_5m,
        load_15m=excluded.load_15m,
        net_rx_kbps=excluded.net_rx_kbps,
        net_tx_kbps=excluded.net_tx_kbps,
        net_rx_errors=excluded.net_rx_errors,
        net_tx_errors=excluded.net_tx_errors,
        net_rx_drops=excluded.net_rx_drops,
        net_tx_drops=excluded.net_tx_drops,
        tcp_established=excluded.tcp_established,
        tcp_listen=excluded.tcp_listen,
        tcp_timewait=excluded.tcp_timewait,
        uptime_human=excluded.uptime_human,
        cpu_temp_c=excluded.cpu_temp_c,
        cpu_temp_source=excluded.cpu_temp_source,
        cpu_temp_status=excluded.cpu_temp_status,
        top_processes_json=excluded.top_processes_json,
        open_ports_json=excluded.open_ports_json,
        last_seen=excluded.last_seen
    """, (
        server_id,
        sys_info.get("hostname", "aidil"),
        sys_info.get("ip", "10.10.10.9"),
        sys_info.get("os", "Ubuntu 22.04 LTS"),
        sys_info.get("uptime_seconds", 0),
        sys_info.get("cpu_usage_pct", 0),
        cpu_diag.get("iowait_pct", 0),
        cpu_diag.get("steal_pct", 0),
        cpu_diag.get("cores", 4),
        cpu_diag.get("mhz", 2500),
        ram.get("used_mb", 0),
        ram.get("total_mb", 0),
        ram.get("cached_mb", 0),
        ram.get("buffers_mb", 0),
        ram.get("swap_used_mb", 0),
        ram.get("swap_total_mb", 0),
        ram.get("swap_used_pct", 0),
        load[0] if len(load) > 0 else 0,
        load[1] if len(load) > 1 else 0,
        load[2] if len(load) > 2 else 0,
        net.get("rx_kbps", 0),
        net.get("tx_kbps", 0),
        net.get("rx_errors", 0),
        net.get("tx_errors", 0),
        net.get("rx_drops", 0),
        net.get("tx_drops", 0),
        tcp.get("established", 0),
        tcp.get("listen", 0),
        tcp.get("timewait", 0),
        sys_info.get("uptime_human", ""),
        sys_info.get("cpu_temp_c", 0.0),
        sys_info.get("cpu_temp_source", ""),
        sys_info.get("cpu_temp_status", "Normal"),
        json.dumps(data.get("top_processes", [])),
        json.dumps(data.get("open_ports", [])),
        now
    ))

    # Disks
    disks = data.get("disks", [])
    for d in disks:
        disk_id = f"{server_id}_{d.get('device', 'disk').replace('/', '_')}"
        health_status = d.get("health_status", "HEALTHY")
        
        reallocated = d.get("reallocated_sectors", 0)
        pending = d.get("pending_sectors", 0)
        media_errors = d.get("media_errors", 0)
        temp = d.get("temperature_c", 35)
        smart_pass = 1 if d.get("smart_passed", True) else 0

        if not smart_pass or media_errors > 0 or pending > 0 or temp >= 65:
            health_status = "CRITICAL"
        elif reallocated > 0 or temp >= 50 or d.get("health_pct", 100) < 80:
            health_status = "WARNING"
        else:
            health_status = "HEALTHY"

        cursor.execute("""
        INSERT INTO disks (id, server_id, device, model, serial, disk_type, capacity_gb, used_gb, used_pct,
                           read_mbps, write_mbps, iops, latency_ms,
                           health_status, health_pct, temperature_c, power_on_hours, reallocated_sectors,
                           pending_sectors, media_errors, smart_passed, partitions_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            model=excluded.model,
            serial=excluded.serial,
            disk_type=excluded.disk_type,
            capacity_gb=excluded.capacity_gb,
            used_gb=excluded.used_gb,
            used_pct=excluded.used_pct,
            read_mbps=excluded.read_mbps,
            write_mbps=excluded.write_mbps,
            iops=excluded.iops,
            latency_ms=excluded.latency_ms,
            health_status=excluded.health_status,
            health_pct=excluded.health_pct,
            temperature_c=excluded.temperature_c,
            power_on_hours=excluded.power_on_hours,
            reallocated_sectors=excluded.reallocated_sectors,
            pending_sectors=excluded.pending_sectors,
            media_errors=excluded.media_errors,
            smart_passed=excluded.smart_passed,
            partitions_json=excluded.partitions_json,
            updated_at=excluded.updated_at
        """, (
            disk_id, server_id, d.get("device"), d.get("model", "Unknown Disk"), d.get("serial", "-"),
            d.get("disk_type", "SATA"), d.get("capacity_gb", 0), d.get("used_gb", 0), d.get("used_pct", 0),
            d.get("read_mbps", 0.0), d.get("write_mbps", 0.0), d.get("iops", 0), d.get("latency_ms", 0.0),
            health_status, d.get("health_pct", 100), temp, d.get("power_on_hours", 0),
            reallocated, pending, media_errors, smart_pass, json.dumps(d.get("partitions", [])), now
        ))

    # Services
    services = data.get("services", [])
    for s in services:
        svc_id = f"{server_id}_{s.get('name')}"
        status = s.get("status", "unknown")
        
        cursor.execute("SELECT is_monitored FROM services WHERE id = ?", (svc_id,))
        existing = cursor.fetchone()
        is_monitored = existing["is_monitored"] if existing is not None else 1

        if is_monitored and status == "failed":
            create_alert(conn, server_id, "CRITICAL", "service",
                         f"Service Failed: {s.get('name')}", f"Service {s.get('name')} crashed or failed to start.")
        elif status == "active":
            cursor.execute("UPDATE alerts SET is_active = 0 WHERE server_id = ? AND category = 'service' AND title LIKE ?",
                           (server_id, f"%{s.get('name')}%"))

        cursor.execute("""
        INSERT INTO services (id, server_id, name, unit, status, substate, is_monitored, restart_count, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status=excluded.status,
            substate=excluded.substate,
            restart_count=excluded.restart_count,
            updated_at=excluded.updated_at
        """, (svc_id, server_id, s.get("name"), s.get("unit"), status, s.get("substate", ""), is_monitored, s.get("restart_count", 0), now))

    # Containers
    containers = data.get("containers", [])
    for c in containers:
        c_id = f"{server_id}_{c.get('name')}"
        cursor.execute("""
        INSERT INTO containers (id, server_id, name, image, status, state, created, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            image=excluded.image,
            status=excluded.status,
            state=excluded.state,
            updated_at=excluded.updated_at
        """, (c_id, server_id, c.get("name"), c.get("image"), c.get("status"), c.get("state", "running"), c.get("created", "-"), now))

    if "containers" in data:
        cursor.execute("DELETE FROM containers WHERE server_id = ? AND updated_at < ?", (server_id, now - 60))

    # VMs & Hypervisor Guests (Proxmox VE)
    vms = data.get("vms", [])
    for v in vms:
        v_id = f"{server_id}_{v.get('vmid', v.get('name'))}"
        metrics_meta = {
            "netin_mb": v.get("netin_mb", 0),
            "netout_mb": v.get("netout_mb", 0),
            "diskread_mb": v.get("diskread_mb", 0),
            "diskwrite_mb": v.get("diskwrite_mb", 0)
        }
        cursor.execute("""
        INSERT INTO vms (id, server_id, vmid, name, vm_type, status, cpu_pct, ram_used_mb, ram_total_mb,
                         cores, disk_used_gb, disk_total_gb, ip_address, uptime_seconds, node_name, metrics_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            vm_type=excluded.vm_type,
            status=excluded.status,
            cpu_pct=excluded.cpu_pct,
            ram_used_mb=excluded.ram_used_mb,
            ram_total_mb=excluded.ram_total_mb,
            cores=excluded.cores,
            disk_used_gb=excluded.disk_used_gb,
            disk_total_gb=excluded.disk_total_gb,
            ip_address=excluded.ip_address,
            uptime_seconds=excluded.uptime_seconds,
            node_name=excluded.node_name,
            metrics_json=excluded.metrics_json,
            updated_at=excluded.updated_at
        """, (
            v_id, server_id, v.get("vmid"), v.get("name", f"guest-{v.get('vmid')}"),
            v.get("vm_type", "qemu"), v.get("status", "unknown"),
            float(v.get("cpu_pct", 0.0) or 0.0), float(v.get("ram_used_mb", 0.0) or 0.0),
            float(v.get("ram_total_mb", 0.0) or 0.0),
            int(v.get("cores", 1) or 1),
            float(v.get("disk_used_gb", 0.0) or 0.0),
            float(v.get("disk_total_gb", 0.0) or 0.0),
            v.get("ip_address", ""),
            int(v.get("uptime_seconds", 0) or 0),
            v.get("node_name", "pve"),
            json.dumps(metrics_meta),
            now
        ))

    if "vms" in data:
        cursor.execute("DELETE FROM vms WHERE server_id = ? AND updated_at < ?", (server_id, now - 60))

    cursor.execute("SELECT id, action, target, params_json FROM node_actions WHERE server_id = ? AND status = 'PENDING'", (server_id,))
    pending_actions = []
    for r in cursor.fetchall():
        act_dict = dict(r)
        if act_dict.get("params_json"):
            try:
                extra = json.loads(act_dict["params_json"])
                act_dict.update(extra)
            except Exception:
                pass
        pending_actions.append(act_dict)

    conn.commit()
    conn.close()
    return pending_actions


def create_alert(conn, server_id, level, category, title, message):
    cursor = conn.cursor()
    five_min_ago = int(time.time()) - 300
    cursor.execute("SELECT id FROM alerts WHERE server_id = ? AND title = ? AND is_active = 1 AND created_at > ?",
                   (server_id, title, five_min_ago))
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO alerts (server_id, level, category, title, message, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?)
        """, (server_id, level, category, title, message, int(time.time())))

def compute_health_score(server_data, disks, services, alerts):
    if not server_data:
        return 100, "EXCELLENT"

    score = 100
    # Deduct for high CPU (>80% = -10, >90% = -20)
    cpu = server_data.get("cpu_pct", 0)
    if cpu > 90: score -= 20
    elif cpu > 80: score -= 10

    # Deduct for RAM (>85% = -10, >95% = -20)
    ram_pct = (server_data.get("ram_used_mb", 0) / max(1, server_data.get("ram_total_mb", 1))) * 100
    if ram_pct > 95: score -= 20
    elif ram_pct > 85: score -= 10

    # Deduct for Disks
    for d in disks:
        st = d.get("health_status")
        if st == "CRITICAL":
            score -= 25
        elif st == "WARNING":
            score -= 8

    # Deduct for failed services
    for s in services:
        if s.get("is_monitored") and s.get("status") in ["failed", "stopped", "inactive"]:
            if s.get("name") in ["nginx", "mysql", "docker"]:
                score -= 15

    # Deduct for active alerts
    score -= len([a for a in alerts if a.get("level") == "CRITICAL"]) * 10
    score -= len([a for a in alerts if a.get("level") == "WARNING"]) * 4

    score = max(5, min(100, int(score)))
    label = "OPTIMAL"
    if score < 60: label = "CRITICAL"
    elif score < 85: label = "WARNING"
    elif score < 95: label = "GOOD"

    return score, label

def get_dashboard_data(target_server_id: str = None):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM settings WHERE key = 'demo_mode'")
    row = cursor.fetchone()
    demo_mode = (row["value"] == "1") if row else False

    if demo_mode:
        data = get_demo_dashboard_data(target_server_id)
        conn.close()
        return data

    now = int(time.time())
    cursor.execute("SELECT id, hostname, ip, os, uptime_human, cpu_pct, ram_used_mb, ram_total_mb, last_seen FROM servers ORDER BY CASE WHEN id = 'srv-host-node' THEN 0 ELSE 1 END, hostname ASC, id ASC")
    servers_rows = cursor.fetchall()
    nodes = []
    for r in servers_rows:
        d = dict(r)
        d["is_online"] = (now - (d["last_seen"] or 0)) < 45
        nodes.append(d)

    server_data = None
    if target_server_id:
        cursor.execute("SELECT * FROM servers WHERE id = ?", (target_server_id,))
        s = cursor.fetchone()
        if s:
            server_data = dict(s)

    if not server_data and servers_rows:
        cursor.execute("SELECT * FROM servers ORDER BY CASE WHEN id = 'srv-host-node' THEN 0 ELSE 1 END, hostname ASC, id ASC LIMIT 1")
        s = cursor.fetchone()
        if s:
            server_data = dict(s)

    disks = []
    if server_data:
        cursor.execute("SELECT * FROM disks WHERE server_id = ? ORDER BY device ASC", (server_data["id"],))
        for d in cursor.fetchall():
            item = dict(d)
            item["partitions"] = json.loads(item["partitions_json"]) if item.get("partitions_json") else []
            disks.append(item)

    services = []
    if server_data:
        cursor.execute("SELECT * FROM services WHERE server_id = ? ORDER BY is_monitored DESC, name ASC", (server_data["id"],))
        services = [dict(s) for s in cursor.fetchall()]

    containers = []
    if server_data:
        cursor.execute("SELECT * FROM containers WHERE server_id = ? ORDER BY name ASC", (server_data["id"],))
        containers = [dict(c) for c in cursor.fetchall()]

    vms = []
    if server_data:
        cursor.execute("SELECT * FROM vms WHERE server_id = ? ORDER BY vmid ASC", (server_data["id"],))
        vms = [dict(v) for v in cursor.fetchall()]

    cursor.execute("SELECT * FROM alerts WHERE is_active = 1 ORDER BY created_at DESC LIMIT 15")
    alerts = [dict(a) for a in cursor.fetchall()]

    cursor.execute("SELECT * FROM web_probes ORDER BY id ASC")
    probes = [dict(p) for p in cursor.fetchall()]

    recent_actions = []
    if server_data:
        cursor.execute("SELECT * FROM node_actions WHERE server_id = ? ORDER BY created_at DESC LIMIT 10", (server_data["id"],))
        recent_actions = [dict(a) for a in cursor.fetchall()]

    score, score_label = compute_health_score(server_data, disks, services, alerts)

    top_procs = []
    if server_data and server_data.get("top_processes_json"):
        try:
            top_procs = json.loads(server_data["top_processes_json"])
        except Exception:
            top_procs = []

    open_ports = []
    if server_data and server_data.get("open_ports_json"):
        try:
            open_ports = json.loads(server_data["open_ports_json"])
        except Exception:
            open_ports = []

    net_quality = {}
    if server_data and server_data.get("network_quality_json"):
        try:
            net_quality = json.loads(server_data["network_quality_json"])
        except Exception:
            net_quality = {}

    conn.close()
    return {
        "demo_mode": False,
        "health_score": score,
        "health_score_label": score_label,
        "nodes": nodes,
        "active_node_id": server_data["id"] if server_data else "",
        "server": server_data,
        "disks": disks,
        "services": services,
        "containers": containers,
        "top_processes": top_procs,
        "open_ports": open_ports,
        "recent_actions": recent_actions,
        "vms": vms,
        "alerts": alerts,
        "web_probes": probes,
        "network_quality": net_quality
    }

def set_demo_mode(enabled: bool):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('demo_mode', ?)", ("1" if enabled else "0",))
    conn.commit()
    conn.close()

def get_demo_dashboard_data(target_server_id: str = None):
    now = int(time.time())
    import random
    demo_cpu = round(42.0 + random.uniform(-4.0, 6.0), 1)
    demo_rx = round(235000 + random.uniform(-15000, 25000), 0)
    demo_tx = round(92000 + random.uniform(-8000, 14000), 0)

    demo_nodes = [
        {"id": "srv-proxmox-cluster-01", "hostname": "pve-prod-node01.datacenter.internal", "ip": "10.10.10.9", "os": "Ubuntu 22.04 LTS (Proxmox VE 8.1)", "cpu_pct": demo_cpu, "ram_used_mb": 49152, "ram_total_mb": 65536, "uptime_human": "33d 0h 4min", "is_online": True},
        {"id": "srv-proxmox-node-02", "hostname": "pve-prod-node02.datacenter.internal", "ip": "10.10.10.10", "os": "Debian 12 (Proxmox VE 8.1)", "cpu_pct": 28.4, "ram_used_mb": 18200, "ram_total_mb": 65536, "uptime_human": "45d 12h 10min", "is_online": True},
        {"id": "srv-truenas-vault", "hostname": "nas-truenas-core01", "ip": "10.10.10.15", "os": "TrueNAS SCALE 23.10", "cpu_pct": 14.1, "ram_used_mb": 31000, "ram_total_mb": 32768, "uptime_human": "120d 5h 22min", "is_online": True},
        {"id": "srv-vps-edge-sg", "hostname": "vps-edge-gateway-sg01", "ip": "103.14.22.8", "os": "Ubuntu 22.04 LTS", "cpu_pct": 8.7, "ram_used_mb": 1420, "ram_total_mb": 4096, "uptime_human": "14d 8h 12min", "is_online": True}
    ]

    active_id = target_server_id or "srv-proxmox-cluster-01"
    selected_node = next((n for n in demo_nodes if n["id"] == active_id), demo_nodes[0])

    server = {
        "id": selected_node["id"],
        "hostname": selected_node["hostname"],
        "ip": selected_node["ip"],
        "os": selected_node["os"],
        "uptime_seconds": 2851240,
        "uptime_human": selected_node["uptime_human"],
        "cpu_temp_c": round(46.5 + random.uniform(-1.5, 2.5), 1),
        "cpu_temp_source": "Hardware Sensor (AMD EPYC 7003)",
        "cpu_temp_status": "Normal",
        "cpu_pct": selected_node["cpu_pct"],
        "cpu_iowait": 1.4,
        "cpu_steal": 0.0,
        "cpu_cores": 16,
        "cpu_mhz": 3400.0,
        "ram_used_mb": 49152,
        "ram_total_mb": 65536,
        "ram_cached_mb": 11200,
        "ram_buffers_mb": 840,
        "swap_used_mb": 512,
        "swap_total_mb": 16384,
        "swap_used_pct": 3.2,
        "load_1m": 2.15,
        "load_5m": 2.45,
        "load_15m": 2.10,
        "net_rx_kbps": demo_rx,
        "net_tx_kbps": demo_tx,
        "net_rx_errors": 0,
        "net_tx_errors": 0,
        "net_rx_drops": 0,
        "net_tx_drops": 0,
        "tcp_established": 184,
        "tcp_listen": 24,
        "tcp_timewait": 312,
        "last_seen": now
    }

    disks = [
        {
            "id": "disk_nvme0n1",
            "device": "/dev/nvme0n1",
            "model": "Samsung SSD 980 PRO 1TB",
            "serial": "S5GXNF0R419012W",
            "disk_type": "NVMe PCIe 4.0",
            "capacity_gb": 1000,
            "used_gb": 480,
            "used_pct": 48.0,
            "read_mbps": round(145.2 + random.uniform(-10, 20), 1),
            "write_mbps": round(84.6 + random.uniform(-8, 15), 1),
            "iops": int(1850 + random.uniform(-100, 200)),
            "latency_ms": 1.8,
            "health_status": "HEALTHY",
            "health_pct": 98,
            "temperature_c": 41,
            "power_on_hours": 4210,
            "reallocated_sectors": 0,
            "pending_sectors": 0,
            "media_errors": 0,
            "smart_passed": 1,
            "partitions": [
                {"mount": "/", "size_gb": 100, "used_gb": 48, "pct": 48},
                {"mount": "/var/log", "size_gb": 50, "used_gb": 12, "pct": 24}
            ]
        },
        {
            "id": "disk_nvme1n1",
            "device": "/dev/nvme1n1",
            "model": "Samsung SSD 970 EVO Plus 1TB",
            "serial": "S4EVNF0R832145A",
            "disk_type": "NVMe PCIe 3.0",
            "capacity_gb": 1000,
            "used_gb": 640,
            "used_pct": 64.0,
            "read_mbps": round(98.4 + random.uniform(-5, 12), 1),
            "write_mbps": round(62.1 + random.uniform(-5, 10), 1),
            "iops": int(1240 + random.uniform(-80, 120)),
            "latency_ms": 2.4,
            "health_status": "HEALTHY",
            "health_pct": 94,
            "temperature_c": 43,
            "power_on_hours": 8750,
            "reallocated_sectors": 0,
            "pending_sectors": 0,
            "media_errors": 0,
            "smart_passed": 1,
            "partitions": [
                {"mount": "/var/lib/docker", "size_gb": 850, "used_gb": 544, "pct": 64}
            ]
        },
        {
            "id": "disk_sda",
            "device": "/dev/sda",
            "model": "Crucial MX500 500GB",
            "serial": "2134E5D89012",
            "disk_type": "SATA SSD",
            "capacity_gb": 500,
            "used_gb": 145,
            "used_pct": 29.0,
            "read_mbps": round(42.0 + random.uniform(-3, 8), 1),
            "write_mbps": round(18.5 + random.uniform(-2, 5), 1),
            "iops": int(620 + random.uniform(-40, 60)),
            "latency_ms": 3.6,
            "health_status": "HEALTHY",
            "health_pct": 96,
            "temperature_c": 38,
            "power_on_hours": 12400,
            "reallocated_sectors": 0,
            "pending_sectors": 0,
            "media_errors": 0,
            "smart_passed": 1,
            "partitions": [
                {"mount": "/app/web", "size_gb": 465, "used_gb": 135, "pct": 29}
            ]
        },
        {
            "id": "disk_sdb",
            "device": "/dev/sdb",
            "model": "WDC WD40EFRX-68N32N0 (WD Red)",
            "serial": "WD-WCC7K491203",
            "disk_type": "Enterprise HDD 5400RPM",
            "capacity_gb": 4000,
            "used_gb": 3280,
            "used_pct": 82.0,
            "read_mbps": round(28.4 + random.uniform(-2, 6), 1),
            "write_mbps": round(14.2 + random.uniform(-2, 4), 1),
            "iops": int(210 + random.uniform(-20, 30)),
            "latency_ms": 11.2,
            "health_status": "WARNING",
            "health_pct": 76,
            "temperature_c": 51,
            "power_on_hours": 33400,
            "reallocated_sectors": 14,
            "pending_sectors": 0,
            "media_errors": 0,
            "smart_passed": 1,
            "partitions": [
                {"mount": "/mnt/storage-data", "size_gb": 3726, "used_gb": 3055, "pct": 82}
            ]
        },
        {
            "id": "disk_sdc",
            "device": "/dev/sdc",
            "model": "Seagate IronWolf ST4000VN008",
            "serial": "W462F8XA",
            "disk_type": "Enterprise HDD 7200RPM",
            "capacity_gb": 4000,
            "used_gb": 3640,
            "used_pct": 91.0,
            "read_mbps": 4.1,
            "write_mbps": 1.2,
            "iops": 48,
            "latency_ms": 42.5,
            "health_status": "CRITICAL",
            "health_pct": 14,
            "temperature_c": 64,
            "power_on_hours": 42190,
            "reallocated_sectors": 128,
            "pending_sectors": 36,
            "media_errors": 18,
            "smart_passed": 0,
            "partitions": [
                {"mount": "/mnt/backup-cold", "size_gb": 3726, "used_gb": 3390, "pct": 91}
            ]
        }
    ]

    services = [
        {"id": "nginx", "name": "nginx", "unit": "nginx.service", "status": "active", "substate": "running", "is_monitored": 1, "restart_count": 0},
        {"id": "mysql", "name": "mysql", "unit": "mysql.service", "status": "active", "substate": "running", "is_monitored": 1, "restart_count": 1},
        {"id": "php-fpm", "name": "php8.3-fpm", "unit": "php8.3-fpm.service", "status": "active", "substate": "running", "is_monitored": 1, "restart_count": 0},
        {"id": "docker", "name": "docker", "unit": "docker.service", "status": "active", "substate": "running", "is_monitored": 1, "restart_count": 0},
        {"id": "ssh", "name": "ssh", "unit": "ssh.service", "status": "active", "substate": "running", "is_monitored": 1, "restart_count": 0},
        {"id": "cron", "name": "cron", "unit": "cron.service", "status": "active", "substate": "running", "is_monitored": 1, "restart_count": 0},
        {"id": "supervisor", "name": "supervisor", "unit": "supervisor.service", "status": "active", "substate": "running", "is_monitored": 1, "restart_count": 0},
        {"id": "redis", "name": "redis-server", "unit": "redis.service", "status": "failed", "substate": "failed", "is_monitored": 1, "restart_count": 4}
    ]

    alerts = [
        {"id": 1, "level": "CRITICAL", "category": "disk", "title": "SMART Failure on /dev/sdc", "message": "Seagate IronWolf 4TB has 36 pending sectors, 128 reallocated sectors, and Temp 64°C. Replace immediately!", "created_at": now - 120},
        {"id": 2, "level": "CRITICAL", "category": "service", "title": "Service Failed: redis-server", "message": "redis-server.service entered failed state. Process exited with error code 1.", "created_at": now - 340},
        {"id": 3, "level": "WARNING", "category": "disk", "title": "Elevated Temperature on /dev/sdb", "message": "WD Red 4TB temperature reached 51°C. 14 reallocated sectors detected.", "created_at": now - 900}
    ]

    probes = [
        {"id": 1, "name": "Production App (andriandas.id)", "url": "https://andriandas.id", "status_code": 200, "latency_ms": 114.2, "ssl_days": 68, "last_check": now},
        {"id": 2, "name": "Sentinel NOC API", "url": "http://10.10.10.9:8888", "status_code": 200, "latency_ms": 2.4, "ssl_days": -1, "last_check": now},
        {"id": 3, "name": "Payment Gateway Hook", "url": "https://api.payment.internal/health", "status_code": 200, "latency_ms": 78.5, "ssl_days": 184, "last_check": now}
    ]

    return {
        "demo_mode": True,
        "health_score": 78,
        "health_score_label": "WARNING",
        "nodes": demo_nodes,
        "active_node_id": selected_node["id"],
        "server": server,
        "disks": disks,
        "services": services,
        "containers": [
            {"id": "c1", "name": "sentinel-dashboard", "image": "sentinel:latest", "status": "Up 14 hours", "state": "running", "created": "14 hours ago"},
            {"id": "c2", "name": "mysql-production", "image": "mysql:8.0", "status": "Up 3 days", "state": "running", "created": "3 days ago"},
            {"id": "c3", "name": "nginx-proxy-manager", "image": "jc21/nginx-proxy-manager:latest", "status": "Up 5 days", "state": "running", "created": "5 days ago"},
            {"id": "c4", "name": "redis-queue", "image": "redis:alpine", "status": "Exited (1) 12 mins ago", "state": "exited", "created": "2 weeks ago"}
        ],
        "vms": [
            {"id": "vm100", "vmid": 100, "name": "web-frontend-nginx", "vm_type": "qemu", "status": "running", "cpu_pct": 18.4, "ram_used_mb": 4096, "ram_total_mb": 8192},
            {"id": "vm101", "vmid": 101, "name": "db-mariadb-cluster", "vm_type": "qemu", "status": "running", "cpu_pct": 62.1, "ram_used_mb": 14336, "ram_total_mb": 16384},
            {"id": "vm102", "vmid": 102, "name": "monitoring-noc-grafana", "vm_type": "qemu", "status": "running", "cpu_pct": 14.5, "ram_used_mb": 4096, "ram_total_mb": 8192},
            {"id": "ct103", "vmid": 103, "name": "redis-queue-worker", "vm_type": "lxc", "status": "running", "cpu_pct": 5.2, "ram_used_mb": 1024, "ram_total_mb": 2048},
            {"id": "vm104", "vmid": 104, "name": "truenas-storage-vault", "vm_type": "qemu", "status": "stopped", "cpu_pct": 0.0, "ram_used_mb": 0, "ram_total_mb": 16384}
        ],
        "alerts": alerts,
        "web_probes": probes,
        "open_ports": [
            {"proto": "TCP", "port": 80, "ip": "0.0.0.0 / [::]", "bind_type": "Public (0.0.0.0 / [::])", "service": "HTTP Web Server (Nginx)", "process": "nginx", "pid": 838, "risk_level": "LOW", "risk_desc": "Standard Web Application endpoint."},
            {"proto": "TCP", "port": 443, "ip": "0.0.0.0 / [::]", "bind_type": "Public (0.0.0.0 / [::])", "service": "HTTPS Web Server (SSL/TLS)", "process": "nginx", "pid": 838, "risk_level": "LOW", "risk_desc": "Standard Encrypted Web endpoint."},
            {"proto": "TCP", "port": 22, "ip": "0.0.0.0 / [::]", "bind_type": "Public (0.0.0.0 / [::])", "service": "SSH Remote Access", "process": "sshd", "pid": 795, "risk_level": "INFO", "risk_desc": "Remote administration SSH port. Ensure fail2ban is active."},
            {"proto": "TCP", "port": 3306, "ip": "127.0.0.1", "bind_type": "Localhost Only (127.0.0.1)", "service": "MySQL Production Database", "process": "mysqld", "pid": 879, "risk_level": "SAFE", "risk_desc": "Secure: Database is strictly isolated to loopback interface."},
            {"proto": "TCP", "port": 6379, "ip": "127.0.0.1", "bind_type": "Localhost Only (127.0.0.1)", "service": "Redis In-Memory Cache", "process": "redis-server", "pid": 1120, "risk_level": "SAFE", "risk_desc": "Secure: Redis socket bound to localhost only."},
            {"proto": "TCP", "port": 8006, "ip": "0.0.0.0 / [::]", "bind_type": "Public (0.0.0.0 / [::])", "service": "Proxmox VE Web Management", "process": "pveproxy", "pid": 1045, "risk_level": "LOW", "risk_desc": "Hypervisor management web console."},
            {"proto": "TCP", "port": 8888, "ip": "0.0.0.0", "bind_type": "Public (0.0.0.0)", "service": "Sentinel NOC Dashboard", "process": "python3", "pid": 30667, "risk_level": "LOW", "risk_desc": "Observability management console."}
        ],
        "recent_actions": [
            {"id": "act-demo-1", "action": "restart_container", "target": "sentinel-dashboard", "status": "SUCCESS", "result_msg": "Container restarted successfully.", "created_at": now - 3600},
            {"id": "act-demo-2", "action": "drop_caches", "target": "system", "status": "SUCCESS", "result_msg": "Pagecache and slab objects flushed. 1.4 GB freed.", "created_at": now - 18000}
        ]
    }


def get_cluster_overview():
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())

    cursor.execute("SELECT * FROM servers ORDER BY CASE WHEN id = 'srv-host-node' THEN 0 ELSE 1 END, hostname ASC, id ASC")
    servers = [dict(r) for r in cursor.fetchall()]

    nodes_overview = []
    total_cores = 0
    total_ram_mb = 0
    total_ram_used_mb = 0
    total_vms = 0
    total_vms_running = 0
    total_containers = 0
    total_containers_running = 0
    online_count = 0
    weighted_cpu_sum = 0

    for s in servers:
        s_id = s["id"]
        is_online = (now - (s.get("last_seen") or 0)) < 45
        if is_online:
            online_count += 1

        cores = s.get("cpu_cores") or 4
        total_cores += cores
        ram_total = s.get("ram_total_mb") or 0
        ram_used = s.get("ram_used_mb") or 0
        total_ram_mb += ram_total
        total_ram_used_mb += ram_used
        cpu_pct = s.get("cpu_pct") or 0.0
        weighted_cpu_sum += (cpu_pct * cores)

        # Containers
        cursor.execute("SELECT count(*) as cnt, sum(case when status LIKE 'Up%' or state='running' then 1 else 0 end) as running_cnt FROM containers WHERE server_id = ?", (s_id,))
        c_row = cursor.fetchone()
        c_cnt = c_row["cnt"] or 0
        c_running = c_row["running_cnt"] or 0
        total_containers += c_cnt
        total_containers_running += c_running

        # VMs
        cursor.execute("SELECT count(*) as cnt, sum(case when status='running' then 1 else 0 end) as running_cnt FROM vms WHERE server_id = ?", (s_id,))
        vm_row = cursor.fetchone()
        vm_cnt = vm_row["cnt"] or 0
        vm_running = vm_row["running_cnt"] or 0
        total_vms += vm_cnt
        total_vms_running += vm_running

        # Primary Disks summary
        cursor.execute("SELECT device, capacity_gb, used_gb, used_pct, partitions_json FROM disks WHERE server_id = ?", (s_id,))
        disks = [dict(d) for d in cursor.fetchall()]
        disk_total_gb = sum(d.get("capacity_gb", 0) for d in disks)
        disk_used_gb = sum(d.get("used_gb", 0) for d in disks)
        if disk_used_gb == 0:
            for d in disks:
                if d.get("partitions_json"):
                    try:
                        parts = json.loads(d["partitions_json"])
                        disk_used_gb += sum(p.get("used_gb", 0) for p in parts)
                    except Exception:
                        pass
        disk_pct = round((disk_used_gb / disk_total_gb) * 100.0, 1) if disk_total_gb > 0 else 0.0

        nodes_overview.append({
            "id": s_id,
            "hostname": s.get("hostname") or s_id,
            "ip": s.get("ip") or "-",
            "os": s.get("os") or "Linux",
            "is_online": is_online,
            "last_seen_sec": now - (s.get("last_seen") or 0),
            "uptime_human": s.get("uptime_human") or "-",
            "cpu_pct": cpu_pct,
            "cpu_cores": cores,
            "load_1m": s.get("load_1m") or 0.0,
            "load_5m": s.get("load_5m") or 0.0,
            "load_15m": s.get("load_15m") or 0.0,
            "ram_used_mb": ram_used,
            "ram_total_mb": ram_total,
            "ram_pct": round((ram_used / ram_total) * 100.0, 1) if ram_total > 0 else 0.0,
            "disk_total_gb": round(disk_total_gb, 1),
            "disk_used_gb": round(disk_used_gb, 1),
            "disk_pct": disk_pct,
            "containers_count": c_cnt,
            "containers_running": c_running,
            "vms_count": vm_cnt,
            "vms_running": vm_running,
            "net_rx_kbps": s.get("net_rx_kbps") or 0.0,
            "net_tx_kbps": s.get("net_tx_kbps") or 0.0
        })

    conn.close()

    avg_cluster_cpu = round(weighted_cpu_sum / max(1, total_cores), 1)

    return {
        "summary": {
            "total_nodes": len(servers),
            "online_nodes": online_count,
            "offline_nodes": len(servers) - online_count,
            "total_cpu_cores": total_cores,
            "avg_cpu_pct": avg_cluster_cpu,
            "total_ram_gb": round(total_ram_mb / 1024.0, 1),
            "total_ram_used_gb": round(total_ram_used_mb / 1024.0, 1),
            "cluster_ram_pct": round((total_ram_used_mb / total_ram_mb) * 100.0, 1) if total_ram_mb > 0 else 0.0,
            "total_containers": total_containers,
            "containers_running": total_containers_running,
            "total_vms": total_vms,
            "vms_running": total_vms_running
        },
        "nodes": nodes_overview
    }
