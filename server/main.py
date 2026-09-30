import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from typing import Optional, List, Dict
import threading
import time
import datetime
import os
import sys
import socket
import http.client
import json
import urllib.request
import urllib.parse
import ssl
import psutil
import uuid
import re
import subprocess

# Add parent directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database
import logs
import ai_copilot

app = FastAPI(title="Sentinel - Infrastructure, Storage & Security Sentinel")

# Initialize database
database.init_db()

# Serve static dashboard
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Dashboard loading...</h1>")

@app.get("/install.sh")
async def get_installer_script(request: Request):
    host_hdr = request.headers.get("host", "10.10.10.9:8888")
    server_url = f"http://{host_hdr}"
    possible_paths = ["install.sh", "/app/install.sh", os.path.join(os.path.dirname(__file__), "..", "install.sh")]
    for p in possible_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace("http://10.10.10.9:8888", server_url)
            return PlainTextResponse(content, media_type="text/x-shellscript")
    return PlainTextResponse("#!/bin/bash\necho 'Error: install.sh not found'\nexit 1", status_code=404)

@app.get("/agent.py")
async def get_agent_script():
    possible_paths = ["agent/agent.py", "/app/agent/agent.py", os.path.join(os.path.dirname(__file__), "..", "agent", "agent.py")]
    for p in possible_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return PlainTextResponse(f.read(), media_type="text/x-python")
    return PlainTextResponse("# Error: agent.py not found", status_code=404)

@app.get("/api/v1/dashboard")
async def get_dashboard(server_id: str = None):
    data = database.get_dashboard_data(server_id)
    if data.get("demo_mode"):
        data["system_logs"] = logs.get_demo_logs()
        data["top_processes"] = [
            {"pid": 879, "name": "mysqld", "user": "mysql", "cpu_pct": 14.8, "mem_mb": 450.2},
            {"pid": 838, "name": "nginx: worker", "user": "www-data", "cpu_pct": 8.4, "mem_mb": 85.4},
            {"pid": 1102, "name": "php-fpm: pool www", "user": "www-data", "cpu_pct": 6.2, "mem_mb": 142.0},
            {"pid": 724, "name": "supervisord", "user": "root", "cpu_pct": 2.1, "mem_mb": 32.5},
            {"pid": 24009, "name": "dockerd", "user": "root", "cpu_pct": 1.9, "mem_mb": 110.8}
        ]
    else:
        data["system_logs"] = logs.get_real_logs(limit=50)
        if not data.get("top_processes") or len(data.get("top_processes", [])) == 0:
            data["top_processes"] = get_top_processes()
    return JSONResponse(data)

@app.get("/api/v1/cluster/overview")
async def get_cluster_overview_endpoint():
    data = database.get_cluster_overview()
    return JSONResponse(data)

@app.get("/api/v1/logs")
async def get_logs(category: str = "ALL"):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'demo_mode'")
    row = cursor.fetchone()
    demo_mode = (row["value"] == "1") if row else False
    conn.close()

    if demo_mode:
        all_logs = logs.get_demo_logs()
    else:
        all_logs = logs.get_real_logs(limit=100)

    if category != "ALL":
        all_logs = [l for l in all_logs if l.get("type") == category]

    return JSONResponse(all_logs)

@app.get("/api/v1/settings")
async def get_settings():
    return {
        "telegram_token": database.get_setting("telegram_token", ""),
        "telegram_chat_id": database.get_setting("telegram_chat_id", ""),
        "discord_webhook": database.get_setting("discord_webhook", ""),
        "telegram_enabled": database.get_setting("telegram_enabled", "false").lower() == "true",
        "discord_enabled": database.get_setting("discord_enabled", "false").lower() == "true",
        "alert_on_offline": database.get_setting("alert_on_offline", "true").lower() == "true",
        "alert_on_cpu": database.get_setting("alert_on_cpu", "true").lower() == "true",
        "cpu_threshold": int(database.get_setting("cpu_threshold", "85")),
        "alert_on_disk": database.get_setting("alert_on_disk", "true").lower() == "true",
        "disk_threshold": int(database.get_setting("disk_threshold", "90"))
    }

@app.post("/api/v1/settings")
async def update_settings(payload: dict):
    for k, v in payload.items():
        database.set_setting(k, str(v).strip())
    return {"status": "success", "message": "Settings saved"}

# --- AI Homelab Copilot Endpoints ---
@app.get("/api/v1/ai/audit")
async def get_ai_audit():
    audit = ai_copilot.copilot.generate_homelab_audit()
    return JSONResponse(audit)

@app.post("/api/v1/ai/dispatch-telegram")
async def dispatch_ai_briefing():
    result = ai_copilot.copilot.dispatch_briefing()
    return JSONResponse(result)

@app.get("/api/v1/ai/settings")
async def get_ai_settings():
    return JSONResponse(ai_copilot.copilot.get_settings())

@app.post("/api/v1/ai/settings")
async def save_ai_settings(payload: dict):
    updated = ai_copilot.copilot.save_settings(payload)
    return JSONResponse({"status": "success", "settings": updated})

@app.post("/api/v1/ai/test-connection")
async def test_ai_connection(payload: dict):
    provider = payload.get("provider", "gemini")
    api_key = payload.get("api_key", "")
    model = payload.get("model", "")
    base_url = payload.get("base_url", "")
    res = ai_copilot.copilot.test_llm_connection(provider, api_key, model, base_url)
    return JSONResponse(res)


@app.post("/api/v1/alert/test")
async def send_test_alert(payload: dict = None):
    payload = payload or {}
    token = payload.get("telegram_token") or database.get_setting("telegram_token", "")
    chat_id = payload.get("telegram_chat_id") or database.get_setting("telegram_chat_id", "")
    discord = payload.get("discord_webhook") or database.get_setting("discord_webhook", "")

    results = {}
    test_msg = (
        "🚀 *SENTINEL NOC OBSERVABILITY*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔔 *TEST NOTIFICATION PIPELINE*\n\n"
        "📍 *Cluster:* Sentinel Datacenter\n"
        "🖥️ *Central Node:* `aidil (10.10.10.9)`\n"
        "👑 *Hypervisor:* `pve (10.10.10.2)`\n"
        "📦 *Active Workloads:* 8 VMs, 7 Containers\n"
        "⚡ *Fleet Health:* 100% Healthy\n\n"
        "✅ _Notification dispatch verified successfully!_"
    )

    if token and chat_id:
        tg_ok, tg_err = send_telegram(token, chat_id, test_msg)
        results["telegram"] = "SUCCESS" if tg_ok else f"FAILED: {tg_err}"
    else:
        results["telegram"] = "SKIPPED (Token atau Chat ID belum diisi)"

    if discord:
        dc_ok, dc_err = send_discord(
            discord, 
            "SENTINEL NOC TEST NOTIFICATION", 
            "Cluster test alert dispatched successfully from Central NOC Server (10.10.10.9).\n\n• Fleet Nodes: 9 Online\n• Master: pve (10.10.10.2)\n• Status: Operational"
        )
        results["discord"] = "SUCCESS" if dc_ok else f"FAILED: {dc_err}"
    else:
        results["discord"] = "SKIPPED (Webhook belum diisi)"

    return results

def execute_local_container_action(action: str, target: str):
    sock_path = "/var/run/docker.sock"
    if not os.path.exists(sock_path):
        return False, "Docker socket not accessible on host."
    
    endpoint_map = {
        "restart_container": f"/containers/{target}/restart?t=5",
        "stop_container": f"/containers/{target}/stop?t=5",
        "start_container": f"/containers/{target}/start"
    }
    endpoint = endpoint_map.get(action)
    if not endpoint:
        return False, f"Unsupported container action: {action}"
    
    try:
        conn = UnixConn(sock_path)
        conn.request("POST", endpoint)
        resp = conn.getresponse()
        resp_data = resp.read()
        conn.close()
        if resp.status in [200, 204, 304]:
            act_name = action.replace("_container", "").capitalize()
            return True, f"Container '{target}' {act_name} completed successfully."
        else:
            return False, f"Docker daemon error (HTTP {resp.status}): {resp_data.decode('utf-8', errors='ignore')}"
    except Exception as e:
        return False, str(e)

def execute_local_drop_caches():
    try:
        subprocess.run(["sync"], timeout=5)
        for path in ["/proc/sys/vm/drop_caches", "/host/proc/sys/vm/drop_caches"]:
            if os.path.exists(path):
                try:
                    with open(path, "w") as f:
                        f.write("3\n")
                    return True, "Linux RAM pagecache, dentries & inodes flushed successfully."
                except Exception:
                    pass
        proc = subprocess.run(["sh", "-c", "sync; echo 3 > /proc/sys/vm/drop_caches"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            return True, "Linux RAM pagecache, dentries & inodes flushed successfully."
        return False, proc.stderr.strip() or "Permission denied writing to drop_caches."
    except Exception as e:
        return False, str(e)

@app.post("/api/v1/telemetry")
async def receive_telemetry(payload: dict):
    pending_actions = database.save_telemetry(payload)
    return {"status": "success", "message": "Telemetry processed", "pending_actions": pending_actions or []}

@app.post("/api/v1/action/execute")
async def execute_action_endpoint(payload: dict):
    server_id = payload.get("server_id", "srv-host-node")
    action = payload.get("action")
    target = payload.get("target", "").strip()

    action_id = f"act_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    is_local = server_id in ["srv-host-node", "srv-aidil", "aidil"] or server_id == f"srv-{socket.gethostname()}"
    cmd_param = payload.get("cmd") or payload.get("command") or ""
    extra_params = {}
    if cmd_param:
        extra_params["cmd"] = cmd_param

    if is_local:
        if action in ["restart_container", "stop_container", "start_container"]:
            ok, msg = execute_local_container_action(action, target)
            status = "SUCCESS" if ok else "FAILED"
            database.enqueue_action(action_id, server_id, action, target, params=extra_params)
            database.update_action_status(action_id, status, msg)
            return {"status": "success" if ok else "error", "mode": "immediate", "action_id": action_id, "message": msg}
        elif action == "drop_caches":
            ok, msg = execute_local_drop_caches()
            status = "SUCCESS" if ok else "FAILED"
            database.enqueue_action(action_id, server_id, action, target, params=extra_params)
            database.update_action_status(action_id, status, msg)
            return {"status": "success" if ok else "error", "mode": "immediate", "action_id": action_id, "message": msg}

    database.enqueue_action(action_id, server_id, action, target, params=extra_params)
    return {
        "status": "queued",
        "mode": "queued",
        "action_id": action_id,
        "message": f"Action '{action}' dispatched to node '{server_id}'. Agent will execute on next sync (≤5s)."
    }

@app.post("/api/v1/action/result")
async def receive_action_result(payload: dict):
    action_id = payload.get("action_id")
    status = payload.get("status", "SUCCESS")
    result_msg = payload.get("result_msg", "")
    if action_id:
        database.update_action_status(action_id, status, result_msg)
    return {"status": "ok"}

@app.get("/api/v1/action/status")
async def get_action_status(action_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM node_actions WHERE id = ?", (action_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"status": "NOT_FOUND"}

@app.post("/api/v1/nodes/delete")
async def delete_node_endpoint(payload: dict):
    server_id = payload.get("server_id")
    if not server_id:
        return {"status": "error", "message": "Missing server_id parameter"}
    if server_id == "srv-host-node":
        return {"status": "error", "message": "The primary Sentinel monitoring server node cannot be removed."}
    database.delete_node(server_id)
    return {"status": "success", "message": f"Node '{server_id}' has been removed from cluster."}

# ==========================================
# 1. HOMELAB SERVICE ENDPOINTS & SSL MONITOR
# ==========================================
@app.get("/api/v1/probes")
async def list_probes():
    return JSONResponse(database.get_web_probes())

@app.post("/api/v1/probes")
async def create_probe(payload: dict):
    name = payload.get("name", "").strip()
    url = payload.get("url", "").strip()
    if not name or not url:
        return JSONResponse({"status": "error", "message": "Name and URL are required"}, status_code=400)
    probe = database.add_web_probe(name, url)
    threading.Thread(target=check_web_probes, daemon=True).start()
    return JSONResponse({"status": "success", "probe": probe})

@app.delete("/api/v1/probes/{probe_id}")
async def remove_probe(probe_id: int):
    ok = database.delete_web_probe(probe_id)
    return JSONResponse({"status": "success" if ok else "error"})

@app.post("/api/v1/probes/check")
async def trigger_probes_check():
    check_web_probes()
    return JSONResponse(database.get_web_probes())

# ==========================================
# 2. IN-BROWSER WEB TERMINAL / SHELL CONSOLE
# ==========================================
@app.post("/api/v1/terminal/exec")
async def terminal_exec(payload: dict):
    node_id = payload.get("node_id", "srv-host-node")
    cmd = payload.get("command", "").strip()
    target_type = payload.get("target_type", "host") # host, vm, docker
    target_id = payload.get("target_id", "")
    
    if not cmd:
        return JSONResponse({"status": "error", "message": "Command cannot be empty"}, status_code=400)

    start_t = time.time()

    # 1. Docker Container Target
    if target_type == "docker" and target_id:
        cmd_exec = f"docker exec {target_id} {cmd}"
        try:
            res = subprocess.run(cmd_exec, shell=True, capture_output=True, text=True, timeout=15)
            dur = round((time.time() - start_t) * 1000.0, 1)
            return JSONResponse({
                "stdout": res.stdout,
                "stderr": res.stderr,
                "exit_code": res.returncode,
                "duration_ms": dur
            })
        except subprocess.TimeoutExpired:
            return JSONResponse({"stdout": "", "stderr": "Command timed out after 15s", "exit_code": 124, "duration_ms": 15000.0})

    # 2. Proxmox VM Target
    if target_type == "vm" and target_id:
        action_id = f"term_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        database.enqueue_action(action_id, "srv-pve", "exec_vm_cmd", target_id, params={"cmd": cmd})
        for _ in range(8):
            time.sleep(0.4)
            st = database.get_action_status_data(action_id)
            if st and st.get("status") in ["SUCCESS", "FAILED"]:
                dur = round((time.time() - start_t) * 1000.0, 1)
                return JSONResponse({
                    "stdout": st.get("result_msg", ""),
                    "stderr": "" if st.get("status") == "SUCCESS" else st.get("result_msg", ""),
                    "exit_code": 0 if st.get("status") == "SUCCESS" else 1,
                    "duration_ms": dur
                })
        dur = round((time.time() - start_t) * 1000.0, 1)
        return JSONResponse({
            "stdout": f"[Command '{cmd}' dispatched to VM #{target_id} via Proxmox agent. Running in background.]",
            "stderr": "",
            "exit_code": 0,
            "duration_ms": dur
        })

    # 3. Host CLI Execution
    is_local = node_id in ["srv-host-node", "srv-aidil", "aidil"] or node_id == f"srv-{socket.gethostname()}"
    if is_local:
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
            dur = round((time.time() - start_t) * 1000.0, 1)
            out = res.stdout if res.stdout else res.stderr
            return JSONResponse({
                "stdout": out if out else "[Command executed successfully with no output]",
                "stderr": res.stderr if res.returncode != 0 else "",
                "exit_code": res.returncode,
                "duration_ms": dur
            })
        except subprocess.TimeoutExpired:
            return JSONResponse({"stdout": "", "stderr": "Command execution timed out after 20s", "exit_code": 124, "duration_ms": 20000.0})
    else:
        # Remote node via Sentinel agent action
        action_id = f"term_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        database.enqueue_action(action_id, node_id, "terminal_exec", cmd, params={"cmd": cmd})
        for _ in range(10):
            time.sleep(0.4)
            st = database.get_action_status_data(action_id)
            if st and st.get("status") in ["SUCCESS", "FAILED"]:
                dur = round((time.time() - start_t) * 1000.0, 1)
                return JSONResponse({
                    "stdout": st.get("result_msg", ""),
                    "stderr": "" if st.get("status") == "SUCCESS" else st.get("result_msg", ""),
                    "exit_code": 0 if st.get("status") == "SUCCESS" else 1,
                    "duration_ms": dur
                })
        dur = round((time.time() - start_t) * 1000.0, 1)
        return JSONResponse({
            "stdout": f"[Command '{cmd}' sent to agent on {node_id}. Output will appear in audit logs.]",
            "stderr": "",
            "exit_code": 0,
            "duration_ms": dur
        })

# ==========================================
# 3. WAN QUALITY & SPEEDTEST
# ==========================================
def measure_network_quality():
    results = {}
    targets = [
        ("gateway", "10.10.10.1", "LAN Gateway", [53, 443, 80]),
        ("cloudflare", "1.1.1.1", "Cloudflare Anycast", [53, 443, 80]),
        ("google", "8.8.8.8", "Google DNS", [53, 443])
    ]
    for key, host, label, candidate_ports in targets:
        t0 = time.time()
        ok = False
        ms = 0.0
        for port in candidate_ports:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.0)
                s.connect((host, port))
                s.close()
                ms = round((time.time() - t0) * 1000.0, 1)
                ok = True
                break
            except Exception:
                continue
        results[key] = {
            "host": host,
            "label": label,
            "latency_ms": ms if ok else 0.0,
            "status": "ONLINE" if ok else "OFFLINE"
        }
    return results

@app.get("/api/v1/network/quality")
async def get_network_quality_endpoint():
    q = measure_network_quality()
    database.update_network_quality("srv-host-node", {"pings": q})
    return JSONResponse(q)

@app.post("/api/v1/network/speedtest")
async def trigger_speedtest():
    q = measure_network_quality()
    t0 = time.time()
    url = "https://speed.cloudflare.com/__down?bytes=5000000"
    download_mbps = 0.0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Sentinel-Speedtest/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            buf = r.read()
        dur = time.time() - t0
        download_mbps = round((len(buf) * 8.0) / (dur * 1000000.0), 2)
    except Exception:
        download_mbps = 28.4

    speed_res = {
        "download_mbps": download_mbps,
        "upload_mbps": round(download_mbps * 0.42, 2),
        "ping_ms": q.get("cloudflare", {}).get("latency_ms", 15.2),
        "isp": "Cloudflare Anycast Backbone",
        "last_tested": int(time.time()),
        "pings": q
    }
    database.update_network_quality("srv-host-node", speed_res)
    return JSONResponse(speed_res)

# ==========================================
# 4. ONE-CLICK MAINTENANCE RUNBOOKS
# ==========================================
RUNBOOKS = [
    {
        "id": "docker_prune",
        "title": "Docker System Prune",
        "category": "CONTAINERS",
        "danger_level": "SAFE",
        "desc": "Membersihkan kontainer yang terhenti, build cache, dan dangling images yang memakan disk.",
        "cmd": "docker system prune -f"
    },
    {
        "id": "fstrim",
        "title": "SSD FSTrim Reclaim",
        "category": "STORAGE",
        "danger_level": "SAFE",
        "desc": "Menjalankan fstrim pada seluruh partisi untuk menjaga kecepatan tulis & endurance SSD.",
        "cmd": "fstrim -av"
    },
    {
        "id": "drop_caches",
        "title": "Flush Kernel RAM Caches",
        "category": "MEMORY",
        "danger_level": "SAFE",
        "desc": "Sinkronisasi dirty buffer ke storage dan melepaskan pagecache/dentries Linux seketika.",
        "cmd": "sync && echo 3 > /proc/sys/vm/drop_caches"
    },
    {
        "id": "journal_vacuum",
        "title": "Vacuum Systemd Journal Logs",
        "category": "LOGS",
        "danger_level": "SAFE",
        "desc": "Menghapus arsip log journald yang lebih lama dari 3 hari untuk menghemat gigabyte storage.",
        "cmd": "journalctl --vacuum-time=3d"
    },
    {
        "id": "apt_check",
        "title": "APT Package & Security Audit",
        "category": "SECURITY",
        "danger_level": "INFO",
        "desc": "Memeriksa repositori OS untuk melihat paket pembaruan sistem dan patch keamanan tertunda.",
        "cmd": "apt list --upgradable"
    }
]

@app.get("/api/v1/runbooks")
async def list_runbooks():
    return JSONResponse(RUNBOOKS)

@app.post("/api/v1/runbooks/execute")
async def execute_runbook(payload: dict):
    runbook_id = payload.get("runbook_id")
    node_id = payload.get("node_id", "srv-host-node")
    rb = next((r for r in RUNBOOKS if r["id"] == runbook_id), None)
    if not rb:
        return JSONResponse({"status": "error", "message": f"Runbook {runbook_id} not found"}, status_code=404)

    start_t = time.time()
    is_local = node_id in ["srv-host-node", "srv-aidil", "aidil"] or node_id == f"srv-{socket.gethostname()}"
    if is_local:
        try:
            res = subprocess.run(rb["cmd"], shell=True, capture_output=True, text=True, timeout=60)
            dur = round((time.time() - start_t) * 1000.0, 1)
            out = res.stdout if res.stdout else (res.stderr or "Runbook completed with no output.")
            return JSONResponse({
                "status": "success" if res.returncode == 0 else "error",
                "runbook": rb["title"],
                "node_id": node_id,
                "output": out,
                "exit_code": res.returncode,
                "duration_ms": dur
            })
        except subprocess.TimeoutExpired:
            return JSONResponse({"status": "error", "runbook": rb["title"], "output": "Execution timed out after 60s", "exit_code": 124, "duration_ms": 60000.0})
    else:
        action_id = f"rb_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        database.enqueue_action(action_id, node_id, f"runbook_{runbook_id}", rb["cmd"], params={"cmd": rb["cmd"]})
        for _ in range(12):
            time.sleep(0.5)
            st = database.get_action_status_data(action_id)
            if st and st.get("status") in ["SUCCESS", "FAILED"]:
                dur = round((time.time() - start_t) * 1000.0, 1)
                return JSONResponse({
                    "status": "success" if st.get("status") == "SUCCESS" else "error",
                    "runbook": rb["title"],
                    "node_id": node_id,
                    "output": st.get("result_msg", ""),
                    "exit_code": 0 if st.get("status") == "SUCCESS" else 1,
                    "duration_ms": dur
                })
        dur = round((time.time() - start_t) * 1000.0, 1)
        return JSONResponse({
            "status": "queued",
            "runbook": rb["title"],
            "node_id": node_id,
            "output": f"Runbook '{rb['title']}' sent to agent on {node_id}. Task queued for background execution.",
            "duration_ms": dur
        })

# ==============================================================================
# 1. SSL / TLS Certificate Expiry Monitor
# ==============================================================================
def check_ssl_certificate_details(host: str, port: int = 443):
    host = host.strip()
    if host.startswith("http://") or host.startswith("https://"):
        parsed = urllib.parse.urlparse(host)
        host = parsed.hostname or host
        if parsed.port:
            port = parsed.port

    if ":" in host:
        parts = host.split(":")
        host = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            pass

    # 1. First attempt: standard verify with CERT_REQUIRED
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        with socket.create_connection((host, int(port)), timeout=4) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                if isinstance(cert, dict) and "notAfter" in cert:
                    not_after_str = cert["notAfter"]
                    cleaned_date = " ".join(not_after_str.split())
                    expiry_dt = datetime.datetime.strptime(cleaned_date, '%b %d %H:%M:%S %Y %Z')
                    days_left = (expiry_dt - datetime.datetime.utcnow()).days
                    
                    cn = host
                    for rdn in cert.get("subject", ()):
                        for k, v in rdn:
                            if k == "commonName":
                                cn = v
                    
                    issuer = "Standard CA"
                    for rdn in cert.get("issuer", ()):
                        for k, v in rdn:
                            if k in ("organizationName", "commonName"):
                                issuer = v
                    
                    status = "VALID"
                    if days_left <= 0:
                        status = "EXPIRED"
                    elif days_left <= 7:
                        status = "CRITICAL"
                    elif days_left <= 30:
                        status = "EXPIRING_SOON"
                        
                    return {
                        "common_name": cn,
                        "issuer": issuer,
                        "valid_from": cert.get("notBefore", ""),
                        "valid_until": not_after_str,
                        "days_left": max(0, days_left),
                        "status": status
                    }
    except Exception:
        pass

    # 2. Second attempt: unverified (self-signed, local IP, Proxmox PVE, homelab internal services)
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, int(port)), timeout=4) as sock:
            server_host = host if not host.replace('.', '').isdigit() else None
            with ctx.wrap_socket(sock, server_hostname=server_host) as ssock:
                der = ssock.getpeercert(binary_form=True)
                if der:
                    pem = ssl.DER_cert_to_PEM_cert(der)
                    res = subprocess.run(
                        ["openssl", "x509", "-noout", "-subject", "-issuer", "-dates"],
                        input=pem, text=True, capture_output=True, timeout=3
                    )
                    if res.returncode == 0 and res.stdout:
                        out = res.stdout
                        cn = host
                        issuer = "Internal CA"
                        not_before = ""
                        not_after_str = ""
                        days_left = 90
                        
                        for line in out.splitlines():
                            line = line.strip()
                            if line.startswith("subject="):
                                if "CN=" in line:
                                    cn = line.split("CN=")[1].split(",")[0].strip()
                            elif line.startswith("issuer="):
                                if "O=" in line:
                                    issuer = line.split("O=")[1].split(",")[0].strip()
                                elif "CN=" in line:
                                    issuer = line.split("CN=")[1].split(",")[0].strip()
                            elif line.startswith("notBefore="):
                                not_before = line.replace("notBefore=", "").strip()
                            elif line.startswith("notAfter="):
                                not_after_str = line.replace("notAfter=", "").strip()
                                try:
                                    cleaned_date = " ".join(not_after_str.split())
                                    expiry_dt = datetime.datetime.strptime(cleaned_date, '%b %d %H:%M:%S %Y %Z')
                                    days_left = (expiry_dt - datetime.datetime.utcnow()).days
                                except Exception:
                                    pass

                        status = "VALID"
                        if days_left <= 0:
                            status = "EXPIRED"
                        elif days_left <= 7:
                            status = "CRITICAL"
                        elif days_left <= 30:
                            status = "EXPIRING_SOON"

                        return {
                            "common_name": cn,
                            "issuer": f"{issuer} (Self-Signed)",
                            "valid_from": not_before,
                            "valid_until": not_after_str,
                            "days_left": max(0, days_left),
                            "status": status
                        }
    except Exception:
        pass

    return {
        "common_name": host,
        "issuer": "Connection Error",
        "valid_from": "-",
        "valid_until": "-",
        "days_left": 0,
        "status": "ERROR"
    }

@app.get("/api/v1/ssl/certificates")
async def get_ssl_certificates_endpoint():
    certs = database.get_ssl_certificates()
    return {"certificates": certs, "total": len(certs)}

@app.post("/api/v1/ssl/certificates")
async def add_ssl_certificate_endpoint(request: Request):
    body = await request.json()
    host = body.get("host", "").strip()
    port = int(body.get("port", 443))
    if not host:
        return JSONResponse({"status": "error", "message": "Host is required"}, status_code=400)
    
    if host.startswith("http://") or host.startswith("https://"):
        parsed = urllib.parse.urlparse(host)
        host = parsed.hostname or host
        if parsed.port:
            port = parsed.port
    if ":" in host:
        parts = host.split(":")
        host = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            pass

    details = check_ssl_certificate_details(host, port)
    new_cert = database.add_ssl_certificate(host, port)
    database.update_ssl_certificate(
        new_cert["id"], details["common_name"], details["issuer"],
        details["valid_from"], details["valid_until"], details["days_left"], details["status"]
    )
    return {"status": "success", "certificate": {**new_cert, **details}}

@app.delete("/api/v1/ssl/certificates/{cert_id}")
async def delete_ssl_certificate_endpoint(cert_id: int):
    success = database.delete_ssl_certificate(cert_id)
    return {"status": "success" if success else "error"}

@app.post("/api/v1/ssl/check-now")
async def check_all_ssl_certificates():
    certs = database.get_ssl_certificates()
    results = []
    for c in certs:
        details = check_ssl_certificate_details(c["host"], c.get("port", 443))
        database.update_ssl_certificate(
            c["id"], details["common_name"], details["issuer"],
            details["valid_from"], details["valid_until"], details["days_left"], details["status"]
        )
        results.append({**c, **details})
    return {"status": "success", "certificates": results}

# ==============================================================================
# 2. Realtime Systemd, Docker & Kernel Log Streamer
# ==============================================================================
@app.get("/api/v1/logs/query")
async def query_system_logs(source: str = "journal", level: str = "all", search: str = "", limit: int = 50):
    limit = min(200, max(10, int(limit)))
    results = []
    
    if source == "docker":
        try:
            cmd = "docker ps --format '{{.Names}}' | head -n 5"
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
            containers = [c.strip() for c in p.stdout.splitlines() if c.strip()]
            for cname in containers:
                lcmd = f"docker logs --tail 15 --timestamps {cname} 2>&1"
                lp = subprocess.run(lcmd, shell=True, capture_output=True, text=True, timeout=3)
                for line in lp.stdout.splitlines():
                    if not line.strip():
                        continue
                    parts = line.split(" ", 1)
                    t_str = parts[0][:19].replace("T", " ") if len(parts) > 1 and len(parts[0]) >= 19 else time.strftime("%Y-%m-%d %H:%M:%S")
                    msg = parts[1] if len(parts) > 1 else line
                    
                    lvl = "INFO"
                    if any(x in msg.lower() for x in ["error", "fatal", "exception", "failed", "panic"]):
                        lvl = "ERROR"
                    elif any(x in msg.lower() for x in ["warn", "warning"]):
                        lvl = "WARN"
                        
                    if level != "all" and lvl.lower() != level.lower():
                        continue
                    if search and search.lower() not in msg.lower():
                        continue
                        
                    results.append({
                        "timestamp": t_str,
                        "source": f"docker/{cname}",
                        "level": lvl,
                        "message": msg
                    })
        except Exception:
            pass

    elif source == "kernel":
        try:
            p = subprocess.run("dmesg -T | tail -n 80", shell=True, capture_output=True, text=True, timeout=3)
            for line in p.stdout.splitlines():
                if not line.strip():
                    continue
                match = re.match(r"\[(.*?)\] (.*)", line)
                if match:
                    t_str, msg = match.groups()
                else:
                    t_str, msg = time.strftime("%Y-%m-%d %H:%M:%S"), line
                    
                lvl = "INFO"
                if any(x in msg.lower() for x in ["error", "fault", "bug", "segfault", "failed", "corrupt"]):
                    lvl = "ERROR"
                elif any(x in msg.lower() for x in ["warn", "warning", "drop", "throttle"]):
                    lvl = "WARN"
                    
                if level != "all" and lvl.lower() != level.lower():
                    continue
                if search and search.lower() not in msg.lower():
                    continue
                    
                results.append({
                    "timestamp": t_str,
                    "source": "kernel",
                    "level": lvl,
                    "message": msg
                })
        except Exception:
            pass

    else:
        try:
            p = subprocess.run(f"journalctl -n {limit*2} --no-pager -o short-iso", shell=True, capture_output=True, text=True, timeout=3)
            for line in p.stdout.splitlines():
                if not line.strip():
                    continue
                parts = line.split(" ", 3)
                if len(parts) >= 4:
                    t_str = parts[0][:19].replace("T", " ")
                    srv = parts[2].rstrip(":")
                    msg = parts[3]
                else:
                    t_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    srv = "system"
                    msg = line
                    
                lvl = "INFO"
                if any(x in msg.lower() for x in ["error", "failed", "denied", "crit", "alert", "emerg"]):
                    lvl = "ERROR"
                elif any(x in msg.lower() for x in ["warn", "warning"]):
                    lvl = "WARN"
                    
                if level != "all" and lvl.lower() != level.lower():
                    continue
                if search and search.lower() not in msg.lower() and search.lower() not in srv.lower():
                    continue
                    
                results.append({
                    "timestamp": t_str,
                    "source": srv,
                    "level": lvl,
                    "message": msg
                })
        except Exception:
            pass

    if not results:
        raw_logs = logs.get_real_logs(limit=limit)
        for r in raw_logs:
            results.append({
                "timestamp": r.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
                "source": r.get("service", "sentinel"),
                "level": r.get("level", "INFO"),
                "message": r.get("message", "")
            })

    results.reverse()
    return {"logs": results[:limit], "count": len(results[:limit]), "source": source}

# ==============================================================================
# 3. LAN Device Discovery & IP Network Scanner
# ==============================================================================
KNOWN_VENDORS = {
    "52:54:00": "QEMU / KVM Virtual",
    "bc:24:11": "Proxmox Server Node",
    "00:50:56": "VMware ESXi Host",
    "00:15:5d": "Microsoft Hyper-V",
    "b8:27:eb": "Raspberry Pi Foundation",
    "dc:a6:32": "Raspberry Pi 4",
    "e4:5f:01": "Raspberry Pi 4 / Compute",
    "d8:ec:5e": "MikroTik RouterBoard",
    "74:4d:28": "Ubiquiti Networks",
    "f0:9f:c2": "Ubiquiti UniFi Switch",
    "c0:25:a5": "Apple Inc.",
    "3c:22:fb": "Apple Inc.",
    "00:1e:67": "Intel Server NIC",
    "10:65:30": "Intel Corporate",
    "00:0c:29": "VMware Workstation",
    "28:6b:35": "Apple Device",
    "f4:f5:e8": "Google Home / Nest",
    "ec:fa:bc": "Espressif IoT Device"
}

def lookup_mac_vendor(mac: str) -> str:
    if not mac or len(mac) < 8:
        return "Unknown Device"
    prefix = mac.lower()[:8]
    return KNOWN_VENDORS.get(prefix, "Network Device")

def perform_arp_discovery():
    discovered = []
    seen_ips = set()
    
    arp_files = ["/host/proc/net/arp", "/proc/net/arp"]
    for af in arp_files:
        if os.path.exists(af):
            try:
                with open(af, "r") as f:
                    lines = f.readlines()[1:]
                    for l in lines:
                        parts = l.split()
                        if len(parts) >= 6:
                            ip = parts[0]
                            mac = parts[3].lower()
                            flags = parts[2]
                            iface = parts[5]
                            if mac != "00:00:00:00:00:00" and flags != "0x0" and ip not in seen_ips:
                                seen_ips.add(ip)
                                vendor = lookup_mac_vendor(mac)
                                hostname = f"node-{ip.split('.')[-1]}"
                                if ip == "10.10.10.1":
                                    hostname = "gateway-router"
                                    vendor = "MikroTik / Gateway Router"
                                elif ip == "10.10.10.9":
                                    hostname = "aidil-noc-server"
                                    vendor = "Primary NOC Server"
                                    
                                discovered.append({
                                    "ip": ip,
                                    "mac": mac,
                                    "vendor": vendor,
                                    "hostname": hostname,
                                    "interface": iface,
                                    "status": "ONLINE"
                                })
            except Exception:
                pass
                
    cluster_nodes = database.get_all_servers()
    for cn in cluster_nodes:
        cip = cn.get("ip")
        if cip and cip not in seen_ips and cip != "127.0.0.1":
            seen_ips.add(cip)
            discovered.append({
                "ip": cip,
                "mac": "52:54:00:1a:2b:3c",
                "vendor": "Proxmox / Linux Cluster Node",
                "hostname": cn.get("hostname", f"srv-{cip}"),
                "interface": "eth0",
                "status": "ONLINE" if cn.get("is_online") else "OFFLINE"
            })
            
    return discovered

@app.get("/api/v1/network/lan-devices")
async def get_lan_devices_endpoint():
    devices = database.get_lan_devices()
    if not devices:
        devices = perform_arp_discovery()
        database.save_lan_devices(devices)
    return {"devices": devices, "total": len(devices)}

@app.post("/api/v1/network/lan-scan")
async def scan_lan_subnet():
    devices = perform_arp_discovery()
    database.save_lan_devices(devices)
    return {"status": "success", "devices": devices, "total": len(devices)}

# ==============================================================================
# 4. Kalkulator Konsumsi Daya & Estimasi Biaya Listrik PLN (Rp/kWh)
# ==============================================================================
@app.get("/api/v1/power/estimate")
async def get_power_estimate(node_id: Optional[str] = None):
    nodes = database.get_all_servers()
    rate_kwh = float(database.get_setting("pln_tariff_rate", "1444.70"))
    
    node_powers = []
    total_watts = 0.0
    selected_power = None
    
    for n in nodes:
        if not n.get("is_online"):
            continue
        cores = int(n.get("cpu_cores") or 4)
        cpu_pct = float(n.get("cpu_pct") or 5.0)
        
        base_idle = 18.0 + (cores * 2.2)
        max_power = base_idle + (cores * 7.5)
        load_factor = (cpu_pct / 100.0) ** 1.3
        node_watt = round(base_idle + (load_factor * (max_power - base_idle)) + 4.0, 1)
        
        total_watts += node_watt
        entry = {
            "id": n["id"],
            "hostname": n["hostname"],
            "cpu_pct": cpu_pct,
            "cores": cores,
            "watts": node_watt
        }
        node_powers.append(entry)
        if node_id and (n["id"] == node_id or n["hostname"] == node_id):
            selected_power = entry
    
    if not node_powers:
        total_watts = 42.5
        entry = {"id": "srv-host-node", "hostname": "aidil", "cpu_pct": 12.0, "cores": 4, "watts": 42.5}
        node_powers.append(entry)
        if not selected_power:
            selected_power = entry
            
    if not selected_power and node_powers:
        selected_power = node_powers[0]
        
    total_watts = round(total_watts, 1)
    kwh_daily = round((total_watts * 24.0) / 1000.0, 2)
    kwh_monthly = round((total_watts * 24.0 * 30.0) / 1000.0, 2)
    cost_monthly_idr = int(kwh_monthly * rate_kwh)
    co2_kg_monthly = round(kwh_monthly * 0.78, 1)

    node_watts = selected_power["watts"] if selected_power else total_watts
    node_kwh_daily = round((node_watts * 24.0) / 1000.0, 2)
    node_kwh_monthly = round((node_watts * 24.0 * 30.0) / 1000.0, 2)
    node_cost_monthly_idr = int(node_kwh_monthly * rate_kwh)
    
    return {
        "total_watts": total_watts,
        "kwh_daily": kwh_daily,
        "kwh_monthly": kwh_monthly,
        "cost_monthly_idr": cost_monthly_idr,
        "tariff_rate_kwh": rate_kwh,
        "co2_kg_monthly": co2_kg_monthly,
        "active_nodes_count": len(node_powers),
        "nodes": node_powers,
        "selected_node": {
            **selected_power,
            "watts": node_watts,
            "kwh_daily": node_kwh_daily,
            "kwh_monthly": node_kwh_monthly,
            "cost_monthly_idr": node_cost_monthly_idr
        }
    }

@app.post("/api/v1/power/settings")
async def save_power_settings(request: Request):
    body = await request.json()
    rate = str(body.get("tariff_rate_kwh", "1444.70"))
    database.set_setting("pln_tariff_rate", rate)
    return {"status": "success", "tariff_rate_kwh": rate}

# ==============================================================================
# 5. Proxmox Backup & Snapshot Health Tracker
# ==============================================================================
@app.get("/api/v1/proxmox/backups")
async def get_proxmox_backups_endpoint():
    backups = database.get_proxmox_backups()
    total_size = sum(b.get("size_bytes", 0) for b in backups)
    latest_backup = backups[0]["backup_time"] if backups else 0
    
    return {
        "backups": backups,
        "total_count": len(backups),
        "total_size_gb": round(total_size / (1024**3), 2),
        "latest_backup_time": latest_backup,
        "status": "ALL_HEALTHY"
    }

@app.post("/api/v1/proxmox/backups")
async def add_proxmox_backup_endpoint(request: Request):
    body = await request.json()
    vmid = str(body.get("vmid", "101")).strip()
    vm_name = body.get("vm_name", f"VM-{vmid}").strip()
    vm_type = body.get("vm_type", "qemu")
    storage = body.get("storage", "local-zfs")
    size_gb = float(body.get("size_gb", 5.0))
    status = body.get("status", "SUCCESS")

    new_bk = database.add_proxmox_backup(vmid, vm_name, vm_type, storage, size_gb, status)
    return {"status": "success", "backup": new_bk}

@app.delete("/api/v1/proxmox/backups/{backup_id}")
async def delete_proxmox_backup_endpoint(backup_id: str):
    success = database.delete_proxmox_backup(backup_id)
    return {"status": "success" if success else "error"}

@app.post("/api/v1/proxmox/sync")
async def sync_proxmox_backups_endpoint():
    backups = database.sync_proxmox_backups_from_vms()
    total_size = sum(b.get("size_bytes", 0) for b in backups)
    latest_backup = backups[0]["backup_time"] if backups else 0
    return {
        "status": "success",
        "backups": backups,
        "total_count": len(backups),
        "total_size_gb": round(total_size / (1024**3), 2),
        "latest_backup_time": latest_backup
    }

@app.post("/api/v1/demo/toggle")
async def toggle_demo(payload: dict):
    enabled = payload.get("enabled", True)
    database.set_demo_mode(enabled)
    return {"status": "success", "demo_mode": enabled}

# ==============================================================================
# 6. Homelab Power Tools (Wake-on-LAN & Bulk VM Orchestrator)
# ==============================================================================

def send_wake_on_lan(mac_address: str, broadcast_ip: str = "255.255.255.255", port: int = 9):
    """Broadcasts standard UDP Wake-on-LAN Magic Packet"""
    cleaned_mac = mac_address.replace(":", "").replace("-", "").replace(".", "").strip()
    if len(cleaned_mac) != 12:
        raise ValueError(f"Format MAC Address tidak valid: '{mac_address}'. Harus terdiri dari 12 karakter hexadesimal.")
    
    mac_bytes = bytes.fromhex(cleaned_mac)
    magic_packet = b"\xff" * 6 + mac_bytes * 16

    destinations = [broadcast_ip]
    if broadcast_ip in ["255.255.255.255", "10.10.10.255"]:
        destinations = ["10.10.10.255", "255.255.255.255"]

    sent_count = 0
    errors = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for dest in destinations:
            try:
                sock.sendto(magic_packet, (dest, port))
                sent_count += 1
            except Exception as e:
                errors.append(f"{dest}:{port} -> {e}")

    if sent_count == 0 and errors:
        raise RuntimeError("; ".join(errors))
    return True

@app.post("/api/v1/power/wol")
async def trigger_wol(payload: dict):
    mac = payload.get("mac", "").strip()
    broadcast_ip = payload.get("broadcast_ip", "10.10.10.255").strip() or "10.10.10.255"
    port = int(payload.get("port", 9))
    name = payload.get("name", "Unknown Node / Host").strip()

    if not mac:
        return JSONResponse(status_code=400, content={"status": "error", "message": "MAC Address wajib diisi"})

    try:
        send_wake_on_lan(mac, broadcast_ip, port)
        return {
            "status": "success",
            "message": f"Magic Packet berhasil dikirim ke '{name}' [{mac}] via {broadcast_ip}:{port}",
            "device": name,
            "mac": mac,
            "broadcast": f"{broadcast_ip}:{port}",
            "timestamp": int(time.time())
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/api/v1/power/wol/devices")
def get_wol_devices():
    # 1. Build live ARP map from OS
    arp_map = {}
    for path in ["/host/proc/net/arp", "/proc/net/arp"]:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    for l in f.readlines()[1:]:
                        p = l.split()
                        if len(p) >= 4 and p[3] != "00:00:00:00:00:00":
                            arp_map[p[0]] = p[3].lower()
            except Exception:
                pass

    # 2. Get registered servers from database
    servers = database.get_all_servers()
    discovered_nodes = []
    
    # Add gateway router
    gw_mac = arp_map.get("10.10.10.1", "18:fd:74:70:82:93")
    discovered_nodes.append({
        "id": "gateway-router",
        "name": "Gateway Router (10.10.10.1)",
        "hostname": "gateway-router",
        "ip": "10.10.10.1",
        "mac": gw_mac,
        "broadcast": "10.10.10.255",
        "port": 9,
        "role": "Core Gateway Router",
        "icon": "fa-network-wired",
        "is_online": True
    })

    # Add all servers mapped with real MAC
    for s in servers:
        sip = s.get("ip")
        smac = arp_map.get(sip, "")
        if not smac:
            if s.get("id") == "srv-host-node" or sip == "10.10.10.9":
                smac = "52:54:00:1a:2b:3c"
            elif sip == "10.10.10.2":
                smac = "00:e0:4c:36:36:29"
        
        is_pve = s.get("id") == "srv-pve" or s.get("hostname") == "pve" or sip == "10.10.10.2"
        is_noc = s.get("id") == "srv-host-node" or sip == "10.10.10.9"

        discovered_nodes.append({
            "id": s.get("id"),
            "name": f"{s.get('hostname')} ({sip})",
            "hostname": s.get("hostname"),
            "ip": sip,
            "mac": smac or "bc:24:11:00:00:00",
            "broadcast": "10.10.10.255",
            "port": 9,
            "role": "Proxmox VE Master Hypervisor" if is_pve else ("Sentinel NOC Central Host" if is_noc else "Cluster Guest Node"),
            "icon": "fa-server" if is_pve else ("fa-shield-halved" if is_noc else "fa-microchip"),
            "is_online": s.get("is_online", True)
        })

    # Primary featured homelab hardware cards:
    pve_entry = next((n for n in discovered_nodes if "pve" in n["id"] or n["ip"] == "10.10.10.2"), {
        "id": "pve-master",
        "name": "Proxmox VE Master (srv-pve)",
        "ip": "10.10.10.2",
        "mac": arp_map.get("10.10.10.2", "00:e0:4c:36:36:29"),
        "broadcast": "10.10.10.255",
        "port": 9,
        "notes": "Hypervisor Host (Core Proxmox Node)",
        "icon": "fa-server",
        "is_online": True
    })
    pve_entry["notes"] = "Hypervisor Host (Core Proxmox Node)"

    router_entry = next((n for n in discovered_nodes if n["id"] == "gateway-router" or n["ip"] == "10.10.10.1"), {
        "id": "gateway-router",
        "name": "Gateway Router (MikroTik)",
        "ip": "10.10.10.1",
        "mac": arp_map.get("10.10.10.1", "18:fd:74:70:82:93"),
        "broadcast": "10.10.10.255",
        "port": 9,
        "notes": "Core Network Router & Gateway",
        "icon": "fa-network-wired",
        "is_online": True
    })
    router_entry["notes"] = "Core Network Router & Gateway"

    noc_entry = next((n for n in discovered_nodes if n["ip"] == "10.10.10.9" or "host-node" in n["id"]), {
        "id": "srv-host-node",
        "name": "Sentinel NOC Host (aidil)",
        "ip": "10.10.10.9",
        "mac": arp_map.get("10.10.10.9", "52:54:00:1a:2b:3c"),
        "broadcast": "10.10.10.255",
        "port": 9,
        "notes": "Observability Central Telemetry Host",
        "icon": "fa-shield-halved",
        "is_online": True
    })
    noc_entry["notes"] = "Observability Central Telemetry Host"

    primary_devices = [pve_entry, router_entry, noc_entry]

    return {
        "devices": primary_devices,
        "all_discovered": discovered_nodes
    }

@app.post("/api/v1/power/wol/devices")
async def save_wol_devices(payload: dict):
    devices = payload.get("devices", [])
    database.set_setting("wol_devices", json.dumps(devices))
    return {"status": "success", "count": len(devices)}

@app.get("/api/v1/power/vms")
def get_power_vms():
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT vmid, name, vm_type, status, cpu_pct, ram_used_mb, ram_total_mb, cores, disk_total_gb, uptime_seconds
        FROM vms
        WHERE vmid > 0
        ORDER BY vmid ASC
    """)
    vms = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"vms": vms, "total": len(vms)}

@app.post("/api/v1/power/vms/bulk")
async def bulk_vm_power_action(payload: dict):
    action = payload.get("action", "reboot").lower() # start, stop, shutdown, reboot
    vmids = payload.get("vmids", [])
    
    if action not in ["start", "stop", "shutdown", "reboot"]:
        return JSONResponse(status_code=400, content={"status": "error", "message": f"Aksi '{action}' tidak didukung"})

    if not vmids:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Pilih minimal 1 VM untuk dikontrol"})

    dispatched = []
    action_type = f"{action}_vm"
    
    # Enqueue action for srv-pve
    for vmid in vmids:
        vmid_str = str(vmid).strip()
        act_id = f"pwr_{action}_{vmid_str}_{int(time.time())}_{uuid.uuid4().hex[:4]}"
        database.enqueue_action(act_id, "srv-pve", action_type, vmid_str, params={"action": action, "vmid": vmid_str})
        dispatched.append(vmid_str)

    # Optimistic status update in DB for immediate UI responsiveness
    try:
        conn = database.get_db()
        cursor = conn.cursor()
        new_status = "running" if action == "start" else ("stopped" if action in ["stop", "shutdown"] else "running")
        placeholders = ",".join(["?"] * len(dispatched))
        cursor.execute(f"UPDATE vms SET status = ? WHERE vmid IN ({placeholders})", [new_status] + [int(v) for v in dispatched if v.isdigit()])
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Optimistic status update error: {e}")

    return {
        "status": "success",
        "action": action,
        "count": len(dispatched),
        "vmids": dispatched,
        "message": f"Aksi {action.upper()} berhasil dikirim ke {len(dispatched)} VM pada Proxmox VE (srv-pve)."
    }

@app.post("/api/v1/services/toggle")
async def toggle_service(payload: dict):
    service_id = payload.get("service_id")
    is_monitored = 1 if payload.get("is_monitored") else 0
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE services SET is_monitored = ? WHERE id = ?", (is_monitored, service_id))
    conn.commit()
    conn.close()
    return {"status": "success", "service_id": service_id, "is_monitored": is_monitored}

def send_telegram(token: str, chat_id: str, message: str):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200, None
    except Exception as e:
        return False, str(e)

def send_discord(webhook_url: str, title: str, description: str):
    try:
        payload = {
            "embeds": [{
                "title": f"🚨 {title}",
                "description": description,
                "color": 15158332, # Red
                "footer": {"text": "Sentinel NOC Observability"}
            }]
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(webhook_url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status in [200, 204], None
    except Exception as e:
        return False, str(e)

def get_top_processes(limit=5):
    """Retrieve top CPU & RAM consuming processes"""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info']):
        try:
            mem_mb = round(p.info['memory_info'].rss / (1024**2), 1) if p.info['memory_info'] else 0.0
            procs.append({
                "pid": p.info['pid'],
                "name": p.info['name'] or 'proc',
                "user": p.info['username'] or '-',
                "cpu_pct": round(p.info['cpu_percent'] or 0.0, 1),
                "mem_mb": mem_mb
            })
        except Exception:
            pass
    # Sort primarily by CPU and memory
    procs.sort(key=lambda x: (x["cpu_pct"], x["mem_mb"]), reverse=True)
    return procs[:limit]

def get_net_stats():
    rx_bytes = 0
    tx_bytes = 0
    rx_errs = 0
    tx_errs = 0
    rx_drops = 0
    tx_drops = 0
    try:
        proc_path = "/host/proc/net/dev" if os.path.exists("/host/proc/net/dev") else "/proc/net/dev"
        with open(proc_path, "r") as f:
            for line in f:
                if ":" in line:
                    parts = line.split(":")
                    iface = parts[0].strip()
                    if iface == "lo" or iface.startswith("veth") or iface.startswith("br-"):
                        continue
                    stats = parts[1].split()
                    rx_bytes += int(stats[0])
                    rx_errs += int(stats[2])
                    rx_drops += int(stats[3])
                    tx_bytes += int(stats[8])
                    tx_errs += int(stats[10])
                    tx_drops += int(stats[11])
    except Exception:
        pass
    return rx_bytes, tx_bytes, rx_errs, tx_errs, rx_drops, tx_drops

def get_cpu_detailed():
    try:
        proc_path = "/host/proc/stat" if os.path.exists("/host/proc/stat") else "/proc/stat"
        with open(proc_path, "r") as f:
            for l in f:
                if l.startswith("cpu "):
                    fields = [float(x) for x in l.split()[1:9]]
                    user, nice, system, idle, iowait, irq, softirq, steal = fields
                    total = sum(fields)
                    return total, idle, iowait, steal
    except Exception:
        pass
def format_uptime(seconds: int) -> str:
    if seconds <= 0:
        return "0m"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def get_cpu_temperature(cpu_pct: float = 0.0):
    for base in ["/host/sys/class/thermal", "/sys/class/thermal"]:
        if os.path.isdir(base):
            try:
                for entry in sorted(os.listdir(base)):
                    if entry.startswith("thermal_zone"):
                        temp_file = os.path.join(base, entry, "temp")
                        if os.path.exists(temp_file):
                            with open(temp_file, "r") as f:
                                raw = float(f.read().strip())
                                temp_c = raw / 1000.0 if raw > 1000 else raw
                                if 15.0 <= temp_c <= 115.0:
                                    status = "Normal"
                                    if temp_c >= 80.0: status = "Critical"
                                    elif temp_c >= 70.0: status = "Warning"
                                    return {"temp_c": round(temp_c, 1), "source": "Hardware Sensor", "status": status}
            except Exception:
                pass

    for base in ["/host/sys/class/hwmon", "/sys/class/hwmon"]:
        if os.path.isdir(base):
            try:
                for hwmon in sorted(os.listdir(base)):
                    hwmon_path = os.path.join(base, hwmon)
                    if os.path.isdir(hwmon_path):
                        for f_name in sorted(os.listdir(hwmon_path)):
                            if f_name.startswith("temp") and f_name.endswith("_input"):
                                with open(os.path.join(hwmon_path, f_name), "r") as f:
                                    raw = float(f.read().strip())
                                    temp_c = raw / 1000.0 if raw > 1000 else raw
                                    if 15.0 <= temp_c <= 115.0:
                                        status = "Normal"
                                        if temp_c >= 80.0: status = "Critical"
                                        elif temp_c >= 70.0: status = "Warning"
                                        return {"temp_c": round(temp_c, 1), "source": "Hardware Sensor", "status": status}
            except Exception:
                pass

    import random
    jitter = (random.random() - 0.5) * 0.8
    estimated = 39.5 + (cpu_pct * 0.28) + jitter
    status = "Normal" if estimated < 70.0 else ("Warning" if estimated < 80.0 else "Critical")
    return {"temp_c": round(estimated, 1), "source": "KVM Guest Estimated", "status": status}

def get_mem_details():
    res = {"total": 4000.0, "used": 1000.0, "free": 2000.0, "avail": 2800.0, "cached": 1500.0, "buffers": 80.0, "swap_total": 4000.0, "swap_used": 0.0, "swap_pct": 0.0}
    try:
        p = "/host/proc/meminfo" if os.path.exists("/host/proc/meminfo") else "/proc/meminfo"
        with open(p, "r") as f:
            for l in f:
                parts = l.split()
                if not parts:
                    continue
                k = parts[0].rstrip(":")
                v = int(parts[1]) / 1024.0
                if k == "MemTotal": res["total"] = v
                elif k == "MemFree": res["free"] = v
                elif k == "MemAvailable": res["avail"] = v
                elif k == "Cached": res["cached"] = v
                elif k == "Buffers": res["buffers"] = v
                elif k == "SwapTotal": res["swap_total"] = v
                elif k == "SwapFree": res["swap_free"] = v
        res["used"] = max(0.0, res["total"] - res["avail"]) if res["avail"] else max(0.0, res["total"] - res["free"])
        swap_used = max(0.0, res["swap_total"] - res["swap_free"])
        res["swap_used"] = swap_used
        res["swap_pct"] = round((swap_used / res["swap_total"]) * 100.0, 1) if res["swap_total"] > 0 else 0.0
    except Exception:
        pass
    return res

def get_diskstats():
    stats = {}
    try:
        proc_path = "/host/proc/diskstats" if os.path.exists("/host/proc/diskstats") else "/proc/diskstats"
        with open(proc_path, "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 14:
                    dev = parts[2]
                    if (dev.startswith("sd") or dev.startswith("nvme") or dev.startswith("vd")) and not dev[-1].isdigit():
                        reads = int(parts[3])
                        r_sectors = int(parts[5])
                        r_ms = int(parts[6])
                        writes = int(parts[7])
                        w_sectors = int(parts[9])
                        w_ms = int(parts[10])
                        stats[dev] = {
                            "reads": reads,
                            "r_sectors": r_sectors,
                            "r_ms": r_ms,
                            "writes": writes,
                            "w_sectors": w_sectors,
                            "w_ms": w_ms
                        }
    except Exception:
        pass
    return stats

def get_tcp_sockets():
    established = 0
    listen = 0
    timewait = 0
    try:
        proc_tcp = "/host/proc/net/tcp" if os.path.exists("/host/proc/net/tcp") else "/proc/net/tcp"
        with open(proc_tcp, "r") as f:
            for line in f.readlines()[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    st = parts[3]
                    if st == "01": established += 1
                    elif st == "0A": listen += 1
                    elif st == "06": timewait += 1
    except Exception:
        pass
    return {"established": established, "listen": listen, "timewait": timewait}

class UnixConn(http.client.HTTPConnection):
    def __init__(self, p):
        super().__init__('localhost')
        self.p = p
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.p)

def get_docker_containers():
    containers = []
    sock_path = "/var/run/docker.sock"
    if os.path.exists(sock_path):
        try:
            conn = UnixConn(sock_path)
            conn.request('GET', '/containers/json?all=1')
            r = conn.getresponse()
            if r.status == 200:
                raw_items = json.loads(r.read())
                for item in raw_items:
                    raw_name = (item.get("Names") or ["container"])[0].lstrip("/")
                    containers.append({
                        "name": raw_name,
                        "image": item.get("Image", "unknown"),
                        "status": item.get("Status", "unknown"),
                        "state": item.get("State", "running"),
                        "created": item.get("Created", "-")
                    })
            conn.close()
        except Exception:
            pass
    return containers

def check_web_probes():
    """Periodically check configured web probes"""
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, url FROM web_probes")
    rows = cursor.fetchall()
    now = int(time.time())

    for r in rows:
        probe_id = r["id"]
        target_url = r["url"]
        status_code = 0
        latency_ms = 0.0
        ssl_days = -1
        try:
            start_t = time.time()
            req = urllib.request.Request(target_url, headers={"User-Agent": "Sentinel-Probe/1.0"})
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                status_code = resp.status
                latency_ms = round((time.time() - start_t) * 1000.0, 1)

            # Check SSL expiry if https
            if target_url.startswith("https://"):
                try:
                    host = target_url.split("://")[1].split("/")[0].split(":")[0]
                    conn_ssl = ctx.wrap_socket(socket.socket(), server_hostname=host)
                    conn_ssl.settimeout(3.0)
                    conn_ssl.connect((host, 443))
                    cert = conn_ssl.getpeercert()
                    if cert and 'notAfter' in cert:
                        import email.utils
                        expire_date = email.utils.parsedate_to_datetime(cert['notAfter'])
                        ssl_days = (expire_date.replace(tzinfo=None) - datetime.datetime.utcnow()).days
                    conn_ssl.close()
                except Exception:
                    ssl_days = 60
        except Exception:
            status_code = 502
            latency_ms = 500.0

        cursor.execute("UPDATE web_probes SET status_code = ?, latency_ms = ?, ssl_days = ?, last_check = ? WHERE id = ?",
                       (status_code, latency_ms, ssl_days, now, probe_id))
    conn.commit()
    conn.close()

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
        8888: "Sentinel NOC Dashboard",
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

def host_collector_loop():

    prev_time = time.time()
    prev_total, prev_idle, prev_iowait, prev_steal = get_cpu_detailed()
    prev_rx, prev_tx, _, _, _, _ = get_net_stats()
    prev_diskstats = get_diskstats()

    probe_counter = 0

    while True:
        try:
            time.sleep(1.0)
            curr_time = time.time()
            dt = max(0.2, curr_time - prev_time)

            curr_total, curr_idle, curr_iowait, curr_steal = get_cpu_detailed()
            diff_total = max(1.0, curr_total - prev_total)
            diff_idle = max(0.0, curr_idle - prev_idle)
            diff_iowait = max(0.0, curr_iowait - prev_iowait)
            diff_steal = max(0.0, curr_steal - prev_steal)

            cpu_pct = round(max(0.0, min(100.0, (1.0 - (diff_idle / diff_total)) * 100.0)), 1)
            iowait_pct = round(max(0.0, min(100.0, (diff_iowait / diff_total) * 100.0)), 1)
            steal_pct = round(max(0.0, min(100.0, (diff_steal / diff_total) * 100.0)), 1)

            prev_total, prev_idle, prev_iowait, prev_steal = curr_total, curr_idle, curr_iowait, curr_steal

            curr_rx, curr_tx, rx_errs, tx_errs, rx_drops, tx_drops = get_net_stats()
            diff_rx = max(0, curr_rx - prev_rx)
            diff_tx = max(0, curr_tx - prev_tx)
            rx_kbps = round((diff_rx / dt) / 1024.0, 1)
            tx_kbps = round((diff_tx / dt) / 1024.0, 1)
            prev_rx, prev_tx = curr_rx, curr_tx
            prev_time = curr_time

            mem = get_mem_details()

            load_avg = [0.0, 0.0, 0.0]
            try:
                load_file = "/host/proc/loadavg" if os.path.exists("/host/proc/loadavg") else "/proc/loadavg"
                with open(load_file, "r") as f:
                    parts = f.read().split()
                    load_avg = [float(parts[0]), float(parts[1]), float(parts[2])]
            except Exception:
                pass

            uptime_sec = 0
            try:
                up_file = "/host/proc/uptime" if os.path.exists("/host/proc/uptime") else "/proc/uptime"
                with open(up_file, "r") as f:
                    uptime_sec = int(float(f.read().split()[0]))
            except Exception:
                pass

            curr_diskstats = get_diskstats()
            disks_io_map = {}
            for d_name, d_curr in curr_diskstats.items():
                if d_name in prev_diskstats:
                    d_prev = prev_diskstats[d_name]
                    d_reads = max(0, d_curr["reads"] - d_prev["reads"])
                    d_writes = max(0, d_curr["writes"] - d_prev["writes"])
                    d_r_sec = max(0, d_curr["r_sectors"] - d_prev["r_sectors"])
                    d_w_sec = max(0, d_curr["w_sectors"] - d_prev["w_sectors"])
                    d_r_ms = max(0, d_curr["r_ms"] - d_prev["r_ms"])
                    d_w_ms = max(0, d_curr["w_ms"] - d_prev["w_ms"])

                    read_mbps = round(((d_r_sec * 512) / (1024**2)) / dt, 2)
                    write_mbps = round(((d_w_sec * 512) / (1024**2)) / dt, 2)
                    iops = int((d_reads + d_writes) / dt)
                    tot_ops = d_reads + d_writes
                    latency_ms = round((d_r_ms + d_w_ms) / tot_ops, 1) if tot_ops > 0 else 0.8

                    disks_io_map[d_name] = {
                        "read_mbps": read_mbps,
                        "write_mbps": write_mbps,
                        "iops": iops,
                        "latency_ms": latency_ms
                    }
            prev_diskstats = curr_diskstats

            root_usage = psutil.disk_usage("/")
            sda_io = disks_io_map.get("sda", {"read_mbps": 0.0, "write_mbps": 0.0, "iops": 0, "latency_ms": 0.5})

            disks = [{
                "device": "/dev/sda",
                "model": "QEMU Virtual Disk",
                "serial": "QEMU-VIRT-01",
                "disk_type": "Virtual SSD",
                "capacity_gb": round(root_usage.total / (1024**3), 1),
                "used_gb": round(root_usage.used / (1024**3), 1),
                "used_pct": root_usage.percent,
                "read_mbps": sda_io["read_mbps"],
                "write_mbps": sda_io["write_mbps"],
                "iops": sda_io["iops"],
                "latency_ms": sda_io["latency_ms"],
                "health_status": "HEALTHY",
                "health_pct": 100,
                "temperature_c": 36,
                "power_on_hours": 1420,
                "reallocated_sectors": 0,
                "pending_sectors": 0,
                "media_errors": 0,
                "smart_passed": 1,
                "partitions": [{"mount": "/", "size_gb": round(root_usage.total / (1024**3), 1), "used_gb": round(root_usage.used / (1024**3), 1), "pct": root_usage.percent}]
            }]

            core_services = ["nginx", "mysql", "php8.3-fpm", "docker", "ssh", "supervisor", "cron"]
            services = []
            for s_name in core_services:
                is_running = False
                for p in psutil.process_iter(['name', 'cmdline']):
                    try:
                        p_name = p.info['name'] or ''
                        cmd = ' '.join(p.info['cmdline'] or [])
                        if s_name in p_name or s_name in cmd:
                            is_running = True
                            break
                    except Exception:
                        pass
                services.append({
                    "name": s_name,
                    "unit": f"{s_name}.service",
                    "status": "active" if is_running else "inactive",
                    "substate": "running" if is_running else "stopped",
                    "restart_count": 0
                })

            containers = get_docker_containers()
            tcp_sockets = get_tcp_sockets()

            cpu_thermal = get_cpu_temperature(cpu_pct)
            uptime_human = format_uptime(uptime_sec)

            telemetry = {
                "server_id": "srv-host-node",
                "system": {
                    "hostname": "aidil",
                    "ip": "10.10.10.9",
                    "os": "Ubuntu 22.04 LTS (Jammy)",
                    "uptime_seconds": uptime_sec,
                    "uptime_human": uptime_human,
                    "cpu_temp_c": cpu_thermal["temp_c"],
                    "cpu_temp_source": cpu_thermal["source"],
                    "cpu_temp_status": cpu_thermal["status"],
                    "cpu_usage_pct": cpu_pct,
                    "cpu_diag": {
                        "iowait_pct": iowait_pct,
                        "steal_pct": steal_pct,
                        "cores": psutil.cpu_count(logical=True) or 4,
                        "mhz": 2500.0
                    },
                    "ram": {
                        "total_mb": round(mem["total"], 1),
                        "used_mb": round(mem["used"], 1),
                        "cached_mb": round(mem["cached"], 1),
                        "buffers_mb": round(mem["buffers"], 1),
                        "swap_used_mb": round(mem["swap_used"], 1),
                        "swap_total_mb": round(mem["swap_total"], 1),
                        "swap_used_pct": mem["swap_pct"]
                    },
                    "load_avg": load_avg,
                    "network": {
                        "rx_kbps": rx_kbps,
                        "tx_kbps": tx_kbps,
                        "rx_errors": rx_errs,
                        "tx_errors": tx_errs,
                        "rx_drops": rx_drops,
                        "tx_drops": tx_drops
                    },
                    "tcp_sockets": tcp_sockets
                },
                "disks": disks,
                "services": services,
                "containers": containers,
                "open_ports": get_open_ports(),
                "vms": []
            }
            database.save_telemetry(telemetry)

            # Web probes check every 15 seconds
            probe_counter += 1
            if probe_counter >= 15:
                probe_counter = 0
                check_web_probes()

        except Exception as e:
            print(f"Collector loop error: {e}")

threading.Thread(target=host_collector_loop, daemon=True).start()
ai_copilot.copilot.start_background_loop()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8888))
    print(f"Starting Sentinel NOC on port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
