# 🛡️ Sentinel NOC - Deep Infrastructure, Storage & Security Sentinel

Sentinel NOC adalah sistem monitoring infrastruktur, server, cluster, dan homelab modern berbasis web yang ringan, cepat, dan berkinerja tinggi. Dirancang khusus untuk administrator sistem, teknisi DevOps, dan homelab enthusiast yang mengelola server Linux dan cluster Proxmox VE (PVE).

---

## 📑 Daftar Isi
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Fitur Utama](#-fitur-utama)
- [Persyaratan Sistem](#-persyaratan-sistem)
- [Panduan Instalasi Server (Central NOC)](#-panduan-instalasi-server-central-noc)
  - [Metode 1: Menggunakan Docker Compose (Direkomendasikan)](#metode-1-docker-compose-direkomendasikan)
  - [Metode 2: Instalasi Manual Python (Native Systemd)](#metode-2-instalasi-manual-python-native-systemd)
- [Panduan Menambahkan Node Remote (Agent Auto-Installer)](#-panduan-menambahkan-node-remote-agent-auto-installer)
- [Struktur Folder & File](#-struktur-folder--file)
- [Konfigurasi & Notifikasi Alert](#-konfigurasi--notifikasi-alert)
- [Perintah Pemeliharaan & Troubleshooting](#-perintah-pemeliharaan--troubleshooting)
- [Lisensi](#-lisensi)

---

## 🏛️ Arsitektur Sistem

Sentinel NOC menggunakan model arsitektur **Hub-and-Spoke (Central Server + Lightweight Node Agents)**:

```
                          ┌─────────────────────────────────────┐
                          │   🖥️  SENTINEL CENTRAL NOC SERVER    │
                          │        (Port 8888 - FastAPI)         │
                          │   - Web Dashboard & Realtime Engine │
                          │   - SQLite Time-Series Database     │
                          │   - Alert Engine (Telegram/Discord) │
                          │   - Speedtest & Multi-hop Probes    │
                          └──────────────────┬──────────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             │ Heartbeat Sync (Tiap 1.5s)    │                               │
             ▼                               ▼                               ▼
  ┌───────────────────────┐       ┌───────────────────────┐       ┌───────────────────────┐
  │   Node 1: Proxmox PVE │       │   Node 2: Ubuntu VM   │       │   Node 3: Debian Host │
  │   (sentinel-agent)    │       │   (sentinel-agent)    │       │   (sentinel-agent)    │
  │ - QEMU/LXC VMs        │       │ - Docker Containers   │       │ - System Services     │
  │ - ZFS Storage Pools   │       │ - NVMe / SMART Disks  │       │ - CPU / RAM / Net     │
  └───────────────────────┘       └───────────────────────┘       └───────────────────────┘
```

- **Sentinel Server (Central Controller)**: Mengumpulkan data telemetri, melayani antarmuka web, menjalankan query pembanding antar-node, serta menguji latensi WAN/LAN secara aktif.
- **Sentinel Agent**: Daemon Python super ringan (hanya menggunakan standar library Linux dan psutil, konsumsi RAM < 15MB) yang dipasang di setiap node remote untuk melaporkan metrik kernel, container Docker, VM Proxmox, dan disk fisik.

---

## ✨ Fitur Utama

1. **Multi-Node Cluster Fleet Matrix**:
   - Memantau seluruh node server dalam 1 cluster secara serentak berdampingan (*side-by-side*) tanpa perlu reload atau ganti tab.
   - Posisi node terkunci permanen (*stable ordering*) berdasarkan ID dan hostname sehingga kartu server tidak melompat-lompat sendiri.

2. **Realtime 60-Second Rolling Waveforms**:
   - Grafik canvas dinamis resolusi tinggi yang menampilkan lonjakan beban CPU (%) dan Throughput Bandwidth Jaringan (RX/TX) per detik secara *live*.

3. **Diagnostik Vital Hardware Mendalam**:
   - Pelacakan suhu CPU Thermal Package (`°C`), I/O Wait, CPU Steal, dan beban load average 1m/5m/15m.
   - Rincian RAM terpakai, cache pagecache, buffer kernel, dan swap space.
   - Tombol **"Free RAM"** (`drop_caches`) instan untuk membebaskan memory cache Linux.

4. **Kualitas Latensi Jaringan WAN / LAN Multi-Hop**:
   - Ping berkala multi-port (Port 53 DNS, 443 HTTPS, 80 HTTP, dan ICMP) ke Router Gateway lokal (`10.10.10.1`), Cloudflare DNS (`1.1.1.1`), dan Google DNS (`8.8.8.8`).
   - Pendeteksian status *Jitter*, *Packet Drop*, dan integrasi Speedtest bandwidth.

5. **Kesehatan Storage & S.M.A.R.T. Disks**:
   - Telemetri status disk NVMe, SSD, HDD, dan ZFS Pool.
   - Monitoring indikator kerusakan hardware: *Reallocated Sectors*, *Pending Sectors*, dan suhu disk.

6. **Manajemen Workload (Docker & Proxmox VE)**:
   - Memantau container Docker yang berjalan, port mapping, dan status uptime.
   - Kontrol langsung untuk **Restart** dan **Stop** container dari dashboard.
   - Mendeteksi VM QEMU dan Container LXC pada node Proxmox VE secara otomatis.

7. **Interactive Web Terminal & Maintenance Runbooks**:
   - Akses shell interaktif langsung dari dashboard browser tanpa perlu membuka aplikasi SSH terpisah.
   - Menu Runbook 1-Klik untuk operasi rutin: `apt update`, pembersihan journal logs systemd, cek port terbuka, dan reset memory.

8. **Realtime Systemd & Docker Log Streamer**:
   - Terminal log viewer terintegrasi bergaya hacker/NOC langsung di browser.
   - Filter logs berdasarkan source (`journalctl`, `docker`, `kernel/dmesg`), level (`ERROR`, `WARN`, `INFO`), dan pencarian teks bebas (*full-text search*).
   - Fitur jeda otomatis (*Pause*), *Clear Terminal*, dan *Auto-scroll*.

9. **SSL / TLS Certificate Expiry Sentinel**:
   - Pelacakan masa aktif sertifikat HTTPS/SSL domain dan port kustom.
   - Indikator sisa hari aktif (*countdown progress bar*), validasi status (*Healthy*, *Warning*, *Critical Expired*), dan issuer.
   - Tombol manual audit (*Check Now*) dan form penambahan domain baru langsung dari UI.

10. **Subnet LAN Discovery & IP Network Scanner**:
    - Pemindaian otomatis dan inventarisasi perangkat pada subnet lokal (contoh: `10.10.10.0/24`).
    - Mendeteksi alamat IP, Hostname, MAC Address, OUI Vendor perangkat (Proxmox, Mikrotik, Raspberry Pi, Intel, dll.), dan status ping.
    - Tombol *Run LAN Discovery* untuk memicu re-scan subnet secara berkala atau on-demand.

11. **Kalkulator Konsumsi Daya & Estimasi Biaya Listrik PLN**:
    - Mengkalkulasi estimasi konsumsi daya listrik (Watt) berdasarkan beban CPU load dan profil daya hardware per node secara *realtime*.
    - Perhitungan otomatis kWh harian, kWh bulanan, serta estimasi tagihan listrik bulanan dalam Rupiah (Rp).
    - Modal kustomisasi tarif dasar listrik PLN (default standar golongan R-1/TR 1.300-2.200 VA: Rp 1.444,70 / kWh).

12. **Proxmox Backup & Snapshot Health Sentinel**:
    - Monitor histori dan integritas backup VM & Container LXC Proxmox VE.
    - Menampilkan target storage (PBS - Proxmox Backup Server, local-zfs, NFS), ukuran backup dalam GB, durasi waktu kompresi, dan status kesehatan job terakhir.

13. **Alert Bot Realtime (Telegram & Discord)**:
    - Notifikasi otomatis saat CPU / RAM / Disk melewati ambang batas darurat atau saat node mengalami *loss connection* (offline).

---

## 📦 Persyaratan Sistem

### Pada Server Utama (Central NOC):
- Sistem Operasi: Linux (Ubuntu 20.04+, Debian 11+, Proxmox VE 7+, Rocky Linux, dll.)
- **Docker & Docker Compose** (Sangat disarankan) ATAU Python 3.9+ dengan `pip`.
- Port terbuka: **8888** (TCP).

### Pada Server / Node Remote (Agent):
- Sistem Operasi Linux apa saja dengan `systemd`.
- `curl` dan `python3` (akan diinstal otomatis jika belum ada).

---

## 🚀 Panduan Instalasi Server (Central NOC)

### Metode 1: Docker Compose (Direkomendasikan)

Metode ini paling mudah dan mengisolasi semua dependensi ke dalam container.

1. **Download & Ekstrak Kode Sumber**:
   ```bash
   mkdir -p /opt/server-monitor
   cd /opt/server-monitor
   # Salin atau ekstrak file server-monitor.zip ke folder ini
   unzip server-monitor.zip
   ```

2. **Jalankan dengan Docker Compose**:
   ```bash
   docker compose up -d --build
   ```

3. **Verifikasi Container Berjalan**:
   ```bash
   docker ps | grep server-monitor
   ```

4. **Akses Dashboard**:
   Buka browser dan arahkan ke:
   ```
   http://<IP-SERVER-ANDA>:8888
   ```
   *(Contoh: `http://10.10.10.9:8888`)*

---

### Metode 2: Instalasi Manual Python (Native Systemd)

Gunakan metode ini jika Anda tidak ingin menggunakan Docker.

1. **Install Paket Dependensi Sistem**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip python3-venv smartmontools nvme-cli procps curl iproute2
   ```

2. **Setup Virtual Environment & Install Library**:
   ```bash
   cd /opt/server-monitor
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Buat Systemd Service (`/etc/systemd/system/sentinel-server.service`)**:
   ```ini
   [Unit]
   Description=Sentinel NOC Central Server
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/opt/server-monitor
   ExecStart=/opt/server-monitor/venv/bin/python server/main.py
   Restart=always
   RestartSec=3
   Environment=PORT=8888

   [Install]
   WantedBy=multi-user.target
   ```

4. **Aktifkan & Jalankan Service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now sentinel-server
   sudo systemctl status sentinel-server
   ```

---

## 🌐 Panduan Menambahkan Node Remote (Agent Auto-Installer)

Sentinel NOC dilengkapi skrip installer 1-perintah otomatis. Untuk memantau node Linux / Proxmox VE lain ke dalam cluster:

1. **Jalankan Perintah Ini di Terminal Server Remote yang Ingin Ditambahkan**:
   ```bash
   curl -sSL http://<IP-SERVER-NOC>:8888/install.sh | sudo bash
   ```
   *Gantilah `<IP-SERVER-NOC>` dengan IP server monitoring Anda (misal: `10.10.10.9`).*

2. **Apa yang Dilakukan oleh Skrip Ini?**:
   - Memeriksa runtime `python3` (otomatis menginstal via package manager jika belum ada).
   - Mengunduh script agent terbaru ke `/opt/sentinel-agent/agent.py`.
   - Mengonfigurasi URL target monitoring server secara otomatis.
   - Mendaftarkan dan mengaktifkan service systemd `sentinel-agent.service`.

3. **Lihat di Dashboard**:
   Node baru akan langsung muncul otomatis pada tab **Cluster Fleet** dan dropdown pemilihan node dalam waktu **2-3 detik**!

---

## 📂 Struktur Folder & File

```
server-monitor/
├── docker-compose.yml          # Konfigurasi deployment container Docker
├── Dockerfile                  # Definisi image container server
├── requirements.txt            # Daftar library Python (FastAPI, uvicorn, psutil, dll.)
├── install.sh                  # Skrip auto-installer 1-perintah untuk node remote
├── DESIGN.md                   # Spesifikasi sistem desain & UI/UX tokens
├── README.md                   # Dokumentasi panduan instalasi & penggunaan ini
├── agent/
│   └── agent.py                # Kode agent telemetri node cluster
└── server/
    ├── main.py                 # Core backend FastAPI, socket terminal, speedtest, alert
    ├── database.py             # SQLite data layer & node registry
    ├── logs.py                 # System logger & event subscriber
    └── static/
        ├── index.html          # Web UI dashboard frontend responsif
        └── datacenter_bg.jpg   # Background datacenter sinematik resolusi tinggi
```

---

## 🔔 Konfigurasi & Notifikasi Alert

Anda dapat mengatur notifikasi alert instan ke Telegram atau Discord melalui tombol icon lonceng (**Alert Settings**) di pojok kanan atas dashboard:

1. **Telegram Bot**:
   - Buat bot di Telegram melalui `@BotFather` untuk mendapatkan **Bot Token**.
   - Kirim pesan ke bot Anda, lalu dapatkan **Chat ID** Anda (bisa menggunakan bot `@userinfobot`).
   - Masukkan Token & Chat ID ke modal pengaturan dashboard lalu klik **Save Settings**.
   - Anda dapat menekan tombol **"Test Send Alert"** untuk menguji pengiriman pesan.

2. **Discord Webhook**:
   - Buat integrasi Webhook pada channel Discord Anda (*Server Settings -> Integrations -> Webhooks*).
   - Masukkan URL Webhook ke input Discord pada modal pengaturan.

---

## 🔧 Perintah Pemeliharaan & Troubleshooting

### Memeriksa Log Server:
- **Jika menggunakan Docker**:
  ```bash
  docker logs -f server-monitor
  ```
- **Jika menggunakan Systemd**:
  ```bash
  sudo journalctl -u sentinel-server -f
  ```

### Memeriksa Status Agent di Node Remote:
```bash
sudo systemctl status sentinel-agent
sudo journalctl -u sentinel-agent -f
```

### Cara Menghapus / Uninstall Node Agent:
Jika Anda ingin mencopot agent dari server remote:
```bash
sudo systemctl disable --now sentinel-agent
sudo rm -rf /opt/sentinel-agent /etc/systemd/system/sentinel-agent.service
sudo systemctl daemon-reload
```
Setelah agent dicopot, Anda dapat menekan tombol **Hapus Node** di dashboard untuk menghapusnya dari database.

---

## 📄 Lisensi
Didistribusikan di bawah lisensi MIT. Bebas digunakan, dimodifikasi, dan disebarluaskan untuk keperluan pribadi maupun komersial.
