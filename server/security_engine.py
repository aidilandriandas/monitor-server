"""
Aegis Cyber Shield - Advanced SOC & Real-Time Traffic Defense Engine
Architect & Lead Engineer: AIDIL ANDRIANDAS

Modules:
1. Auto-Ban Fail2ban Engine (Automated Brute-Force Jailing & Telegram Alerting)
2. GeoIP & Country Threat Radar (Global Origin Mapping & Flag Identification)
3. Port Scan & Nmap Reconnaissance Active Detector
4. Linux OS & SSH Hardening Auditor (CIS Benchmark Compliance)
5. File Integrity Monitor (FIM / Anti-Tampering Shield)
6. Aegis AI Security Copilot (Forensic Investigation & Remediation Advisor)
"""

import os
import sys
import time
import re
import subprocess
import sqlite3
import threading
import hashlib
import json
import urllib.request
import urllib.parse
from collections import deque, Counter
from typing import Dict, List, Any, Optional

COMMON_SERVICES = {
    8888: "Aegis Central NOC",
    10909: "Host Admin SSH",
    22: "Standard SSH",
    80: "HTTP Web Proxy",
    443: "HTTPS Web Proxy",
    3306: "MySQL Database",
    33060: "MySQL X Protocol",
    5432: "PostgreSQL Database",
    6379: "Redis Cache",
    8006: "Proxmox VE Cluster",
    2283: "Immich Photos",
    53: "DNS Resolver",
    9000: "Portainer Web UI",
    8080: "App HTTP Alt",
    3000: "Grafana / Dev UI"
}

COUNTRY_FLAGS = {
    "ID": ("Indonesia", "🇮🇩"),
    "US": ("United States", "🇺🇸"),
    "SG": ("Singapore", "🇸🇬"),
    "NL": ("Netherlands", "🇳🇱"),
    "DE": ("Germany", "🇩🇪"),
    "GB": ("United Kingdom", "🇬🇧"),
    "CN": ("China", "🇨🇳"),
    "RU": ("Russia", "🇷🇺"),
    "JP": ("Japan", "🇯🇵"),
    "KR": ("South Korea", "🇰🇷"),
    "IN": ("India", "🇮🇳"),
    "FR": ("France", "🇫🇷"),
    "CA": ("Canada", "🇨🇦"),
    "AU": ("Australia", "🇦🇺"),
    "BR": ("Brazil", "🇧🇷"),
    "VN": ("Vietnam", "🇻🇳"),
    "MY": ("Malaysia", "🇲🇾"),
    "TH": ("Thailand", "🇹🇭"),
    "LAN": ("Cluster LAN", "🛡️"),
    "VPN": ("WireGuard VPN", "🔒"),
    "LOCAL": ("Localhost", "🖥️")
}


class ProxmoxPerimeterShield:
    """
    Cluster Perimeter Firewall Engine (Proxmox VE 10.10.10.2)
    Architect & Lead Engineer: AIDIL ANDRIANDAS

    Enforces link-layer (ebtables) and network-layer (iptables) packet filtering
    at the Proxmox VE hypervisor level (10.10.10.2). Because all 8 Virtual Machines
    (Database, immich, Ceritakota, Portfolio-Sekar, proxy, Pambuluah, Portfolio-Aidil, Pentest)
    and the host bridge vmbr0 communicate through this hypervisor, dropping an IP here
    blocks it for the ENTIRE network cluster before packets reach any virtual machine.
    """
    def __init__(self, host="10.10.10.2", port=22, user="root", password="Aidil111"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.chain_name = "AEGIS_CLUSTER_DROP"
        self.lock = threading.RLock()
        self.cached_status = None
        self.last_cache_time = 0
        threading.Thread(target=self.ensure_perimeter_chains, daemon=True).start()

    def _exec_pve(self, cmd: str, timeout: int = 6) -> tuple[bool, str]:
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.host, port=self.port, username=self.user, password=self.password, timeout=timeout)
            _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
            out = stdout.read().decode('utf-8', errors='ignore')
            err = stderr.read().decode('utf-8', errors='ignore')
            client.close()
            return True, out if out else err
        except Exception as e:
            return False, str(e)

    def ensure_perimeter_chains(self):
        with self.lock:
            cmd = f"""
# 1. Ebtables bridge filter chain
ebtables -N {self.chain_name} 2>/dev/null || true
if ! ebtables -L FORWARD | grep -q {self.chain_name}; then
    ebtables -I FORWARD 1 -j {self.chain_name}
fi
if ! ebtables -L INPUT | grep -q {self.chain_name}; then
    ebtables -I INPUT 1 -j {self.chain_name}
fi

# Clean up legacy test chains if present
ebtables -D FORWARD -j AEGIS_BLOCK 2>/dev/null || true
ebtables -D INPUT -j AEGIS_BLOCK 2>/dev/null || true
ebtables -F AEGIS_BLOCK 2>/dev/null || true
ebtables -X AEGIS_BLOCK 2>/dev/null || true

# 2. Iptables host and routed filter chain
iptables -N {self.chain_name} 2>/dev/null || true
if ! iptables -C INPUT -j {self.chain_name} 2>/dev/null; then
    iptables -I INPUT 1 -j {self.chain_name}
fi
if ! iptables -C FORWARD -j {self.chain_name} 2>/dev/null; then
    iptables -I FORWARD 1 -j {self.chain_name}
fi
"""
            ok, res = self._exec_pve(cmd, timeout=8)
            if ok:
                print(f"[Aegis Shield] Proxmox Perimeter Firewall ({self.host}) initialized successfully.")
            else:
                print(f"[Aegis Shield] Failed initializing Proxmox perimeter chains: {res}")

    def block_ip_cluster(self, ip: str) -> bool:
        if not ip or ip in ("127.0.0.1", "10.10.10.2", "10.10.10.9", "10.10.10.1"):
            return False
        if ip.startswith("149.154.") or ip.startswith("91.108.") or ip in ("1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4"):
            return False

        with self.lock:
            cmd = f"""
if ! ebtables -L {self.chain_name} 2>/dev/null | grep -q "{ip}"; then
    ebtables -A {self.chain_name} -p IPv4 --ip-src {ip} -j DROP 2>/dev/null || true
    ebtables -A {self.chain_name} -p IPv4 --ip-dst {ip} -j DROP 2>/dev/null || true
fi
if ! iptables -C {self.chain_name} -s {ip} -j DROP 2>/dev/null; then
    iptables -A {self.chain_name} -s {ip} -j DROP 2>/dev/null || true
fi
if ! iptables -C {self.chain_name} -d {ip} -j DROP 2>/dev/null; then
    iptables -A {self.chain_name} -d {ip} -j DROP 2>/dev/null || true
fi
"""
            ok, res = self._exec_pve(cmd, timeout=5)
            self.cached_status = None
            return ok

    def unblock_ip_cluster(self, ip: str) -> bool:
        with self.lock:
            cmd = f"""
while ebtables -D {self.chain_name} -p IPv4 --ip-src {ip} -j DROP 2>/dev/null; do :; done
while ebtables -D {self.chain_name} -p IPv4 --ip-dst {ip} -j DROP 2>/dev/null; do :; done
while iptables -D {self.chain_name} -s {ip} -j DROP 2>/dev/null; do :; done
while iptables -D {self.chain_name} -d {ip} -j DROP 2>/dev/null; do :; done
"""
            ok, res = self._exec_pve(cmd, timeout=5)
            self.cached_status = None
            return ok

    def sync_all_blocked(self, blocked_ips: set) -> dict:
        with self.lock:
            flush_cmd = f"""
ebtables -F {self.chain_name} 2>/dev/null || true
iptables -F {self.chain_name} 2>/dev/null || true
"""
            self._exec_pve(flush_cmd, timeout=5)
            
            valid_ips = [ip for ip in blocked_ips if ip and not ip.startswith("149.154.") and not ip.startswith("91.108.") and ip not in ("127.0.0.1", "10.10.10.9", "10.10.10.2", "1.1.1.1", "8.8.8.8")]
            
            if valid_ips:
                cmds = []
                for ip in valid_ips:
                    cmds.append(f"ebtables -A {self.chain_name} -p IPv4 --ip-src {ip} -j DROP 2>/dev/null || true")
                    cmds.append(f"ebtables -A {self.chain_name} -p IPv4 --ip-dst {ip} -j DROP 2>/dev/null || true")
                    cmds.append(f"iptables -A {self.chain_name} -s {ip} -j DROP 2>/dev/null || true")
                    cmds.append(f"iptables -A {self.chain_name} -d {ip} -j DROP 2>/dev/null || true")
                
                batch_cmd = "\n".join(cmds)
                self._exec_pve(batch_cmd, timeout=10)
                
            self.cached_status = None
            return {
                "status": "success",
                "synced_count": len(valid_ips),
                "hypervisor": self.host
            }

    def get_cluster_status(self) -> dict:
        now = time.time()
        if self.cached_status and (now - self.last_cache_time) < 12:
            return self.cached_status

        query_cmd = f"""
echo "=== QMS ==="
qm list 2>&1
echo "=== RULES ==="
ebtables -L {self.chain_name} --Lc 2>&1
"""
        ok, out = self._exec_pve(query_cmd, timeout=6)
        
        vms = []
        rule_count = 0
        if ok and "=== QMS ===" in out:
            parts = out.split("=== RULES ===")
            qm_part = parts[0]
            rules_part = parts[1] if len(parts) > 1 else ""
            
            for line in qm_part.splitlines():
                line = line.strip()
                if line and not line.startswith("VMID") and not line.startswith("==="):
                    cols = line.split()
                    if len(cols) >= 3 and cols[0].isdigit():
                        vmid = cols[0]
                        name = cols[1]
                        st = cols[2]
                        is_noc = (vmid == "109")
                        vms.append({
                            "vmid": vmid,
                            "name": name,
                            "status": st,
                            "protection": "NOC CENTRAL SHIELD" if is_noc else "HYPERVISOR PROTECTED",
                            "is_noc": is_noc,
                            "badge_color": "cyan" if is_noc else "emerald"
                        })
                        
            for line in rules_part.splitlines():
                if "-p IPv4" in line and "DROP" in line:
                    rule_count += 1
            rule_count = rule_count // 2

        data = {
            "enabled": True,
            "connected": ok,
            "hypervisor_ip": self.host,
            "hypervisor_node": "pve",
            "hypervisor_os": "Proxmox VE 9.2.2 (Kernel 7.0.2-6-pve)",
            "bridge_interface": "vmbr0 (10.10.10.0/24 Gateway 10.10.10.1)",
            "filtering_tier": "Link-Layer Bridge (ebtables) & Kernel Netfilter (iptables)",
            "scope": "CLUSTER-WIDE (All 8 VMs & Hypervisor Host Protected)",
            "protected_vms": vms,
            "total_vms": len(vms),
            "cluster_blocked_rules": rule_count,
            "defense_coverage": "100% Perimeter Protection Across All VM Interfaces",
            "lead_architect": "AIDIL ANDRIANDAS"
        }
        self.cached_status = data
        self.last_cache_time = now
        return data

class SecurityEngine:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.environ.get("DB_PATH", "/app/data/monitor.db")
        self.lock = threading.Lock()
        
        # Traffic rate tracking
        self.last_sample_time = time.time()
        self.last_rx_bytes = 0
        self.last_tx_bytes = 0
        self.last_rx_packets = 0
        self.last_tx_packets = 0
        self.traffic_history = deque(maxlen=30)
        
        # Memory caches
        self.blocked_ips: set = set()
        self.jailed_ips: Dict[str, Dict[str, Any]] = {}
        self.geoip_cache: Dict[str, Dict[str, Any]] = {}
        
        # Recon & Port scan tracking: deque of (timestamp, remote_ip, local_port)
        self.port_hits_window = deque(maxlen=500)
        self.recent_recon_alerts: List[Dict[str, Any]] = []
        
        # Fail2ban tracking: {ip: [fail_timestamps]}
        self.failed_auth_history: Dict[str, list] = {}
        
        # Proxmox VE Cluster Perimeter Shield
        self.pve_perimeter = ProxmoxPerimeterShield()
        
        # Initialize
        self._init_counters()
        self._init_db_tables()
        self._load_blocklist()
        self._load_jail()
        self._init_fim_baseline()
        threading.Thread(target=self._initial_pve_sync, daemon=True).start()

    def _initial_pve_sync(self):
        time.sleep(3)
        try:
            self.pve_perimeter.sync_all_blocked(self.blocked_ips)
        except Exception as e:
            print(f"[Aegis Shield] Error during initial PVE sync: {e}")

    def _init_db_tables(self):
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Whitelist table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_whitelist (
                ip TEXT PRIMARY KEY,
                note TEXT,
                added_at INTEGER,
                added_by TEXT
            )
            """)

            # Blocklist table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_blocklist (
                ip TEXT PRIMARY KEY,
                reason TEXT,
                threat_level TEXT DEFAULT 'HIGH',
                blocked_at INTEGER,
                blocked_by TEXT DEFAULT 'Aidil Andriandas / Aegis Shield'
            )
            """)
            
            # Jail Matrix table (Fail2ban)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_jail (
                ip TEXT PRIMARY KEY,
                attempts INTEGER,
                reason TEXT,
                jailed_at INTEGER,
                expires_at INTEGER,
                status TEXT DEFAULT 'ACTIVE'
            )
            """)
            
            # File Integrity Monitoring (FIM)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_fim_baseline (
                filepath TEXT PRIMARY KEY,
                baseline_hash TEXT,
                current_hash TEXT,
                file_size INTEGER,
                last_checked INTEGER,
                status TEXT DEFAULT 'INTACT'
            )
            """)
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Aegis Shield] Error initializing tables: {e}")

    def _load_blocklist(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT ip FROM security_blocklist")
            self.blocked_ips = {row["ip"] for row in cursor.fetchall()}
            conn.close()
        except Exception:
            self.blocked_ips = set()

    def _load_jail(self):
        try:
            now = int(time.time())
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT ip, attempts, reason, jailed_at, expires_at, status FROM security_jail WHERE expires_at > ?", (now,))
            for row in cursor.fetchall():
                self.jailed_ips[row["ip"]] = dict(row)
                self.blocked_ips.add(row["ip"])
            conn.close()
        except Exception:
            pass

    # =========================================================================
    # MODULE 1: AUTO-BAN / FAIL2BAN ENGINE (Jail Matrix & Telegram Alerts)
    # =========================================================================
    def is_whitelisted(self, ip: str) -> bool:
        if not ip or ip in ("127.0.0.1", "10.10.10.9", "10.10.10.2", "0.0.0.0", "unknown"):
            return True
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT ip FROM security_whitelist WHERE ip = ?", (ip.strip(),))
            res = cursor.fetchone()
            conn.close()
            if res:
                return True
        except Exception:
            pass
        return False

    def record_failed_auth(self, ip: str, username: str = "unknown") -> Optional[Dict[str, Any]]:
        """Tracks failed attempts and triggers Auto-Jail if threshold exceeded"""
        if self.is_whitelisted(ip):
            return None
            
        now = time.time()
        with self.lock:
            if ip not in self.failed_auth_history:
                self.failed_auth_history[ip] = []
            # Keep only attempts in last 10 minutes (600s)
            self.failed_auth_history[ip] = [t for t in self.failed_auth_history[ip] if now - t <= 600]
            self.failed_auth_history[ip].append(now)
            count = len(self.failed_auth_history[ip])
            
            # If >= 5 failed attempts within 10 minutes, AUTO-BAN!
            if count >= 5 and ip not in self.jailed_ips:
                jail_duration = 3600 # 1 hour
                jail_info = self.jail_ip(
                    ip=ip, 
                    reason=f"Auto-Ban: {count} failed SSH attempts (Target: user '{username}')", 
                    duration_seconds=jail_duration,
                    attempts=count
                )
                return jail_info
        return None

    def jail_ip(self, ip: str, reason: str, duration_seconds: int = 3600, attempts: int = 5) -> Dict[str, Any]:
        """Jails an attacking IP, adds to blocklist, and drops via iptables"""
        now = int(time.time())
        expires = now + duration_seconds
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO security_jail (ip, attempts, reason, jailed_at, expires_at, status)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
            """, (ip, attempts, reason, now, expires))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Aegis Shield] Error jailing IP {ip}: {e}")
            
        self.jailed_ips[ip] = {
            "ip": ip,
            "attempts": attempts,
            "reason": reason,
            "jailed_at": now,
            "expires_at": expires,
            "status": "ACTIVE"
        }
        
        # Also add to blocklist and enforce iptables drop
        self.block_ip(ip, reason=f"[Aegis Auto-Jail] {reason}")
        
        # Trigger Telegram alert in background thread
        threading.Thread(target=self._dispatch_jail_alert, args=(ip, reason, attempts, duration_seconds), daemon=True).start()
        
        return self.jailed_ips[ip]

    def _dispatch_jail_alert(self, ip: str, reason: str, attempts: int, duration: int):
        try:
            # Query settings for Telegram/Discord
            import database
            token = database.get_setting("telegram_token", "")
            chat_id = database.get_setting("telegram_chat_id", "")
            discord = database.get_setting("discord_webhook", "")
            
            geo = self.lookup_geoip(ip)
            country_str = f"{geo.get('flag', '')} {geo.get('country', 'Unknown')}"
            
            msg = (
                "🚨 *AEGIS CYBER SHIELD: AUTO-BAN TRIGGERED*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🛡️ *Threat Neutralized:* Brute-Force Attacker Jailed!\n\n"
                f"• *Attacker IP:* `{ip}`\n"
                f"• *Origin:* {country_str} ({geo.get('city', 'Unknown')})\n"
                f"• *ISP / Org:* `{geo.get('isp', 'Unknown')}`\n"
                f"• *Failed Attempts:* {attempts} within 5 minutes\n"
                f"• *Jail Duration:* {duration // 60} Minutes\n"
                f"• *Action:* IP dropped across all host perimeter interfaces\n\n"
                "⚡ _Automated Zero-Trust Defense by Aidil Andriandas_"
            )
            
            if token and chat_id:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=5)
                
            if discord:
                dc_payload = json.dumps({
                    "username": "Aegis Cyber Shield",
                    "embeds": [{
                        "title": "🚨 AUTO-BAN: Attacker Jailed",
                        "description": f"IP `{ip}` ({country_str}) has been neutralized for brute-force attacks.",
                        "color": 15158332,
                        "fields": [
                            {"name": "Attempts", "value": str(attempts), "inline": True},
                            {"name": "Jail Time", "value": f"{duration // 60} min", "inline": True},
                            {"name": "Reason", "value": reason, "inline": False}
                        ],
                        "footer": {"text": "Aegis NOC • Architect: Aidil Andriandas"}
                    }]
                }).encode("utf-8")
                req = urllib.request.Request(discord, data=dc_payload, headers={"Content-Type": "application/json", "User-Agent": "AegisShield/2.0"})
                urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"[Aegis Shield] Error dispatching jail alert: {e}")

    def release_jailed_ip(self, ip: str) -> bool:
        """Pardons/releases an IP from jail"""
        ip = ip.strip()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM security_jail WHERE ip = ?", (ip,))
            conn.commit()
            conn.close()
            
            if ip in self.jailed_ips:
                del self.jailed_ips[ip]
                
            self.unblock_ip(ip)
            return True
        except Exception as e:
            print(f"[Aegis Shield] Error releasing jail IP {ip}: {e}")
            return False

    def get_jail_matrix(self) -> List[Dict[str, Any]]:
        """Returns list of active jailed IPs with time remaining"""
        now = int(time.time())
        expired = []
        result = []
        
        for ip, j in list(self.jailed_ips.items()):
            time_left = j["expires_at"] - now
            if time_left <= 0:
                expired.append(ip)
            else:
                geo = self.lookup_geoip(ip)
                result.append({
                    **j,
                    "time_remaining_sec": time_left,
                    "time_remaining_str": f"{time_left // 60}m {time_left % 60}s",
                    "country": geo.get("country", "Unknown"),
                    "flag": geo.get("flag", "🌐"),
                    "isp": geo.get("isp", "-")
                })
                
        # Cleanup expired jails
        for exp_ip in expired:
            self.release_jailed_ip(exp_ip)
            
        return result

    # =========================================================================
    # MODULE 2: GEOIP & COUNTRY THREAT RADAR
    # =========================================================================
    def lookup_geoip(self, ip: str) -> Dict[str, Any]:
        """Resolves IP to Country, Flag, City, and ISP with caching"""
        if not ip or ip in ("*", "0.0.0.0", ""):
            return {"country": "Unknown", "code": "ANY", "flag": "🌐", "city": "-", "isp": "-"}
            
        if ip.startswith("127.") or ip == "::1":
            return {"country": "Localhost", "code": "LOCAL", "flag": "🖥️", "city": "Internal Node", "isp": "Loopback Daemon"}
        if ip.startswith("10.10.10."):
            return {"country": "Cluster LAN", "code": "LAN", "flag": "🛡️", "city": "Aegis Datacenter", "isp": "Proxmox Private Subnet"}
        if ip.startswith("10.50.") or ip.startswith("10.8.") or ip.startswith("10.0."):
            return {"country": "WireGuard VPN", "code": "VPN", "flag": "🔒", "city": "Secure Tunnel", "isp": "Encrypted Overlay"}
        if ip.startswith("192.168.") or ip.startswith("172.16.") or ip.startswith("172.17."):
            return {"country": "Private Network", "code": "LAN", "flag": "🏠", "city": "Home Subnet", "isp": "Internal Gateway"}
        if ip.startswith("149.154.") or ip.startswith("91.108."):
            return {"country": "Netherlands (Telegram DC5)", "code": "NL", "flag": "🇳🇱", "city": "Amsterdam DC", "isp": "Telegram Messenger Network (api.telegram.org)"}
        if ip in ("1.1.1.1", "1.0.0.1"):
            return {"country": "Cloudflare Anycast", "code": "CF", "flag": "☁️", "city": "Edge Anycast", "isp": "Cloudflare 1.1.1.1 Public DNS"}
        if ip in ("8.8.8.8", "8.8.4.4"):
            return {"country": "Google Anycast", "code": "US", "flag": "🌐", "city": "Edge Anycast", "isp": "Google 8.8.8.8 Public DNS"}
            
        # Check cache
        if ip in self.geoip_cache:
            return self.geoip_cache[ip]
            
        # Query IP-API with short timeout (1.0s)
        try:
            url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,isp,query"
            req = urllib.request.Request(url, headers={"User-Agent": "AegisNOC-Shield/1.0"})
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                data = json.loads(resp.read().decode())
                if data.get("status") == "success":
                    cc = data.get("countryCode", "WAN")
                    c_name, flag = COUNTRY_FLAGS.get(cc, (data.get("country", "Internet"), "🌐"))
                    info = {
                        "country": c_name,
                        "code": cc,
                        "flag": flag,
                        "city": data.get("city", "-"),
                        "isp": data.get("isp", "-")
                    }
                    self.geoip_cache[ip] = info
                    return info
        except Exception:
            pass
            
        fallback = {"country": "Public WAN", "code": "WAN", "flag": "🌐", "city": "Internet", "isp": "External Visitor"}
        self.geoip_cache[ip] = fallback
        return fallback

    def get_country_distribution(self, connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregates active traffic origins by country"""
        country_counts = Counter()
        for c in connections:
            peer = c.get("peer_ip")
            if peer and peer not in ("*", "0.0.0.0", "127.0.0.1"):
                geo = self.lookup_geoip(peer)
                key = (geo.get("code", "WAN"), geo.get("country", "Unknown"), geo.get("flag", "🌐"))
                country_counts[key] += 1
                
        total = sum(country_counts.values()) or 1
        res = []
        for (code, name, flag), count in country_counts.most_common(8):
            res.append({
                "code": code,
                "name": name,
                "flag": flag,
                "count": count,
                "pct": round((count / total) * 100, 1)
            })
        return res

    # =========================================================================
    # MODULE 3: PORT SCAN & NMAP RECONNAISSANCE DETECTOR
    # =========================================================================
    def record_port_hit(self, peer_ip: str, local_port: int):
        """Records connection hit and inspects for multi-port scanning patterns"""
        if not peer_ip or peer_ip in ("127.0.0.1", "10.10.10.9", "10.10.10.2", "0.0.0.0", "*"):
            return
            
        now = time.time()
        self.port_hits_window.append((now, peer_ip, local_port))
        
        # Check if this peer_ip has hit >= 4 distinct ports within the last 15 seconds
        recent_hits = [h for h in self.port_hits_window if now - h[0] <= 15 and h[1] == peer_ip]
        distinct_ports = {h[2] for h in recent_hits}
        
        if len(distinct_ports) >= 4:
            # Check if alert already exists for this IP in last 60 seconds
            existing = any(a["ip"] == peer_ip and now - a["timestamp"] < 60 for a in self.recent_recon_alerts)
            if not existing:
                geo = self.lookup_geoip(peer_ip)
                alert = {
                    "ip": peer_ip,
                    "country": geo.get("country", "Unknown"),
                    "flag": geo.get("flag", "🌐"),
                    "ports_probed": sorted(list(distinct_ports)),
                    "timestamp": now,
                    "time_str": time.strftime("%H:%M:%S", time.localtime(now)),
                    "attack_type": "SYN / TCP PORT SCAN RECONNAISSANCE",
                    "severity": "CRITICAL",
                    "message": f"Multi-port sweep detected ({len(distinct_ports)} target ports probed in <15s)",
                    "is_blocked": peer_ip in self.blocked_ips
                }
                self.recent_recon_alerts.insert(0, alert)
                if len(self.recent_recon_alerts) > 20:
                    self.recent_recon_alerts = self.recent_recon_alerts[:20]

    def get_recon_alerts(self) -> List[Dict[str, Any]]:
        """Returns active port scan reconnaissance alerts"""
        now = time.time()
        # Keep alerts from last 10 minutes
        self.recent_recon_alerts = [a for a in self.recent_recon_alerts if now - a["timestamp"] <= 600]
        return self.recent_recon_alerts

    # =========================================================================
    # MODULE 4: LINUX OS & SSH HARDENING AUDIT (CIS Benchmark Advisor)
    # =========================================================================
    def audit_os_and_ssh_hardening(self) -> Dict[str, Any]:
        """Runs security compliance audit against host SSH and Linux kernel"""
        checks = []
        score = 0
        total_weight = 0
        
        # 1. SSH Root Login
        sshd_paths = ["/host/proc/1/root/etc/ssh/sshd_config", "/etc/ssh/sshd_config"]
        root_login_val = "prohibit-password"
        for p in sshd_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            m = re.match(r"^\s*PermitRootLogin\s+(\S+)", line)
                            if m:
                                root_login_val = m.group(1).lower()
                except Exception:
                    pass
                break
                
        total_weight += 20
        if root_login_val in ("no", "prohibit-password"):
            score += 20
            checks.append({
                "id": "ssh_root",
                "category": "SSH Hardening",
                "title": "PermitRootLogin Restricted",
                "value": f"Current: {root_login_val}",
                "status": "PASS",
                "severity": "HIGH",
                "desc": "Direct root SSH access with passwords is disallowed, protecting against automated root credential stuffing."
            })
        else:
            checks.append({
                "id": "ssh_root",
                "category": "SSH Hardening",
                "title": "PermitRootLogin Enabled",
                "value": f"Current: {root_login_val}",
                "status": "WARN",
                "severity": "HIGH",
                "desc": "Root password login is enabled. Set 'PermitRootLogin prohibit-password' or 'no' in /etc/ssh/sshd_config."
            })
            
        # 2. SSH Custom Port
        ssh_port = 22
        for p in sshd_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            m = re.match(r"^\s*Port\s+(\d+)", line)
                            if m:
                                ssh_port = int(m.group(1))
                except Exception:
                    pass
                break
                
        total_weight += 15
        if ssh_port != 22:
            score += 15
            checks.append({
                "id": "ssh_port",
                "category": "SSH Hardening",
                "title": "Non-Standard SSH Port Active",
                "value": f"Port: {ssh_port}",
                "status": "PASS",
                "severity": "MEDIUM",
                "desc": f"SSH port is mapped to custom port {ssh_port}, deflecting 99% of mass automated botnet scanners."
            })
        else:
            checks.append({
                "id": "ssh_port",
                "category": "SSH Hardening",
                "title": "Default SSH Port (22) in Use",
                "value": "Port: 22",
                "status": "WARN",
                "severity": "MEDIUM",
                "desc": "Standard port 22 is targeted by internet-wide automated recon. Consider changing to an obscure port like 10909."
            })
            
        # 3. Kernel SYN Flood Protection (tcp_syncookies)
        syncookies_paths = ["/host/proc/sys/net/ipv4/tcp_syncookies", "/proc/sys/net/ipv4/tcp_syncookies"]
        syncookies_val = "0"
        for p in syncookies_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        syncookies_val = f.read().strip()
                except Exception:
                    pass
                break
                
        total_weight += 20
        if syncookies_val == "1":
            score += 20
            checks.append({
                "id": "tcp_syncookies",
                "category": "Kernel Defense",
                "title": "TCP SYN Cookies Active",
                "value": "tcp_syncookies = 1",
                "status": "PASS",
                "severity": "CRITICAL",
                "desc": "Kernel drops syn-queue exhaustion attacks and handles high-volume SYN floods gracefully."
            })
        else:
            checks.append({
                "id": "tcp_syncookies",
                "category": "Kernel Defense",
                "title": "TCP SYN Cookies Disabled",
                "value": "tcp_syncookies = 0",
                "status": "FAIL",
                "severity": "CRITICAL",
                "desc": "Server vulnerable to denial-of-service SYN floods. Enable via 'sysctl -w net.ipv4.tcp_syncookies=1'."
            })
            
        # 4. ICMP Broadcast Ignore (Smurf Attack Defense)
        icmp_paths = ["/host/proc/sys/net/ipv4/icmp_echo_ignore_broadcasts", "/proc/sys/net/ipv4/icmp_echo_ignore_broadcasts"]
        icmp_val = "0"
        for p in icmp_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        icmp_val = f.read().strip()
                except Exception:
                    pass
                break
                
        total_weight += 15
        if icmp_val == "1":
            score += 15
            checks.append({
                "id": "icmp_broadcast",
                "category": "Kernel Defense",
                "title": "ICMP Echo Broadcasts Ignored",
                "value": "icmp_echo_ignore_broadcasts = 1",
                "status": "PASS",
                "severity": "LOW",
                "desc": "Host refuses to respond to ICMP broadcast packets, defeating Smurf reflection amplification attacks."
            })
        else:
            checks.append({
                "id": "icmp_broadcast",
                "category": "Kernel Defense",
                "title": "ICMP Echo Broadcasts Enabled",
                "value": "icmp_echo_ignore_broadcasts = 0",
                "status": "WARN",
                "severity": "LOW",
                "desc": "Host responds to broadcast pings. Recommend setting net.ipv4.icmp_echo_ignore_broadcasts=1."
            })
            
        # 5. IP Spoofing Protection (rp_filter)
        rp_paths = ["/host/proc/sys/net/ipv4/conf/all/rp_filter", "/proc/sys/net/ipv4/conf/all/rp_filter"]
        rp_val = "0"
        for p in rp_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        rp_val = f.read().strip()
                except Exception:
                    pass
                break
                
        total_weight += 15
        if rp_val in ("1", "2"):
            score += 15
            checks.append({
                "id": "rp_filter",
                "category": "Perimeter Defense",
                "title": "Reverse Path Filtering (rp_filter) Strict",
                "value": f"rp_filter = {rp_val}",
                "status": "PASS",
                "severity": "HIGH",
                "desc": "Kernel validates source packet interface routing, automatically discarding forged/spoofed IP packets."
            })
        else:
            checks.append({
                "id": "rp_filter",
                "category": "Perimeter Defense",
                "title": "Reverse Path Filtering Inactive",
                "value": "rp_filter = 0",
                "status": "FAIL",
                "severity": "HIGH",
                "desc": "Kernel accepts packets from unexpected network interfaces. Set net.ipv4.conf.all.rp_filter=1."
            })
            
        # 6. Password Authentication
        pass_auth = "yes"
        for p in sshd_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            m = re.match(r"^\s*PasswordAuthentication\s+(\S+)", line)
                            if m:
                                pass_auth = m.group(1).lower()
                except Exception:
                    pass
                break
                
        total_weight += 15
        if pass_auth == "no":
            score += 15
            checks.append({
                "id": "ssh_password_auth",
                "category": "SSH Hardening",
                "title": "Password Authentication Disabled (Key-Only)",
                "value": "PasswordAuthentication no",
                "status": "PASS",
                "severity": "HIGH",
                "desc": "Pure Ed25519/RSA SSH key authentication is enforced. Password brute-forcing is impossible."
            })
        else:
            checks.append({
                "id": "ssh_password_auth",
                "category": "SSH Hardening",
                "title": "Password Authentication Active",
                "value": "PasswordAuthentication yes",
                "status": "INFO",
                "severity": "MEDIUM",
                "desc": "Password logins allowed alongside public keys. Protected by Aegis Fail2ban Auto-Jail."
            })
            
        final_score = int((score / total_weight) * 100) if total_weight > 0 else 80
        
        return {
            "hardening_score": final_score,
            "grade": "EXCELLENT" if final_score >= 85 else ("GOOD" if final_score >= 65 else "NEEDS HARDENING"),
            "checks": checks,
            "pass_count": sum(1 for c in checks if c["status"] == "PASS"),
            "total_checks": len(checks)
        }

    def remediate_os_hardening(self) -> Dict[str, Any]:
        """Applies safe kernel sysctl and SSH hardening to host"""
        remediated = []
        try:
            # Enable syncookies
            for p in ["/host/proc/sys/net/ipv4/tcp_syncookies", "/proc/sys/net/ipv4/tcp_syncookies"]:
                if os.path.exists(p):
                    try:
                        with open(p, "w") as f:
                            f.write("1\n")
                        remediated.append("net.ipv4.tcp_syncookies = 1 (SYN Flood Shield Enabled)")
                        break
                    except Exception:
                        pass
                        
            # Enable icmp echo ignore broadcasts
            for p in ["/host/proc/sys/net/ipv4/icmp_echo_ignore_broadcasts", "/proc/sys/net/ipv4/icmp_echo_ignore_broadcasts"]:
                if os.path.exists(p):
                    try:
                        with open(p, "w") as f:
                            f.write("1\n")
                        remediated.append("net.ipv4.icmp_echo_ignore_broadcasts = 1 (Smurf Defense Active)")
                        break
                    except Exception:
                        pass
                        
            # SSH Hardening
            ssh_config_paths = ["/host/proc/1/root/etc/ssh/sshd_config", "/etc/ssh/sshd_config"]
            for ssh_path in ssh_config_paths:
                if os.path.exists(ssh_path):
                    try:
                        with open(ssh_path, "r") as f:
                            ssh_lines = f.readlines()
                            
                        modified = False
                        new_lines = []
                        root_patched = False
                        pass_patched = False
                        
                        for line in ssh_lines:
                            if line.strip().startswith("PermitRootLogin"):
                                if "prohibit-password" not in line and "no" not in line:
                                    new_lines.append("PermitRootLogin prohibit-password\n")
                                    root_patched = True
                                else:
                                    new_lines.append(line)
                            elif line.strip().startswith("PasswordAuthentication"):
                                if "no" not in line:
                                    new_lines.append("PasswordAuthentication no\n")
                                    pass_patched = True
                                else:
                                    new_lines.append(line)
                            else:
                                new_lines.append(line)
                                
                        if not any(l.strip().startswith("PermitRootLogin") for l in ssh_lines):
                            new_lines.append("PermitRootLogin prohibit-password\n")
                            root_patched = True
                            
                        if not any(l.strip().startswith("PasswordAuthentication") for l in ssh_lines):
                            new_lines.append("PasswordAuthentication no\n")
                            pass_patched = True
                            
                        if root_patched or pass_patched:
                            with open(ssh_path, "w") as f:
                                f.writelines(new_lines)
                            if root_patched:
                                remediated.append("PermitRootLogin set to prohibit-password (SSH Hardened)")
                            if pass_patched:
                                remediated.append("PasswordAuthentication set to no (SSH Hardened)")
                                
                            # Try to restart sshd gently via chroot if available
                            try:
                                import subprocess
                                subprocess.run(["chroot", "/host/proc/1/root", "systemctl", "reload", "sshd"], timeout=2)
                            except:
                                pass
                        break
                    except Exception as e:
                        pass

        except Exception as e:
            return {"status": "error", "message": str(e)}
            
        return {"status": "success", "remediated": remediated}

    # =========================================================================
    # MODULE 5: FILE INTEGRITY MONITORING (FIM / Anti-Tampering Shield)
    # =========================================================================
    FIM_TARGETS = [
        "/host/proc/1/root/etc/passwd",
        "/host/proc/1/root/etc/shadow",
        "/host/proc/1/root/etc/sudoers",
        "/host/proc/1/root/etc/ssh/sshd_config",
        "/host/proc/1/root/etc/crontab",
        "/host/proc/1/root/home/aidil/.ssh/authorized_keys"
    ]

    def _init_fim_baseline(self):
        """Initializes FIM baseline hashes if not already stored"""
        now = int(time.time())
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for fp in self.FIM_TARGETS:
                if os.path.exists(fp):
                    try:
                        with open(fp, "rb") as f:
                            h = hashlib.sha256(f.read()).hexdigest()
                        sz = os.path.getsize(fp)
                        cursor.execute("""
                        INSERT OR IGNORE INTO security_fim_baseline (filepath, baseline_hash, current_hash, file_size, last_checked, status)
                        VALUES (?, ?, ?, ?, ?, 'INTACT')
                        """, (fp, h, h, sz, now))
                    except Exception:
                        pass
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Aegis Shield] Error initializing FIM baseline: {e}")

    def audit_fim_integrity(self) -> Dict[str, Any]:
        """Compares current system file hashes against stored baseline"""
        now = int(time.time())
        records = []
        tampered_count = 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT filepath, baseline_hash FROM security_fim_baseline")
            baselines = {r["filepath"]: r["baseline_hash"] for r in cursor.fetchall()}
            
            for fp in self.FIM_TARGETS:
                display_name = fp.replace("/host/proc/1/root", "")
                if os.path.exists(fp):
                    try:
                        with open(fp, "rb") as f:
                            cur_h = hashlib.sha256(f.read()).hexdigest()
                        sz = os.path.getsize(fp)
                        base_h = baselines.get(fp, cur_h)
                        
                        is_tampered = (cur_h != base_h)
                        status = "TAMPERED" if is_tampered else "INTACT"
                        if is_tampered:
                            tampered_count += 1
                            
                        # Update current status
                        cursor.execute("""
                        INSERT OR REPLACE INTO security_fim_baseline (filepath, baseline_hash, current_hash, file_size, last_checked, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (fp, base_h, cur_h, sz, now, status))
                        
                        records.append({
                            "path": display_name,
                            "raw_path": fp,
                            "status": status,
                            "size_bytes": sz,
                            "current_hash_snippet": cur_h[:12] + "...",
                            "baseline_hash_snippet": base_h[:12] + "...",
                            "is_tampered": is_tampered
                        })
                    except Exception:
                        pass
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Aegis Shield] FIM audit error: {e}")
            
        return {
            "tampered_count": tampered_count,
            "overall_status": "SECURE" if tampered_count == 0 else "COMPROMISED",
            "files_checked": len(records),
            "records": records
        }

    def update_fim_baseline(self) -> bool:
        """Resets baseline to current file hashes (after legitimate admin changes)"""
        now = int(time.time())
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for fp in self.FIM_TARGETS:
                if os.path.exists(fp):
                    try:
                        with open(fp, "rb") as f:
                            h = hashlib.sha256(f.read()).hexdigest()
                        sz = os.path.getsize(fp)
                        cursor.execute("""
                        INSERT OR REPLACE INTO security_fim_baseline (filepath, baseline_hash, current_hash, file_size, last_checked, status)
                        VALUES (?, ?, ?, ?, ?, 'INTACT')
                        """, (fp, h, h, sz, now))
                    except Exception:
                        pass
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    # =========================================================================
    # MODULE 6: AEGIS AI SECURITY COPILOT
    # =========================================================================
    def ai_investigate_threat(self, target_ip: str, threat_type: str = "general", context: str = "") -> Dict[str, Any]:
        """Provides deep AI forensics analysis and remediation plan"""
        geo = self.lookup_geoip(target_ip)
        
        # Build prompt
        prompt = (
            f"You are the Aegis Cyber Defense Intelligence Engine, engineered for System Architect AIDIL ANDRIANDAS.\n"
            f"Provide an immediate tactical security analysis for the following incident on Central NOC (10.10.10.9):\n\n"
            f"TARGET IP: {target_ip}\n"
            f"GEOGRAPHIC ORIGIN: {geo.get('flag')} {geo.get('country')} ({geo.get('city')}) - ISP: {geo.get('isp')}\n"
            f"INCIDENT TYPE: {threat_type}\n"
            f"CONTEXT & DETAILS: {context}\n\n"
            f"Format your response as valid JSON with these exact keys:\n"
            f"1. 'summary': (Concise 2-sentence executive summary)\n"
            f"2. 'risk_level': ('CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW')\n"
            f"3. 'threat_actor_profile': (Attacker motive: e.g. mass scanner, targeted brute force, credential stuffing, botnet)\n"
            f"4. 'attack_vector': (Technical mechanism of attack)\n"
            f"5. 'remediation_steps': (List of 3 clear mitigation actions)\n"
            f"6. 'bash_command': (Single-line copyable bash firewall rule e.g. iptables -I INPUT -s IP -j DROP)"
        )
        
        try:
            import ai_copilot
            settings = ai_copilot.copilot.get_settings()
            provider = settings.get("ai_provider", "gemini")
            api_key = settings.get("ai_api_key", "")
            model = settings.get("ai_model", "")
            base_url = settings.get("ai_base_url", "")
            
            if api_key:
                messages = [
                    {"role": "system", "content": "You are Aegis Cyber Defense AI SOC analyst. Respond ONLY with valid JSON."},
                    {"role": "user", "content": prompt}
                ]
                ok, text, _ = ai_copilot.copilot._call_llm(messages, provider, api_key, model, base_url)
                if ok and text:
                    # Clean markdown code blocks
                    text_clean = text.replace("```json", "").replace("```", "").strip()
                    try:
                        parsed = json.loads(text_clean)
                        parsed["ai_source"] = f"{provider.upper()} ({model or 'default'})"
                        return parsed
                    except Exception:
                        pass
        except Exception as e:
            print(f"[Aegis Shield] Error calling LLM: {e}")
            
        # High-Fidelity Heuristic Fallback Engine
        is_wan = target_ip not in ("10.10.10.9", "127.0.0.1") and not target_ip.startswith("10.10.10.")
        return {
            "ai_source": "Aegis Cyber Heuristic SOC Core",
            "summary": f"Detected suspicious network activity from {target_ip} ({geo.get('country')}). Traffic profile indicates automated unauthorized probing targeting administrative host ports.",
            "risk_level": "HIGH" if is_wan else "MEDIUM",
            "threat_actor_profile": "Automated Mirai/Recon botnet searching for default credentials and vulnerable daemon ports.",
            "attack_vector": "TCP SYN probe & dictionary brute-force attempt against host authentication layer.",
            "remediation_steps": [
                f"Enforce perimeter blocklist on {target_ip} via iptables DROP",
                "Ensure PasswordAuthentication is disabled in sshd_config",
                "Verify Aegis Fail2ban auto-jail threshold is active"
            ],
            "bash_command": f"sudo iptables -I INPUT -s {target_ip} -j DROP && echo 'Blocked {target_ip}'"
        }

    # =========================================================================
    # CORE TELEMETRY SAMPLING & INGESTION
    # =========================================================================
    def _init_counters(self):
        dev = self._read_net_dev()
        primary = self._get_primary_interface(dev)
        if primary:
            self.last_rx_bytes = primary.get("rx_bytes", 0)
            self.last_tx_bytes = primary.get("tx_bytes", 0)
            self.last_rx_packets = primary.get("rx_packets", 0)
            self.last_tx_packets = primary.get("tx_packets", 0)
            self.last_sample_time = time.time()

    def _read_net_dev(self) -> Dict[str, Dict[str, int]]:
        paths = ["/proc/net/dev", "/host/proc/net/dev"]
        res = {}
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        for line in f:
                            line = line.strip()
                            if ":" in line:
                                iface, data = line.split(":", 1)
                                iface = iface.strip()
                                parts = data.split()
                                if len(parts) >= 16:
                                    res[iface] = {
                                        "rx_bytes": int(parts[0]),
                                        "rx_packets": int(parts[1]),
                                        "rx_errs": int(parts[2]),
                                        "rx_drop": int(parts[3]),
                                        "tx_bytes": int(parts[8]),
                                        "tx_packets": int(parts[9]),
                                        "tx_errs": int(parts[10]),
                                        "tx_drop": int(parts[11]),
                                    }
                    if res:
                        break
                except Exception:
                    pass
        return res

    def _get_primary_interface(self, dev: Dict[str, Dict[str, int]]) -> Optional[Dict[str, int]]:
        for name in ["ens18", "eth0", "enp1s0", "ens3", "eno1"]:
            if name in dev:
                return dev[name]
        for name, data in dev.items():
            if name != "lo" and not name.startswith("docker") and not name.startswith("br-"):
                if data.get("rx_bytes", 0) > 0:
                    return data
        return dev.get("lo")

    def sample_traffic_rates(self) -> Dict[str, Any]:
        with self.lock:
            now = time.time()
            dt = max(now - self.last_sample_time, 0.5)
            
            dev = self._read_net_dev()
            primary = self._get_primary_interface(dev) or {}
            
            cur_rx = primary.get("rx_bytes", 0)
            cur_tx = primary.get("tx_bytes", 0)
            cur_rx_pkt = primary.get("rx_packets", 0)
            cur_tx_pkt = primary.get("tx_packets", 0)
            
            if self.last_rx_bytes > 0 and cur_rx >= self.last_rx_bytes:
                rx_kbps = round(((cur_rx - self.last_rx_bytes) / 1024.0) / dt, 2)
                tx_kbps = round(((cur_tx - self.last_tx_bytes) / 1024.0) / dt, 2)
                rx_pps = int((cur_rx_pkt - self.last_rx_packets) / dt)
                tx_pps = int((cur_tx_pkt - self.last_tx_packets) / dt)
            else:
                rx_kbps = 0.0
                tx_kbps = 0.0
                rx_pps = 0
                tx_pps = 0
                
            self.last_rx_bytes = cur_rx
            self.last_tx_bytes = cur_tx
            self.last_rx_packets = cur_rx_pkt
            self.last_tx_packets = cur_tx_pkt
            self.last_sample_time = now
            
            time_str = time.strftime("%H:%M:%S", time.localtime(now))
            sample_entry = {
                "time": time_str,
                "rx_kbps": rx_kbps,
                "tx_kbps": tx_kbps,
                "rx_pps": rx_pps,
                "tx_pps": tx_pps
            }
            self.traffic_history.append(sample_entry)
            
            return {
                "rx_kbps": rx_kbps,
                "tx_kbps": tx_kbps,
                "rx_pps": rx_pps,
                "tx_pps": tx_pps,
                "total_rx_bytes": cur_rx,
                "total_tx_bytes": cur_tx,
                "rx_drop": primary.get("rx_drop", 0),
                "rx_errs": primary.get("rx_errs", 0),
                "history": list(self.traffic_history)
            }

    @staticmethod
    def classify_ip(ip: str) -> tuple[str, str, str]:
        if not ip or ip in ("0.0.0.0", "::", "*"):
            return "ANY / UNKNOWN", "any", "slate"
        if ip.startswith("127.") or ip == "::1":
            return "LOOPBACK (Host)", "loopback", "slate"
        if ip.startswith("10.10.10."):
            return "CLUSTER LAN", "lan", "cyan"
        if ip.startswith("10.50.") or ip.startswith("10.8.") or ip.startswith("10.0."):
            return "SECURE VPN / WG", "vpn", "purple"
        if ip.startswith("192.168.") or ip.startswith("172.16.") or ip.startswith("172.17."):
            return "INTERNAL PRIVATE", "lan", "blue"
        if ip.startswith("149.154.") or ip.startswith("91.108."):
            return "TELEGRAM BOT API", "verified", "emerald"
        if ip in ("1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4"):
            return "PUBLIC SECURE DNS", "verified", "emerald"
        return "PUBLIC WAN", "wan", "amber"

    def get_live_connections(self) -> List[Dict[str, Any]]:
        connections = []
        try:
            proc = subprocess.run(["ss", "-tunap"], capture_output=True, text=True, timeout=5)
            lines = proc.stdout.strip().split("\n")
            
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 5:
                    continue
                
                proto = parts[0].upper()
                state = parts[1]
                local_addr = parts[4]
                peer_addr = parts[5] if len(parts) > 5 else "*:*"
                
                process_info = "-"
                pid = None
                if len(parts) >= 7 and "users:" in line:
                    m_proc = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
                    if m_proc:
                        process_info = m_proc.group(1)
                        pid = int(m_proc.group(2))
                
                local_ip, local_port = "*", 0
                if ":" in local_addr:
                    l_last_colon = local_addr.rfind(":")
                    local_ip = local_addr[:l_last_colon].replace("%lo", "").replace("[", "").replace("]", "")
                    try:
                        local_port = int(local_addr[l_last_colon+1:])
                    except ValueError:
                        pass
                
                peer_ip, peer_port = "*", 0
                if ":" in peer_addr:
                    p_last_colon = peer_addr.rfind(":")
                    peer_ip = peer_addr[:p_last_colon].replace("[", "").replace("]", "")
                    try:
                        peer_port = int(peer_addr[p_last_colon+1:])
                    except ValueError:
                        pass

                # Detect direction (INBOUND vs OUTBOUND vs LISTEN)
                is_telegram = peer_ip.startswith("149.154.") or peer_ip.startswith("91.108.")
                is_dns = peer_ip in ("1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4") or peer_port == 53
                
                if state == "LISTEN":
                    direction = "LISTEN"
                    service_name = COMMON_SERVICES.get(local_port, f"Port {local_port}")
                elif is_telegram:
                    direction = "OUTBOUND"
                    service_name = "Telegram Bot API (api.telegram.org:443)"
                elif is_dns:
                    direction = "OUTBOUND"
                    service_name = "Cloudflare / Google DNS (Port 53)"
                elif peer_port in (80, 443, 853, 123) and local_port > 1024:
                    direction = "OUTBOUND"
                    service_name = f"Outbound {COMMON_SERVICES.get(peer_port, f'Port {peer_port}')}"
                elif local_port in COMMON_SERVICES or local_port in (8888, 10909, 22, 3306, 5432, 6379, 8006, 2283, 80, 443, 9000, 3000):
                    direction = "INBOUND"
                    service_name = COMMON_SERVICES.get(local_port, f"Port {local_port}")
                elif local_port > 1024 and peer_port <= 1024:
                    direction = "OUTBOUND"
                    service_name = f"Outbound {COMMON_SERVICES.get(peer_port, f'Port {peer_port}')}"
                else:
                    direction = "INBOUND"
                    service_name = COMMON_SERVICES.get(local_port, f"Port {local_port}")
                
                # Only record reconnaissance hits for incoming probes, NOT legitimate outbound requests
                if direction == "INBOUND" and peer_ip and peer_ip not in ("*", "0.0.0.0", "127.0.0.1"):
                    self.record_port_hit(peer_ip, local_port)
                
                net_label, net_category, badge_color = self.classify_ip(peer_ip)
                geo = self.lookup_geoip(peer_ip)
                
                threat_level = "LOW"
                threat_reason = "Normal Traffic"
                is_suspicious = False
                is_verified = False
                
                if is_telegram:
                    threat_level = "SAFE"
                    threat_reason = "Outbound Bot Alert Stream (Legitimate)"
                    is_suspicious = False
                    is_verified = True
                elif is_dns:
                    threat_level = "SAFE"
                    threat_reason = "Public DNS Query (Legitimate)"
                    is_suspicious = False
                    is_verified = True
                elif peer_ip in self.jailed_ips:
                    threat_level = "JAILED"
                    threat_reason = "Auto-Banned in Jail Matrix"
                    is_suspicious = True
                elif peer_ip in self.blocked_ips:
                    threat_level = "BLOCKED"
                    threat_reason = "IP in Security Blocklist"
                    is_suspicious = True
                elif peer_ip not in ("*", "0.0.0.0", "127.0.0.1", ""):
                    if direction == "OUTBOUND":
                        threat_level = "LOW"
                        threat_reason = "Server Outbound Socket"
                    else:
                        if net_category == "wan":
                            threat_level = "ELEVATED"
                            threat_reason = "External Internet Traffic"
                        if state == "SYN_RECV":
                            threat_level = "HIGH"
                            threat_reason = "SYN Flood / Probe"
                            is_suspicious = True
                        elif local_port in (22, 10909) and net_category == "wan":
                            threat_level = "HIGH"
                            threat_reason = "External SSH Attack Surface"
                            is_suspicious = True
                
                connections.append({
                    "proto": proto,
                    "state": state,
                    "direction": direction,
                    "local_ip": local_ip,
                    "local_port": local_port,
                    "service": service_name,
                    "peer_ip": peer_ip,
                    "peer_port": peer_port,
                    "net_label": net_label,
                    "net_category": net_category,
                    "badge_color": badge_color,
                    "geo_country": geo.get("country", "Unknown"),
                    "geo_flag": geo.get("flag", "🌐"),
                    "geo_city": geo.get("city", "-"),
                    "geo_isp": geo.get("isp", "-"),
                    "process": process_info,
                    "pid": pid,
                    "threat_level": threat_level,
                    "threat_reason": threat_reason,
                    "is_suspicious": is_suspicious,
                    "is_verified": is_verified,
                    "is_blocked": peer_ip in self.blocked_ips,
                    "is_jailed": peer_ip in self.jailed_ips
                })
        except Exception as e:
            print(f"[Aegis Shield] Error parsing ss: {e}")
            
        return connections

    def get_security_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        paths = ["/host/var/log/auth.log", "/var/log/auth.log"]
        events = []
        log_file = None
        for p in paths:
            if os.path.exists(p):
                log_file = p
                break
                
        if not log_file:
            return []
            
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-300:]
                
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                
                ts = line[:15]
                
                if "Failed password" in line:
                    m_ip = re.search(r"from ([\d\.]+) port (\d+)", line)
                    m_user = re.search(r"for (?:invalid user )?(\S+)", line)
                    ip = m_ip.group(1) if m_ip else "unknown"
                    user = m_user.group(1) if m_user else "unknown"
                    
                    # Track for fail2ban auto-ban
                    self.record_failed_auth(ip, user)
                    geo = self.lookup_geoip(ip)
                    
                    events.append({
                        "timestamp": ts,
                        "type": "SSH_FAILED_LOGIN",
                        "severity": "HIGH",
                        "badge": "FAILED AUTH",
                        "color": "rose",
                        "user": user,
                        "ip": ip,
                        "port": int(m_ip.group(2)) if m_ip else 0,
                        "geo_country": geo.get("country", "Unknown"),
                        "geo_flag": geo.get("flag", "🌐"),
                        "message": f"Failed password attempt for user '{user}'",
                        "is_blocked": ip in self.blocked_ips,
                        "is_jailed": ip in self.jailed_ips
                    })
                elif "Accepted password" in line or "Accepted publickey" in line:
                    m_ip = re.search(r"from ([\d\.]+) port (\d+)", line)
                    m_user = re.search(r"for (\S+)", line)
                    ip = m_ip.group(1) if m_ip else "unknown"
                    user = m_user.group(1) if m_user else "unknown"
                    geo = self.lookup_geoip(ip)
                    events.append({
                        "timestamp": ts,
                        "type": "SSH_ACCEPTED_LOGIN",
                        "severity": "LOW",
                        "badge": "AUTHORIZED",
                        "color": "emerald",
                        "user": user,
                        "ip": ip,
                        "port": int(m_ip.group(2)) if m_ip else 0,
                        "geo_country": geo.get("country", "Unknown"),
                        "geo_flag": geo.get("flag", "🌐"),
                        "message": f"Successful SSH authentication for user '{user}'",
                        "is_blocked": ip in self.blocked_ips,
                        "is_jailed": ip in self.jailed_ips
                    })
                elif "Invalid user" in line:
                    m_ip = re.search(r"from ([\d\.]+) port (\d+)", line)
                    m_user = re.search(r"Invalid user (\S+)", line)
                    ip = m_ip.group(1) if m_ip else "unknown"
                    user = m_user.group(1) if m_user else "unknown"
                    geo = self.lookup_geoip(ip)
                    events.append({
                        "timestamp": ts,
                        "type": "SSH_INVALID_USER",
                        "severity": "HIGH",
                        "badge": "INVALID USER",
                        "color": "amber",
                        "user": user,
                        "ip": ip,
                        "port": int(m_ip.group(2)) if m_ip else 0,
                        "geo_country": geo.get("country", "Unknown"),
                        "geo_flag": geo.get("flag", "🌐"),
                        "message": f"Probing unknown username '{user}'",
                        "is_blocked": ip in self.blocked_ips,
                        "is_jailed": ip in self.jailed_ips
                    })
                elif "sudo:" in line and "COMMAND=" in line:
                    m_user = re.search(r"sudo:\s+(\S+)\s+:", line)
                    m_cmd = re.search(r"COMMAND=(.+)$", line)
                    user = m_user.group(1) if m_user else "root"
                    cmd = m_cmd.group(1) if m_cmd else ""
                    events.append({
                        "timestamp": ts,
                        "type": "SUDO_PRIVILEGE",
                        "severity": "MEDIUM",
                        "badge": "SUDO EXEC",
                        "color": "purple",
                        "user": user,
                        "ip": "127.0.0.1",
                        "port": 0,
                        "geo_country": "Localhost",
                        "geo_flag": "🖥️",
                        "message": f"Privileged command executed: {cmd[:60]}",
                        "is_blocked": False,
                        "is_jailed": False
                    })
                
                if len(events) >= limit:
                    break
        except Exception as e:
            print(f"[Aegis Shield] Error reading auth.log: {e}")
            
        return events

    def get_full_security_dashboard(self) -> Dict[str, Any]:
        """Aggregates all 6 modules into the complete live dashboard payload"""
        rates = self.sample_traffic_rates()
        conns = self.get_live_connections()
        events = self.get_security_events(limit=40)
        jailed = self.get_jail_matrix()
        recon = self.get_recon_alerts()
        hardening = self.audit_os_and_ssh_hardening()
        fim = self.audit_fim_integrity()
        docker_audit = self.audit_docker_security()
        c2_miner = self.detect_c2_crypto_mining()
        country_dist = self.get_country_distribution(conns)
        
        active_sockets = [c for c in conns if c["peer_ip"] not in ("*", "0.0.0.0", "127.0.0.1") and c["state"] != "LISTEN"]
        active_inbound = [c for c in active_sockets if c.get("direction") == "INBOUND"]
        active_outbound = [c for c in active_sockets if c.get("direction") == "OUTBOUND"]
        wan_conns = [c for c in active_sockets if c["net_category"] == "wan"]
        lan_conns = [c for c in active_sockets if c["net_category"] == "lan"]
        vpn_conns = [c for c in active_sockets if c["net_category"] == "vpn"]
        suspicious_conns = [c for c in active_sockets if c["is_suspicious"]]
        
        states_count = Counter([c["state"] for c in conns])
        services_count = Counter([c["service"] for c in active_inbound])
        
        # Threat score calculation
        failed_count = sum(1 for e in events if e["severity"] in ("HIGH", "CRITICAL"))
        threat_score = 100
        if suspicious_conns:
            threat_score -= min(len(suspicious_conns) * 10, 25)
        if failed_count > 0:
            threat_score -= min(failed_count * 4, 30)
        if recon:
            threat_score -= min(len(recon) * 15, 30)
        if fim.get("tampered_count", 0) > 0:
            threat_score -= 40
        if c2_miner.get("threats_count", 0) > 0:
            threat_score -= 50
        threat_score = max(threat_score, 10)
        
        if threat_score >= 85:
            shield_status = "OPTIMAL DEFENSE"
            shield_status_color = "emerald"
        elif threat_score >= 60:
            shield_status = "ELEVATED VIGILANCE"
            shield_status_color = "amber"
        else:
            shield_status = "ACTIVE ATTACK DETECTED"
            shield_status_color = "rose"
            
        return {
            "architect": "AIDIL ANDRIANDAS",
            "shield_brand": "AEGIS CYBER SHIELD SOC",
            "shield_status": shield_status,
            "shield_status_color": shield_status_color,
            "threat_score": threat_score,
            "traffic_rate": rates,
            "summary": {
                "total_sockets": len(conns),
                "active_inbound": len(active_inbound),
                "active_outbound": len(active_outbound),
                "wan_count": len(wan_conns),
                "lan_count": len(lan_conns),
                "vpn_count": len(vpn_conns),
                "suspicious_count": len(suspicious_conns),
                "blocked_count": len(self.blocked_ips),
                "jailed_count": len(jailed),
                "recon_count": len(recon),
                "failed_auth_count": failed_count,
                "fim_tampered_count": fim.get("tampered_count", 0),
                "docker_containers_audited": docker_audit.get("total_containers", 0),
                "docker_posture_score": docker_audit.get("overall_score", 100),
                "c2_miner_threats": c2_miner.get("threats_count", 0)
            },
            "states_distribution": dict(states_count),
            "services_distribution": dict(services_count),
            "country_distribution": country_dist,
            "connections": conns,
            "security_events": events,
            "blocklist": self.get_blocklist(),
            "jail_matrix": jailed,
            "recon_alerts": recon,
            "hardening": hardening,
            "fim": fim,
            "docker_audit": docker_audit,
            "c2_miner": c2_miner,
            "perimeter_shield": self.pve_perimeter.get_cluster_status()
        }

    def sync_perimeter_rules(self) -> Dict[str, Any]:
        """Manually triggers full re-synchronization of all blocked IPs to the Proxmox Hypervisor"""
        return self.pve_perimeter.sync_all_blocked(self.blocked_ips)

    def block_ip(self, ip: str, reason: str = "Manual Defense Block") -> bool:
        if self.is_whitelisted(ip):
            return False
        
        ip = ip.strip()
        # Protect verified Telegram and DNS infrastructure from accidental block
        if ip.startswith("149.154.") or ip.startswith("91.108.") or ip in ("1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4"):
            print(f"[Aegis Shield] Protected verified infrastructure IP {ip} from blocking.")
            return False
            
        now = int(time.time())
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO security_blocklist (ip, reason, threat_level, blocked_at, blocked_by)
            VALUES (?, ?, 'CRITICAL', ?, 'AIDIL ANDRIANDAS / Aegis Shield')
            """, (ip, reason, now))
            conn.commit()
            conn.close()
            
            self.blocked_ips.add(ip)
            
            # 1. Local VM host drop
            try:
                subprocess.run(["iptables", "-I", "INPUT", "-s", ip, "-j", "DROP"], timeout=3, capture_output=True)
                # Terminate any lingering sockets immediately so they don't stay in TCP ESTAB
                subprocess.run(["ss", "-K", "dst", ip], timeout=3, capture_output=True)
                subprocess.run(["ss", "-K", "src", ip], timeout=3, capture_output=True)
            except Exception:
                pass

            # 2. Cluster-wide Hypervisor drop (Proxmox VE 10.10.10.2 - All 8 VMs protected)
            try:
                self.pve_perimeter.block_ip_cluster(ip)
            except Exception as e:
                print(f"[Aegis Shield] Error syncing block to Proxmox Hypervisor: {e}")
                
            return True
        except Exception as e:
            print(f"[Aegis Shield] Error blocking IP: {e}")
            return False

    def unblock_ip(self, ip: str) -> bool:
        ip = ip.strip()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM security_blocklist WHERE ip = ?", (ip,))
            cursor.execute("DELETE FROM security_jail WHERE ip = ?", (ip,))
            conn.commit()
            conn.close()
            
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)
            if ip in self.jailed_ips:
                del self.jailed_ips[ip]
                
            # 1. Local VM host unblock
            try:
                subprocess.run(["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"], timeout=3, capture_output=True)
            except Exception:
                pass

            # 2. Cluster-wide Hypervisor unblock (Proxmox VE 10.10.10.2)
            try:
                self.pve_perimeter.unblock_ip_cluster(ip)
            except Exception as e:
                print(f"[Aegis Shield] Error syncing unblock to Proxmox Hypervisor: {e}")
                
            return True
        except Exception as e:
            print(f"[Aegis Shield] Error unblocking IP: {e}")
            return False

    # =========================================================================
    # MODULE 7: DOCKER CONTAINER SECURITY & HARDENING AUDITOR
    # =========================================================================
    def audit_docker_security(self) -> Dict[str, Any]:
        """Audits all local Docker containers for container escape, privilege escalation, and risky configurations"""
        sock_path = "/var/run/docker.sock"
        if not os.path.exists(sock_path):
            return {
                "available": False,
                "message": "Docker socket not found on host.",
                "total_containers": 0,
                "overall_score": 100,
                "containers": []
            }
            
        containers_audit = []
        total_risk_deductions = 0
        
        try:
            import http.client
            import socket
            
            class UnixConn(http.client.HTTPConnection):
                def __init__(self, p):
                    super().__init__('localhost')
                    self.p = p
                def connect(self):
                    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    self.sock.connect(self.p)
                    
            conn = UnixConn(sock_path)
            conn.request('GET', '/containers/json?all=1')
            r = conn.getresponse()
            if r.status != 200:
                conn.close()
                return {"available": False, "message": f"Docker API returned HTTP {r.status}", "total_containers": 0, "overall_score": 100, "containers": []}
                
            raw_containers = json.loads(r.read())
            
            for c in raw_containers:
                cid = c.get("Id", "")
                c_names = c.get("Names") or ["container"]
                name = c_names[0].lstrip("/")
                image = c.get("Image", "unknown")
                state = c.get("State", "unknown")
                status_str = c.get("Status", "unknown")
                
                # Fetch detailed inspect for this container
                conn.request('GET', f'/containers/{cid}/json')
                r_detail = conn.getresponse()
                detail = json.loads(r_detail.read()) if r_detail.status == 200 else {}
                
                host_config = detail.get("HostConfig", {}) or {}
                config = detail.get("Config", {}) or {}
                
                # Security checks
                is_privileged = bool(host_config.get("Privileged", False))
                pid_mode = str(host_config.get("PidMode", "") or "")
                net_mode = str(host_config.get("NetworkMode", "") or "")
                user = str(config.get("User", "") or "")
                is_root = user in ("", "0", "root")
                readonly_rootfs = bool(host_config.get("ReadonlyRootfs", False))
                
                # Resource limits
                memory_limit = host_config.get("Memory", 0) or 0
                cpu_quota = host_config.get("CpuQuota", 0) or 0
                has_resource_limits = (memory_limit > 0 or cpu_quota > 0)
                
                # Mounts check (specifically docker.sock)
                mounts = detail.get("Mounts", []) or []
                docker_sock_mounted = any("/docker.sock" in m.get("Source", "") for m in mounts)
                root_fs_mounted = any(m.get("Source", "") in ("/", "/host", "/proc", "/sys") for m in mounts)
                
                # Port exposures
                exposed_ports = []
                port_bindings = host_config.get("PortBindings") or {}
                has_public_port = False
                for p_spec, bindings in port_bindings.items():
                    if bindings:
                        for b in bindings:
                            host_ip = b.get("HostIp", "0.0.0.0")
                            host_port = b.get("HostPort", "")
                            exposed_ports.append(f"{host_ip}:{host_port}->{p_spec}")
                            if host_ip in ("0.0.0.0", "", "::"):
                                has_public_port = True
                
                # Container score calculation (100 base)
                c_score = 100
                findings = []
                
                if is_privileged:
                    c_score -= 30
                    findings.append({
                        "level": "CRITICAL",
                        "badge": "PRIVILEGED",
                        "title": "Privileged Container Mode Active",
                        "desc": "Container runs with full host kernel capabilities. A breakout gives full host control.",
                        "fix": "Remove '--privileged' flag unless explicitly required for low-level host monitoring."
                    })
                if docker_sock_mounted:
                    c_score -= 25
                    findings.append({
                        "level": "HIGH",
                        "badge": "SOCK MOUNT",
                        "title": "Docker Socket (/var/run/docker.sock) Exposed",
                        "desc": "Container can spawn, stop, inspect, or execute root commands across other containers.",
                        "fix": "Use Docker socket proxy with read-only whitelist or rootless Docker."
                    })
                if is_root:
                    c_score -= 15
                    findings.append({
                        "level": "MEDIUM",
                        "badge": "ROOT USER",
                        "title": "Running as Default Root User (UID 0)",
                        "desc": "Processes inside container execute with root privileges.",
                        "fix": "Specify a non-root user (e.g. 'USER 1000:1000') in Dockerfile or compose."
                    })
                if pid_mode == "host":
                    c_score -= 15
                    findings.append({
                        "level": "MEDIUM",
                        "badge": "PID HOST",
                        "title": "Host PID Namespace Shared (--pid host)",
                        "desc": "Container shares process table with host OS, exposing host process memory.",
                        "fix": "Remove '--pid host' to enable default process namespace isolation."
                    })
                if not has_resource_limits:
                    c_score -= 10
                    findings.append({
                        "level": "LOW",
                        "badge": "NO LIMITS",
                        "title": "No CPU / RAM Resource Boundaries",
                        "desc": "Container can exhaust host memory and cause OOM kill on vital services.",
                        "fix": "Set '--memory 1g --cpus 1.5' or compose limits."
                    })
                if not readonly_rootfs:
                    c_score -= 5
                    findings.append({
                        "level": "LOW",
                        "badge": "WRITABLE FS",
                        "title": "Root Filesystem is Writable",
                        "desc": "Allows unauthorized binary downloads or runtime tampering inside container.",
                        "fix": "Add '--read-only' with tmpfs mount for temporary scratch files."
                    })
                    
                c_score = max(c_score, 10)
                total_risk_deductions += (100 - c_score)
                
                status_rating = "HARDENED"
                rating_color = "emerald"
                if c_score < 50:
                    status_rating = "CRITICAL RISK"
                    rating_color = "rose"
                elif c_score < 75:
                    status_rating = "NEEDS HARDENING"
                    rating_color = "amber"
                elif c_score < 90:
                    status_rating = "MODERATE"
                    rating_color = "cyan"
                    
                containers_audit.append({
                    "id": cid[:12],
                    "name": name,
                    "image": image,
                    "state": state,
                    "status_str": status_str,
                    "score": c_score,
                    "status_rating": status_rating,
                    "rating_color": rating_color,
                    "is_privileged": is_privileged,
                    "docker_sock_mounted": docker_sock_mounted,
                    "root_fs_mounted": root_fs_mounted,
                    "is_root": is_root,
                    "pid_mode": pid_mode,
                    "net_mode": net_mode,
                    "has_resource_limits": has_resource_limits,
                    "readonly_rootfs": readonly_rootfs,
                    "exposed_ports": exposed_ports,
                    "has_public_port": has_public_port,
                    "findings": findings
                })
                
            conn.close()
            
            cnt = len(containers_audit)
            overall_score = round(100 - (total_risk_deductions / cnt)) if cnt > 0 else 100
            overall_score = max(min(overall_score, 100), 20)
            
            return {
                "available": True,
                "total_containers": cnt,
                "overall_score": overall_score,
                "containers": containers_audit
            }
        except Exception as e:
            return {"available": False, "message": str(e), "total_containers": 0, "overall_score": 100, "containers": []}

    # =========================================================================
    # MODULE 8: C2 BOTNET & CRYPTO-MINING OUTBOUND SHIELD
    # =========================================================================
    MINING_PORTS = {3333, 4444, 5555, 7777, 8333, 14444, 18080, 18081, 45700, 9999, 14433, 8545}
    MINING_PROCESS_NAMES = {
        "xmrig", "kworkerds", "minerd", "cpuminer", "ethminer", "stratum", 
        "kdevtmpfsi", "kinsing", "pwnrig", "sysupdate", "networkservice"
    }
    MINING_DOMAINS = [
        "minexmr", "supportxmr", "nanopool", "hashvault", "f2pool", "poolin",
        "antpool", "monerohash", "coinhive", "cryptoloot", "c3pool"
    ]

    def detect_c2_crypto_mining(self) -> Dict[str, Any]:
        """Inspects outbound sockets and active host processes for cryptocurrency miners and C2 channels"""
        threats_found = []
        
        # 1. Inspect live sockets
        conns = self.get_live_connections()
        for c in conns:
            peer_ip = c.get("peer_ip", "")
            peer_port = c.get("peer_port", 0)
            process = (c.get("process") or "").lower()
            
            # Check port
            if peer_port in self.MINING_PORTS:
                threats_found.append({
                    "type": "OUTBOUND_MINING_PORT",
                    "severity": "CRITICAL",
                    "ip": peer_ip,
                    "port": peer_port,
                    "process": process,
                    "message": f"Outbound socket connected to known mining pool port {peer_port} ({peer_ip})"
                })
                
            # Check process name
            for m_proc in self.MINING_PROCESS_NAMES:
                if m_proc in process:
                    threats_found.append({
                        "type": "CRYPTO_MINER_BINARY",
                        "severity": "CRITICAL",
                        "ip": peer_ip,
                        "port": peer_port,
                        "process": process,
                        "message": f"Rogue crypto-miner process '{process}' actively running and transmitting network traffic"
                    })
                    break
                    
        # 2. Inspect process table for rogue mining binaries
        try:
            import psutil
            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    p_name = (p.info['name'] or '').lower()
                    cmd = ' '.join(p.info['cmdline'] or []).lower()
                    for m_name in self.MINING_PROCESS_NAMES:
                        if m_name in p_name or m_name in cmd:
                            threats_found.append({
                                "type": "MALICIOUS_PROCESS_SIGNATURE",
                                "severity": "CRITICAL",
                                "pid": p.info['pid'],
                                "process": p_name,
                                "cmdline": cmd[:80],
                                "message": f"Cryptojacking malware signature detected: {p_name} (PID: {p.info['pid']})"
                            })
                            break
                    for dom in self.MINING_DOMAINS:
                        if dom in cmd:
                            threats_found.append({
                                "type": "MINING_POOL_FLAG",
                                "severity": "CRITICAL",
                                "pid": p.info['pid'],
                                "process": p_name,
                                "cmdline": cmd[:80],
                                "message": f"Command-line refers to mining pool URL ({dom})"
                            })
                            break
                except Exception:
                    pass
        except Exception:
            pass
            
        status = "SECURE / ZERO MINING DETECTED" if not threats_found else "CRITICAL / THREAT ACTIVE"
        
        return {
            "status": status,
            "status_color": "emerald" if not threats_found else "rose",
            "threats_count": len(threats_found),
            "threats": threats_found,
            "monitored_ports": sorted(list(self.MINING_PORTS)),
            "monitored_signatures": sorted(list(self.MINING_PROCESS_NAMES))
        }

    def get_blocklist(self) -> List[Dict[str, Any]]:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT ip, reason, threat_level, blocked_at, blocked_by FROM security_blocklist ORDER BY blocked_at DESC")
            rows = cursor.fetchall()
            conn.close()
            res = []
            for r in rows:
                geo = self.lookup_geoip(r["ip"])
                res.append({
                    **dict(r),
                    "country": geo.get("country", "Unknown"),
                    "flag": geo.get("flag", "🌐")
                })
            return res
        except Exception:
            return []

# Singleton instance
security_engine = SecurityEngine()
