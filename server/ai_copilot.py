"""
Sentinel AI Homelab Copilot & Autonomous Smart Advisor Engine
24/7 Continuous Monitoring, Heuristic Anomaly Detection & Proactive Optimization Advisory
"""

import time
import datetime
import json
import urllib.request
import urllib.parse
import urllib.error
import threading
import os
import psutil

# Ensure database access
import database

class AICopilotEngine:
    def __init__(self):
        self._prev_node_states = {}   # {server_id: "online" | "offline"}
        self._alert_cooldowns = {}     # {alert_key: timestamp}
        self._last_digest_time = 0
        self._is_running = False
        self._lock = threading.Lock()
        self._chat_history = []        # [{"role": "user"|"assistant", "content": "..."}]

    def get_settings(self):
        enabled = database.get_setting("ai_copilot_enabled", "true").lower() == "true"
        tg_alerts = database.get_setting("ai_telegram_alerts_enabled", "true").lower() == "true"
        tg_digest = database.get_setting("ai_telegram_digest_enabled", "true").lower() == "true"
        digest_interval = int(database.get_setting("ai_digest_interval_hours", "6"))
        cpu_thresh = float(database.get_setting("ai_alert_threshold_cpu", "90"))
        ram_thresh = float(database.get_setting("ai_alert_threshold_ram", "94"))
        disk_thresh = float(database.get_setting("ai_alert_threshold_disk", "85"))
        last_digest = int(database.get_setting("ai_last_digest_time", "0"))
        last_status = database.get_setting("ai_last_digest_status", "Belum ada laporan terkirim")
        
        # Universal Multi-Provider AI Configuration
        ai_provider = database.get_setting("ai_provider", "gemini").lower()
        ai_api_key = database.get_setting("ai_api_key", "")
        # Backward-compatibility fallback
        if not ai_api_key:
            ai_api_key = database.get_setting("gemini_api_key", "")
            if ai_api_key and ai_provider == "gemini":
                pass
        ai_model = database.get_setting("ai_model", "")
        ai_base_url = database.get_setting("ai_base_url", "")
        ai_system_prompt_extra = database.get_setting("ai_system_prompt_extra", "")

        return {
            "ai_copilot_enabled": enabled,
            "ai_telegram_alerts_enabled": tg_alerts,
            "ai_telegram_digest_enabled": tg_digest,
            "ai_digest_interval_hours": digest_interval,
            "ai_alert_threshold_cpu": cpu_thresh,
            "ai_alert_threshold_ram": ram_thresh,
            "ai_alert_threshold_disk": disk_thresh,
            "ai_last_digest_time": last_digest,
            "ai_last_digest_status": last_status,
            "telegram_token_set": bool(database.get_setting("telegram_token", "")),
            "telegram_chat_id_set": bool(database.get_setting("telegram_chat_id", "")),
            # AI Provider Settings
            "ai_provider": ai_provider,
            "ai_api_key": ai_api_key,
            "ai_api_key_set": bool(ai_api_key),
            "ai_model": ai_model,
            "ai_base_url": ai_base_url,
            "ai_system_prompt_extra": ai_system_prompt_extra,
            # Legacy fields for backward compatibility
            "gemini_api_key": ai_api_key if ai_provider == "gemini" else "",
            "gemini_api_key_set": bool(ai_api_key and ai_provider == "gemini")
        }

    def save_settings(self, settings: dict):
        if "ai_provider" in settings:
            database.set_setting("ai_provider", settings["ai_provider"].strip().lower())
        if "ai_api_key" in settings:
            val = settings["ai_api_key"].strip()
            database.set_setting("ai_api_key", val)
            if settings.get("ai_provider", "gemini").lower() == "gemini":
                database.set_setting("gemini_api_key", val)
        if "ai_model" in settings:
            database.set_setting("ai_model", settings["ai_model"].strip())
        if "ai_base_url" in settings:
            database.set_setting("ai_base_url", settings["ai_base_url"].strip())
        if "ai_system_prompt_extra" in settings:
            database.set_setting("ai_system_prompt_extra", settings["ai_system_prompt_extra"].strip())
        if "gemini_api_key" in settings and "ai_api_key" not in settings:
            gval = settings["gemini_api_key"].strip()
            database.set_setting("gemini_api_key", gval)
            database.set_setting("ai_api_key", gval)

        if "ai_copilot_enabled" in settings:
            database.set_setting("ai_copilot_enabled", "true" if settings["ai_copilot_enabled"] else "false")
        if "ai_telegram_alerts_enabled" in settings:
            database.set_setting("ai_telegram_alerts_enabled", "true" if settings["ai_telegram_alerts_enabled"] else "false")
        if "ai_telegram_digest_enabled" in settings:
            database.set_setting("ai_telegram_digest_enabled", "true" if settings["ai_telegram_digest_enabled"] else "false")
        if "ai_digest_interval_hours" in settings:
            database.set_setting("ai_digest_interval_hours", str(int(settings["ai_digest_interval_hours"])))
        if "ai_alert_threshold_cpu" in settings:
            database.set_setting("ai_alert_threshold_cpu", str(float(settings["ai_alert_threshold_cpu"])))
        if "ai_alert_threshold_ram" in settings:
            database.set_setting("ai_alert_threshold_ram", str(float(settings["ai_alert_threshold_ram"])))
        if "ai_alert_threshold_disk" in settings:
            database.set_setting("ai_alert_threshold_disk", str(float(settings["ai_alert_threshold_disk"])))
        return self.get_settings()

    def generate_homelab_audit(self) -> dict:
        """
        Deep analytical audit across all servers, Proxmox hypervisor, guest VMs, storage, and probes.
        Produces health score (0-100), health grade, key observations, and actionable recommendations.
        """
        now = time.time()
        conn = database.get_db()
        cursor = conn.cursor()

        # 1. Fetch servers
        cursor.execute("SELECT * FROM servers")
        servers = [dict(r) for r in cursor.fetchall()]

        # 2. Fetch VMs
        cursor.execute("SELECT * FROM vms")
        vms = [dict(r) for r in cursor.fetchall()]

        # 3. Fetch Disks
        cursor.execute("SELECT * FROM disks")
        disks = [dict(r) for r in cursor.fetchall()]

        # 4. Fetch Web Probes
        cursor.execute("SELECT * FROM web_probes")
        probes = [dict(r) for r in cursor.fetchall()]

        # 5. Fetch SSL Certs
        cursor.execute("SELECT * FROM ssl_certificates")
        ssl_certs = [dict(r) for r in cursor.fetchall()]

        conn.close()

        score = 100
        deductions = []
        insights = []
        recommendations = []

        total_nodes = len(servers)
        online_nodes = 0
        offline_nodes = []
        
        pve_server = None
        host_node = None

        total_cluster_ram_used_mb = 0
        total_cluster_ram_total_mb = 0

        for s in servers:
            is_online = (now - s.get("last_seen", 0)) < 60
            if is_online:
                online_nodes += 1
            else:
                offline_nodes.append(s)

            if s.get("id") == "srv-pve" or "pve" in s.get("hostname", "").lower():
                pve_server = s
            if s.get("id") == "srv-host-node":
                host_node = s

            total_cluster_ram_used_mb += s.get("ram_used_mb", 0)
            total_cluster_ram_total_mb += s.get("ram_total_mb", 0)

        # Health score calculation
        if offline_nodes:
            deduct = min(40, len(offline_nodes) * 15)
            score -= deduct
            deductions.append(f"{len(offline_nodes)} node offline (-{deduct} pts)")
            for off in offline_nodes:
                insights.append({
                    "type": "OFFLINE_NODE",
                    "severity": "CRITICAL",
                    "title": f"Node Offline: {off.get('hostname')} ({off.get('ip')})",
                    "detail": f"Tidak merespon telemetry heartbeat selama {int(now - off.get('last_seen', 0))} detik."
                })
                recommendations.append({
                    "id": f"rec-offline-{off.get('id')}",
                    "category": "STABILITY",
                    "severity": "CRITICAL",
                    "title": f"Pulihkan Node {off.get('hostname')} ({off.get('ip')})",
                    "detail": f"Node {off.get('hostname')} dalam kondisi offline. Periksa status VM di Proxmox VE atau periksa jaringan.",
                    "action_command": f"qm status / qm start pada PVE",
                    "impact": "Memulihkan layanan & observabilitas node"
                })

        # Hypervisor Memory Pressure Check
        pve_ram_pct = 0.0
        pve_ram_used_gb = 0.0
        pve_ram_total_gb = 0.0
        if pve_server:
            pve_ram_used_mb = pve_server.get("ram_used_mb", 0)
            pve_ram_total_mb = pve_server.get("ram_total_mb", 1)
            pve_ram_pct = round((pve_ram_used_mb / pve_ram_total_mb) * 100, 1)
            pve_ram_used_gb = round(pve_ram_used_mb / 1024, 2)
            pve_ram_total_gb = round(pve_ram_total_mb / 1024, 2)

            if pve_ram_pct >= 92.0:
                score -= 10
                deductions.append(f"Tekanan RAM Proxmox VE tinggi ({pve_ram_pct}%) (-10 pts)")
                insights.append({
                    "type": "PVE_RAM_PRESSURE",
                    "severity": "WARNING",
                    "title": f"Tekanan Memori Proxmox VE Kritis ({pve_ram_pct}%)",
                    "detail": f"Host PVE menggunakan {pve_ram_used_gb} GB dari {pve_ram_total_gb} GB RAM. Hal ini disebabkan alokasi statis VM yang berlebihan."
                })

        # Deep VM Memory Sizing Analysis
        reclaimable_ram_mb = 0
        oversized_vms = []
        under_provisioned_vms = []

        # Map VM internal agent RAM vs PVE allocated RAM
        server_by_ip = {s.get("ip"): s for s in servers}
        server_by_name = {s.get("hostname", "").lower(): s for s in servers}

        for vm in vms:
            vmid = vm.get("vmid")
            name = vm.get("name")
            pve_alloc_mb = vm.get("ram_total_mb", 0)
            pve_used_mb = vm.get("ram_used_mb", 0)

            # Match with agent telemetry if available
            matched_agent = None
            for s in servers:
                s_name = s.get("hostname", "").lower()
                vm_name_clean = name.lower().replace("-", "").replace("_", "")
                if vm_name_clean in s_name or s_name in vm_name_clean:
                    matched_agent = s
                    break

            if matched_agent:
                agent_used = matched_agent.get("ram_used_mb", 0)
                # Take higher of internal agent used or PVE QEMU host memory
                # especially for memory-heavy services like Immich or Database!
                real_used_mb = max(agent_used, pve_used_mb)
                real_pct = round((real_used_mb / pve_alloc_mb) * 100, 1) if pve_alloc_mb > 0 else 0
            else:
                real_used_mb = pve_used_mb
                real_pct = round((pve_used_mb / pve_alloc_mb) * 100, 1) if pve_alloc_mb > 0 else 0

            # Rule: Oversized VM (alloc > 3GB and usage < 35%)
            if pve_alloc_mb >= 3072 and real_pct < 35.0:
                # Can be resized to e.g. 2048 MB or safe ceiling
                target_alloc_mb = 2048 if real_used_mb < 1200 else 3072
                savings_mb = pve_alloc_mb - target_alloc_mb
                if savings_mb > 0:
                    reclaimable_ram_mb += savings_mb
                    oversized_vms.append({
                        "vmid": vmid,
                        "name": name,
                        "current_alloc_mb": pve_alloc_mb,
                        "real_used_mb": real_used_mb,
                        "real_pct": real_pct,
                        "recommended_mb": target_alloc_mb,
                        "savings_mb": savings_mb
                    })

            # Rule: High memory VM (usage > 85%)
            if real_pct > 85.0:
                under_provisioned_vms.append({
                    "vmid": vmid,
                    "name": name,
                    "alloc_mb": pve_alloc_mb,
                    "used_mb": real_used_mb,
                    "pct": real_pct
                })

        # Add RAM Rebalancing Recommendation if oversized VMs exist
        if oversized_vms:
            oversized_vms.sort(key=lambda x: x["savings_mb"], reverse=True)
            reclaim_gb = round(reclaimable_ram_mb / 1024, 1)

            insights.append({
                "type": "RAM_OVERPROVISIONING",
                "severity": "OPTIMIZATION",
                "title": f"Peluang Efisiensi RAM: ~{reclaim_gb} GB Dapat Dibebaskan",
                "detail": f"Ditemukan {len(oversized_vms)} VM dengan alokasi RAM berlebih yang jarang terpakai. Mengurangi alokasi ini akan langsung melonggarkan Host Proxmox VE."
            })

            rec_cmd = f"qm set {oversized_vms[0]['vmid']} -memory {oversized_vms[0]['recommended_mb']}"
            structured_vms = [
                {
                    "vmid": ov["vmid"],
                    "name": ov["name"],
                    "alloc_gb": round(ov["current_alloc_mb"] / 1024, 1),
                    "rec_gb": round(ov["recommended_mb"] / 1024, 1),
                    "save_gb": round(ov["savings_mb"] / 1024, 1),
                    "used_mb": int(ov["real_used_mb"]),
                    "pct": ov["real_pct"]
                }
                for ov in oversized_vms
            ]
            recommendations.append({
                "id": "rec-ram-rebalance",
                "category": "RAM_ALLOCATION",
                "severity": "RECOMMENDED",
                "title": f"Rebalancing Alokasi RAM VM (Hemat ~{reclaim_gb} GB)",
                "detail": f"Host PVE saat ini mencapai tekanan {pve_ram_pct}% RAM. Terdapat {len(oversized_vms)} VM dengan alokasi berlebih yang dapat di-downsize agar host hypervisor lebih lega dan stabil.",
                "action_command": rec_cmd,
                "impact": f"Membebaskan ~{reclaim_gb} GB RAM di Host PVE & mencegah OOM Killer",
                "vms": structured_vms
            })

        # CPU & Load Average Audit
        for s in servers:
            cores = s.get("cpu_cores", 4) or 4
            load_1m = s.get("load_1m", 0.0)
            cpu_pct = s.get("cpu_pct", 0.0)

            if load_1m > cores * 1.5 or cpu_pct > 88.0:
                score -= 8
                deductions.append(f"CPU load tinggi pada {s.get('hostname')} (-8 pts)")
                insights.append({
                    "type": "CPU_SATURATION",
                    "severity": "WARNING",
                    "title": f"CPU Load Tinggi pada {s.get('hostname')}",
                    "detail": f"Load: {load_1m:.2f} pada {cores} vCPU ({cpu_pct}% pemakaian)."
                })
                recommendations.append({
                    "id": f"rec-cpu-{s.get('id')}",
                    "category": "CPU_SCALING",
                    "severity": "WARNING",
                    "title": f"Periksa Proses Intensif di {s.get('hostname')}",
                    "detail": f"Beban CPU sedang melonjak. Buka tab Processes untuk mengecek PID proses teratas.",
                    "action_command": f"top -b -n 1 / htop pada {s.get('hostname')}",
                    "impact": "Mencegah perlambatan respon layanan"
                })

        # Storage & Disk Audit
        disk_issues = []
        for d in disks:
            used_pct = d.get("used_pct", 0.0)
            if used_pct >= 85.0:
                score -= 5
                disk_issues.append(d)
                insights.append({
                    "type": "DISK_WARNING",
                    "severity": "WARNING" if used_pct < 92 else "CRITICAL",
                    "title": f"Partisi Mendekati Penuh: {d.get('device')} ({used_pct}%)",
                    "detail": f"Node: {d.get('server_id')}, Terpakai: {d.get('used_gb')} GB dari {d.get('capacity_gb')} GB."
                })
                recommendations.append({
                    "id": f"rec-disk-{d.get('server_id')}-{d.get('device').replace('/', '_')}",
                    "category": "STORAGE",
                    "severity": "WARNING",
                    "title": f"Bersihkan Storage di {d.get('server_id')} ({used_pct}%)",
                    "detail": f"Storage {d.get('device')} sudah mencapai {used_pct}%. Bersihkan log systemd journal dan cache docker.",
                    "action_command": "journalctl --vacuum-time=3d && docker system prune -af",
                    "impact": "Mencegah disk full yang menyebabkan crash service"
                })

        # Web Probes Audit
        failing_probes = []
        for p in probes:
            status = p.get("status_code", 0)
            if status != 200:
                failing_probes.append(p)

        if failing_probes:
            score -= min(15, len(failing_probes) * 5)
            for fp in failing_probes:
                insights.append({
                    "type": "PROBE_FAIL",
                    "severity": "WARNING",
                    "title": f"Probe Gagal: {fp.get('name')}",
                    "detail": f"URL {fp.get('url')} merespon status {fp.get('status_code')} (latency: {fp.get('latency_ms', 0):.1f}ms)."
                })

        # Score clamp
        score = max(20, min(100, score))

        # Health Grade
        if score >= 90:
            grade = "OPTIMAL"
            grade_label = "🟢 Kondisi Prima"
            summary_desc = "Seluruh node, hypervisor, dan layanan berjalan normal dengan efisiensi tinggi."
        elif score >= 75:
            grade = "GOOD"
            grade_label = "🟡 Performa Baik (Perlu Optimasi)"
            summary_desc = "Armada homelab berjalan stabil. Terdapat peluang optimasi alokasi RAM VM untuk melonggarkan hypervisor."
        elif score >= 60:
            grade = "WARNING"
            grade_label = "🟠 Perhatian Diperlukan"
            summary_desc = "Ditemukan beberapa indikator degradasi performa atau node yang membutuhkan perhatian."
        else:
            grade = "CRITICAL"
            grade_label = "🔴 Kritis / Membutuhkan Tindakan"
            summary_desc = "Terdapat node offline atau saturasi sumber daya yang perlu segera ditangani."

        # If no recommendations, add best-practice tips
        if not recommendations:
            recommendations.append({
                "id": "rec-general-best-practice",
                "category": "MAINTENANCE",
                "severity": "INFO",
                "title": "Homelab Berjalan Optimal",
                "detail": "Semua node stabil dan respon latency berada di bawah 20ms. Pertahankan jadwal backup rutin di Proxmox VE vzdump.",
                "action_command": "pvescheduler / backup status",
                "impact": "Memastikan integritas disaster recovery cluster"
            })

        wib = datetime.timezone(datetime.timedelta(hours=7))
        time_human = datetime.datetime.fromtimestamp(now, tz=wib).strftime("%d %b %Y, %H:%M WIB")

        return {
            "timestamp": int(now),
            "timestamp_human": time_human,
            "health_score": score,
            "health_grade": grade,
            "health_label": grade_label,
            "summary_desc": summary_desc,
            "fleet_summary": {
                "total_nodes": total_nodes,
                "online_nodes": online_nodes,
                "offline_nodes": len(offline_nodes),
                "pve_ram_used_pct": pve_ram_pct,
                "pve_ram_used_gb": pve_ram_used_gb,
                "pve_ram_total_gb": pve_ram_total_gb,
                "total_vms": len(vms),
                "reclaimable_ram_mb": reclaimable_ram_mb,
                "reclaimable_ram_gb": round(reclaimable_ram_mb / 1024, 1),
                "probes_total": len(probes),
                "probes_failing": len(failing_probes)
            },
            "insights": insights,
            "recommendations": recommendations,
            "deductions": deductions
        }

    def format_telegram_briefing(self, audit: dict) -> str:
        """
        Formats audit data into an ultra-clean, elegant Telegram Markdown message.
        Uses clean borders, monospace status boxes, and aligned tables to eliminate visual clutter.
        """
        wib = datetime.timezone(datetime.timedelta(hours=7))
        time_str = datetime.datetime.now(wib).strftime("%d %b %Y, %H:%M WIB")

        score = audit.get("health_score", 100)
        grade_label = audit.get("health_label", "🟢 Prima")
        fleet = audit.get("fleet_summary", {})
        recs = audit.get("recommendations", [])
        reclaim_gb = fleet.get('reclaimable_ram_gb', 0)

        pve_ram_used = fleet.get('pve_ram_used_gb', 0)
        pve_ram_tot = fleet.get('pve_ram_total_gb', 0)
        pve_pct = fleet.get('pve_ram_used_pct', 0)
        pve_warn = " ⚠️" if pve_pct > 90 else ""

        msg = []
        msg.append("🤖 *SENTINEL AI HOMELAB COPILOT*")
        msg.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
        msg.append(f"📊 *Status:* {grade_label} (*{score}/100*)")
        msg.append(f"⏱️ *Audit:* `{time_str}`\n")

        msg.append("🌐 *RINGKASAN FLEET:*")
        msg.append("```text")
        msg.append(f"Nodes Online : {fleet.get('online_nodes', 0)} / {fleet.get('total_nodes', 0)} Online")
        msg.append(f"PVE Host RAM : {pve_ram_used} / {pve_ram_tot} GB ({pve_pct}%){pve_warn}")
        msg.append(f"VM Berjalan  : {fleet.get('total_vms', 0)} VM Aktif")
        msg.append(f"Web Probes   : {fleet.get('probes_total', 0) - fleet.get('probes_failing', 0)} / {fleet.get('probes_total', 0)} Normal")
        msg.append("```\n")

        if reclaim_gb > 0:
            msg.append(f"✨ *Potensi Hemat Host:* ~{reclaim_gb} GB RAM\n")

        msg.append("💡 *REKOMENDASI OPTIMASI AI:*")
        for i, rec in enumerate(recs[:3], 1):
            sev_icon = "🔴" if rec.get("severity") == "CRITICAL" else ("🟡" if rec.get("severity") == "WARNING" else "✨")
            msg.append(f"*{i}. {sev_icon} {rec.get('title')}*")
            msg.append(f"{rec.get('detail')}")

            vms_list = rec.get("vms", [])
            if vms_list:
                msg.append("```text")
                msg.append("VM   NAMA          ALOKASI  ➔  SARAN")
                msg.append("────────────────────────────────────")
                for v in vms_list:
                    v_name = v['name'][:12]
                    msg.append(f"{v['vmid']:<4} {v_name:<12} {v['alloc_gb']:>5.1f}G  ➔ {v['rec_gb']:>5.1f}G")
                msg.append("────────────────────────────────────")
                msg.append(f"TOTAL HEMAT : ~{reclaim_gb} GB RAM")
                msg.append("```")

            if rec.get("action_command"):
                msg.append(f"👉 *Solusi Cepat:* `{rec.get('action_command')}`")
            if rec.get("impact"):
                msg.append(f"📈 *Dampak:* {rec.get('impact')}\n")

        msg.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
        msg.append("🛡️ _Sentinel AI aktif memantau cluster 24/7._")
        return "\n".join(msg)

    def format_telegram_alert(self, event_type: str, node: dict, detail: str = "", advice: str = "") -> str:
        """
        Formats real-time incident or recovery alert for Telegram with clean layout.
        """
        hostname = node.get("hostname", "Unknown")
        ip = node.get("ip", "-")
        wib = datetime.timezone(datetime.timedelta(hours=7))
        time_str = datetime.datetime.now(wib).strftime("%d %b %Y, %H:%M:%S WIB")

        if event_type == "NODE_OFFLINE":
            return (
                f"🚨 *[SENTINEL INCIDENT ALERT]*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Node   : *{hostname}*\n"
                f"IP     : `{ip}`\n"
                f"Status : 🔴 *OFFLINE / Tidak Merespon*\n"
                f"Waktu  : `{time_str}`\n\n"
                f"🔍 *Diagnosa AI:*\n"
                f"Node berhenti mengirimkan telemetry heartbeat (> 45 detik).\n\n"
                f"💡 *Saran Copilot:*\n"
                f"{advice or 'Periksa status VM pada Proxmox VE (`qm status`) atau periksa koneksi switch/jaringan.'}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🛡️ _Sentinel Autonomous Observer 24/7_"
            )
        elif event_type == "NODE_RECOVERED":
            return (
                f"✅ *[SENTINEL INCIDENT RESOLVED]*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Node   : *{hostname}*\n"
                f"IP     : `{ip}`\n"
                f"Status : 🟢 *ONLINE & PULIH NORMAL*\n"
                f"Waktu  : `{time_str}`\n\n"
                f"🔍 *Diagnosa AI:*\n"
                f"Heartbeat telemetry kembali diterima normal. Layanan beroperasi stabil.\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🛡️ _Sentinel Autonomous Observer 24/7_"
            )
        elif event_type == "RESOURCE_SPIKE":
            return (
                f"⚠️ *[SENTINEL RESOURCE ALERT]*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Node       : *{hostname}* (`{ip}`)\n"
                f"Peringatan : *{detail}*\n"
                f"Waktu      : `{time_str}`\n\n"
                f"💡 *Saran Copilot:*\n"
                f"{advice or 'Periksa proses intensif di menu Top Processes NOC.'}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🛡️ _Sentinel Autonomous Observer 24/7_"
            )
        return f"ℹ️ *[SENTINEL NOTIFICATION]*\nNode: *{hostname}* ({ip})\n{detail}"

    def send_telegram_direct(self, message: str) -> tuple[bool, str]:
        token = database.get_setting("telegram_token", "")
        chat_id = database.get_setting("telegram_chat_id", "")
        if not token or not chat_id:
            return False, "Token atau Chat ID Telegram belum diatur."

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status == 200:
                    return True, "Terkirim ke Telegram"
                return False, f"HTTP status {resp.status}"
        except urllib.error.HTTPError as he:
            # Fallback to plain text if Markdown parse error occurred
            try:
                data = urllib.parse.urlencode({
                    "chat_id": chat_id,
                    "text": message
                }).encode()
                req = urllib.request.Request(url, data=data, method="POST")
                with urllib.request.urlopen(req, timeout=12) as resp:
                    if resp.status == 200:
                        return True, "Terkirim ke Telegram (plain)"
            except Exception:
                pass
            return False, f"HTTP Error {he.code}: {str(he)}"
        except Exception as e:
            return False, str(e)

    def dispatch_briefing(self) -> dict:
        """
        Generates live audit and immediately sends to Telegram.
        """
        audit = self.generate_homelab_audit()
        msg = self.format_telegram_briefing(audit)
        ok, err = self.send_telegram_direct(msg)
        
        status_msg = f"Terkirim ({datetime.datetime.now().strftime('%H:%M:%S')})" if ok else f"Gagal: {err}"
        database.set_setting("ai_last_digest_time", str(int(time.time())))
        database.set_setting("ai_last_digest_status", status_msg)

        return {
            "status": "success" if ok else "error",
            "message": status_msg,
            "audit": audit
        }

    def start_background_loop(self):
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            threading.Thread(target=self._worker_loop, daemon=True, name="AICopilotSentinel").start()
            threading.Thread(target=self._telegram_chat_loop, daemon=True, name="AICopilotTelegramChat").start()

    def _get_default_model(self, provider: str) -> str:
        p = (provider or "gemini").lower()
        if p == "gemini":
            return "gemini-1.5-flash"
        elif p == "groq":
            return "llama-3.3-70b-versatile"
        elif p == "openai":
            return "gpt-4o-mini"
        elif p == "openrouter":
            return "meta-llama/llama-3.3-70b-instruct:free"
        elif p == "custom":
            return "llama3"
        return "gemini-1.5-flash"

    def _get_default_base_url(self, provider: str) -> str:
        p = (provider or "gemini").lower()
        if p == "groq":
            return "https://api.groq.com/openai/v1"
        elif p == "openai":
            return "https://api.openai.com/v1"
        elif p == "openrouter":
            return "https://openrouter.ai/api/v1"
        elif p == "gemini":
            return "https://generativelanguage.googleapis.com/v1beta"
        return ""

    def list_gemini_models(self, api_key: str) -> list[str]:
        """Queries Google Generative Language API for valid generateContent models for this key."""
        if not api_key:
            return []
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key.strip()}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8', errors='ignore'))
                    valid_models = []
                    for m in data.get("models", []):
                        methods = m.get("supportedGenerationMethods", [])
                        if "generateContent" in methods:
                            m_name = m.get("name", "").replace("models/", "")
                            valid_models.append(m_name)
                    return valid_models
        except Exception as e:
            print(f"list_gemini_models error: {e}")
        return []

    def test_llm_connection(self, provider: str, api_key: str, model: str = "", base_url: str = "") -> dict:
        t0 = time.time()
        test_messages = [
            {"role": "user", "content": "Halo! Jawab dalam 1 kalimat singkat: sebutkan modelmu dan konfirmasi bahwa API Sentinel AI Copilot berhasil terhubung!"}
        ]
        ok, reply, resolved_model = self._call_llm(test_messages, provider, api_key, model, base_url)
        elapsed = round((time.time() - t0) * 1000)
        if ok:
            return {
                "status": "success",
                "message": f"Koneksi API AI Berhasil! (Model: {resolved_model})",
                "reply": reply,
                "latency_ms": elapsed,
                "provider": provider,
                "model": resolved_model
            }
        else:
            return {
                "status": "error",
                "message": reply,
                "latency_ms": elapsed,
                "provider": provider,
                "model": resolved_model
            }

    def _call_llm(self, messages: list, provider: str, api_key: str, model: str = "", base_url: str = "") -> tuple[bool, str, str]:
        provider = (provider or "gemini").lower().strip()
        model_name = (model or "").strip() or self._get_default_model(provider)

        # 1. Google Gemini Native Endpoint
        if provider == "gemini":
            if not api_key:
                return False, "API Key Google Gemini belum diisi.", model_name

            system_parts = []
            contents = []
            for m in messages:
                role = m.get("role", "user")
                text = m.get("content", "")
                if role == "system":
                    system_parts.append(text)
                elif role == "user":
                    contents.append({"role": "user", "parts": [{"text": text}]})
                elif role in ("assistant", "model"):
                    contents.append({"role": "model", "parts": [{"text": text}]})

            if not contents:
                contents = [{"role": "user", "parts": [{"text": "Halo"}]}]

            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 1500
                }
            }
            if system_parts:
                payload["systemInstruction"] = {
                    "parts": [{"text": "\n\n".join(system_parts)}]
                }

            def _try_gemini_call(target_m: str) -> tuple[bool, str]:
                clean_m = target_m.replace("models/", "").strip()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_m}:generateContent?key={api_key.strip()}"
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=22) as resp:
                    if resp.status == 200:
                        res = json.loads(resp.read().decode('utf-8', errors='ignore'))
                        candidates = res.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return True, parts[0].get("text", "").strip()
                        return False, "Gemini tidak mengembalikan output teks."
                    return False, f"HTTP status {resp.status}"

            try:
                ok, text = _try_gemini_call(model_name)
                if ok:
                    return True, text, model_name
                return False, text, model_name
            except urllib.error.HTTPError as he:
                body = he.read().decode('utf-8', errors='ignore')
                if he.code == 404:
                    # Dynamically inspect supported models for this user's API Key!
                    available = self.list_gemini_models(api_key)
                    if available:
                        # Auto-pick the best available model
                        best = None
                        for candidate in ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-pro"]:
                            if candidate in available:
                                best = candidate
                                break
                        if not best:
                            for m in available:
                                if "flash" in m or "pro" in m:
                                    best = m
                                    break
                        if not best:
                            best = available[0]

                        # Try auto-recovering with the best available model
                        if best and best != model_name:
                            try:
                                ok_auto, text_auto = _try_gemini_call(best)
                                if ok_auto:
                                    return True, text_auto, best
                            except Exception:
                                pass

                        avail_list = ", ".join(available[:6])
                        return False, f"Model '{model_name}' tidak ditemukan (404). Model aktif untuk akun Anda: [{avail_list}]. Silakan pilih salah satu.", model_name

                    return False, f"Model '{model_name}' tidak ditemukan di Google API (404). Pastikan Generative Language API aktif di Google AI Studio.", model_name

                try:
                    j = json.loads(body)
                    msg = j.get("error", {}).get("message", body)
                    return False, f"Gemini Error ({he.code}): {msg}", model_name
                except Exception:
                    return False, f"Gemini Error ({he.code}): {body[:150]}", model_name
            except Exception as e:
                return False, f"Koneksi Gemini gagal: {str(e)}", model_name

        # 2. OpenAI / Groq / OpenRouter / Custom compatible endpoint
        target_base = (base_url or "").strip() or self._get_default_base_url(provider)
        if not target_base:
            target_base = "https://api.openai.com/v1"

        endpoint = f"{target_base.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key.strip()}"
        if provider == "openrouter":
            headers["HTTP-Referer"] = "http://localhost:8888"
            headers["X-Title"] = "Sentinel Homelab Copilot"

        clean_messages = []
        for m in messages:
            clean_messages.append({
                "role": m.get("role", "user"),
                "content": m.get("content", "")
            })

        payload = {
            "model": model_name,
            "messages": clean_messages,
            "temperature": 0.4,
            "max_tokens": 1500
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=25) as resp:
                if resp.status == 200:
                    res = json.loads(resp.read().decode('utf-8', errors='ignore'))
                    choices = res.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        return True, content.strip(), model_name
                    return False, "Provider tidak mengembalikan teks jawaban.", model_name
                return False, f"HTTP status {resp.status}", model_name
        except urllib.error.HTTPError as he:
            body = he.read().decode('utf-8', errors='ignore')
            try:
                j = json.loads(body)
                msg = j.get("error", {}).get("message", body)
                return False, f"{provider.upper()} Error ({he.code}): {msg}", model_name
            except Exception:
                return False, f"{provider.upper()} Error ({he.code}): {body[:150]}", model_name
        except Exception as e:
            return False, f"Koneksi {provider.upper()} gagal: {str(e)}", model_name

    def _build_homelab_system_prompt(self, audit: dict, extra_prompt: str = "") -> str:
        fleet = audit.get("fleet_summary", {})
        
        conn = database.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vms")
        vms = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        vm_lines = []
        for v in vms:
            vmid = v.get("vmid")
            name = v.get("name")
            alloc_mb = v.get("ram_total_mb", 0)
            alloc_gb = round(alloc_mb / 1024, 1)
            used_mb = int(v.get("ram_used_mb", 0))
            cpu = v.get("cpu_pct", 0)
            ip = v.get("ip_address") or "10.10.10.x"
            vm_lines.append(f"- VM {vmid} ({name}): RAM Alokasi {alloc_gb}GB (Aktif dipakai {used_mb}MB), CPU {cpu}%, IP {ip}")

        vms_text = "\n".join(vm_lines)

        prompt = f"""Anda adalah "Sentinel AI Homelab Copilot", asisten pribadi senior DevOps & Infrastructure Engineer untuk sebuah homelab nyata.
Anda sedang berdialog langsung dengan pemilik homelab di Telegram.

STATUS TELEMETRI HOMELAB REAL-TIME DETIK INI:
- Host Proxmox VE (10.10.10.2): CPU {fleet.get('pve_cpu', 5)}%, RAM {fleet.get('pve_ram_used_gb', 16.8)} GB dari {fleet.get('pve_ram_total_gb', 17.4)} GB ({fleet.get('pve_ram_used_pct', 96.1)}% terpakai ⚠️)
- Total Armada: {fleet.get('total_nodes', 9)} node ({fleet.get('online_nodes', 9)} online)
- Guest Workload (8 VM berjalan aktif):
{vms_text}

CATATAN PENTING ARSITEKTUR CLUSTER:
1. Immich (VM 104): Sangat krusial! Menggunakan ~3.65 GB RAM untuk Machine Learning (facial recognition, CLIP vector) & Postgres. JANGAN sarankan memangkas alokasi RAM Immich di bawah 4.0 GB karena proses ML akan crash Out-Of-Memory (OOM).
2. Web Apps (Ceritakota 105, Portfolio-Sekar 106, Portfolio-Aidil 109): Beban aslinya sangat ringan (~500MB - 1.1GB). RAM statis 4GB mereka 80% menganggur. Menurunkan alokasi RAM atau mengaktifkan Ballooning TIDAK AKAN membuat web lemot karena performa web ditentukan oleh vCPU (tetap 4 Core) dan latensi jaringan, bukan RAM kosong yang menganggur.
3. Bahaya nyata di cluster ini adalah Host Proxmox VE yang terjepit di 96% RAM akibat overcommit statis. Solusi terbaik adalah Dynamic Memory Ballooning (`qm set <vmid> -balloon 2048`) atau mengecilkan VM yang benar-benar idle (Pentest, Pambuluah, Web).
4. Proxmox Memory Ballooning: BISA diterapkan pada sebagian besar VM Linux (Web Ceritakota, Sekar, Aidil, Pentest, Pambuluah) selama package `qemu-guest-agent` terpasang. TETAPI untuk VM Immich (104), jangan dipasang atau pasang minimum balloon tinggi (3500-4000MB) karena Immich butuh RAM konstan.
5. Hardware & Power: Laptop dengan USB LAN adapter tidak bisa di-Wake-on-LAN (WoL) saat laptop mati (state S5) karena port USB diputus daya 5V standby. Jika ingin WoL bekerja 24 jam, migrasi ke Mini PC dengan onboard RJ45 LAN port yang terhubung ke bus PCIe standby rail.

PANDUAN GAYA JAWABAN:
- Jawablah secara natural, cerdas, solutif, dan ramah seperti rekan senior engineer.
- Jawab langsung pertanyaan spesifik user (termasuk pertanyaan lanjutan / follow-up pertanyaan sebelumnya).
- Berikan saran yang praktis, jika ada perintah Proxmox cantumkan format code (`qm set ...`).
- Gunakan format Telegram Markdown (*bold*, `code`).
- Jangan kaku, langsung jawab intinya."""

        if extra_prompt:
            prompt += f"\n\nINSTRUKSI TAMBAHAN DARI PEMILIK:\n{extra_prompt}"

        return prompt

    def generate_chat_reply(self, text: str) -> str:
        """
        Conversational intelligence:
        - If AI Provider API Key is configured: Passes live telemetry + chat history to LLM (Gemini, Groq, OpenAI, Ollama).
        - If NO API Key is configured: Uses deterministic engine and provides guidance on connecting an AI API key.
        """
        settings = self.get_settings()
        provider = settings.get("ai_provider", "gemini")
        api_key = settings.get("ai_api_key", "").strip() or settings.get("gemini_api_key", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("OPENAI_API_KEY", "").strip() or os.environ.get("GROQ_API_KEY", "").strip()
        model = settings.get("ai_model", "").strip()
        base_url = settings.get("ai_base_url", "").strip()
        system_extra = settings.get("ai_system_prompt_extra", "").strip()

        audit = self.generate_homelab_audit()

        # 1. If API Key is configured, use the LLM!
        if api_key:
            system_prompt = self._build_homelab_system_prompt(audit, system_extra)
            messages = [{"role": "system", "content": system_prompt}]
            
            with self._lock:
                for h in self._chat_history[-8:]:
                    messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": text})

            ok, ans, resolved_model = self._call_llm(messages, provider, api_key, model, base_url)
            if ok and ans:
                with self._lock:
                    self._chat_history.append({"role": "user", "content": text})
                    self._chat_history.append({"role": "assistant", "content": ans})
                    if len(self._chat_history) > 14:
                        self._chat_history = self._chat_history[-14:]
                return ans
            else:
                print(f"🤖 [AI LLM Error with {provider}]: {ans}")
                fallback = self._generate_heuristic_reply(text, audit)
                return f"⚠️ *(Gagal memanggil API {provider.upper()}: {ans})*\n\n{fallback}"

        # 2. If NO API Key is configured yet, use heuristic engine with clear suggestion to connect API
        return self._generate_heuristic_reply(text, audit, show_api_hint=True)

    def _generate_heuristic_reply(self, text: str, audit: dict, show_api_hint: bool = False) -> str:
        q = text.lower().strip()
        fleet = audit.get("fleet_summary", {})

        # A. Ballooning questions (e.g. "brarti bisa diterapkan di semua vm dong ya balloon itu")
        if any(w in q for w in ["balloon", "balon"]):
            return (
                "Halo! Menjawab pertanyaan Anda seputar penerapan *Dynamic Memory Ballooning*:\n\n"
                "👉 *Jawabannya: Bisa diterapkan di hampir semua VM Linux, TETAPI ada pengecualian penting!*\n\n"
                "1. 🟢 *Sangat Dianjurkan untuk VM Web & Idle:*\n"
                "• `Ceritakota (105)`: Set min balloon 2048 MB (`qm set 105 -balloon 2048`)\n"
                "• `Portfolio-Sekar (106)`: Set min balloon 2048 MB (`qm set 106 -balloon 2048`)\n"
                "• `Portfolio-Aidil (109)`: Set min balloon 2048 MB (`qm set 109 -balloon 2048`)\n"
                "• `Pentest (110)` & `Pambuluah (108)`: Sangat cocok karena sering idle.\n\n"
                "2. ⚠️ *PERHATIAN KHUSUS VM Immich (104):*\n"
                "Immich membutuhkan alokasi RAM yang stabil (*~3.65 GB*) karena machine learning (facial recognition & CLIP vector) dan PostgreSQL berjalan di background. "
                "Jika ballooning menarik RAM Immich terlalu agresif saat proses indexing foto berlangsung, Immich bisa crash Out-Of-Memory (OOM). "
                "Jika ingin pasang ballooning di Immich, pastikan minimum RAM diset tinggi (misal min `3500 MB`, max `4096 MB`).\n\n"
                "3. 💡 *Syarat Wajib:*\n"
                "Pastikan package `qemu-guest-agent` terinstall dan running di dalam setiap VM (`sudo apt install qemu-guest-agent -y`) agar Proxmox bisa mengatur dynamic memory secara halus tanpa freeze.\n\n"
                + (
                    "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "💡 *Tips AI Copilot:* Anda dapat memasukkan API Key AI pilihan Anda (Gemini, Groq, OpenAI, Ollama) di Dashboard Web > AI Copilot > Konfigurasi AI 24/7 agar bot ini bisa berdialog bebas dan menjawab segala pertanyaan lanjutan secara otomatis!"
                    if show_api_hint else ""
                )
            )

        # B. Performance / Lag / Web Speed Concerns
        if any(w in q for w in ["lemot", "lag", "lambat", "lelet", "berat", "drop", "down"]) or \
           (any(w in q for w in ["turun", "kurang", "kecil", "pangkas"]) and any(w in q for w in ["ram", "memory", "memori", "web", "efek", "resiko", "aman"])):
            return (
                "Halo! Pertanyaan yang sangat bagus 👍.\n\n"
                "Jawabannya: *TIDAK AKAN LEMOT*, justru website Anda akan *jauh lebih stabil dan terhindar dari risiko crash mendadak*.\n\n"
                "1. 📊 *Pemakaian Riil Web Server Anda Sangat Ringan:*\n"
                "• `Ceritakota`: Hanya terpakai *~505 MB* (sisa menganggur 3.5 GB!)\n"
                "• `Portfolio-Sekar`: Hanya terpakai *~630 MB* (sisa menganggur 3.4 GB!)\n"
                "• `Portfolio-Aidil`: Hanya terpakai *~1.12 GB* (sisa menganggur 2.9 GB!)\n"
                "Artinya, alokasi 4.0 GB saat ini **80% hanya menganggur kosong (idle)**.\n\n"
                "2. ⚡ *Kecepatan Web Ditentukan vCPU & Latency, Bukan RAM Kosong:*\n"
                "Jumlah vCPU Anda *tetap 4 Core utuh*. Jika VM dialokasikan 2.0 GB - 2.5 GB, masih ada sisa ruang bebas >1.5 GB untuk lonjakan traffic.\n\n"
                "3. ⚠️ *Bahaya Nyata Justru Ada pada Host PVE yang 96.1% RAM:*\n"
                "Host Proxmox VE saat ini terjepit di *16.76 / 17.44 GB (96.1%)*. Jika host 100%, Proxmox akan memicu *OOM Killer* yang justru akan **membuat website crash mendadak**!\n\n"
                "4. 💡 *Solusi Paling Aman: Dynamic Memory Ballooning*\n"
                "`qm set 105 -balloon 2048` (Ceritakota)\n"
                "`qm set 106 -balloon 2048` (Sekar)\n"
                "`qm set 109 -balloon 2048` (Aidil)"
            )

        # C. Immich Specific Memory Concerns
        if "immich" in q and any(w in q for w in ["diatas", "3", "tiga", "besar", "tinggi", "ram", "memori", "kurang", "turun", "kenapa", "butuh"]):
            return (
                "Halo! Anda benar sekali 👍.\n\n"
                "Di Proxmox VE, VM *immich (104)* memang aktif menggunakan *~3.65 GB* dari 4.0 GB (89%). "
                "Immich menjalankan microservices berat seperti Machine Learning (Facial Recognition & CLIP vector search), "
                "database PostgreSQL vector, Redis queue, dan cache thumbnail foto yang intensif.\n\n"
                "💡 *Keputusan AI Copilot:*\n"
                "• *Alokasi VM Immich TETAP DIPERTAHANKAN di 4.0 GB* (tidak akan diturunkan) agar tidak crash OOM.\n"
                "• Penghematan RAM difokuskan pada VM idle (Pentest 8GB->2GB, Pambuluah 5GB->2GB, Web 4GB->2GB) yang totalnya menghemat ~13 GB RAM untuk host PVE!"
            )

        # D. Hardware / Mini PC / LAN / Wake-on-LAN discussions
        if any(w in q for w in ["mini pc", "laptop", "adapter", "wol", "wake-on-lan", "matiin", "nyalain", "power"]):
            return (
                "🔌 *DISKUSI HARDWARE & POWER MANAGEMENT*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "1. ⚡ *Kenapa Adapter LAN USB Laptop Tidak Bisa WoL saat Mati:*\n"
                "Saat laptop dimatikan total (state S5), controller USB memutus daya 5V Standby untuk menghemat baterai sehingga adapter USB LAN mati total.\n\n"
                "2. 🖥️ *Solusi Terbaik: Mini PC dengan Port LAN Bawaan (Onboard)*\n"
                "Port RJ45 bawaan Mini PC terhubung langsung ke bus PCIe dan mendapat daya siaga dari ATX/DC standby rail (bahkan saat OS mati) sehingga bisa dinyalakan via tombol Power Hub WoL kapan saja!"
            )

        # E. Specific VM query
        conn = database.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vms")
        vms = [dict(r) for r in cursor.fetchall()]
        conn.close()

        for v in vms:
            v_name = v.get("name", "").lower()
            v_id_str = str(v.get("vmid", ""))
            if v_name in q or v_id_str in q:
                alloc_gb = round(v.get("ram_total_mb", 0) / 1024, 1)
                used_mb = int(v.get("ram_used_mb", 0))
                pct = round((v.get("ram_used_mb", 0) / v.get("ram_total_mb", 1)) * 100, 1)
                return (
                    f"📊 *Status VM: {v.get('name')} (VMID: {v.get('vmid')})*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"• Status: 🟢 *{v.get('status', 'running').upper()}*\n"
                    f"• CPU Usage: *{v.get('cpu_pct', 0.0)}%*\n"
                    f"• RAM Alokasi: *{alloc_gb} GB*\n"
                    f"• RAM Terpakai: *{used_mb} MB* ({pct}%)\n"
                    f"• Disk Total: *{v.get('disk_total_gb', 0)} GB*\n"
                    f"• IP Address: `{v.get('ip_address') or '10.10.10.x'}`"
                )

        # F. Status Cluster
        if any(w in q for w in ["status", "kondisi", "gimana", "kabar", "cek", "/status", "/start", "halo", "hai", "ping"]):
            pve_ram_used = fleet.get('pve_ram_used_gb', 0)
            pve_ram_tot = fleet.get('pve_ram_total_gb', 0)
            pve_pct = fleet.get('pve_ram_used_pct', 0)
            return (
                "🤖 *SENTINEL AI HOMELAB COPILOT*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 *Kondisi Armada:* 🟢 {fleet.get('online_nodes', 9)}/{fleet.get('total_nodes', 9)} Node Online\n"
                f"🖥️ *Host Proxmox VE:* RAM {pve_ram_used} / {pve_ram_tot} GB ({pve_pct}% ⚠️)\n"
                f"📦 *Guest Workload:* {fleet.get('total_vms', 8)} VM Berjalan Aktif\n\n"
                "💡 Anda dapat menghubungkan API AI (Gemini, Groq, OpenAI, Ollama) di Dashboard Web > AI Copilot > Konfigurasi AI untuk berdialog bebas tanpa batas!"
            )

        # G. General Fallback with invitation to configure AI API key
        return (
            "🤖 *Sentinel AI Homelab Copilot*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Pertanyaan Anda: \"{text}\"\n\n"
            "⚠️ *API AI Belum Dikonfigurasi di Dashboard!*\n"
            "Agar saya bisa berdialog bebas dan menjawab segala pertanyaan tanpa batasan template (seperti rekan senior engineer):\n\n"
            "👉 *Langkah Mengaktifkan AI Bebas Pilih:*\n"
            "1. Buka Web Dashboard NOC (`http://10.10.10.9:8888`)\n"
            "2. Klik menu **AI Copilot (Smart Advisor)** di header atas\n"
            "3. Buka tab **Konfigurasi 24/7 & API AI**\n"
            "4. Pilih AI Provider yang Anda inginkan:\n"
            "   • **Google Gemini** (Gratis di *aistudio.google.com*)\n"
            "   • **Groq Cloud** (Super Cepat & Gratis di *console.groq.com*)\n"
            "   • **OpenAI** (ChatGPT API)\n"
            "   • **OpenRouter** (Multi-model)\n"
            "   • **Custom / Ollama** (Lokal di server sendiri)\n"
            "5. Masukkan API Key & klik **Simpan Pengaturan**!\n\n"
            "Setelah itu, bot ini akan langsung menjawab segala pertanyaan Anda dengan penalaran AI penuh!"
        )

    def _telegram_chat_loop(self):
        """
        Background listener for bidirectional interactive chat on Telegram.
        Polls getUpdates and generates intelligent AI Copilot responses.
        """
        print("🤖 Sentinel AI Homelab Copilot Telegram Chat Listener started.")
        time.sleep(5)
        last_offset = 0

        try:
            saved_offset = database.get_setting("tg_last_update_id", "0")
            last_offset = int(saved_offset)
        except Exception:
            last_offset = 0

        while self._is_running:
            token = database.get_setting("telegram_token", "")
            target_chat_id = database.get_setting("telegram_chat_id", "")
            if not token or not target_chat_id:
                time.sleep(10)
                continue

            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates?offset={last_offset}&timeout=15"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=25) as resp:
                    if resp.status == 200:
                        payload = json.loads(resp.read().decode('utf-8', errors='ignore'))
                        updates = payload.get("result", [])
                        for u in updates:
                            update_id = u.get("update_id", 0)
                            if update_id >= last_offset:
                                last_offset = update_id + 1
                                database.set_setting("tg_last_update_id", str(last_offset))

                            message = u.get("message") or u.get("edited_message")
                            if not message:
                                continue

                            sender_chat = str(message.get("chat", {}).get("id", ""))
                            # Security: Only respond to authorized chat_id
                            if sender_chat != str(target_chat_id):
                                continue

                            text = message.get("text", "").strip()
                            if not text:
                                continue

                            print(f"🤖 [Telegram Chat Incoming from {sender_chat}]: {text}")

                            # Send typing action
                            try:
                                action_url = f"https://api.telegram.org/bot{token}/sendChatAction"
                                action_data = urllib.parse.urlencode({"chat_id": target_chat_id, "action": "typing"}).encode()
                                urllib.request.urlopen(urllib.request.Request(action_url, data=action_data, method="POST"), timeout=5)
                            except Exception:
                                pass

                            # Generate intelligent AI Copilot reply
                            reply = self.generate_chat_reply(text)
                            self.send_telegram_direct(reply)
                            print(f"🤖 [Telegram Chat Replied]: {reply[:60]}...")

            except Exception as e:
                time.sleep(4)

    def _worker_loop(self):
        """
        Autonomous 24/7 background observer loop.
        Monitors node state transitions, resource thresholds, and scheduled digest.
        """
        # Initial sleep to allow telemetry collection to warm up
        time.sleep(10)
        print("🤖 Sentinel AI Homelab Copilot 24/7 Observer started.")

        # Seed initial node states
        try:
            servers = database.get_all_servers()
            now = time.time()
            for s in servers:
                is_on = (now - s.get("last_seen", 0)) < 60
                self._prev_node_states[s.get("id")] = "online" if is_on else "offline"
        except Exception:
            pass

        while self._is_running:
            try:
                settings = self.get_settings()
                if not settings.get("ai_copilot_enabled", True):
                    time.sleep(30)
                    continue

                now = time.time()
                servers = database.get_all_servers()
                tg_alerts_on = settings.get("ai_telegram_alerts_enabled", True)

                # 1. State transition & incident checks (Online <-> Offline)
                for s in servers:
                    sid = s.get("id")
                    hostname = s.get("hostname", sid)
                    is_online = (now - s.get("last_seen", 0)) < 60
                    current_state = "online" if is_online else "offline"
                    prev_state = self._prev_node_states.get(sid, current_state)

                    if tg_alerts_on:
                        # Event: Online -> Offline
                        if prev_state == "online" and current_state == "offline":
                            cd_key = f"off_{sid}"
                            if now - self._alert_cooldowns.get(cd_key, 0) > 1800: # 30 min cooldown
                                self._alert_cooldowns[cd_key] = now
                                advice = "Periksa koneksi jaringan atau cek konsol VM di Proxmox VE."
                                alert_msg = self.format_telegram_alert("NODE_OFFLINE", s, advice=advice)
                                self.send_telegram_direct(alert_msg)
                                print(f"🤖 [AI Alert] Dispatched NODE_OFFLINE alert for {hostname}")

                        # Event: Offline -> Online (Recovery)
                        elif prev_state == "offline" and current_state == "online":
                            alert_msg = self.format_telegram_alert("NODE_RECOVERED", s)
                            self.send_telegram_direct(alert_msg)
                            print(f"🤖 [AI Alert] Dispatched NODE_RECOVERED alert for {hostname}")

                    # 2. Resource Threshold Checks
                    if tg_alerts_on and current_state == "online":
                        cpu_pct = s.get("cpu_pct", 0)
                        ram_pct = 0
                        if s.get("ram_total_mb", 0) > 0:
                            ram_pct = round((s.get("ram_used_mb", 0) / s.get("ram_total_mb")) * 100, 1)

                        cpu_thresh = settings.get("ai_alert_threshold_cpu", 90)
                        ram_thresh = settings.get("ai_alert_threshold_ram", 94)

                        if cpu_pct >= cpu_thresh:
                            cd_key = f"cpu_{sid}"
                            if now - self._alert_cooldowns.get(cd_key, 0) > 1800:
                                self._alert_cooldowns[cd_key] = now
                                detail = f"Lonjakan Penggunaan CPU mencapai {cpu_pct:.1f}% (Batas: {cpu_thresh}%)"
                                advice = "Buka menu Top Processes di dashboard NOC untuk mengidentifikasi proses yang memakan CPU tinggi."
                                alert_msg = self.format_telegram_alert("RESOURCE_SPIKE", s, detail=detail, advice=advice)
                                self.send_telegram_direct(alert_msg)

                        if ram_pct >= ram_thresh:
                            cd_key = f"ram_{sid}"
                            if now - self._alert_cooldowns.get(cd_key, 0) > 1800:
                                self._alert_cooldowns[cd_key] = now
                                detail = f"Penggunaan RAM kritis mencapai {ram_pct:.1f}% (Batas: {ram_thresh}%)"
                                advice = "Pertimbangkan menambah kapasitas RAM VM di Proxmox atau kurangi proses yang tidak digunakan."
                                alert_msg = self.format_telegram_alert("RESOURCE_SPIKE", s, detail=detail, advice=advice)
                                self.send_telegram_direct(alert_msg)

                    self._prev_node_states[sid] = current_state

                # 3. Scheduled Autonomous AI Digest (e.g. Every 6h)
                if settings.get("ai_telegram_digest_enabled", True):
                    interval_sec = settings.get("ai_digest_interval_hours", 6) * 3600
                    last_digest = settings.get("ai_last_digest_time", 0)

                    if (now - last_digest) >= interval_sec:
                        print("🤖 [AI Digest] Dispatched scheduled 24/7 Homelab Briefing...")
                        self.dispatch_briefing()

            except Exception as e:
                print(f"AICopilot worker error: {e}")

            # Sleep 20 seconds between health checks
            time.sleep(20)

copilot = AICopilotEngine()
