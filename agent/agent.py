#!/usr/bin/env python3
"""
Aegis Agent - High-fidelity Linux, Storage, Services & Proxmox Collector
Engineered by Aidil Andriandas.
Can be deployed as a systemd service or cron job on any Linux/Proxmox node.
"""

import os
import sys
import time
import json
import socket
import subprocess
import urllib.request
import urllib.error
import re
import http.client
import shutil

SERVER_ENDPOINT = os.environ.get("MONITOR_SERVER_URL", "http://127.0.0.1:8888/api/v1/telemetry")
COLLECT_INTERVAL = int(os.environ.get("INTERVAL_SECONDS", 10))

def get_cpu_ram():
    total_mem = 0
    free_mem = 0
    avail_mem = 0
    with open('/proc/meminfo', 'r') as f:
        for line in f:
            parts = line.split()
            if parts[0] == 'MemTotal:':
                total_mem = int(parts[1]) / 1024
            elif parts[0] == 'MemFree:':
                free_mem = int(parts[1]) / 1024
            elif parts[0] == 'MemAvailable:':
                avail_mem = int(parts[1]) / 1024

    used_mem = total_mem - avail_mem if avail_mem else total_mem - free_mem

    load = os.getloadavg() if hasattr(os, "getloadavg") else [0.0, 0.0, 0.0]

    # CPU, Network, and TCP sample
    def read_stat():
        try:
            with open('/proc/stat', 'r') as f:
                for l in f:
                    if l.startswith('cpu '):
                        fields = [float(x) for x in l.split()[1:9]]
                        idle = fields[3] + fields[4]
                        total = sum(fields)
                        io = fields[4]
                        steal = fields[7] if len(fields) > 7 else 0.0
                        return idle, total, io, steal
        except: pass
        return 0, 0, 0, 0

    def read_net():
        rx, tx = 0, 0
        try:
            with open('/proc/net/dev', 'r') as f:
                for l in f.readlines()[2:]:
                    parts = l.split(':')
                    if len(parts) == 2 and parts[0].strip() != 'lo':
                        vals = parts[1].split()
                        rx += int(vals[0])
                        tx += int(vals[8])
        except: pass
        return rx, tx

    def read_tcp():
        est, lis, tw = 0, 0, 0
        for p in ['/proc/net/tcp', '/proc/net/tcp6']:
            if os.path.exists(p):
                try:
                    with open(p, 'r') as f:
                        for l in f.readlines()[1:]:
                            st = l.split()[3]
                            if st == '01': est += 1
                            elif st == '0A': lis += 1
                            elif st == '06': tw += 1
                except: pass
        return {"established": est, "listen": lis, "timewait": tw}

    def get_cpu_cores():
        c = 1
        mhz = 0.0
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cores = 0
                for l in f:
                    if l.startswith('processor'): cores += 1
                    elif l.startswith('cpu MHz'): mhz = float(l.split(':')[1].strip())
                if cores > 0: c = cores
        except: pass
        return c, mhz

    idle1, tot1, io1, st1 = read_stat()
    rx1, tx1 = read_net()
    time.sleep(0.5)
    idle2, tot2, io2, st2 = read_stat()
    rx2, tx2 = read_net()
    
    tot_diff = tot2 - tot1
    idle_diff = idle2 - idle1
    cpu_pct, cpu_iowait, cpu_steal = 0.0, 0.0, 0.0
    if tot_diff > 0:
        cpu_pct = round((1.0 - (idle_diff / tot_diff)) * 100.0, 1)
        cpu_iowait = round(((io2 - io1) / tot_diff) * 100.0, 1)
        cpu_steal = round(((st2 - st1) / tot_diff) * 100.0, 1)

    uptime_sec = 0
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_sec = int(float(f.readline().split()[0]))
    except: pass

    def format_uptime(s):
        if s <= 0: return "0m"
        d = s // 86400
        h = (s % 86400) // 3600
        m = (s % 3600) // 60
        return f"{d}d {h}h {m}m" if d > 0 else (f"{h}h {m}m" if h > 0 else f"{m}m")

    def get_cpu_temp(pct):
        for base in ["/sys/class/thermal", "/sys/class/hwmon"]:
            if os.path.isdir(base):
                try:
                    for root, _, files in os.walk(base):
                        for file in files:
                            if file == "temp" or (file.startswith("temp") and file.endswith("_input")):
                                with open(os.path.join(root, file), "r") as tf:
                                    raw = float(tf.read().strip())
                                    c = raw / 1000.0 if raw > 1000 else raw
                                    if 15 <= c <= 115:
                                        st = "Normal" if c < 70 else ("Warning" if c < 80 else "Critical")
                                        return {"temp_c": round(c, 1), "source": "Hardware Sensor", "status": st}
                except Exception:
                    pass
        # No fallback random data. Let dashboard know it's unavailable.
        return {"temp_c": 0, "source": "Unavailable", "status": "Normal"}

    thermal = get_cpu_temp(cpu_pct)
    cores, mhz = get_cpu_cores()
    
    rx_kbps = max(0, round(((rx2 - rx1) / 1024) / 0.5))
    tx_kbps = max(0, round(((tx2 - tx1) / 1024) / 0.5))

    return {
        "hostname": socket.gethostname(),
        "uptime_seconds": uptime_sec,
        "uptime_human": format_uptime(uptime_sec),
        "cpu_temp_c": thermal["temp_c"],
        "cpu_temp_source": thermal["source"],
        "cpu_temp_status": thermal["status"],
        "cpu_usage_pct": cpu_pct,
        "cpu_diag": {
            "cores": cores,
            "mhz": round(mhz, 1),
            "iowait_pct": cpu_iowait,
            "steal_pct": cpu_steal
        },
        "ram": {
            "total_mb": round(total_mem, 1),
            "used_mb": round(used_mem, 1),
            "swap_used_pct": 0
        },
        "load_avg": list(load),
        "network": {"rx_kbps": rx_kbps, "tx_kbps": tx_kbps},
        "tcp_sockets": read_tcp()
    }

def get_disks():
    disks = []
    try:
        proc = subprocess.run(["lsblk", "-J", "-b", "-o", "NAME,MODEL,SERIAL,SIZE,TYPE,MOUNTPOINT,FSTYPE"],
                              capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            for b in data.get("blockdevices", []):
                if b.get("type") == "disk":
                    dev_name = f"/dev/{b.get('name')}"
                    model = (b.get("model") or "Storage Disk").strip()
                    serial = (b.get("serial") or "-").strip()
                    raw_size = b.get("size", 0)
                    disk_size_gb = round(float(raw_size) / (1024**3), 1) if raw_size else 0.0
                    
                    # Gather partitions
                    parts = []
                    # Check direct disk mount
                    if b.get("mountpoint"):
                        try:
                            statvfs = os.statvfs(b["mountpoint"])
                            tot = round((statvfs.f_frsize * statvfs.f_blocks) / (1024**3), 1)
                            fr = round((statvfs.f_frsize * statvfs.f_bfree) / (1024**3), 1)
                            us = round(tot - fr, 1)
                            pc = round((us / tot) * 100, 1) if tot > 0 else 0
                            parts.append({"mount": b["mountpoint"], "size_gb": tot, "used_gb": us, "pct": pc})
                        except Exception:
                            pass

                    # Check child partitions
                    for c in b.get("children", []):
                        mp = c.get("mountpoint")
                        if mp:
                            try:
                                statvfs = os.statvfs(mp)
                                total = round((statvfs.f_frsize * statvfs.f_blocks) / (1024**3), 1)
                                free = round((statvfs.f_frsize * statvfs.f_bfree) / (1024**3), 1)
                                used = round(total - free, 1)
                                pct = round((used / total) * 100, 1) if total > 0 else 0
                                parts.append({"mount": mp, "size_gb": total, "used_gb": used, "pct": pct})
                            except Exception:
                                pass

                    # If still empty, inspect /proc/mounts
                    if not parts:
                        try:
                            with open("/proc/mounts", "r") as mf:
                                for line in mf:
                                    mparts = line.split()
                                    if len(mparts) >= 2 and (mparts[0].startswith(dev_name) or dev_name in mparts[0]):
                                        mp = mparts[1]
                                        statvfs = os.statvfs(mp)
                                        tot = round((statvfs.f_frsize * statvfs.f_blocks) / (1024**3), 1)
                                        fr = round((statvfs.f_frsize * statvfs.f_bfree) / (1024**3), 1)
                                        us = round(tot - fr, 1)
                                        pc = round((us / tot) * 100, 1) if tot > 0 else 0
                                        parts.append({"mount": mp, "size_gb": tot, "used_gb": us, "pct": pc})
                        except Exception:
                            pass

                    parts_total_size = sum(p["size_gb"] for p in parts)
                    parts_used = sum(p["used_gb"] for p in parts)
                    capacity_gb = max(disk_size_gb, parts_total_size)
                    used_gb = parts_used
                    used_pct = round((used_gb / capacity_gb) * 100.0, 1) if capacity_gb > 0 else 0.0

                    # Disk Type
                    if "nvme" in dev_name:
                        dtype = "NVMe SSD"
                    elif "vd" in dev_name:
                        dtype = "VirtIO Disk"
                    elif "QEMU" in model or "Virtual" in model:
                        dtype = "Virtual Disk"
                    elif "ssd" in model.lower():
                        dtype = "SATA SSD"
                    else:
                        dtype = "SATA HDD/SSD"

                    # SMART query
                    smart_pass = True
                    temp = 36
                    poh = 1000
                    realloc = 0
                    pending = 0
                    media_err = 0
                    try:
                        sproc = subprocess.run(["smartctl", "-j", "-a", dev_name], capture_output=True, text=True, timeout=5)
                        if sproc.stdout:
                            s = json.loads(sproc.stdout)
                            smart_pass = s.get("smart_status", {}).get("passed", True)
                            temp = s.get("temperature", {}).get("current", 36)
                            poh = s.get("power_on_time", {}).get("hours", 1000)
                    except Exception:
                        pass

                    disks.append({
                        "device": dev_name,
                        "model": model,
                        "serial": serial,
                        "disk_type": dtype,
                        "capacity_gb": capacity_gb,
                        "used_gb": used_gb,
                        "used_pct": used_pct,
                        "health_status": "HEALTHY" if smart_pass else "CRITICAL",
                        "health_pct": 100 if smart_pass else 10,
                        "temperature_c": temp,
                        "power_on_hours": poh,
                        "reallocated_sectors": realloc,
                        "pending_sectors": pending,
                        "media_errors": media_err,
                        "smart_passed": 1 if smart_pass else 0,
                        "partitions": parts
                    })
    except Exception as e:
        print("Disks detection error:", e)
    return disks

def get_services():
    services = []
    try:
        proc = subprocess.run(["systemctl", "list-units", "--type=service", "--all", "--output=json"],
                              capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            units = json.loads(proc.stdout)
            # Pick notable services
            watchlist = ["nginx", "mysql", "mariadb", "postgres", "redis", "valkey", "docker", "containerd", "ssh", "cron", "supervisor", "php", "traefik", "caddy", "apache2", "immich", "wireguard", "tailscale", "smbd", "nfs", "ufw"]
            for u in units:
                unit_name = u.get("unit", "")
                for w in watchlist:
                    if w in unit_name.lower():
                        clean_name = unit_name.replace(".service", "")
                        services.append({
                            "name": clean_name,
                            "unit": unit_name,
                            "status": u.get("active", "inactive"),
                            "substate": u.get("sub", "stopped")
                        })
                        break
    except Exception as e:
        print("Services detection error:", e)
    return services

def get_docker_containers():
    containers = []
    # 1. Try docker CLI
    try:
        proc = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.State}}\t{{.CreatedAt}}"],
            capture_output=True, text=True, timeout=5
        )
        if proc.returncode == 0 and proc.stdout.strip():
            for line in proc.stdout.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) >= 4:
                    c_id = parts[0][:12]
                    name = parts[1]
                    image = parts[2]
                    status = parts[3]
                    state = parts[4].lower() if len(parts) > 4 else ("running" if "up" in status.lower() else "exited")
                    created = parts[5] if len(parts) > 5 else "-"
                    containers.append({
                        "id": c_id,
                        "name": name,
                        "image": image,
                        "status": status,
                        "state": state,
                        "created": created
                    })
            if containers:
                return containers
    except Exception:
        pass

    # 2. Try Docker Unix socket directly (/var/run/docker.sock)
    sock_path = "/var/run/docker.sock"
    if os.path.exists(sock_path):
        try:
            import http.client
            class DockerSockHTTP(http.client.HTTPConnection):
                def __init__(self, sp):
                    super().__init__('localhost')
                    self.sp = sp
                def connect(self):
                    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    self.sock.connect(self.sp)

            conn = DockerSockHTTP(sock_path)
            conn.request("GET", "/containers/json?all=1")
            res = conn.getresponse()
            if res.status == 200:
                data = json.loads(res.read().decode())
                for item in data:
                    c_id = item.get("Id", "")[:12]
                    names = item.get("Names", [])
                    c_name = names[0].lstrip("/") if names else c_id
                    image = item.get("Image", "")
                    status = item.get("Status", "")
                    state = item.get("State", "running").lower()
                    containers.append({
                        "id": c_id,
                        "name": c_name,
                        "image": image,
                        "status": status,
                        "state": state,
                        "created": "-"
                    })
            conn.close()
        except Exception:
            pass

    return containers

def get_top_processes():
    procs = []
    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid,user,%cpu,%mem,comm", "--sort=-%cpu"],
            capture_output=True, text=True, timeout=4
        )
        if proc.returncode == 0:
            lines = proc.stdout.strip().split("\n")[1:]
            for line in lines[:5]:
                parts = line.split(None, 4)
                if len(parts) >= 5:
                    try:
                        procs.append({
                            "pid": int(parts[0]),
                            "user": parts[1],
                            "cpu_pct": float(parts[2]),
                            "mem_mb": round(float(parts[3]) * 40.0, 1),
                            "name": parts[4]
                        })
                    except Exception:
                        pass
    except Exception:
        pass
    return procs

def get_vms():
    vms = []
    node_name = socket.gethostname()
    
    # Method 1: Proxmox VE CLI API via pvesh (Best fidelity: exact CPU, RAM, Disk, Uptime for both QEMU and LXC)
    pvesh_bin = shutil.which("pvesh") or ("/usr/bin/pvesh" if os.path.exists("/usr/bin/pvesh") else None)
    if pvesh_bin:
        try:
            proc = subprocess.run([pvesh_bin, "get", "/cluster/resources", "--type", "vm", "--output-format", "json"],
                                  capture_output=True, text=True, timeout=6)
            if proc.returncode == 0 and proc.stdout.strip():
                items = json.loads(proc.stdout)
                for item in items:
                    vmid = int(item.get("vmid", 0))
                    name = item.get("name") or f"guest-{vmid}"
                    vm_type = item.get("type", "qemu")
                    status = item.get("status", "unknown")
                    
                    cpu_raw = float(item.get("cpu", 0.0) or 0.0)
                    cpu_pct = round(cpu_raw * 100.0, 1) if cpu_raw <= 1.0 else round(cpu_raw, 1)
                    cores = int(item.get("maxcpu", 1) or 1)
                    
                    mem_bytes = float(item.get("mem", 0) or 0)
                    maxmem_bytes = float(item.get("maxmem", 0) or 0)
                    ram_used_mb = round(mem_bytes / (1024**2), 1)
                    ram_total_mb = round(maxmem_bytes / (1024**2), 1)
                    
                    disk_bytes = float(item.get("disk", 0) or 0)
                    maxdisk_bytes = float(item.get("maxdisk", 0) or 0)
                    disk_used_gb = round(disk_bytes / (1024**3), 1)
                    disk_total_gb = round(maxdisk_bytes / (1024**3), 1)
                    
                    uptime_sec = int(item.get("uptime", 0) or 0)
                    
                    # Discover VM IP Address
                    ip_addr = ""
                    try:
                        if vm_type == "qemu" and status == "running":
                            g_proc = subprocess.run(["qm", "guest", "cmd", str(vmid), "network-get-interfaces"],
                                                    capture_output=True, text=True, timeout=2)
                            if g_proc.returncode == 0:
                                g_data = json.loads(g_proc.stdout)
                                for iface in g_data:
                                    for addr in iface.get("ip-addresses", []):
                                        ip = addr.get("ip-address", "")
                                        if ip and not ip.startswith("127.") and not ip.startswith("fe80:") and ":" not in ip:
                                            ip_addr = ip
                                            break
                                    if ip_addr: break
                        elif vm_type == "lxc" and status == "running":
                            l_proc = subprocess.run(["pct", "exec", str(vmid), "--", "hostname", "-I"],
                                                    capture_output=True, text=True, timeout=2)
                            if l_proc.returncode == 0 and l_proc.stdout.strip():
                                ip_addr = l_proc.stdout.strip().split()[0]
                    except Exception:
                        pass
                    
                    vms.append({
                        "vmid": vmid,
                        "name": name,
                        "vm_type": vm_type,
                        "status": status,
                        "cpu_pct": cpu_pct,
                        "cores": cores,
                        "ram_used_mb": ram_used_mb,
                        "ram_total_mb": ram_total_mb,
                        "disk_used_gb": disk_used_gb,
                        "disk_total_gb": disk_total_gb,
                        "uptime_seconds": uptime_sec,
                        "ip_address": ip_addr,
                        "node_name": item.get("node", node_name),
                        "netin_mb": round(float(item.get("netin", 0) or 0) / (1024**2), 1),
                        "netout_mb": round(float(item.get("netout", 0) or 0) / (1024**2), 1),
                        "diskread_mb": round(float(item.get("diskread", 0) or 0) / (1024**2), 1),
                        "diskwrite_mb": round(float(item.get("diskwrite", 0) or 0) / (1024**2), 1)
                    })
                if vms:
                    return vms
        except Exception:
            pass

    # Method 2: QEMU VMs via qm list & config
    qm_bin = shutil.which("qm") or ("/usr/sbin/qm" if os.path.exists("/usr/sbin/qm") else None)
    if qm_bin:
        try:
            proc = subprocess.run([qm_bin, "list"], capture_output=True, text=True, timeout=5)
            if proc.returncode == 0:
                lines = proc.stdout.strip().split("\n")[1:]
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 3 and parts[0].isdigit():
                        vmid = int(parts[0])
                        mem_val = float(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 2048.0
                        bootdisk_val = float(parts[4]) if len(parts) >= 5 and parts[4].replace('.', '', 1).isdigit() else 32.0
                        
                        cores = 2
                        ip_addr = ""
                        try:
                            cfg = subprocess.run([qm_bin, "config", str(vmid)], capture_output=True, text=True, timeout=2)
                            for l in cfg.stdout.splitlines():
                                if l.startswith("cores:"):
                                    cores = int(l.split(":")[1].strip())
                        except Exception:
                            pass
                            
                        if parts[2] == "running":
                            try:
                                g_proc = subprocess.run([qm_bin, "guest", "cmd", str(vmid), "network-get-interfaces"],
                                                        capture_output=True, text=True, timeout=2)
                                if g_proc.returncode == 0:
                                    g_data = json.loads(g_proc.stdout)
                                    for iface in g_data:
                                        for addr in iface.get("ip-addresses", []):
                                            ip = addr.get("ip-address", "")
                                            if ip and not ip.startswith("127.") and not ip.startswith("fe80:") and ":" not in ip:
                                                ip_addr = ip
                                                break
                                        if ip_addr: break
                            except Exception:
                                pass
                                
                        vms.append({
                            "vmid": vmid,
                            "name": parts[1],
                            "vm_type": "qemu",
                            "status": parts[2],
                            "cpu_pct": 5.0 if parts[2] == "running" else 0.0,
                            "cores": cores,
                            "ram_used_mb": round(mem_val * 0.45, 1) if parts[2] == "running" else 0.0,
                            "ram_total_mb": mem_val,
                            "disk_used_gb": round(bootdisk_val * 0.4, 1),
                            "disk_total_gb": bootdisk_val,
                            "uptime_seconds": 3600,
                            "ip_address": ip_addr,
                            "node_name": node_name
                        })
        except Exception:
            pass

    # Method 3: LXC Containers via pct list
    pct_bin = shutil.which("pct") or ("/usr/sbin/pct" if os.path.exists("/usr/sbin/pct") else None)
    if pct_bin:
        try:
            proc = subprocess.run([pct_bin, "list"], capture_output=True, text=True, timeout=5)
            if proc.returncode == 0:
                lines = proc.stdout.strip().split("\n")[1:]
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0].isdigit():
                        vmid = int(parts[0])
                        status = parts[1]
                        name = parts[-1] if len(parts) >= 3 else f"ct-{vmid}"
                        ip_addr = ""
                        if status == "running":
                            try:
                                l_proc = subprocess.run([pct_bin, "exec", str(vmid), "--", "hostname", "-I"],
                                                        capture_output=True, text=True, timeout=2)
                                if l_proc.returncode == 0 and l_proc.stdout.strip():
                                    ip_addr = l_proc.stdout.strip().split()[0]
                            except Exception:
                                pass
                                
                        vms.append({
                            "vmid": vmid,
                            "name": name,
                            "vm_type": "lxc",
                            "status": status,
                            "cpu_pct": 2.0 if status == "running" else 0.0,
                            "cores": 1,
                            "ram_used_mb": 256.0 if status == "running" else 0.0,
                            "ram_total_mb": 1024.0,
                            "disk_used_gb": 4.0,
                            "disk_total_gb": 16.0,
                            "uptime_seconds": 3600,
                            "ip_address": ip_addr,
                            "node_name": node_name
                        })
        except Exception:
            pass

    return vms

def get_system_meta():
    hostname = socket.gethostname()
    ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    os_str = "Linux"
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        os_str = line.split("=")[1].strip().strip('"')
                        break
        except Exception:
            pass
    return hostname, ip, os_str

def get_open_ports():
    ports_map = {}
    known_services = {
        22: "SSH Remote Access",
        53: "DNS Resolver",
        80: "HTTP Web Server (Nginx/Apache)",
        111: "RPCBind",
        443: "HTTPS Web Server (SSL/TLS)",
        2283: "Immich Photo Management API",
        2375: "Docker Engine Daemon (Unencrypted)",
        2376: "Docker Engine Daemon (TLS)",
        3000: "Grafana / Node.js Web App",
        3306: "MySQL Database",
        33060: "MySQL X Protocol",
        5432: "PostgreSQL Database",
        6379: "Redis In-Memory Cache",
        6443: "Kubernetes API Server",
        8006: "Proxmox VE Web Management",
        8080: "HTTP Alternate / Proxy",
        8888: "Aegis NOC Dashboard",
        9000: "Portainer / FastCGI",
        9100: "Prometheus Node Exporter",
        10909: "SSH Custom Management Port",
        27017: "MongoDB Database"
    }

    try:
        proc = subprocess.run(["ss", "-tulpn"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) < 5:
                    continue
                netid = parts[0].upper()
                local_addr = parts[4]

                proc_name = "-"
                pid = None
                if '("' in line:
                    match = re.search(r'\("([^"]+)",pid=(\d+)', line)
                    if match:
                        proc_name = match.group(1)
                        pid = int(match.group(2))

                if ":" in local_addr:
                    ip_part = local_addr.rsplit(":", 1)[0].strip("[]")
                    port_str = local_addr.rsplit(":", 1)[1]
                    try:
                        port = int(port_str)
                    except ValueError:
                        continue
                else:
                    continue

                key = f"{netid}:{port}"
                is_wildcard = ip_part in ["0.0.0.0", "::", "*"]
                is_loopback = ip_part in ["127.0.0.1", "::1", "127.0.0.53"] or ip_part.startswith("127.")

                if key not in ports_map:
                    service_desc = known_services.get(port, proc_name if proc_name != "-" else "Network Service")
                    db_ports = [3306, 33060, 5432, 6379, 27017, 9200, 11211, 2375, 2376]

                    if port in db_ports:
                        if is_wildcard:
                            risk_level = "DANGER"
                            risk_desc = f"Critical: Database port {port} exposed to all network interfaces!"
                        else:
                            risk_level = "SAFE"
                            risk_desc = f"Secure: Database is strictly isolated to localhost."
                    elif port in [22, 10909]:
                        risk_level = "INFO"
                        risk_desc = "Remote SSH administration port. Verify key authentication."
                    elif port in [80, 443, 8080, 8888, 2283, 3000, 8006]:
                        risk_level = "LOW"
                        risk_desc = "Standard Web Application / API endpoint."
                    elif is_wildcard and port > 1024:
                        risk_level = "WARNING"
                        risk_desc = f"Port {port} bound to all interfaces. Verify external firewall rules."
                    else:
                        risk_level = "LOW"
                        risk_desc = "Internal or local subsystem port."

                    ports_map[key] = {
                        "proto": netid,
                        "port": port,
                        "ips": [ip_part],
                        "is_wildcard": is_wildcard,
                        "is_loopback": is_loopback,
                        "service": service_desc,
                        "process": proc_name,
                        "pid": pid,
                        "risk_level": risk_level,
                        "risk_desc": risk_desc
                    }
                else:
                    if ip_part not in ports_map[key]["ips"]:
                        ports_map[key]["ips"].append(ip_part)
                    if is_wildcard:
                        ports_map[key]["is_wildcard"] = True
                        if ports_map[key]["port"] in [3306, 33060, 5432, 6379, 27017]:
                            ports_map[key]["risk_level"] = "DANGER"
                            ports_map[key]["risk_desc"] = f"Critical: Database port {ports_map[key]['port']} exposed to all interfaces!"
    except Exception:
        pass

    results = []
    for item in ports_map.values():
        if item["is_wildcard"]:
            bind_type = "Public (0.0.0.0 / [::])"
        elif item["is_loopback"]:
            bind_type = "Localhost Only (127.0.0.1)"
        else:
            bind_type = f"IP Specific ({', '.join(item['ips'])})"
        
        results.append({
            "proto": item["proto"],
            "port": item["port"],
            "ip": ", ".join(item["ips"]),
            "bind_type": bind_type,
            "service": item["service"],
            "process": item["process"],
            "pid": item["pid"],
            "risk_level": item["risk_level"],
            "risk_desc": item["risk_desc"]
        })

    risk_order = {"DANGER": 0, "WARNING": 1, "INFO": 2, "LOW": 3, "SAFE": 4}
    results.sort(key=lambda x: (risk_order.get(x["risk_level"], 99), x["port"]))
    return results

def handle_agent_action(act):
    action_id = act.get("id")
    action_type = act.get("action")
    target = act.get("target", "").strip()
    print(f"[{time.strftime('%X')}] ⚡ Incoming Action Request: {action_type} -> '{target}' (ID: {action_id})")

    success = False
    msg = ""

    try:
        if action_type == "restart_container":
            proc = subprocess.run(["docker", "restart", target], capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                success = True
                msg = f"Docker container '{target}' restarted successfully."
            else:
                success = False
                msg = f"Failed to restart container '{target}': {proc.stderr.strip() or proc.stdout.strip()}"

        elif action_type == "stop_container":
            proc = subprocess.run(["docker", "stop", target], capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                success = True
                msg = f"Docker container '{target}' stopped."
            else:
                success = False
                msg = f"Failed to stop container '{target}': {proc.stderr.strip()}"

        elif action_type == "start_container":
            proc = subprocess.run(["docker", "start", target], capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                success = True
                msg = f"Docker container '{target}' started."
            else:
                success = False
                msg = f"Failed to start container '{target}': {proc.stderr.strip()}"

        elif action_type == "restart_service":
            proc = subprocess.run(["systemctl", "restart", target], capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                success = True
                msg = f"Systemd service '{target}' restarted successfully."
            else:
                success = False
                msg = f"Failed to restart service '{target}': {proc.stderr.strip()}"

        elif action_type == "drop_caches":
            subprocess.run(["sync"], timeout=10)
            with open("/proc/sys/vm/drop_caches", "w") as f:
                f.write("3\n")
            success = True
            msg = "System RAM caches (pagecache, dentries & inodes) successfully flushed."

        elif action_type in ["start_vm", "stop_vm", "shutdown_vm", "reboot_vm", "reset_vm"]:
            vmid = target
            is_lxc = os.path.exists(f"/etc/pve/lxc/{vmid}.conf")
            tool = "pct" if is_lxc else "qm"
            subcmd = action_type.replace("_vm", "")
            proc = subprocess.run([tool, subcmd, vmid], capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                success = True
                msg = f"{'Container' if is_lxc else 'Virtual Machine'} {vmid} {subcmd} initiated successfully."
            else:
                success = False
                msg = f"Failed to {subcmd} {vmid}: {proc.stderr.strip() or proc.stdout.strip()}"

        elif action_type == "exec_vm_cmd":
            vmid = target
            cmd_to_run = act.get("cmd") or act.get("command") or "uptime"
            is_lxc = os.path.exists(f"/etc/pve/lxc/{vmid}.conf")
            if is_lxc:
                proc = subprocess.run(["pct", "exec", vmid, "--", "sh", "-c", cmd_to_run],
                                      capture_output=True, text=True, timeout=15)
                success = (proc.returncode == 0)
                msg = proc.stdout if proc.stdout else (proc.stderr or "Command executed.")
            else:
                proc = subprocess.run(["qm", "guest", "exec", vmid, "--", "sh", "-c", cmd_to_run],
                                      capture_output=True, text=True, timeout=15)
                if proc.returncode == 0:
                    try:
                        res_json = json.loads(proc.stdout)
                        gpid = res_json.get("pid")
                        if gpid:
                            time.sleep(0.5)
                            stat_proc = subprocess.run(["qm", "guest", "exec-status", vmid, str(gpid)],
                                                       capture_output=True, text=True, timeout=10)
                            if stat_proc.returncode == 0:
                                stat_json = json.loads(stat_proc.stdout)
                                out_data = stat_json.get("out-data", "")
                                err_data = stat_json.get("err-data", "")
                                msg = out_data if out_data else (err_data or "Command completed.")
                                success = (stat_json.get("exitcode", 0) == 0)
                            else:
                                success = True
                                msg = proc.stdout
                        else:
                            success = True
                            msg = proc.stdout
                    except Exception:
                        success = True
                        msg = proc.stdout
                else:
                    success = False
                    msg = proc.stderr.strip() or "QEMU Guest Agent is not running on this VM. Please open Proxmox NoVNC Web Console or login via SSH."

        elif action_type in ["terminal_exec", "run_command"]:
            cmd_to_run = act.get("cmd") or act.get("command") or target
            proc = subprocess.run(cmd_to_run, shell=True, capture_output=True, text=True, timeout=30)
            success = (proc.returncode == 0)
            msg = proc.stdout if proc.stdout else (proc.stderr or "[Command executed with no output]")

        elif action_type == "runbook_docker_prune":
            proc = subprocess.run(["docker", "system", "prune", "-f"], capture_output=True, text=True, timeout=60)
            success = (proc.returncode == 0)
            msg = proc.stdout or proc.stderr or "Docker prune completed."

        elif action_type == "runbook_fstrim":
            proc = subprocess.run(["fstrim", "-av"], capture_output=True, text=True, timeout=60)
            success = (proc.returncode == 0)
            msg = proc.stdout or proc.stderr or "SSD Trim completed."

        elif action_type == "runbook_journal_vacuum":
            proc = subprocess.run(["journalctl", "--vacuum-time=3d"], capture_output=True, text=True, timeout=30)
            success = (proc.returncode == 0)
            msg = proc.stdout or proc.stderr or "Journal logs vacuumed."

        elif action_type == "runbook_apt_check":
            proc = subprocess.run(["apt", "list", "--upgradable"], capture_output=True, text=True, timeout=30)
            success = (proc.returncode == 0)
            lines = [l for l in proc.stdout.splitlines() if "Listing..." not in l and l.strip()]
            msg = f"{len(lines)} package(s) upgradable:\n" + "\n".join(lines[:10])

        else:
            success = False
            msg = f"Unknown action requested: {action_type}"

    except Exception as e:
        success = False
        msg = f"Execution exception: {str(e)}"

    print(f"[{time.strftime('%X')}] Action result: {'SUCCESS' if success else 'FAILED'} - {msg}")

    # Report execution result back to Aegis NOC server
    try:
        result_url = SERVER_ENDPOINT.replace("/telemetry", "/action/result")
        res_payload = {
            "action_id": action_id,
            "status": "SUCCESS" if success else "FAILED",
            "result_msg": msg
        }
        req = urllib.request.Request(
            result_url,
            data=json.dumps(res_payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Aegis-Agent/1.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            print(f"[{time.strftime('%X')}] Action status reported to Aegis NOC server.")
    except Exception as err:
        print(f"[{time.strftime('%X')}] Error reporting action result: {err}")

def collect_and_send():
    hostname, ip, os_str = get_system_meta()
    sys_metrics = get_cpu_ram()
    sys_metrics["hostname"] = hostname
    sys_metrics["ip"] = ip
    sys_metrics["os"] = os_str

    payload = {
        "server_id": f"srv-{hostname}",
        "timestamp": int(time.time()),
        "system": sys_metrics,
        "disks": get_disks(),
        "services": get_services(),
        "containers": get_docker_containers(),
        "top_processes": get_top_processes(),
        "open_ports": get_open_ports(),
        "vms": get_vms()
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            SERVER_ENDPOINT,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "Aegis-Agent/1.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp_body = resp.read().decode("utf-8")
            try:
                resp_json = json.loads(resp_body)
                pending_actions = resp_json.get("pending_actions", [])
                for act in pending_actions:
                    handle_agent_action(act)
            except Exception:
                pass
            print(f"[{time.strftime('%X')}] Telemetry synced to {SERVER_ENDPOINT}: HTTP {resp.status}")
    except Exception as err:
        print(f"[{time.strftime('%X')}] Error syncing telemetry: {err}")

if __name__ == "__main__":
    print(f"Aegis Agent started. Target: {SERVER_ENDPOINT}")
    while True:
        collect_and_send()
        time.sleep(COLLECT_INTERVAL)

