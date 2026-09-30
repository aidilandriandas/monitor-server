import os
import re
import time

HOST_LOG = os.environ.get("HOST_LOG", "/host/var/log")

def get_real_logs(limit=100):
    logs = []
    
    # 1. Parse Auth Logs (SSH & Sudo)
    auth_paths = [
        os.path.join(HOST_LOG, "auth.log"),
        "/var/log/auth.log"
    ]
    
    auth_file = None
    for p in auth_paths:
        if os.path.exists(p):
            auth_file = p
            break

    if auth_file:
        try:
            with open(auth_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-300:] # Last 300 lines
                for l in reversed(lines):
                    l_str = l.strip()
                    if not l_str:
                        continue
                    
                    # Timestamp extraction (e.g. Sep 28 03:46:36)
                    ts = l_str[:15]
                    content = l_str[16:]

                    # Failed password (Brute Force / Unauthorized)
                    failed_m = re.search(r'Failed password for (invalid user )?(\w+) from ([\d\.]+) port (\d+)', content)
                    if failed_m:
                        user = failed_m.group(2)
                        ip = failed_m.group(3)
                        logs.append({
                            "timestamp": ts,
                            "type": "SECURITY",
                            "level": "CRITICAL",
                            "badge": "AUTH_FAILED",
                            "source": "sshd",
                            "ip": ip,
                            "user": user,
                            "message": f"Failed SSH password for user '{user}' from {ip}"
                        })
                        continue

                    # Accepted password (Successful login)
                    accepted_m = re.search(r'Accepted (password|publickey) for (\w+) from ([\d\.]+) port (\d+)', content)
                    if accepted_m:
                        method = accepted_m.group(1)
                        user = accepted_m.group(2)
                        ip = accepted_m.group(3)
                        logs.append({
                            "timestamp": ts,
                            "type": "SECURITY",
                            "level": "SUCCESS",
                            "badge": "AUTH_SUCCESS",
                            "source": "sshd",
                            "ip": ip,
                            "user": user,
                            "message": f"Successful SSH login ({method}) for user '{user}' from {ip}"
                        })
                        continue

                    # Sudo execution
                    sudo_m = re.search(r'sudo:\s+(\w+)\s+:.*COMMAND=(.*)', content)
                    if sudo_m:
                        user = sudo_m.group(1)
                        cmd = sudo_m.group(2).strip()
                        logs.append({
                            "timestamp": ts,
                            "type": "SECURITY",
                            "level": "WARNING",
                            "badge": "SUDO_EXEC",
                            "source": "sudo",
                            "ip": "local",
                            "user": user,
                            "message": f"User '{user}' executed root command: {cmd}"
                        })
                        continue

                    # Invalid user attempt
                    invalid_m = re.search(r'Invalid user (\w+) from ([\d\.]+)', content)
                    if invalid_m:
                        user = invalid_m.group(1)
                        ip = invalid_m.group(2)
                        logs.append({
                            "timestamp": ts,
                            "type": "SECURITY",
                            "level": "CRITICAL",
                            "badge": "INVALID_USER",
                            "source": "sshd",
                            "ip": ip,
                            "user": user,
                            "message": f"Attempted login with non-existent user '{user}' from {ip}"
                        })
                        continue

        except Exception as e:
            print(f"Error reading auth.log: {e}")

    # 2. Parse Syslog / Service Errors
    syslog_paths = [
        os.path.join(HOST_LOG, "syslog"),
        "/var/log/syslog"
    ]
    syslog_file = None
    for p in syslog_paths:
        if os.path.exists(p):
            syslog_file = p
            break

    if syslog_file:
        try:
            with open(syslog_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-300:]
                for l in reversed(lines):
                    l_str = l.strip()
                    lower_l = l_str.lower()
                    if any(k in lower_l for k in ["error", "failed", "critical", "panic", "fatal", "timed out", "down"]):
                        ts = l_str[:15]
                        rest = l_str[16:]
                        
                        # Extract process name
                        src_m = re.search(r'([a-zA-Z0-9_\-\.]+)(\[\d+\])?:', rest)
                        source = src_m.group(1) if src_m else "system"
                        
                        # Filter out noisy lines
                        if any(x in lower_l for x in ["cron", "dbus", "snapd", "getty"]):
                            continue

                        level = "CRITICAL" if any(x in lower_l for x in ["fail", "fatal", "panic", "critical"]) else "WARNING"
                        
                        logs.append({
                            "timestamp": ts,
                            "type": "SERVICE",
                            "level": level,
                            "badge": f"{source.upper()}_ERR",
                            "source": source,
                            "ip": "-",
                            "user": "-",
                            "message": rest[:200]
                        })
        except Exception as e:
            print(f"Error reading syslog: {e}")

    # Sort logs by timestamp or keep most recent
    return logs[:limit]

def get_demo_logs():
    now_str = time.strftime("%b %d %H:%M:%S")
    return [
        {
            "timestamp": time.strftime("%b %d %H:%M:%S", time.localtime(time.time() - 35)),
            "type": "SECURITY",
            "level": "CRITICAL",
            "badge": "BRUTE_FORCE",
            "source": "sshd",
            "ip": "185.220.101.5",
            "user": "root",
            "message": "SSH Brute-Force Alert: 48 failed password attempts in 60s for user 'root'"
        },
        {
            "timestamp": time.strftime("%b %d %H:%M:%S", time.localtime(time.time() - 95)),
            "type": "SERVICE",
            "level": "CRITICAL",
            "badge": "REDIS_ERR",
            "source": "redis-server",
            "ip": "-",
            "user": "-",
            "message": "redis.service: Main process exited, code=exited, status=1/FAILURE (OOM memory limit exceeded)"
        },
        {
            "timestamp": time.strftime("%b %d %H:%M:%S", time.localtime(time.time() - 140)),
            "type": "SECURITY",
            "level": "SUCCESS",
            "badge": "AUTH_SUCCESS",
            "source": "sshd",
            "ip": "10.50.0.1",
            "user": "aidil",
            "message": "Accepted password for aidil from 10.50.0.1 port 59510 ssh2"
        },
        {
            "timestamp": time.strftime("%b %d %H:%M:%S", time.localtime(time.time() - 210)),
            "type": "SECURITY",
            "level": "WARNING",
            "badge": "SUDO_EXEC",
            "source": "sudo",
            "ip": "local",
            "user": "aidil",
            "message": "User 'aidil' executed root command: /usr/bin/systemctl restart nginx"
        },
        {
            "timestamp": time.strftime("%b %d %H:%M:%S", time.localtime(time.time() - 320)),
            "type": "SERVICE",
            "level": "WARNING",
            "badge": "NGINX_WARN",
            "source": "nginx",
            "ip": "172.16.1.45",
            "user": "-",
            "message": "[warn] 838#838: *1420 upstream server temporarily disabled while connecting to upstream 'unix:/run/php/php8.3-fpm.sock'"
        },
        {
            "timestamp": time.strftime("%b %d %H:%M:%S", time.localtime(time.time() - 410)),
            "type": "SECURITY",
            "level": "CRITICAL",
            "badge": "AUTH_FAILED",
            "source": "sshd",
            "ip": "45.142.214.88",
            "user": "admin",
            "message": "Failed password for invalid user 'admin' from 45.142.214.88 port 41882"
        },
        {
            "timestamp": time.strftime("%b %d %H:%M:%S", time.localtime(time.time() - 560)),
            "type": "SERVICE",
            "level": "CRITICAL",
            "badge": "STORAGE_ERR",
            "source": "smartd",
            "ip": "-",
            "user": "-",
            "message": "Device: /dev/sdc [SAT], 36 Currently unreadable (pending) sectors detected. SMART health test FAILED."
        },
        {
            "timestamp": time.strftime("%b %d %H:%M:%S", time.localtime(time.time() - 720)),
            "type": "SECURITY",
            "level": "WARNING",
            "badge": "SUDO_EXEC",
            "source": "sudo",
            "ip": "local",
            "user": "aidil",
            "message": "User 'aidil' executed root command: /usr/bin/ufw allow 8888/tcp"
        },
        {
            "timestamp": time.strftime("%b %d %H:%M:%S", time.localtime(time.time() - 900)),
            "type": "SERVICE",
            "level": "WARNING",
            "badge": "MYSQL_WARN",
            "source": "mysqld",
            "ip": "-",
            "user": "-",
            "message": "[Warning] InnoDB: 1 lock struct(s) have not been released. Transaction lock wait timeout exceeded."
        },
        {
            "timestamp": time.strftime("%b %d %H:%M:%S", time.localtime(time.time() - 1100)),
            "type": "SECURITY",
            "level": "CRITICAL",
            "badge": "AUTH_FAILED",
            "source": "sshd",
            "ip": "194.26.29.112",
            "user": "test",
            "message": "Failed password for invalid user 'test' from 194.26.29.112 port 38921"
        }
    ]
