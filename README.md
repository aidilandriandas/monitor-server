# Aegis System - Advanced Linux & Proxmox Server Monitor
**Engineered & Designed by AIDIL ANDRIANDAS**

Aegis is an enterprise-grade, high-fidelity Host-Based Intrusion Detection System (HIDS), Telemetry Collector, and Datacenter Controller. Whether you are running a multi-node Baremetal Proxmox Cluster in your Home Lab or a single isolated Cloud VPS, Aegis automatically adapts to protect and monitor your infrastructure.

## 🚀 Key Features

### 🧠 State-Aware AI Copilot (New)
* **Contextual Memory Sandbox:** The AI isn't just a basic chatbot. It maintains a short-term memory of your last interactions combined with real-time cluster telemetry and execution logs (`[Sistem Otomatis]`). It knows exactly what succeeded and what failed.
* **Smart Intent Parsing:** Intelligent regex word-boundary mapping ensures the AI accurately identifies targeted VMs without confusing substrings (e.g., distinguishing the VM named "sekar" from the word "sekarang").
* **Direct SSH Execution:** AI actions (like resizing VM RAM or rebooting nodes) are executed with zero latency via a native SSH tunnel direct to the Proxmox Hypervisor, bypassing legacy agent queues for instant reliability.
* **Telegram Integration:** Get instant alerts on your phone for FIM tampering, C2 Miner detection, or ask the AI to manage your cluster directly via chat.

### 🛡️ Multi-Layer Cyber Defense (HIDS)
* **Proxmox Perimeter Shield:** Automatically blocks malicious IPs at the Hypervisor level (`ebtables` & `iptables` on `vmbr0`) protecting all VMs behind it.
* **Smart VPS Fallback:** If deployed on a Cloud VPS without hypervisor access, Aegis automatically falls back to locking down the local instance via native `iptables` and immediate socket termination (`ss -K`).
* **Auto-Jail & C2 Miner Detection:** Actively scans for Crypto Miners, Command & Control (C2) domains, and immediately jails offending IPs.
* **File Integrity Monitoring (FIM):** Hashes and monitors critical OS files (`/etc/passwd`, `sshd_config`, etc.). Alerts you the second a file is tampered with.
* **One-Click OS Hardening:** Automatically enforces `PermitRootLogin prohibit-password`, disables `PasswordAuthentication`, enables SYN Flood shields (`tcp_syncookies`), and activates Smurf Defense (`icmp_echo_ignore_broadcasts`).

### 📊 High-Fidelity Telemetry (Real-Time)
* **Deep CPU & RAM Diagnostics:** Tracks CPU IO-Wait, Steal Time, Core MHz, and RAM/Swap utilization.
* **Accurate Network IO:** Real-time bandwidth tracking (`RX/TX kbps`) parsed directly from `/proc/net/dev`.
* **TCP Socket State Monitor:** Live tracking of `ESTABLISHED`, `LISTEN`, and `TIME_WAIT` connection states.
* **Process Hunter:** View and instantly kill high-resource processes.
* **Hardware Sensors:** Safely reads actual thermal sensors (`/sys/class/thermal`).

### 🐳 Docker & Infrastructure Management
* **Docker Audit:** Deep integration with `/var/run/docker.sock` to monitor container states, uptime, and perform bulk restarts.
* **Proxmox VM Control:** Turn VMs on/off/reboot directly from the dashboard using `pvesh` APIs.
* **Proxmox Backup Health:** Tracks `vzdump` backups, sizes, and timestamps to ensure zero data loss.
* **SSL Certificate Monitor:** Track multiple domain certificates and get expiration warnings.

---

## 🛠️ Architecture

Aegis consists of two primary components:
1. **Aegis Server (NOC/Dashboard):** A FastAPI Python backend and beautiful responsive HTML5 frontend running inside a Docker Container on your central monitoring node.
2. **Aegis Agent:** A lightweight, pure-Python script (`agent.py`) installed on target VMs/Servers that collects metrics and sends JSON payloads to the central server via HTTP POST.

---

## ⚙️ Installation

### 1. Install Central Aegis Server
Clone this repository on your central monitoring node (e.g., `10.10.10.9`), then deploy via Docker:

```bash
docker-compose up -d --build
```
*The dashboard will be available at `http://<your-ip>:8888` (or port 8000 depending on your environment).*

### 2. Install Aegis Agent on Targets (VPS / VMs)
Run the auto-installer on any Linux machine (Ubuntu, Debian, CentOS, Proxmox Hypervisor) you wish to monitor.

```bash
export MONITOR_SERVER_URL="http://<aegis-server-ip>:8888"
curl -s http://<aegis-server-ip>:8888/install.sh | bash
```

The agent runs as a systemd service (`aegis-agent.service`) and automatically registers itself to the dashboard.

---

## ☁️ Cloud VPS vs Baremetal Proxmox

Aegis dynamically adapts to its environment:
* **On Baremetal Proxmox:** Unlocks powerful Hypervisor Perimeter Defense, AI Direct SSH Execution, VM Power Controls, and Backup tracking.
* **On Cloud VPS (DigitalOcean, AWS, etc.):** Safely ignores hypervisor-specific features without crashing. Focuses 100% of its power on local OS Hardening, Docker tracking, and VPS Network monitoring.

---

## 👨‍💻 Credits & Attribution
Architected and developed from the ground up by **AIDIL ANDRIANDAS**.

*Crafted with precision for secure, high-performance infrastructure monitoring.*
