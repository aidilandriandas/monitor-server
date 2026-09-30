
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
          },
          colors: {
            brand: {
              50: '#eff6ff',
              500: '#3b82f6',
              900: '#1e3a8a',
            },
            surface: {
              750: '#1e2638',
              800: '#141926',
              850: '#0f1420',
              900: '#0a0d15',
              950: '#05070c'
            }
          }
        }
      }
    }
  
;

    let isDemoMode = false;
    let currentLogCategory = 'ALL';
    let allLogsCache = [];

    // Rolling History Buffers for Charts (60 data points)
    const MAX_POINTS = 30;
    const chartLabels = Array(MAX_POINTS).fill('');
    const cpuHistory = Array(MAX_POINTS).fill(0);
    const iowaitHistory = Array(MAX_POINTS).fill(0);
    const rxHistory = Array(MAX_POINTS).fill(0);
    const txHistory = Array(MAX_POINTS).fill(0);

    let cpuChart = null;
    let netChart = null;

    function initCharts() {
      const chartCommonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: {
            grid: { color: 'rgba(51, 65, 85, 0.2)' },
            ticks: { color: '#94a3b8', font: { family: 'monospace', size: 10 } }
          }
        }
      };

      // CPU Chart
      const cpuCtx = document.getElementById('cpuChart').getContext('2d');
      cpuChart = new Chart(cpuCtx, {
        type: 'line',
        data: {
          labels: chartLabels,
          datasets: [
            {
              data: cpuHistory,
              borderColor: '#3b82f6',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              fill: true,
              tension: 0.35,
              borderWidth: 2,
              pointRadius: 0
            },
            {
              data: iowaitHistory,
              borderColor: '#f59e0b',
              backgroundColor: 'transparent',
              fill: false,
              tension: 0.35,
              borderWidth: 1.5,
              borderDash: [3, 3],
              pointRadius: 0
            }
          ]
        },
        options: {
          ...chartCommonOptions,
          scales: {
            ...chartCommonOptions.scales,
            y: { ...chartCommonOptions.scales.y, min: 0, max: 100 }
          }
        }
      });

      // Network Chart
      const netCtx = document.getElementById('netChart').getContext('2d');
      netChart = new Chart(netCtx, {
        type: 'line',
        data: {
          labels: chartLabels,
          datasets: [
            {
              data: rxHistory,
              borderColor: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              fill: true,
              tension: 0.35,
              borderWidth: 2,
              pointRadius: 0
            },
            {
              data: txHistory,
              borderColor: '#06b6d4',
              backgroundColor: 'transparent',
              fill: false,
              tension: 0.35,
              borderWidth: 1.5,
              pointRadius: 0
            }
          ]
        },
        options: chartCommonOptions
      });
    }

    let selectedServerId = null;
    let registeredNodesCache = [];
    let clusterNodesCache = [];

    async function fetchDashboard() {
      try {
        let url = '/api/v1/dashboard';
        if (selectedServerId) {
          url += '?server_id=' + encodeURIComponent(selectedServerId);
        }
        const res = await fetch(url);
        const data = await res.json();
        renderDashboard(data);
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      }
    }

    function toggleNodeDropdown() {
      const menu = document.getElementById('nodeDropdownMenu');
      const chev = document.getElementById('nodeChevron');
      menu.classList.toggle('hidden');
      if (!menu.classList.contains('hidden')) {
        chev.classList.add('rotate-180');
      } else {
        chev.classList.remove('rotate-180');
      }
    }

    document.addEventListener('click', (e) => {
      const wrapper = document.getElementById('nodeSelectorWrapper');
      if (wrapper && !wrapper.contains(e.target)) {
        const menu = document.getElementById('nodeDropdownMenu');
        const chev = document.getElementById('nodeChevron');
        if (menu && !menu.classList.contains('hidden')) {
          menu.classList.add('hidden');
          if (chev) chev.classList.remove('rotate-180');
        }
      }
    });

    function selectNode(nodeId) {
      selectedServerId = nodeId;
      const menu = document.getElementById('nodeDropdownMenu');
      if (menu) menu.classList.add('hidden');
      const chev = document.getElementById('nodeChevron');
      if (chev) chev.classList.remove('rotate-180');
      if (currentDashboardView === 'cluster') {
        switchDashboardView('single');
      } else {
        fetchDashboard();
      }
      fetchPowerEstimate();
    }

    function renderNodeDropdownList(nodes, activeId) {
      const container = document.getElementById('nodeListContainer');
      if (!container) return;
      if (!nodes || nodes.length === 0) {
        container.innerHTML = '<div class="text-slate-500 text-[11px] p-2 text-center">No nodes registered</div>';
        return;
      }

      container.innerHTML = nodes.map(n => {
        const isActive = (n.id === activeId);
        const isOnline = (n.is_online !== undefined) ? n.is_online : true;
        const dotColor = isOnline ? 'bg-emerald-400' : 'bg-red-500';
        const activeClass = isActive ? 'bg-blue-600/20 border-blue-500/40 text-white' : 'hover:bg-surface-800/80 border-transparent text-slate-300';
        return `
          <div onclick="selectNode('${n.id}')" class="px-2.5 py-2 rounded-xl cursor-pointer border transition-all flex items-center justify-between ${activeClass}">
            <div class="flex items-center gap-2 truncate">
              <span class="w-2 h-2 rounded-full ${dotColor} shrink-0"></span>
              <div class="truncate">
                <div class="text-xs font-bold truncate flex items-center gap-1.5">
                  <span>${n.hostname || n.id}</span>
                  ${isActive ? '<span class="text-[9px] px-1.5 py-0.2 bg-blue-500/30 text-blue-300 rounded uppercase font-semibold">Active</span>' : ''}
                </div>
                <div class="text-[10px] text-slate-400 font-mono">${n.ip || '127.0.0.1'} | ${n.os || 'Linux'}</div>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <div class="text-right font-mono text-[11px]">
                <span class="text-blue-400 font-semibold">${Number(n.cpu_pct || 0).toFixed(0)}% CPU</span>
              </div>
              ${n.id !== 'srv-host-node' && !isDemoMode ? `
                <button onclick="event.stopPropagation(); confirmDeleteNode('${n.id}', '${n.hostname || n.id}', '${n.ip || ''}')" 
                        title="Hapus node ${n.hostname || n.id} dari cluster" 
                        class="w-6 h-6 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 flex items-center justify-center transition">
                  <i class="fa-solid fa-trash-can text-[11px]"></i>
                </button>
              ` : ''}
            </div>
          </div>
        `;
      }).join('');
    }

    function openAddNodeModal() {
      const modal = document.getElementById('addNodeModal');
      const menu = document.getElementById('nodeDropdownMenu');
      if (menu) menu.classList.add('hidden');
      const chev = document.getElementById('nodeChevron');
      if (chev) chev.classList.remove('rotate-180');

      const serverHost = window.location.host || '10.10.10.9:8888';
      const cmdText = `curl -sSL http://${serverHost}/install.sh | sudo bash`;
      const updateText = `sudo mkdir -p /opt/sentinel-agent && curl -sSL http://${serverHost}/agent.py -o /tmp/agent.py && sudo mv /tmp/agent.py /opt/sentinel-agent/agent.py && sudo systemctl restart sentinel-agent`;
      
      const elInstall = document.getElementById('installCmdText');
      if (elInstall) elInstall.innerText = cmdText;
      const elUpdate = document.getElementById('updateCmdText');
      if (elUpdate) elUpdate.innerText = updateText;

      switchInstallTab('fresh');
      modal.classList.remove('hidden');
    }

    function closeAddNodeModal() {
      document.getElementById('addNodeModal').classList.add('hidden');
    }

    let pendingDeleteNodeId = null;

    function confirmDeleteNode(nodeId, hostname, ip) {
      pendingDeleteNodeId = nodeId;
      const elHost = document.getElementById('deleteModalHost');
      if (elHost) elHost.innerText = hostname || nodeId;
      const elIp = document.getElementById('deleteModalIp');
      if (elIp) elIp.innerText = ip || 'Unknown IP';
      const elId = document.getElementById('deleteModalId');
      if (elId) elId.innerText = nodeId;
      
      const menu = document.getElementById('nodeDropdownMenu');
      if (menu) menu.classList.add('hidden');
      const chev = document.getElementById('nodeChevron');
      if (chev) chev.classList.remove('rotate-180');

      document.getElementById('deleteNodeModal').classList.remove('hidden');
    }

    function closeDeleteNodeModal() {
      document.getElementById('deleteNodeModal').classList.add('hidden');
      pendingDeleteNodeId = null;
    }

    async function executeDeleteNode() {
      if (!pendingDeleteNodeId) return;
      const btn = document.getElementById('modalConfirmDeleteBtn');
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Menghapus...`;

      try {
        const res = await fetch('/api/v1/nodes/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ server_id: pendingDeleteNodeId })
        });
        const result = await res.json();
        closeDeleteNodeModal();

        if (result.status === 'success') {
          showToast(result.message || 'Node berhasil dihapus!', 'success');
          if (currentActiveNodeId === pendingDeleteNodeId) {
            currentActiveNodeId = '';
          }
          setTimeout(fetchDashboard, 600);
        } else {
          showToast(result.message || 'Gagal menghapus node.', 'error');
        }
      } catch (err) {
        closeDeleteNodeModal();
        showToast(`Error: ${err.message}`, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-trash-can"></i><span>Ya, Hapus Node</span>`;
      }
    }


    function switchInstallTab(tab) {
      const tabFresh = document.getElementById('tabContentFresh');
      const tabUpdate = document.getElementById('tabContentUpdate');
      const btnFresh = document.getElementById('tabBtnFresh');
      const btnUpdate = document.getElementById('tabBtnUpdate');

      if (!tabFresh || !tabUpdate) return;

      if (tab === 'fresh') {
        tabFresh.classList.remove('hidden');
        tabUpdate.classList.add('hidden');
        btnFresh.className = "px-2.5 py-1 rounded bg-blue-600 text-white font-medium transition";
        btnUpdate.className = "px-2.5 py-1 rounded text-slate-400 hover:text-white font-medium transition";
      } else {
        tabFresh.classList.add('hidden');
        tabUpdate.classList.remove('hidden');
        btnFresh.className = "px-2.5 py-1 rounded text-slate-400 hover:text-white font-medium transition";
        btnUpdate.className = "px-2.5 py-1 rounded bg-amber-600 text-white font-medium transition";
      }
    }

    function copyCommand(textOrId, btnId) {
      let text = textOrId;
      const el = document.getElementById(textOrId);
      if (el) text = el.innerText;
      navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById(btnId);
        if (btn) {
          const orig = btn.innerHTML;
          btn.innerHTML = `<i class="fa-solid fa-check text-emerald-400"></i> Copied!`;
          setTimeout(() => { btn.innerHTML = orig; }, 2000);
        }
      }).catch(() => {
        alert('Copied to clipboard: ' + text);
      });
    }

    function copyInstallCmd() {
      copyCommand('installCmdText', 'copyBtnTextFresh');
    }

    function formatSpeed(kbps) {
      const val = parseFloat(kbps) || 0;
      if (val >= 1024) {
        return `${(val / 1024).toFixed(2)} MB/s`;
      }
      return `${val.toFixed(1)} KB/s`;
    }

    function formatNetworkRate(kbps) {
      return formatSpeed(kbps);
    }

    function renderDashboard(data) {
      isDemoMode = data.demo_mode;
      const srv = data.server || {};
      activeServerData = srv;

      // Multi-node cluster selector
      const nodes = (data.nodes || []).slice();
      nodes.sort((a, b) => {
        if (a.id === 'srv-host-node') return -1;
        if (b.id === 'srv-host-node') return 1;
        return (a.hostname || a.id).localeCompare(b.hostname || b.id);
      });
      registeredNodesCache = nodes;
      const activeId = data.active_node_id || (srv ? srv.id : '');

      const nodeCountBadge = document.getElementById('nodeCountBadge');
      if (nodeCountBadge) nodeCountBadge.innerText = `${nodes.length} Node${nodes.length > 1 ? 's' : ''}`;

      const clusterBadge = document.getElementById('clusterTotalBadge');
      if (clusterBadge) clusterBadge.innerText = nodes.length;

      const selectedNodeLabel = document.getElementById('selectedNodeLabel');
      if (selectedNodeLabel) {
        selectedNodeLabel.innerText = `${srv.hostname || 'aidil'} (${srv.ip || '10.10.10.9'})`;
      }

      renderNodeDropdownList(nodes, activeId);
      
      // Update Node Context Banner & Role Intelligence
      const srvMeta = getNodeRoleMeta(srv);

      const bannerHost = document.getElementById('nodeBannerHostname');
      if (bannerHost) bannerHost.innerText = srv.hostname || 'aidil';

      const bannerIp = document.getElementById('nodeBannerIp');
      if (bannerIp) bannerIp.innerText = srv.ip || '10.10.10.9';

      const bannerOs = document.getElementById('nodeBannerOs');
      if (bannerOs) bannerOs.innerText = srv.os || 'Ubuntu 22.04 LTS';

      const bannerArch = document.getElementById('nodeBannerArch');
      if (bannerArch) bannerArch.innerText = srv.kernel ? srv.kernel : 'x86_64 Linux';

      const roleBadge = document.getElementById('nodeBannerRoleBadge');
      if (roleBadge) {
        roleBadge.className = `px-2.5 py-0.5 text-[10px] font-mono font-bold tracking-wider uppercase rounded-md ${srvMeta.badgeClass}`;
        roleBadge.innerText = srvMeta.roleTitle;
      }

      const iconBox = document.getElementById('nodeBannerIconBox');
      const bannerIcon = document.getElementById('nodeBannerIcon');
      if (iconBox && bannerIcon) {
        iconBox.className = `w-12 h-12 rounded-2xl ${srvMeta.iconBg} border flex items-center justify-center font-bold shrink-0 shadow-sm group-hover:scale-105 transition-transform duration-300`;
        bannerIcon.className = `${srvMeta.icon} text-xl`;
      }

      const bannerContainer = document.getElementById('activeNodeBannerContainer');
      const ambientGlow = document.getElementById('activeNodeAmbientGlow');
      if (bannerContainer) {
        if (srvMeta.isMaster) {
          bannerContainer.className = `relative overflow-hidden border-amber-500/40 bg-gradient-to-r from-amber-500/[0.06] via-surface-900/95 to-surface-950/95 backdrop-blur-md rounded-2xl p-4 sm:p-5 shadow-[0_4px_30px_rgba(245,158,11,0.1)] hover:border-amber-400/80 transition-all duration-300 flex flex-col md:flex-row md:items-center justify-between gap-4 group`;
          if (ambientGlow) ambientGlow.className = "absolute -top-12 -left-12 w-48 h-48 bg-amber-500/15 rounded-full blur-3xl pointer-events-none group-hover:bg-amber-500/20 transition-all";
        } else {
          bannerContainer.className = `relative overflow-hidden bg-gradient-to-r from-surface-900/95 via-surface-950/90 to-surface-900/95 backdrop-blur-md border border-slate-800/80 hover:border-cyan-500/40 rounded-2xl p-4 sm:p-5 shadow-lg transition-all duration-300 flex flex-col md:flex-row md:items-center justify-between gap-4 group`;
          if (ambientGlow) ambientGlow.className = "absolute -top-12 -left-12 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none group-hover:bg-cyan-500/15 transition-all";
        }
      }

      const bannerStatus = document.getElementById('nodeBannerStatus');
      if (bannerStatus) {
        const isOnline = (data.nodes || []).find(n => n.id === srv.id)?.is_online ?? true;
        bannerStatus.innerHTML = isOnline ? 
          `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> ONLINE` :
          `<span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span> OFFLINE`;
        bannerStatus.className = isOnline ?
          "px-2.5 py-0.5 text-[10px] font-mono font-bold rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 flex items-center gap-1.5 shadow-[0_0_8px_rgba(16,185,129,0.2)]" :
          "px-2.5 py-0.5 text-[10px] font-mono font-bold rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/40 flex items-center gap-1.5";
      }
      
      const demoBtn = document.getElementById('toggleDemoBtn');
      const demoLabel = document.getElementById('demoBtnLabel');
      if (demoLabel) {
        demoLabel.innerText = isDemoMode ? 'Live Host' : 'Demo Disks';
      }
      if (demoBtn) {
        if (isDemoMode) {
          demoBtn.className = "w-8 h-8 rounded-lg bg-amber-500/15 border border-amber-500/40 text-amber-300 transition-all flex items-center justify-center shadow-sm";
        } else {
          demoBtn.className = "w-8 h-8 rounded-lg bg-surface-800 hover:bg-surface-850 border border-slate-700/80 hover:border-slate-600 text-slate-400 hover:text-slate-200 transition-all flex items-center justify-center shadow-sm";
        }
      }
      
      const score = data.health_score || 100;
      const scoreLabel = data.health_score_label || 'OPTIMAL';
      let scoreColor = 'emerald';
      if (score < 60) scoreColor = 'red';
      else if (score < 85) scoreColor = 'amber';

      const scoreEl = document.getElementById('healthScoreBadge');
      if (scoreEl) {
        scoreEl.className = `inline-flex items-center gap-1 px-2.5 py-0.5 text-[11px] font-mono font-bold rounded-md bg-${scoreColor}-500/15 text-${scoreColor}-400 border border-${scoreColor}-500/30`;
        document.getElementById('healthScoreText').innerText = `${score}/100 ${scoreLabel}`;
      }

      const now = new Date();
      const timeEl = document.getElementById('lastUpdatedTime');
      if (timeEl) timeEl.innerText = now.toLocaleTimeString();

      // Row 1: Vitals (REALTIME)
      const cpu = (srv.cpu_pct !== undefined ? Number(srv.cpu_pct) : 0);
      const iowait = (srv.cpu_iowait !== undefined ? Number(srv.cpu_iowait) : 0);
      document.getElementById('cpuPct').innerText = `${cpu.toFixed(1)}%`;
      document.getElementById('cpuBar').style.width = `${Math.min(cpu, 100)}%`;
      document.getElementById('cpuLoad').innerText = `Load: ${srv.load_1m?.toFixed(2) || '0'}, ${srv.load_5m?.toFixed(2) || '0'}`;
      document.getElementById('cpuIowait').innerText = `${iowait.toFixed(1)}%`;
      document.getElementById('cpuSteal').innerText = `${(srv.cpu_steal || 0).toFixed(1)}%`;
      document.getElementById('cpuCores').innerText = `${srv.cpu_cores || 4} Cores`;

      const ramTotal = srv.ram_total_mb || 1;
      const ramUsed = srv.ram_used_mb || 0;
      const ramPct = Math.round((ramUsed / ramTotal) * 100);
      document.getElementById('ramPct').innerText = `${ramPct}%`;
      document.getElementById('ramBar').style.width = `${Math.min(ramPct, 100)}%`;
      document.getElementById('ramDetail').innerText = `${(ramUsed/1024).toFixed(1)} / ${(ramTotal/1024).toFixed(1)} GB`;
      document.getElementById('ramCached').innerText = `${Math.round(srv.ram_cached_mb || 0)}M`;
      document.getElementById('ramBuffers').innerText = `${Math.round(srv.ram_buffers_mb || 0)}M`;
      document.getElementById('ramSwap').innerText = `${Math.round(srv.swap_used_pct || 0)}%`;

      // Realtime Network
      const rxKbps = srv.net_rx_kbps || 0;
      const txKbps = srv.net_tx_kbps || 0;
      document.getElementById('netRx').innerText = formatSpeed(rxKbps);
      document.getElementById('netTx').innerText = formatSpeed(txKbps);
      document.getElementById('netErrors').innerText = (srv.net_rx_errors || 0) + (srv.net_tx_errors || 0);
      document.getElementById('netDrops').innerText = (srv.net_rx_drops || 0) + (srv.net_tx_drops || 0);
      document.getElementById('tcpSockets').innerText = `${srv.tcp_established || 0} Est`;

      // Uptime
      const uptimeSec = srv.uptime_seconds || 0;
      const days = Math.floor(uptimeSec / 86400);
      const hours = Math.floor((uptimeSec % 86400) / 3600);
      const mins = Math.floor((uptimeSec % 3600) / 60);
      const uptimeHuman = srv.uptime_human || (days > 0 ? `${days}d ${hours}h ${mins}m` : (hours > 0 ? `${hours}h ${mins}m` : `${mins}m`));
      document.getElementById('uptimeText').innerText = `Uptime: ${uptimeHuman}`;
      if (document.getElementById('headerUptimeVal')) {
        document.getElementById('headerUptimeVal').innerText = uptimeHuman;
      }

      // CPU Temperature
      const tempC = srv.cpu_temp_c !== undefined ? Number(srv.cpu_temp_c) : 0;
      const tempStatus = srv.cpu_temp_status || 'Normal';
      const tempSource = srv.cpu_temp_source || 'Hardware Sensor';
      const tempBadge = document.getElementById('cpuTempBadge');
      const tempText = document.getElementById('cpuTempText');
      const tempSourceEl = document.getElementById('cpuTempSource');
      const chartTempEl = document.getElementById('chartCpuTemp');

      if (tempText) tempText.innerText = `${tempC.toFixed(1)}°C`;
      if (chartTempEl) chartTempEl.innerText = `${tempC.toFixed(1)}°C`;
      if (tempSourceEl) {
        tempSourceEl.innerText = tempSource.length > 15 ? tempSource.substring(0, 15) + '...' : tempSource;
        tempSourceEl.title = `Sensor: ${tempSource} (${tempStatus})`;
      }

      if (tempBadge) {
        if (tempC >= 80) {
          tempBadge.className = 'flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-mono font-bold animate-pulse';
        } else if (tempC >= 70) {
          tempBadge.className = 'flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-mono font-bold';
        } else {
          tempBadge.className = 'flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono font-bold';
        }
      }

      // Alerts Counter
      const alerts = data.alerts || [];
      const crits = alerts.filter(a => a.level === 'CRITICAL').length;
      const warns = alerts.filter(a => a.level === 'WARNING').length;
      document.getElementById('critAlertCount').innerText = crits;
      document.getElementById('warnAlertCount').innerText = warns;
      document.getElementById('systemStateBadge').innerText = crits > 0 ? 'CRITICAL' : (warns > 0 ? 'WARNING' : 'HEALTHY');
      document.getElementById('systemStateBadge').className = crits > 0 ? 'text-red-400 font-bold' : (warns > 0 ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold');

      // Push into Rolling Waveform Charts
      if (cpuChart && netChart) {
        cpuHistory.shift();
        cpuHistory.push(cpu);
        iowaitHistory.shift();
        iowaitHistory.push(iowait);
        cpuChart.update();

        rxHistory.shift();
        rxHistory.push(Math.round(rxKbps));
        txHistory.shift();
        txHistory.push(Math.round(txKbps));
        netChart.update();
      }

      // Render Multi-Disks
      renderDisks(data.disks || []);

      // Render Disk I/O Performance Table
      renderDiskIO(data.disks || []);

      // Render Top Processes & Web Probes
      renderTopProcesses(data.top_processes || []);
      renderWebProbes(data.web_probes || []);
      renderNetworkQuality(data.network_quality || {});

      // Docker Containers & Services
      renderContainers(data.containers || []);
      renderServices(data.services || []);

      // Open Ports Security Audit
      renderOpenPorts(data.open_ports || []);

      // Logs
      allLogsCache = data.system_logs || [];
      filterLogs();

      // VMs
      renderVMs(data.vms || []);
    }

    function renderDisks(disks) {
      const container = document.getElementById('disksGrid');
      document.getElementById('diskTotalBadge').innerText = `${disks.length} Disks Monitored`;

      if (!disks.length) {
        container.innerHTML = `<div class="col-span-full py-8 text-center text-slate-500">No storage disks detected.</div>`;
        return;
      }

      container.innerHTML = disks.map((d) => {
        let statusColor = "emerald";
        let statusBadge = "HEALTHY";
        let statusIcon = "fa-check-circle";

        if (d.health_status === "CRITICAL") {
          statusColor = "red";
          statusBadge = "CRITICAL";
          statusIcon = "fa-triangle-exclamation";
        } else if (d.health_status === "WARNING") {
          statusColor = "amber";
          statusBadge = "WARNING";
          statusIcon = "fa-circle-exclamation";
        }

        let tempColor = "text-slate-300";
        if (d.temperature_c >= 60) tempColor = "text-red-400 font-bold";
        else if (d.temperature_c >= 50) tempColor = "text-amber-400 font-semibold";

        const partitionsHtml = (d.partitions || []).map(p => `
          <div class="mt-2 text-[11px] bg-surface-950/80 p-2 rounded-xl border border-slate-800/80">
            <div class="flex justify-between text-slate-400 font-mono">
              <span class="truncate max-w-[120px] font-semibold text-slate-200">${p.mount}</span>
              <span class="text-slate-300">${p.used_gb} / ${p.size_gb} GB (${p.pct}%)</span>
            </div>
            <div class="w-full bg-slate-900 rounded-full h-1.5 mt-1 overflow-hidden border border-slate-800/60 p-[1px]">
              <div class="bg-gradient-to-r from-blue-500 to-cyan-400 h-full rounded-full transition-all duration-300" style="width: ${p.pct}%"></div>
            </div>
          </div>
        `).join('');

        const partsTotal = (d.partitions || []).reduce((acc, p) => acc + (Number(p.size_gb) || 0), 0);
        const capVal = Math.max(Number(d.capacity_gb) || 0, partsTotal);
        const capFormatted = capVal >= 1000 ? `${(capVal / 1000).toFixed(1)} TB (${Math.round(capVal)} GB)` : `${Math.round(capVal)} GB`;

        return `
          <div class="bg-gradient-to-b from-surface-900/90 to-surface-950/95 border border-slate-800/90 hover:border-cyan-500/40 hover:shadow-[0_0_20px_rgba(6,182,212,0.12)] transition-all duration-300 rounded-2xl p-4 flex flex-col justify-between shadow-sm relative overflow-hidden group">
            <div>
              <div class="flex items-center justify-between gap-1 mb-2.5">
                <span class="text-xs font-mono font-bold text-cyan-300 bg-surface-950 border border-slate-800 px-2 py-0.5 rounded-lg shadow-sm">
                  ${d.device}
                </span>
                <span class="text-[10px] font-semibold uppercase px-2.5 py-0.5 rounded-full bg-${statusColor}-500/15 border border-${statusColor}-500/40 text-${statusColor}-400 flex items-center gap-1 shadow-sm">
                  <i class="fa-solid ${statusIcon} text-[9px]"></i> ${statusBadge}
                </span>
              </div>

              <h4 class="text-xs font-bold text-white group-hover:text-cyan-300 transition truncate" title="${d.model}">
                ${d.model}
              </h4>
              <div class="text-[10px] text-slate-400 font-mono mb-3">
                ${d.disk_type} • SN: ${d.serial || '-'}
              </div>

              <div class="grid grid-cols-2 gap-2 bg-surface-950/80 p-2.5 rounded-xl border border-slate-800/80 text-xs mb-3">
                <div>
                  <div class="text-[10px] text-slate-500 uppercase font-semibold">Life Health</div>
                  <div class="font-mono text-sm font-black text-${statusColor}-400">${d.health_pct}%</div>
                </div>
                <div>
                  <div class="text-[10px] text-slate-500 uppercase font-semibold">Temperature</div>
                  <div class="font-mono text-sm ${tempColor} font-bold">${d.temperature_c}°C</div>
                </div>
                <div>
                  <div class="text-[10px] text-slate-500 uppercase font-semibold">Realloc / Err</div>
                  <div class="font-mono text-xs ${d.reallocated_sectors > 0 ? 'text-amber-400 font-bold' : 'text-slate-300'}">
                    ${d.reallocated_sectors || 0}
                  </div>
                </div>
                <div>
                  <div class="text-[10px] text-slate-500 uppercase font-semibold">Power Hours</div>
                  <div class="font-mono text-xs text-slate-300">${d.power_on_hours || 0}h</div>
                </div>
              </div>

              <div class="space-y-1 text-[11px] text-slate-400 pb-1">
                <div class="flex justify-between">
                  <span>SMART Self-Test:</span>
                  <span class="font-mono font-semibold ${d.smart_passed ? 'text-emerald-400' : 'text-rose-400'}">
                    ${d.smart_passed ? 'PASSED' : 'FAILED'}
                  </span>
                </div>
                <div class="flex justify-between">
                  <span>Pending / Media Err:</span>
                  <span class="font-mono font-semibold ${(d.pending_sectors > 0 || d.media_errors > 0) ? 'text-rose-400' : 'text-slate-300'}">
                    ${(d.pending_sectors || 0) + (d.media_errors || 0)}
                  </span>
                </div>
              </div>
            </div>

            <div class="mt-2 pt-2 border-t border-slate-800/80">
              <div class="text-[10px] uppercase font-bold text-slate-400">Capacity (${capFormatted})</div>
              ${partitionsHtml || '<div class="text-[11px] text-slate-500 italic mt-1 font-sans">RAW / Unmounted</div>'}
            </div>
          </div>
        `;
      }).join('');
    }

    function renderDiskIO(disks) {
      const tbody = document.getElementById('diskIOTableBody');
      if (!disks.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="py-4 text-center text-slate-500">No storage I/O metrics available.</td></tr>`;
        return;
      }

      tbody.innerHTML = disks.map(d => {
        let latBadge = "text-emerald-400";
        if (d.latency_ms > 20) latBadge = "text-red-400 font-bold";
        else if (d.latency_ms > 5) latBadge = "text-amber-400 font-semibold";

        return `
          <tr class="hover:bg-surface-850/60 transition-all">
            <td class="py-2.5 font-bold text-white">${d.device}</td>
            <td class="py-2.5 text-slate-300 truncate max-w-[180px]">${d.model}</td>
            <td class="py-2.5 text-emerald-400 font-bold">${(d.read_mbps || 0).toFixed(1)} MB/s</td>
            <td class="py-2.5 text-blue-400 font-bold">${(d.write_mbps || 0).toFixed(1)} MB/s</td>
            <td class="py-2.5 text-slate-200">${d.iops || 0} op/s</td>
            <td class="py-2.5 ${latBadge}">${(d.latency_ms || 0.8).toFixed(1)} ms</td>
            <td class="py-2.5">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold ${d.latency_ms > 20 ? 'bg-red-500/10 text-red-400 border border-red-500/30' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'}">
                ${d.latency_ms > 20 ? 'HEAVY_LOAD' : 'OPTIMAL'}
              </span>
            </td>
          </tr>
        `;
      }).join('');
    }

    function renderTopProcesses(procs) {
      const tbody = document.getElementById('topProcsTableBody');
      if (!procs.length) {
        tbody.innerHTML = `<tr><td colspan="5" class="py-4 text-center text-slate-500">No active process data available.</td></tr>`;
        return;
      }

      tbody.innerHTML = procs.map(p => `
        <tr class="hover:bg-surface-850/60 transition-all">
          <td class="py-2 text-slate-400">${p.pid}</td>
          <td class="py-2 font-bold text-slate-200 truncate max-w-[140px]">${p.name}</td>
          <td class="py-2 text-slate-400">${p.user}</td>
          <td class="py-2 text-blue-400 font-bold">${p.cpu_pct}%</td>
          <td class="py-2 text-purple-400 font-bold">${p.mem_mb} MB</td>
        </tr>
      `).join('');
    }

    function renderWebProbes(probes) {
      const list = document.getElementById('webProbesList');
      if (!list) return;
      if (!probes.length) {
        list.innerHTML = `<div class="p-6 text-center text-slate-500 text-xs">No web endpoints monitored yet. Click '+ Add URL' above to add Immich, Proxmox, or custom services.</div>`;
        return;
      }

      list.innerHTML = probes.map(p => {
        const isOk = (p.status_code >= 200 && p.status_code < 400);
        const statusColor = isOk ? 'emerald' : 'rose';
        const sslText = p.ssl_days > 0 ? `${p.ssl_days}d SSL` : (p.url.startsWith('https') ? 'SSL Active' : 'HTTP Internal');
        const sslColor = (p.ssl_days < 14 && p.ssl_days > 0) ? 'text-amber-400' : 'text-slate-400';

        return `
          <div class="p-3 rounded-xl bg-surface-950/80 border border-slate-800/80 hover:border-cyan-500/40 hover:bg-surface-900/80 transition-all duration-300 text-xs flex items-center justify-between gap-3 group">
            <div class="flex items-center gap-3 min-w-0">
              <span class="w-2.5 h-2.5 rounded-full bg-${statusColor}-400 shrink-0 ${isOk ? '' : 'animate-ping'}"></span>
              <div class="min-w-0">
                <div class="font-bold text-slate-200 flex items-center gap-2">
                  <span class="truncate group-hover:text-cyan-300 transition">${p.name}</span>
                  <a href="${p.url}" target="_blank" rel="noopener noreferrer" title="Open ${p.url}" class="text-slate-500 hover:text-cyan-400 transition text-[11px]">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i>
                  </a>
                </div>
                <div class="text-[11px] text-slate-400 font-mono truncate max-w-[240px]">${p.url}</div>
              </div>
            </div>
            
            <div class="flex items-center gap-3 shrink-0">
              <div class="text-right font-mono">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-${statusColor}-500/15 text-${statusColor}-400 border border-${statusColor}-500/30">
                  ${p.status_code ? 'HTTP ' + p.status_code : 'CHECKING'}
                </span>
                <div class="text-[10px] text-slate-400 mt-0.5">${p.latency_ms || 0} ms • <span class="${sslColor}">${sslText}</span></div>
              </div>
              <button onclick="deleteProbe(${p.id}, '${p.name}')" title="Delete endpoint" class="w-7 h-7 rounded-lg bg-surface-950 hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 flex items-center justify-center transition border border-slate-800 hover:border-rose-500/30">
                <i class="fa-regular fa-trash-can text-xs"></i>
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    function renderContainers(containers) {
      const list = document.getElementById('containersList');
      document.getElementById('dockerSummary').innerText = `${containers.length} Containers`;

      if (!containers.length) {
        list.innerHTML = `<div class="p-4 text-center text-slate-500 text-xs">No active Docker containers discovered on host.</div>`;
        return;
      }

      list.innerHTML = containers.map(c => {
        const isRunning = (c.state === 'running' || c.status.toLowerCase().includes('up'));
        const badgeColor = isRunning ? 'emerald' : 'red';
        const badgeText = isRunning ? 'RUNNING' : 'STOPPED';

        return `
          <div class="p-3 rounded-xl bg-surface-950/80 border border-slate-800/80 hover:border-cyan-500/40 hover:bg-surface-900/80 transition-all duration-300 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 group">
            <div class="flex items-center gap-3">
              <span class="w-8 h-8 rounded-xl bg-blue-500/15 border border-blue-500/30 text-blue-400 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
                <i class="fa-brands fa-docker text-sm"></i>
              </span>
              <div>
                <div class="font-bold text-white group-hover:text-cyan-300 transition font-mono">${c.name}</div>
                <div class="text-[10px] text-slate-400 font-mono truncate max-w-[170px] sm:max-w-[200px]">${c.image}</div>
              </div>
            </div>
            <div class="flex items-center justify-between sm:justify-end gap-2.5">
              <div class="text-right">
                <span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-${badgeColor}-500/15 text-${badgeColor}-400 border border-${badgeColor}-500/30">
                  ${badgeText}
                </span>
                <div class="text-[9px] text-slate-500 font-mono mt-0.5">${c.status}</div>
              </div>
              <div class="flex items-center gap-1.5 ml-1">
                ${isRunning ? `
                  <button onclick="confirmAction('restart_container', '${c.name}', 'Restart Docker Container', 'Restarts container ${c.name} on the active node.')" 
                          title="Restart container ${c.name}" 
                          class="px-2.5 py-1 text-[10px] font-semibold bg-blue-500/15 hover:bg-blue-500/25 text-blue-400 border border-blue-500/30 rounded-lg flex items-center gap-1 transition">
                    <i class="fa-solid fa-arrows-rotate text-[9px]"></i> <span>Restart</span>
                  </button>
                  <button onclick="confirmAction('stop_container', '${c.name}', 'Stop Docker Container', 'Stops running container ${c.name}.')" 
                          title="Stop container ${c.name}" 
                          class="px-2.5 py-1 text-[10px] font-semibold bg-rose-500/15 hover:bg-rose-500/25 text-rose-400 border border-rose-500/30 rounded-lg flex items-center gap-1 transition">
                    <i class="fa-solid fa-stop text-[9px]"></i> <span>Stop</span>
                  </button>
                ` : `
                  <button onclick="confirmAction('start_container', '${c.name}', 'Start Docker Container', 'Starts container ${c.name}.')" 
                          title="Start container ${c.name}" 
                          class="px-2.5 py-1 text-[10px] font-semibold bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 border border-emerald-500/30 rounded-lg flex items-center gap-1 transition">
                    <i class="fa-solid fa-play text-[9px]"></i> <span>Start</span>
                  </button>
                `}
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function setLogCategory(cat) {
      currentLogCategory = cat;
      ['ALL', 'SECURITY', 'SERVICE'].forEach(c => {
        const btn = document.getElementById(`btnCat${c}`);
        if (c === cat) {
          btn.className = "px-2.5 py-1 rounded-md text-white bg-blue-600 font-medium";
        } else {
          btn.className = "px-2.5 py-1 rounded-md text-slate-400 hover:text-white";
        }
      });
      filterLogs();
    }

    function filterLogs() {
      const search = (document.getElementById('logSearchInput')?.value || '').toLowerCase();
      const container = document.getElementById('logsStreamList');
      
      let filtered = allLogsCache;
      if (currentLogCategory !== 'ALL') {
        filtered = filtered.filter(l => l.type === currentLogCategory);
      }
      if (search) {
        filtered = filtered.filter(l => 
          (l.message && l.message.toLowerCase().includes(search)) ||
          (l.ip && l.ip.toLowerCase().includes(search)) ||
          (l.user && l.user.toLowerCase().includes(search)) ||
          (l.source && l.source.toLowerCase().includes(search))
        );
      }

      document.getElementById('logsCountBadge').innerText = `${filtered.length} Events`;

      if (!filtered.length) {
        container.innerHTML = `<div class="p-6 text-center text-slate-500 text-xs font-sans">No log events matching current criteria.</div>`;
        return;
      }

      container.innerHTML = filtered.map(log => {
        let badgeColor = "slate";
        let icon = "fa-circle-info";

        if (log.badge === "AUTH_FAILED" || log.badge === "BRUTE_FORCE" || log.badge === "INVALID_USER" || log.level === "CRITICAL") {
          badgeColor = "red";
          icon = "fa-shield-halved";
        } else if (log.badge === "AUTH_SUCCESS" || log.level === "SUCCESS") {
          badgeColor = "emerald";
          icon = "fa-key";
        } else if (log.badge === "SUDO_EXEC" || log.level === "WARNING") {
          badgeColor = "amber";
          icon = "fa-terminal";
        } else if (log.type === "SERVICE") {
          badgeColor = "purple";
          icon = "fa-triangle-exclamation";
        }

        return `
          <div class="p-2.5 rounded-xl bg-surface-850 border border-slate-800/80 hover:border-slate-700 transition-all text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div class="flex items-start sm:items-center gap-3">
              <span class="w-6 h-6 rounded-lg bg-${badgeColor}-500/10 border border-${badgeColor}-500/30 text-${badgeColor}-400 flex items-center justify-center flex-shrink-0 mt-0.5 sm:mt-0">
                <i class="fa-solid ${icon} text-[10px]"></i>
              </span>
              <div>
                <div class="flex flex-wrap items-center gap-2 mb-0.5">
                  <span class="text-[10px] font-bold px-1.5 py-0.2 rounded bg-surface-900 border border-slate-800 text-${badgeColor}-400">
                    ${log.badge || 'LOG'}
                  </span>
                  <span class="text-[11px] font-bold text-slate-300 font-mono">${log.source || 'sys'}</span>
                  ${log.ip && log.ip !== '-' ? `<span class="text-[10px] bg-slate-800/80 text-blue-400 px-1.5 py-0.2 rounded font-mono">IP: ${log.ip}</span>` : ''}
                  ${log.user && log.user !== '-' ? `<span class="text-[10px] bg-slate-800/80 text-purple-400 px-1.5 py-0.2 rounded font-mono">User: ${log.user}</span>` : ''}
                </div>
                <div class="text-[11px] text-slate-300 font-sans break-all">${log.message}</div>
              </div>
            </div>
            <div class="text-[10px] text-slate-500 font-mono whitespace-nowrap self-end sm:self-center pl-2">
              ${log.timestamp}
            </div>
          </div>
        `;
      }).join('');
    }

    function renderServices(services) {
      const list = document.getElementById('servicesList');
      document.getElementById('servicesSummary').innerText = `${services.length} Total Units`;

      if (!services.length) {
        list.innerHTML = `<div class="p-4 text-center text-slate-500 text-xs">No system services discovered.</div>`;
        return;
      }

      list.innerHTML = services.map(s => {
        const isRunning = (s.status === 'active' || s.substate === 'running');
        const isFailed = (s.status === 'failed' || s.substate === 'failed');
        
        let badgeColor = isRunning ? 'emerald' : (isFailed ? 'red' : 'slate');
        let badgeText = isRunning ? 'RUNNING' : (isFailed ? 'FAILED' : 'STOPPED');

        return `
          <div class="flex items-center justify-between p-3 rounded-xl bg-surface-950/80 border border-slate-800/80 hover:border-emerald-500/40 hover:bg-surface-900/80 transition-all duration-300 text-xs group">
            <div class="flex items-center gap-3">
              <input type="checkbox" ${s.is_monitored ? 'checked' : ''} 
                     onchange="toggleServiceMonitoring('${s.id}', this.checked)"
                     class="w-4 h-4 rounded bg-slate-900 border-slate-700 text-blue-500 focus:ring-0 cursor-pointer">
              <div>
                <div class="font-bold text-white group-hover:text-emerald-300 transition font-mono">${s.name}</div>
                <div class="text-[10px] text-slate-400">${s.unit}</div>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-${badgeColor}-500/15 text-${badgeColor}-400 border border-${badgeColor}-500/30">
                ${badgeText}
              </span>
              <button onclick="confirmAction('restart_service', '${s.unit || s.name}', 'Restart Systemd Service', 'Restarts systemd unit ${s.unit || s.name} on the active node.')" 
                      title="Restart service ${s.name}" 
                      class="px-2.5 py-1 text-[10px] font-semibold bg-surface-950 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-slate-700 rounded-lg flex items-center gap-1 transition">
                <i class="fa-solid fa-arrows-rotate text-[9px]"></i> <span>Restart</span>
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    let currentVmsCache = [];
    let activeModalVm = null;
    let activeServerData = null;

    function renderVMs(vms) {
      currentVmsCache = vms || [];
      const list = document.getElementById('vmsList');
      document.getElementById('vmsSummary').innerText = `${vms.length} Hypervisor Guests`;

      if (!vms.length) {
        list.innerHTML = `
          <div class="p-6 text-center text-slate-500 text-xs col-span-full">
            <i class="fa-solid fa-circle-info mb-1 text-slate-400 text-sm"></i><br>
            Belum ada Virtual Machine (QEMU) atau LXC Container yang terdaftar di node ini.
            <div class="text-[11px] text-slate-600 mt-1">Jika ini adalah node Proxmox VE, pastikan VM atau Container sudah dibuat di web GUI Proxmox.</div>
          </div>
        `;
        return;
      }

      list.innerHTML = vms.map(v => {
        const isRunning = v.status === 'running';
        const typeBadge = v.vm_type === 'lxc' ? 'LXC' : 'QEMU';
        
        return `
          <div onclick="openVmModal(${v.vmid})" class="p-4 rounded-2xl bg-gradient-to-b from-surface-900/90 to-surface-950/95 border border-slate-800/90 hover:border-cyan-500/50 hover:shadow-[0_0_20px_rgba(6,182,212,0.15)] transition-all duration-300 text-xs cursor-pointer group relative overflow-hidden">
            <div class="flex items-center justify-between mb-2.5">
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-lg bg-blue-500/15 text-blue-300 font-mono text-[11px] font-bold border border-blue-500/30">
                  #${v.vmid}
                </span>
                <span class="font-black text-white group-hover:text-cyan-300 transition text-[13px] tracking-tight">${v.name}</span>
                <span class="text-[9px] uppercase px-1.5 py-0.5 bg-slate-800/80 text-slate-400 rounded-md font-mono border border-slate-700/50">
                  ${typeBadge}
                </span>
              </div>
              <span class="px-2.5 py-0.5 text-[10px] font-bold rounded-full ${isRunning ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.2)]' : 'bg-rose-500/15 text-rose-400 border border-rose-500/40'}">
                ${v.status.toUpperCase()}
              </span>
            </div>

            <div class="grid grid-cols-2 gap-2 text-[11px] text-slate-400 font-mono my-2.5 bg-surface-950/80 p-2.5 rounded-xl border border-slate-800/80">
              <div class="flex items-center gap-1.5">
                <i class="fa-solid fa-microchip text-indigo-400 text-[10px]"></i>
                <span>CPU: <b class="text-white">${v.cpu_pct}%</b> <span class="text-[9px] text-slate-500">(${v.cores || 1}c)</span></span>
              </div>
              <div class="flex items-center gap-1.5">
                <i class="fa-solid fa-memory text-purple-400 text-[10px]"></i>
                <span>RAM: <b class="text-white">${Math.round(v.ram_used_mb || 0)} MB</b></span>
              </div>
              ${v.ip_address ? `
              <div class="col-span-2 flex items-center gap-1.5 text-cyan-400 pt-1 border-t border-slate-800/50">
                <i class="fa-solid fa-network-wired text-[10px]"></i>
                <span>IP: <b class="font-mono text-cyan-300">${v.ip_address}</b></span>
              </div>` : ''}
            </div>

            <div class="flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-slate-800/80">
              <span class="flex items-center gap-1.5">
                <i class="fa-solid fa-server text-cyan-400 text-[9px]"></i> Induk: <b class="text-slate-300">${v.node_name || 'pve'}</b>
              </span>
              <div class="flex items-center gap-2">
                <button onclick="event.stopPropagation(); openTerminalModal('srv-pve', 'vm', '${v.vmid}')" title="Buka Interactive Shell VM #${v.vmid}" class="px-2.5 py-1 rounded-lg bg-surface-950 hover:bg-cyan-500/20 text-cyan-400 border border-slate-800 hover:border-cyan-500/40 text-[10px] font-mono flex items-center gap-1 transition">
                  <i class="fa-solid fa-terminal text-[8px]"></i> Shell
                </button>
                <span class="text-blue-400 font-semibold group-hover:translate-x-0.5 transition-transform flex items-center gap-1">
                  Detail <i class="fa-solid fa-chevron-right text-[8px]"></i>
                </span>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function openVmModal(vmid) {
      const vm = currentVmsCache.find(v => v.vmid === vmid);
      if (!vm) return;
      activeModalVm = vm;

      document.getElementById('vmDetailModal').classList.remove('hidden');
      document.getElementById('vmModalTitle').innerText = `VM #${vm.vmid} - ${vm.name}`;
      
      const isLxc = (vm.vm_type === 'lxc');
      const isRunning = (vm.status === 'running');
      
      // Icon & Type
      document.getElementById('vmModalIcon').className = isLxc ? "fa-solid fa-box text-lg" : "fa-solid fa-cube text-lg";
      const typeBadge = document.getElementById('vmModalTypeBadge');
      typeBadge.innerText = isLxc ? "LXC CONTAINER" : "QEMU KVM";
      
      // Status Badge
      const stBadge = document.getElementById('vmModalStatusBadge');
      stBadge.innerText = vm.status.toUpperCase();
      stBadge.className = `px-2 py-0.5 text-[10px] font-mono font-bold rounded ${isRunning ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-red-500/10 text-red-400 border border-red-500/30'}`;

      // Node text
      const nodeIp = (activeServerData && activeServerData.ip) ? activeServerData.ip : '10.10.10.2';
      document.getElementById('vmModalSub').innerText = `Hypervisor Node: ${vm.node_name || 'pve'} (${nodeIp})`;

      // Stats
      document.getElementById('vmStatCpu').innerText = `${vm.cpu_pct}%`;
      document.getElementById('vmStatCores').innerText = `${vm.cores || 1} Cores Allocated`;
      document.getElementById('vmStatRam').innerText = `${Math.round(vm.ram_used_mb || 0)} MB`;
      document.getElementById('vmStatRamTotal').innerText = `${Math.round(vm.ram_total_mb || 2048)} MB Total`;
      document.getElementById('vmStatDisk').innerText = `${Math.round(vm.disk_total_gb || 32)} GB`;
      
      const ip = vm.ip_address || '';
      document.getElementById('vmStatIp').innerText = ip || 'Not Detected';
      document.getElementById('vmStatIpSub').innerText = ip ? 'Live Guest IP' : 'Agent not running';

      // Full details
      document.getElementById('vmDetailId').innerText = vm.vmid;
      document.getElementById('vmDetailName').innerText = vm.name;
      document.getElementById('vmDetailType').innerText = isLxc ? "LXC (Linux Container)" : "QEMU / KVM Virtual Machine";
      document.getElementById('vmDetailNode').innerText = `${vm.node_name || 'pve'} (${nodeIp})`;
      
      let upSec = vm.uptime_seconds || 0;
      let upStr = "Offline";
      if (isRunning && upSec > 0) {
        let d = Math.floor(upSec / 86400);
        let h = Math.floor((upSec % 86400) / 3600);
        let m = Math.floor((upSec % 3600) / 60);
        upStr = `${d}d ${h}h ${m}m`;
      }
      document.getElementById('vmDetailUptime').innerText = upStr;

      // NoVNC URLs
      const consoleType = isLxc ? "lxc&xtermjs=1" : "kvm&novnc=1";
      const novncUrl = `https://${nodeIp}:8006/?console=${consoleType}&vmid=${vm.vmid}&node=${vm.node_name || 'pve'}`;
      document.getElementById('vmNoVncBtn').href = novncUrl;
      document.getElementById('vmLaunchNoVncDirect').href = novncUrl;
      document.getElementById('vmDetailNoVncLink').href = novncUrl;
      document.getElementById('vmDetailNoVncLink').innerText = novncUrl;

      // SSH Command
      document.getElementById('vmSshCmd').innerText = `ssh root@${ip || nodeIp}`;

      // Reset Terminal
      document.getElementById('vmTerminalOutput').innerHTML = `<span class="text-slate-500">// Terminal session ready for ${vm.name} (VM #${vm.vmid}) on ${nodeIp}.\n// Jalankan perintah di bawah atau gunakan tombol preset.</span>`;
      
      // Switch to default tab
      switchVmTab('overview');
    }

    function closeVmModal() {
      document.getElementById('vmDetailModal').classList.add('hidden');
      activeModalVm = null;
    }

    function switchVmTab(tab) {
      if (tab === 'overview') {
        document.getElementById('vmTabOverview').classList.remove('hidden');
        document.getElementById('vmTabShell').classList.add('hidden');
        document.getElementById('vmTabBtnOverview').className = 'px-4 py-1.5 font-bold rounded-lg bg-blue-600 text-white transition flex items-center gap-2';
        document.getElementById('vmTabBtnShell').className = 'px-4 py-1.5 font-bold rounded-lg text-slate-400 hover:text-white transition flex items-center gap-2';
      } else {
        document.getElementById('vmTabOverview').classList.add('hidden');
        document.getElementById('vmTabShell').classList.remove('hidden');
        document.getElementById('vmTabBtnOverview').className = 'px-4 py-1.5 font-bold rounded-lg text-slate-400 hover:text-white transition flex items-center gap-2';
        document.getElementById('vmTabBtnShell').className = 'px-4 py-1.5 font-bold rounded-lg bg-blue-600 text-white transition flex items-center gap-2';
      }
    }

    function setVmCommand(cmd) {
      document.getElementById('vmCmdInput').value = cmd;
      executeVmCommand();
    }

    async function executeVmCommand() {
      if (!activeModalVm) return;
      const cmd = document.getElementById('vmCmdInput').value.trim();
      if (!cmd) return;

      const outputBox = document.getElementById('vmTerminalOutput');
      const runBtn = document.getElementById('vmCmdRunBtn');
      
      outputBox.innerHTML += `\n<span class="text-cyan-400 font-bold">root@${activeModalVm.name}:~#</span> <span class="text-white">${escapeHtml(cmd)}</span>\n<span class="text-slate-500 font-sans italic" id="vmPendingWait"> Menjalankan perintah di VM...</span>`;
      outputBox.scrollTop = outputBox.scrollHeight;
      runBtn.disabled = true;

      try {
        const res = await fetch('/api/v1/action/execute', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            server_id: selectedServerId || 'srv-pve',
            action: 'exec_vm_cmd',
            target: String(activeModalVm.vmid),
            cmd: cmd
          })
        });
        const data = await res.json();
        
        if (data.action_id) {
          let attempts = 0;
          const poll = setInterval(async () => {
            attempts++;
            try {
              const sRes = await fetch(`/api/v1/action/status?action_id=${data.action_id}`);
              const sData = await sRes.json();
              if (sData.status === 'SUCCESS' || sData.status === 'FAILED' || attempts > 15) {
                clearInterval(poll);
                runBtn.disabled = false;
                const resultText = sData.result_msg || (sData.status === 'SUCCESS' ? 'Command completed.' : 'Execution timeout.');
                const colorClass = sData.status === 'SUCCESS' ? 'text-emerald-300' : 'text-rose-400';
                const waitEl = document.getElementById('vmPendingWait');
                if (waitEl) waitEl.outerHTML = `<span class="${colorClass}">${escapeHtml(resultText)}</span>\n`;
                outputBox.scrollTop = outputBox.scrollHeight;
              }
            } catch (err) {
              clearInterval(poll);
              runBtn.disabled = false;
            }
          }, 1000);
        } else {
          runBtn.disabled = false;
          outputBox.innerHTML += `\n<span class="text-rose-400">${data.message || 'Error executing command.'}</span>\n`;
        }
      } catch (err) {
        runBtn.disabled = false;
        outputBox.innerHTML += `\n<span class="text-rose-400">Request error: ${err.message}</span>\n`;
      }
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    async function vmAction(type) {
      if (!activeModalVm) return;
      const vmid = activeModalVm.vmid;
      const name = activeModalVm.name;
      
      const actionMap = {
        'start': 'start_vm',
        'reboot': 'reboot_vm',
        'shutdown': 'shutdown_vm',
        'stop': 'stop_vm'
      };
      
      const act = actionMap[type];
      if (!act) return;

      confirmAction(act, String(vmid), `${type.toUpperCase()} VM #${vmid}`, `Kirim instruksi ${type.toUpperCase()} ke VM '${name}' di Proxmox VE.`);
    }

    async function toggleDemoMode() {
      try {
        await fetch('/api/v1/demo/toggle', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({enabled: !isDemoMode})
        });
        fetchDashboard();
      } catch (err) {
        console.error("Toggle error:", err);
      }
    }

    async function toggleServiceMonitoring(serviceId, isMonitored) {
      try {
        await fetch('/api/v1/services/toggle', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({service_id: serviceId, is_monitored: isMonitored})
        });
      } catch (err) {
        console.error("Service toggle error:", err);
      }
    }

    // ==========================================
    //  HOMELAB POWER TOOLS & ORCHESTRATOR
    // ==========================================
    let currentPowerTab = 'vms';
    let powerVmsCache = [];
    let wolDevicesCache = [];

    function openPowerToolsModal() {
      const modal = document.getElementById('powerToolsModal');
      if (modal) modal.classList.remove('hidden');
      switchPowerTab(currentPowerTab || 'vms');
      loadPowerVms();
      loadWolDevices();
    }

    function closePowerToolsModal() {
      const modal = document.getElementById('powerToolsModal');
      if (modal) modal.classList.add('hidden');
    }

    function switchPowerTab(tab) {
      currentPowerTab = tab;
      const vmsBtn = document.getElementById('tabBtnPowerVms');
      const wolBtn = document.getElementById('tabBtnPowerWol');
      const vmsContent = document.getElementById('tabContentPowerVms');
      const wolContent = document.getElementById('tabContentPowerWol');

      if (tab === 'vms') {
        if (vmsBtn) vmsBtn.className = "power-tab-btn px-3 py-1.5 rounded-lg bg-amber-600/20 text-amber-400 border border-amber-500/30 font-semibold flex items-center gap-1.5 transition";
        if (wolBtn) wolBtn.className = "power-tab-btn px-3 py-1.5 rounded-lg bg-surface-900 text-slate-400 border border-slate-800 font-semibold flex items-center gap-1.5 hover:text-white transition";
        if (vmsContent) vmsContent.classList.remove('hidden');
        if (wolContent) wolContent.classList.add('hidden');
      } else {
        if (wolBtn) wolBtn.className = "power-tab-btn px-3 py-1.5 rounded-lg bg-amber-600/20 text-amber-400 border border-amber-500/30 font-semibold flex items-center gap-1.5 transition";
        if (vmsBtn) vmsBtn.className = "power-tab-btn px-3 py-1.5 rounded-lg bg-surface-900 text-slate-400 border border-slate-800 font-semibold flex items-center gap-1.5 hover:text-white transition";
        if (wolContent) wolContent.classList.remove('hidden');
        if (vmsContent) vmsContent.classList.add('hidden');
      }
    }

    async function loadPowerVms() {
      const tbody = document.getElementById('powerVmsTableBody');
      if (!tbody) return;
      tbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-slate-500"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Memuat data guest VM dari Proxmox...</td></tr>`;

      try {
        const res = await fetch('/api/v1/power/vms');
        const data = await res.json();
        powerVmsCache = data.vms || [];
        renderPowerVms(powerVmsCache);
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-rose-400">Gagal memuat VM: ${err}</td></tr>`;
      }
    }

    function renderPowerVms(vms) {
      const tbody = document.getElementById('powerVmsTableBody');
      if (!tbody) return;

      if (!vms || vms.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-slate-500">Tidak ada VM atau LXC terdaftar pada cluster.</td></tr>`;
        return;
      }

      tbody.innerHTML = vms.map(vm => {
        const isRunning = vm.status === 'running';
        const statusBadge = isRunning ? 
          `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 w-max">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> RUNNING
           </span>` :
          `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center gap-1 w-max">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span> STOPPED
           </span>`;

        const typeBadge = vm.vm_type === 'lxc' ?
          `<span class="px-1.5 py-0.5 rounded text-[9px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">LXC CT</span>` :
          `<span class="px-1.5 py-0.5 rounded text-[9px] font-mono bg-blue-500/10 text-blue-300 border border-blue-500/30">QEMU VM</span>`;

        const ramGb = (vm.ram_total_mb / 1024).toFixed(1);
        const diskGb = Math.round(vm.disk_total_gb || 0);

        return `
          <tr class="hover:bg-surface-850/60 transition-colors">
            <td class="py-2.5 px-3 text-center">
              <input type="checkbox" class="vm-row-checkbox w-4 h-4 rounded accent-amber-500 bg-slate-800 border-slate-700 cursor-pointer"
                     data-vmid="${vm.vmid}" onchange="updateSelectedVmCount()">
            </td>
            <td class="py-2.5 px-3">
              <div class="flex items-center gap-2">
                <span class="px-1.5 py-0.5 rounded bg-surface-900 border border-slate-700 text-amber-400 font-bold text-[10px]">#${vm.vmid}</span>
                <span class="font-bold text-white text-xs">${vm.name}</span>
              </div>
            </td>
            <td class="py-2.5 px-3">
              ${typeBadge}
            </td>
            <td class="py-2.5 px-3">
              ${statusBadge}
            </td>
            <td class="py-2.5 px-3 text-slate-300">
              <span>${vm.cores || 1} vCPU</span> • <span>${ramGb} GB RAM</span> • <span>${diskGb} GB Disk</span>
            </td>
            <td class="py-2.5 px-3 text-right space-x-1">
              ${isRunning ? `
                <button onclick="singleVmPower('reboot', ${vm.vmid}, '${vm.name}')" title="Reboot VM" class="px-2 py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-[10px] border border-amber-500/30 transition">
                  <i class="fa-solid fa-rotate"></i>
                </button>
                <button onclick="singleVmPower('shutdown', ${vm.vmid}, '${vm.name}')" title="Graceful Shutdown" class="px-2 py-1 rounded bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 text-[10px] border border-purple-500/30 transition">
                  <i class="fa-solid fa-power-off"></i>
                </button>
                <button onclick="singleVmPower('stop', ${vm.vmid}, '${vm.name}')" title="Force Stop" class="px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-[10px] border border-rose-500/30 transition">
                  <i class="fa-solid fa-stop"></i>
                </button>
              ` : `
                <button onclick="singleVmPower('start', ${vm.vmid}, '${vm.name}')" title="Start VM" class="px-2.5 py-1 rounded bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 text-[10px] font-bold border border-emerald-500/30 transition flex items-center gap-1 inline-flex">
                  <i class="fa-solid fa-play text-[9px]"></i> <span>Start</span>
                </button>
              `}
            </td>
          </tr>
        `;
      }).join('');

      updateSelectedVmCount();
    }

    function toggleSelectAllVms(checked) {
      const boxes = document.querySelectorAll('.vm-row-checkbox');
      boxes.forEach(b => b.checked = checked);
      updateSelectedVmCount();
    }

    function updateSelectedVmCount() {
      const checkedBoxes = document.querySelectorAll('.vm-row-checkbox:checked');
      const countEl = document.getElementById('selectedVmCount');
      if (countEl) countEl.innerText = checkedBoxes.length;

      const selectAll = document.getElementById('selectAllVmsToggle');
      const allBoxes = document.querySelectorAll('.vm-row-checkbox');
      if (selectAll && allBoxes.length > 0) {
        selectAll.checked = (checkedBoxes.length === allBoxes.length);
      }
    }

    async function executeBulkVmPower(action) {
      const checkedBoxes = document.querySelectorAll('.vm-row-checkbox:checked');
      if (checkedBoxes.length === 0) {
        alert("Pilih minimal 1 VM terlebih dahulu menggunakan checkbox!");
        return;
      }

      const vmids = Array.from(checkedBoxes).map(b => b.getAttribute('data-vmid'));
      const resBox = document.getElementById('vmBulkResultBox');
      if (resBox) {
        resBox.classList.remove('hidden');
        resBox.className = "p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono flex items-center gap-2";
        resBox.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Mendispatch perintah '${action.toUpperCase()}' ke ${vmids.length} VM Proxmox VE...</span>`;
      }

      try {
        const res = await fetch('/api/v1/power/vms/bulk', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ action, vmids })
        });
        const data = await res.json();

        if (resBox) {
          resBox.className = "p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-mono";
          resBox.innerHTML = `<i class="fa-solid fa-circle-check mr-1.5 text-emerald-400"></i> ${data.message || 'Perintah power berhasil dikirim ke Proxmox!'}`;
        }

        setTimeout(() => {
          loadPowerVms();
        }, 1500);
      } catch (err) {
        if (resBox) {
          resBox.className = "p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono";
          resBox.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1.5 text-rose-400"></i> Gagal mengeksekusi aksi: ${err}`;
        }
      }
    }

    async function singleVmPower(action, vmid, vmName) {
      if (!confirm(`Konfirmasi: Jalankan aksi '${action.toUpperCase()}' untuk VM #${vmid} (${vmName})?`)) return;

      try {
        const res = await fetch('/api/v1/power/vms/bulk', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ action, vmids: [vmid] })
        });
        const data = await res.json();
        
        const resBox = document.getElementById('vmBulkResultBox');
        if (resBox) {
          resBox.classList.remove('hidden');
          resBox.className = "p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-mono";
          resBox.innerHTML = `<i class="fa-solid fa-circle-check mr-1.5 text-emerald-400"></i> Aksi '${action.toUpperCase()}' untuk #${vmid} (${vmName}) berhasil dikirim ke Proxmox VE.`;
        }

        setTimeout(() => {
          loadPowerVms();
        }, 1200);
      } catch (err) {
        alert("Gagal menjalankan aksi power: " + err);
      }
    }

    // --- WAKE-ON-LAN DISPATCHER ---
    let wolAllDiscoveredCache = [];

    async function loadWolDevices() {
      const grid = document.getElementById('wolDevicesGrid');
      if (!grid) return;

      try {
        const res = await fetch('/api/v1/power/wol/devices');
        const data = await res.json();
        wolDevicesCache = data.devices || [];
        wolAllDiscoveredCache = data.all_discovered || [];
        renderWolDevices(wolDevicesCache, wolAllDiscoveredCache);
      } catch (err) {
        console.error("WoL devices load error:", err);
      }
    }

    function renderWolDevices(devices, allDiscovered) {
      // 1. Render primary hardware cards
      const grid = document.getElementById('wolDevicesGrid');
      if (grid) {
        grid.innerHTML = (devices || []).map(dev => {
          return `
            <div class="p-3.5 rounded-xl bg-surface-950 border border-slate-800 hover:border-amber-500/40 transition-all flex flex-col justify-between space-y-3 group shadow-sm">
              <div class="flex items-start gap-3">
                <div class="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 text-sm shrink-0">
                  <i class="fa-solid ${dev.icon || 'fa-server'}"></i>
                </div>
                <div class="min-w-0 flex-1">
                  <div class="font-bold text-white text-xs truncate">${dev.name}</div>
                  <div class="text-[10px] text-slate-400 font-mono">${dev.ip}</div>
                  <div class="text-[9px] text-amber-400/90 font-mono truncate mt-0.5">MAC: ${dev.mac.toUpperCase()}</div>
                </div>
              </div>

              <div class="flex items-center justify-between pt-2 border-t border-slate-800/80">
                <span class="text-[10px] text-slate-500 font-mono">${dev.notes || 'Physical Node'}</span>
                <button onclick="sendWol('${dev.mac}', '${dev.broadcast || '10.10.10.255'}', ${dev.port || 9}, '${dev.name}')" 
                        class="px-2.5 py-1 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-400 border border-amber-500/30 font-bold font-mono text-[10px] transition flex items-center gap-1 shadow-sm">
                  <i class="fa-solid fa-bolt text-[9px]"></i> <span>Wake Up</span>
                </button>
              </div>
            </div>
          `;
        }).join('');
      }

      // 2. Populate fast-select dropdown
      const select = document.getElementById('wolDeviceSelect');
      if (select) {
        const nodes = allDiscovered || [];
        select.innerHTML = `<option value="">-- Pilih Node Cluster / Perangkat LAN Terdeteksi (${nodes.length} Ditemukan) --</option>` +
          nodes.map((node, idx) => {
            return `<option value="${idx}">⚡ ${node.hostname || node.name} (${node.ip}) • MAC: ${node.mac.toUpperCase()} [${node.role}]</option>`;
          }).join('');
      }

      // 3. Populate complete discovered nodes table
      const tbody = document.getElementById('wolClusterNodesTableBody');
      if (tbody) {
        const nodes = allDiscovered || [];
        tbody.innerHTML = nodes.map(node => {
          return `
            <tr class="hover:bg-surface-850/60 transition-colors">
              <td class="py-2.5 px-3">
                <div class="flex items-center gap-2">
                  <i class="fa-solid ${node.icon || 'fa-server'} text-xs text-amber-400"></i>
                  <div>
                    <div class="font-bold text-white text-xs">${node.name || node.hostname}</div>
                    <div class="text-[9px] text-slate-500 font-mono">${node.id}</div>
                  </div>
                </div>
              </td>
              <td class="py-2.5 px-3 font-mono text-xs text-slate-300">
                ${node.ip}
              </td>
              <td class="py-2.5 px-3">
                <div class="flex items-center gap-1.5">
                  <code class="px-1.5 py-0.5 rounded bg-surface-900 border border-slate-700 text-amber-400 text-[10px] font-bold">${node.mac.toUpperCase()}</code>
                  <button onclick="copyIpToClipboard('${node.mac}', this)" title="Copy MAC" class="text-slate-500 hover:text-slate-300 text-[10px]">
                    <i class="fa-regular fa-copy"></i>
                  </button>
                </div>
              </td>
              <td class="py-2.5 px-3 text-[11px] text-slate-400">
                ${node.role}
              </td>
              <td class="py-2.5 px-3 text-right">
                <button onclick="sendWol('${node.mac}', '${node.broadcast || '10.10.10.255'}', 9, '${node.name}')" 
                        class="px-2.5 py-1 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-400 border border-amber-500/30 font-bold font-mono text-[10px] transition inline-flex items-center gap-1">
                  <i class="fa-solid fa-bolt text-[9px]"></i> <span>Wake</span>
                </button>
              </td>
            </tr>
          `;
        }).join('');
      }
    }

    function onWolDeviceSelected(idxVal) {
      if (idxVal === "" || !wolAllDiscoveredCache[idxVal]) return;
      const dev = wolAllDiscoveredCache[idxVal];
      
      const nameInput = document.getElementById('customWolName');
      const macInput = document.getElementById('customWolMac');
      const bcastInput = document.getElementById('customWolBroadcast');
      const portInput = document.getElementById('customWolPort');

      if (nameInput) nameInput.value = dev.name || dev.hostname;
      if (macInput) macInput.value = dev.mac.toUpperCase();
      if (bcastInput) bcastInput.value = dev.broadcast || '10.10.10.255';
      if (portInput) portInput.value = dev.port || 9;
    }

    function sendQuickSelectedWol() {
      const select = document.getElementById('wolDeviceSelect');
      const idxVal = select ? select.value : '';
      
      if (idxVal === "" || !wolAllDiscoveredCache[idxVal]) {
        alert("Silakan pilih salah satu node cluster dari dropdown terlebih dahulu!");
        return;
      }

      const dev = wolAllDiscoveredCache[idxVal];
      sendWol(dev.mac, dev.broadcast || '10.10.10.255', dev.port || 9, dev.name || dev.hostname);
    }

    async function sendWol(mac, broadcast, port, name) {
      const resBox = document.getElementById('wolResultBox');
      if (resBox) {
        resBox.classList.remove('hidden');
        resBox.className = "p-3 rounded-xl bg-surface-950 border border-slate-800 text-slate-300 text-xs font-mono flex items-center gap-2";
        resBox.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-amber-400"></i> <span>Membroadcast Magic Packet ke ${name} [${mac}]...</span>`;
      }

      try {
        const res = await fetch('/api/v1/power/wol', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            mac: mac,
            broadcast_ip: broadcast || '10.10.10.255',
            port: port || 9,
            name: name || 'Hardware Node'
          })
        });
        const data = await res.json();

        if (resBox) {
          if (res.ok && data.status === 'success') {
            resBox.className = "p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-mono";
            resBox.innerHTML = `<i class="fa-solid fa-circle-check mr-1.5 text-emerald-400"></i> <b>WAKE SIGNAL SENT:</b> ${data.message}`;
          } else {
            resBox.className = "p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono";
            resBox.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1.5 text-rose-400"></i> ${data.message || 'Gagal mengirim sinyal WoL'}`;
          }
        }
      } catch (err) {
        if (resBox) {
          resBox.className = "p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono";
          resBox.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1.5 text-rose-400"></i> Network WoL error: ${err}`;
        }
      }
    }

    function dispatchCustomWol() {
      const name = document.getElementById('customWolName')?.value.trim() || 'Custom Device';
      const mac = document.getElementById('customWolMac')?.value.trim();
      const broadcast = document.getElementById('customWolBroadcast')?.value.trim() || '10.10.10.255';
      const port = parseInt(document.getElementById('customWolPort')?.value || '9');

      if (!mac) {
        alert("Silakan pilih target dari dropdown atau masukkan MAC Address!");
        return;
      }

      sendWol(mac, broadcast, port, name);
    }

    // ==========================================
    //  AI HOMELAB COPILOT & AUTONOMOUS ADVISOR
    // ==========================================
    let currentAiTab = 'recommendations';
    let aiAuditCache = null;

    function openAiCopilotModal() {
      const modal = document.getElementById('aiCopilotModal');
      if (modal) modal.classList.remove('hidden');
      switchAiTab(currentAiTab || 'recommendations');
      loadAiAudit(false);
      loadAiSettings();
    }

    function closeAiCopilotModal() {
      const modal = document.getElementById('aiCopilotModal');
      if (modal) modal.classList.add('hidden');
    }

    function switchAiTab(tab) {
      currentAiTab = tab;
      const recsBtn = document.getElementById('tabBtnAiRecs');
      const insightsBtn = document.getElementById('tabBtnAiInsights');
      const configBtn = document.getElementById('tabBtnAiConfig');

      const recsContent = document.getElementById('tabContentAiRecs');
      const insightsContent = document.getElementById('tabContentAiInsights');
      const configContent = document.getElementById('tabContentAiConfig');

      const activeBtnClass = "ai-tab-btn px-3 py-1.5 rounded-lg bg-purple-600/20 text-purple-400 border border-purple-500/30 font-semibold flex items-center gap-1.5 transition";
      const inactiveBtnClass = "ai-tab-btn px-3 py-1.5 rounded-lg bg-surface-900 text-slate-400 border border-slate-800 font-semibold flex items-center gap-1.5 hover:text-white transition";

      if (recsBtn) recsBtn.className = (tab === 'recommendations') ? activeBtnClass : inactiveBtnClass;
      if (insightsBtn) insightsBtn.className = (tab === 'insights') ? activeBtnClass : inactiveBtnClass;
      if (configBtn) configBtn.className = (tab === 'config') ? activeBtnClass : inactiveBtnClass;

      if (recsContent) recsContent.classList.toggle('hidden', tab !== 'recommendations');
      if (insightsContent) insightsContent.classList.toggle('hidden', tab !== 'insights');
      if (configContent) configContent.classList.toggle('hidden', tab !== 'config');
    }

    async function loadAiAudit(forceFresh = false) {
      const spinIcon = document.querySelector('#btnAiAuditRun i');
      if (spinIcon) spinIcon.classList.add('animate-spin');

      try {
        const res = await fetch('/api/v1/ai/audit');
        if (!res.ok) throw new Error("Gagal mengambil audit AI");
        const data = await res.json();
        aiAuditCache = data;

        // 1. Update Executive Score & Summary
        const scoreVal = document.getElementById('aiModalScoreVal');
        if (scoreVal) {
          scoreVal.innerText = data.health_score;
          if (data.health_score >= 90) scoreVal.className = "text-2xl font-black text-emerald-400 font-mono tracking-tight leading-none";
          else if (data.health_score >= 75) scoreVal.className = "text-2xl font-black text-amber-400 font-mono tracking-tight leading-none";
          else scoreVal.className = "text-2xl font-black text-rose-400 font-mono tracking-tight leading-none";
        }

        const gradeBadge = document.getElementById('aiModalGradeBadge');
        if (gradeBadge) {
          gradeBadge.innerText = `${data.health_grade} (${data.health_score}/100)`;
          if (data.health_score >= 90) gradeBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30";
          else if (data.health_score >= 75) gradeBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30";
          else gradeBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30";
        }

        const auditTime = document.getElementById('aiModalAuditTime');
        if (auditTime) auditTime.innerText = `Audit: ${data.timestamp_human}`;

        const summaryDesc = document.getElementById('aiModalSummaryDesc');
        if (summaryDesc) summaryDesc.innerText = data.summary_desc;

        // 2. Update Navbar & Cluster Banner Badges
        const navBadge = document.getElementById('aiNavScoreBadge');
        if (navBadge) navBadge.innerText = `${data.health_score}%`;

        const bannerBadge = document.getElementById('aiBannerScoreBadge');
        if (bannerBadge) {
          bannerBadge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full ${data.health_score >= 90 ? 'bg-emerald-400' : 'bg-amber-400'} animate-pulse"></span> ${data.health_score}/100 ${data.health_grade}`;
        }

        const bannerInsight = document.getElementById('aiBannerQuickInsight');
        if (bannerInsight) {
          if (data.fleet_summary && data.fleet_summary.reclaimable_ram_gb > 0) {
            bannerInsight.innerHTML = `<b class="text-purple-300">Peluang Optimasi:</b> Host PVE mengalami tekanan RAM ${data.fleet_summary.pve_ram_used_pct}%. Potensi ~${data.fleet_summary.reclaimable_ram_gb} GB RAM bisa dibebaskan dari VM yang idle.`;
          } else {
            bannerInsight.innerText = data.summary_desc;
          }
        }

        // 3. Update Fleet Metrics
        const fleet = data.fleet_summary || {};
        const fleetNodes = document.getElementById('aiFleetNodesVal');
        if (fleetNodes) fleetNodes.innerText = `${fleet.online_nodes || 0} / ${fleet.total_nodes || 0}`;

        const pveRamVal = document.getElementById('aiFleetPveRamVal');
        if (pveRamVal) pveRamVal.innerText = `${fleet.pve_ram_used_pct || 0}%`;

        const pveRamSub = document.getElementById('aiFleetPveRamSub');
        if (pveRamSub) pveRamSub.innerText = `${fleet.pve_ram_used_gb || 0} GB / ${fleet.pve_ram_total_gb || 0} GB`;

        const reclaimVal = document.getElementById('aiFleetReclaimVal');
        if (reclaimVal) reclaimVal.innerText = `~${fleet.reclaimable_ram_gb || 0} GB`;

        const probesVal = document.getElementById('aiFleetProbesVal');
        if (probesVal) probesVal.innerText = `${(fleet.probes_total || 0) - (fleet.probes_failing || 0)} / ${fleet.probes_total || 0}`;

        // 4. Render recommendations & insights
        renderAiRecommendations(data.recommendations || []);
        renderAiInsights(data.insights || [], data.deductions || []);

      } catch (err) {
        console.error("AI audit load error:", err);
      } finally {
        if (spinIcon) {
          setTimeout(() => spinIcon.classList.remove('animate-spin'), 600);
        }
      }
    }

    function renderAiRecommendations(recs) {
      const container = document.getElementById('aiRecommendationsList');
      const badge = document.getElementById('aiRecsCountBadge');
      if (badge) badge.innerText = `${recs.length} Rekomendasi Aktif`;
      if (!container) return;

      if (!recs || recs.length === 0) {
        container.innerHTML = `
          <div class="p-6 rounded-2xl bg-surface-950 border border-slate-800 text-center">
            <i class="fa-solid fa-circle-check text-emerald-400 text-2xl mb-2"></i>
            <h5 class="text-white font-bold text-xs">Semua Parameter Homelab Optimal</h5>
            <p class="text-slate-400 text-xs mt-1">Tidak ada rekomendasi tindakan darurat saat ini. AI tetap memantau 24 jam.</p>
          </div>
        `;
        return;
      }

      container.innerHTML = recs.map((r, idx) => {
        let catColor = "purple";
        let catIcon = "fa-bolt";
        if (r.category === 'RAM_ALLOCATION') { catColor = "amber"; catIcon = "fa-memory"; }
        else if (r.category === 'CPU_SCALING') { catColor = "blue"; catIcon = "fa-microchip"; }
        else if (r.category === 'STORAGE') { catColor = "cyan"; catIcon = "fa-hard-drive"; }
        else if (r.category === 'STABILITY') { catColor = "rose"; catIcon = "fa-shield-halved"; }

        let sevBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30">OPTIMAL</span>`;
        if (r.severity === 'CRITICAL') {
          sevBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30 animate-pulse">KRITIS</span>`;
        } else if (r.severity === 'RECOMMENDED' || r.severity === 'WARNING') {
          sevBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">DISARANKAN</span>`;
        }

        const cmdBlock = r.action_command ? `
          <div class="mt-2.5 pt-2.5 border-t border-slate-800/80 flex items-center justify-between gap-2">
            <div class="flex items-center gap-2 overflow-hidden text-xs font-mono text-slate-300 bg-surface-900 px-3 py-1.5 rounded-lg border border-slate-800 flex-1">
              <span class="text-slate-500">$</span>
              <code class="truncate">${r.action_command}</code>
            </div>
            <button onclick="copyIpToClipboard('${r.action_command}', this)" class="px-2.5 py-1.5 rounded-lg bg-surface-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-[11px] font-mono flex items-center gap-1 transition shrink-0" title="Salin Perintah">
              <i class="fa-regular fa-copy"></i>
              <span>Salin</span>
            </button>
          </div>
        ` : '';

        const impactBlock = r.impact ? `
          <div class="mt-2 text-[11px] font-mono text-emerald-400 flex items-center gap-1.5">
            <i class="fa-solid fa-arrow-trend-up text-xs"></i>
            <span><b>Dampak:</b> ${r.impact}</span>
          </div>
        ` : '';

        const vmsTable = (r.vms && r.vms.length > 0) ? `
          <div class="mt-3 rounded-xl overflow-hidden border border-slate-800 bg-surface-900/90 shadow-inner">
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs font-mono">
                <thead class="bg-surface-850/80 text-[10px] text-slate-400 uppercase tracking-wider border-b border-slate-800">
                  <tr>
                    <th class="py-2 px-3">VM ID</th>
                    <th class="py-2 px-3">Nama Guest</th>
                    <th class="py-2 px-3 text-center">Alokasi Saat Ini</th>
                    <th class="py-2 px-3 text-center">Saran AI</th>
                    <th class="py-2 px-3 text-right text-purple-400">Hemat Host</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/50 text-[11px]">
                  ${r.vms.map(v => `
                    <tr class="hover:bg-surface-800/40 transition-colors">
                      <td class="py-1.5 px-3 text-slate-400 font-bold">${v.vmid}</td>
                      <td class="py-1.5 px-3 font-semibold text-white">${v.name}</td>
                      <td class="py-1.5 px-3 text-center text-slate-300">${v.alloc_gb.toFixed(1)} GB</td>
                      <td class="py-1.5 px-3 text-center text-emerald-400 font-bold">➔ ${v.rec_gb.toFixed(1)} GB</td>
                      <td class="py-1.5 px-3 text-right text-purple-300 font-bold">+${v.save_gb.toFixed(1)} GB</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        ` : '';

        return `
          <div class="p-4 rounded-xl bg-surface-950 border border-slate-800/90 hover:border-${catColor}-500/40 transition-all shadow-sm">
            <div class="flex items-start justify-between gap-2">
              <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-lg bg-${catColor}-500/15 border border-${catColor}-500/30 flex items-center justify-center text-${catColor}-400 text-xs shrink-0">
                  <i class="fa-solid ${catIcon}"></i>
                </div>
                <div>
                  <h5 class="text-xs font-bold text-white tracking-wide">${r.title}</h5>
                  <span class="text-[10px] font-mono text-slate-500 uppercase tracking-wider">${r.category}</span>
                </div>
              </div>
              <div>${sevBadge}</div>
            </div>

            <p class="text-xs text-slate-300 mt-2.5 whitespace-pre-line leading-relaxed">${r.detail}</p>
            ${vmsTable}
            ${impactBlock}
            ${cmdBlock}
          </div>
        `;
      }).join('');
    }

    function renderAiInsights(insights, deductions) {
      const dedContainer = document.getElementById('aiDeductionsList');
      if (dedContainer) {
        if (!deductions || deductions.length === 0) {
          dedContainer.innerHTML = `<div class="text-emerald-400 text-xs"><i class="fa-solid fa-circle-check mr-1.5"></i> Tidak ada penalti skor (100% Sempurna).</div>`;
        } else {
          dedContainer.innerHTML = deductions.map(d => `
            <div class="flex items-center gap-2 py-0.5 text-amber-300 text-xs">
              <i class="fa-solid fa-triangle-exclamation text-amber-400 text-[10px]"></i>
              <span>${d}</span>
            </div>
          `).join('');
        }
      }

      const insContainer = document.getElementById('aiInsightsList');
      if (insContainer) {
        if (!insights || insights.length === 0) {
          insContainer.innerHTML = `
            <div class="p-4 rounded-xl bg-surface-950 border border-slate-800 text-slate-400 text-xs font-mono text-center">
              Seluruh node dan workload dalam kondisi nominal.
            </div>
          `;
        } else {
          insContainer.innerHTML = insights.map(ins => {
            let color = "amber";
            if (ins.severity === 'CRITICAL') color = "rose";
            else if (ins.severity === 'OPTIMIZATION') color = "purple";
            return `
              <div class="p-3.5 rounded-xl bg-surface-950 border border-slate-800 flex items-start gap-3">
                <span class="w-2 h-2 rounded-full bg-${color}-400 mt-1.5 shrink-0"></span>
                <div class="flex-1">
                  <div class="flex items-center justify-between gap-2">
                    <span class="font-bold text-white text-xs">${ins.title}</span>
                    <span class="text-[10px] font-mono text-${color}-400 uppercase font-bold">${ins.severity}</span>
                  </div>
                  <p class="text-xs text-slate-300 mt-1">${ins.detail}</p>
                </div>
              </div>
            `;
          }).join('');
        }
      }
    }

    async function dispatchAiTelegram() {
      const btn = document.getElementById('btnAiDispatchTg');
      const box = document.getElementById('aiDispatchResultBox');

      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-white"></i> <span>Mengirim...</span>`;
      }

      try {
        const res = await fetch('/api/v1/ai/dispatch-telegram', { method: 'POST' });
        const data = await res.json();

        if (box) {
          box.classList.remove('hidden');
          if (res.ok && data.status === 'success') {
            box.className = "px-6 py-2.5 text-xs font-mono border-b bg-emerald-500/10 border-emerald-500/30 text-emerald-300 flex items-center justify-between";
            box.innerHTML = `<span><i class="fa-solid fa-circle-check mr-2 text-emerald-400"></i> Laporan AI Copilot berhasil dikirimkan ke Telegram (@cigak_bot)!</span>
                             <button onclick="document.getElementById('aiDispatchResultBox').classList.add('hidden')" class="text-emerald-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>`;
          } else {
            box.className = "px-6 py-2.5 text-xs font-mono border-b bg-rose-500/10 border-rose-500/30 text-rose-300 flex items-center justify-between";
            box.innerHTML = `<span><i class="fa-solid fa-triangle-exclamation mr-2 text-rose-400"></i> ${data.message || 'Gagal mengirim ke Telegram'}</span>
                             <button onclick="document.getElementById('aiDispatchResultBox').classList.add('hidden')" class="text-rose-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>`;
          }
        }
      } catch (err) {
        if (box) {
          box.classList.remove('hidden');
          box.className = "px-6 py-2.5 text-xs font-mono border-b bg-rose-500/10 border-rose-500/30 text-rose-300";
          box.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-2 text-rose-400"></i> Error pengiriman: ${err}`;
        }
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<i class="fa-brands fa-telegram text-white"></i> <span>Kirim ke Telegram</span>`;
        }
      }
    }

    async function dispatchAiTelegramQuick(btn) {
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-sky-400"></i> <span>Mengirim...</span>`;
      }

      try {
        const res = await fetch('/api/v1/ai/dispatch-telegram', { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
          alert("✅ Laporan Analisis Sentinel AI Homelab Copilot berhasil dikirim ke Telegram!");
        } else {
          alert(`⚠️ Pengiriman Telegram: ${data.message || 'Gagal'}`);
        }
      } catch (err) {
        alert("Error pengiriman Telegram: " + err);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<i class="fa-brands fa-telegram text-sky-400"></i> <span>Kirim ke Telegram</span>`;
        }
      }
    }
    const AI_PROVIDER_PRESETS = {
      gemini: {
        model: "gemini-1.5-flash",
        baseUrl: "https://generativelanguage.googleapis.com/v1beta",
        help: 'Dapatkan API Key gratis di: <a href="https://aistudio.google.com" target="_blank" class="text-purple-400 hover:underline">aistudio.google.com</a>',
        placeholder: "AIzaSy...",
        presets: [
          { name: "gemini-1.5-flash", label: "gemini-1.5-flash" },
          { name: "gemini-2.0-flash", label: "gemini-2.0-flash" },
          { name: "gemini-1.5-pro", label: "gemini-1.5-pro" }
        ]
      },
      groq: {
        model: "llama-3.3-70b-versatile",
        baseUrl: "https://api.groq.com/openai/v1",
        help: 'Dapatkan API Key gratis (super cepat) di: <a href="https://console.groq.com/keys" target="_blank" class="text-purple-400 hover:underline">console.groq.com</a>',
        placeholder: "gsk_...",
        presets: [
          { name: "llama-3.3-70b-versatile", label: "llama-3.3-70b-versatile" },
          { name: "llama-3.1-8b-instant", label: "llama-3.1-8b-instant" }
        ]
      },
      openai: {
        model: "gpt-4o-mini",
        baseUrl: "https://api.openai.com/v1",
        help: 'Dapatkan API Key di: <a href="https://platform.openai.com/api-keys" target="_blank" class="text-purple-400 hover:underline">platform.openai.com</a>',
        placeholder: "sk-proj-...",
        presets: [
          { name: "gpt-4o-mini", label: "gpt-4o-mini" },
          { name: "gpt-4o", label: "gpt-4o" }
        ]
      },
      openrouter: {
        model: "meta-llama/llama-3.3-70b-instruct:free",
        baseUrl: "https://openrouter.ai/api/v1",
        help: 'Dapatkan API Key di: <a href="https://openrouter.ai/keys" target="_blank" class="text-purple-400 hover:underline">openrouter.ai</a> (tersedia ratusan model gratis &amp; berbayar)',
        placeholder: "sk-or-v1-...",
        presets: [
          { name: "meta-llama/llama-3.3-70b-instruct:free", label: "llama-3.3-free" },
          { name: "google/gemini-2.0-flash-exp:free", label: "gemini-2.0-free" }
        ]
      },
      custom: {
        model: "llama3",
        baseUrl: "http://10.10.10.x:11434/v1",
        help: 'Gunakan endpoint lokal Ollama, vLLM, LM Studio, atau OpenAI-compatible server Anda sendiri.',
        placeholder: "API key jika endpoint memerlukan autentikasi...",
        presets: [
          { name: "llama3", label: "llama3" },
          { name: "deepseek-r1", label: "deepseek-r1" },
          { name: "mistral", label: "mistral" }
        ]
      }
    };

    function onAiProviderChange() {
      const p = document.getElementById('aiConfigProvider')?.value || 'gemini';
      const meta = AI_PROVIDER_PRESETS[p] || AI_PROVIDER_PRESETS.gemini;
      
      const modelInput = document.getElementById('aiConfigModel');
      const baseUrlInput = document.getElementById('aiConfigBaseUrl');
      const apiKeyInput = document.getElementById('aiConfigApiKey');
      const helpLink = document.getElementById('aiProviderHelpLink');
      const presetsContainer = document.getElementById('aiModelPresets');

      if (helpLink) helpLink.innerHTML = meta.help;
      if (apiKeyInput) apiKeyInput.placeholder = meta.placeholder;

      if (modelInput && (!modelInput.value || Object.values(AI_PROVIDER_PRESETS).some(x => x.model === modelInput.value))) {
        modelInput.value = meta.model;
      }
      if (baseUrlInput && (!baseUrlInput.value || Object.values(AI_PROVIDER_PRESETS).some(x => x.baseUrl === baseUrlInput.value))) {
        baseUrlInput.value = meta.baseUrl;
      }

      if (presetsContainer) {
        presetsContainer.innerHTML = '<span class="text-slate-400">Preset:</span> ' +
          meta.presets.map(pr => `<button type="button" onclick="selectAiModelPreset('${pr.name}')" class="text-purple-400 hover:text-purple-300 underline">${pr.label}</button>`).join(' ');
      }
    }

    function selectAiModelPreset(modelName) {
      const modelInput = document.getElementById('aiConfigModel');
      if (modelInput) modelInput.value = modelName;
    }

    function toggleApiKeyVisibility() {
      const input = document.getElementById('aiConfigApiKey');
      const icon = document.getElementById('aiKeyEyeIcon');
      const text = document.getElementById('aiKeyEyeText');
      if (!input) return;
      if (input.type === 'password') {
        input.type = 'text';
        if (icon) icon.className = 'fa-regular fa-eye-slash';
        if (text) text.innerText = 'Sembunyikan';
      } else {
        input.type = 'password';
        if (icon) icon.className = 'fa-regular fa-eye';
        if (text) text.innerText = 'Lihat';
      }
    }

    async function testAiConnection() {
      const btn = document.getElementById('btnTestAiConnection');
      const resultBox = document.getElementById('aiTestResultBox');
      const provider = document.getElementById('aiConfigProvider')?.value || 'gemini';
      const apiKey = document.getElementById('aiConfigApiKey')?.value?.trim() || '';
      const model = document.getElementById('aiConfigModel')?.value?.trim() || '';
      const baseUrl = document.getElementById('aiConfigBaseUrl')?.value?.trim() || '';

      if (!apiKey && provider !== 'custom') {
        alert("Harap masukkan API Key terlebih dahulu untuk menguji koneksi.");
        return;
      }

      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin text-purple-400"></i> <span>Menguji API...</span>`;
      }
      if (resultBox) {
        resultBox.classList.remove('hidden');
        resultBox.className = "p-3 rounded-xl border border-slate-700 bg-surface-900 text-slate-300 text-xs font-mono leading-relaxed";
        resultBox.innerHTML = `Mengirim prompt uji ke ${provider.toUpperCase()} (${model || 'default'})...`;
      }

      try {
        const res = await fetch('/api/v1/ai/test-connection', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ provider, api_key: apiKey, model, base_url: baseUrl })
        });
        const data = await res.json();
        
        if (data.status === 'success') {
          if (resultBox) {
            resultBox.className = "p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs font-mono leading-relaxed";
            resultBox.innerHTML = `
              <div class="flex items-center justify-between mb-1.5 font-bold">
                <span class="flex items-center gap-1.5"><i class="fa-solid fa-circle-check text-emerald-400"></i> ${data.message}</span>
                <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold">${data.latency_ms} ms</span>
              </div>
              <div class="text-[11px] text-slate-300 bg-surface-950 p-2 rounded-lg border border-slate-800 mt-1">
                <b class="text-purple-300">${data.model}:</b> "${data.reply}"
              </div>
            `;
          }
        } else {
          if (resultBox) {
            resultBox.className = "p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs font-mono leading-relaxed";
            resultBox.innerHTML = `
              <div class="flex items-center gap-1.5 font-bold mb-1">
                <i class="fa-solid fa-triangle-exclamation text-rose-400"></i> Koneksi Gagal (${data.latency_ms || 0} ms)
              </div>
              <div class="text-[11px] text-rose-200 mt-1">
                ${data.message || 'Terjadi kesalahan saat memanggil provider API'}
              </div>
            `;
          }
        }
      } catch (err) {
        if (resultBox) {
          resultBox.className = "p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs font-mono";
          resultBox.innerText = "Error: " + err;
        }
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<i class="fa-solid fa-bolt text-yellow-400"></i> <span>Test Koneksi API</span>`;
        }
      }
    }

    async function loadAiSettings() {
      try {
        const res = await fetch('/api/v1/ai/settings');
        if (!res.ok) return;
        const s = await res.json();

        const copilotCheck = document.getElementById('aiConfigCopilotEnabled');
        if (copilotCheck) copilotCheck.checked = s.ai_copilot_enabled;

        const tgAlertsCheck = document.getElementById('aiConfigTgAlerts');
        if (tgAlertsCheck) tgAlertsCheck.checked = s.ai_telegram_alerts_enabled;

        const tgDigestCheck = document.getElementById('aiConfigTgDigest');
        if (tgDigestCheck) tgDigestCheck.checked = s.ai_telegram_digest_enabled;

        const intervalSel = document.getElementById('aiConfigDigestInterval');
        if (intervalSel) intervalSel.value = s.ai_digest_interval_hours;

        const threshCpu = document.getElementById('aiConfigThreshCpu');
        if (threshCpu) threshCpu.value = s.ai_alert_threshold_cpu;

        const threshRam = document.getElementById('aiConfigThreshRam');
        if (threshRam) threshRam.value = s.ai_alert_threshold_ram;

        const threshDisk = document.getElementById('aiConfigThreshDisk');
        if (threshDisk) threshDisk.value = s.ai_alert_threshold_disk;

        // Universal AI Provider Fields
        const providerSel = document.getElementById('aiConfigProvider');
        if (providerSel && s.ai_provider) {
          providerSel.value = s.ai_provider;
          onAiProviderChange();
        }

        const apiKeyInput = document.getElementById('aiConfigApiKey');
        if (apiKeyInput) {
          apiKeyInput.value = s.ai_api_key || s.gemini_api_key || '';
        }

        const modelInput = document.getElementById('aiConfigModel');
        if (modelInput && s.ai_model) {
          modelInput.value = s.ai_model;
        }

        const baseUrlInput = document.getElementById('aiConfigBaseUrl');
        if (baseUrlInput && s.ai_base_url) {
          baseUrlInput.value = s.ai_base_url;
        }

        const activeBadge = document.getElementById('aiActiveProviderBadge');
        if (activeBadge) {
          if (s.ai_api_key_set || (s.ai_provider === 'custom' && s.ai_base_url)) {
            activeBadge.className = "px-2.5 py-1 rounded-lg text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30";
            activeBadge.innerText = `${(s.ai_provider || 'AI').toUpperCase()} Terhubung`;
          } else {
            activeBadge.className = "px-2.5 py-1 rounded-lg text-[10px] font-mono font-semibold bg-slate-800 text-slate-400 border border-slate-700";
            activeBadge.innerText = "Mode Heuristik";
          }
        }

        const lastStat = document.getElementById('aiLastDigestStatusLabel');
        if (lastStat) lastStat.innerText = `Laporan Terakhir: ${s.ai_last_digest_status || 'Siap'}`;

      } catch (err) {
        console.error("AI settings load error:", err);
      }
    }

    async function saveAiSettings() {
      const payload = {
        ai_copilot_enabled: document.getElementById('aiConfigCopilotEnabled')?.checked ?? true,
        ai_telegram_alerts_enabled: document.getElementById('aiConfigTgAlerts')?.checked ?? true,
        ai_telegram_digest_enabled: document.getElementById('aiConfigTgDigest')?.checked ?? true,
        ai_digest_interval_hours: parseInt(document.getElementById('aiConfigDigestInterval')?.value || '6'),
        ai_alert_threshold_cpu: parseFloat(document.getElementById('aiConfigThreshCpu')?.value || '90'),
        ai_alert_threshold_ram: parseFloat(document.getElementById('aiConfigThreshRam')?.value || '94'),
        ai_alert_threshold_disk: parseFloat(document.getElementById('aiConfigThreshDisk')?.value || '85'),
        ai_provider: document.getElementById('aiConfigProvider')?.value || 'gemini',
        ai_api_key: document.getElementById('aiConfigApiKey')?.value?.trim() || '',
        ai_model: document.getElementById('aiConfigModel')?.value?.trim() || '',
        ai_base_url: document.getElementById('aiConfigBaseUrl')?.value?.trim() || ''
      };

      try {
        const res = await fetch('/api/v1/ai/settings', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          const msg = document.getElementById('aiConfigSaveMsg');
          if (msg) {
            msg.classList.remove('hidden');
            setTimeout(() => msg.classList.add('hidden'), 3500);
          }
          await loadAiSettings();
        }
      } catch (err) {
        alert("Gagal menyimpan konfigurasi AI: " + err);
      }
    }

    // ==========================================
    //  INCIDENT ALERT BOT INTEGRATOR
    // ==========================================
    let currentAlertTab = 'telegram';

    function switchAlertTab(tab) {
      currentAlertTab = tab;
      const tabs = ['telegram', 'discord', 'rules'];
      tabs.forEach(t => {
        const btn = document.getElementById(`tabBtn${t.charAt(0).toUpperCase() + t.slice(1)}`);
        const content = document.getElementById(`tabContent${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (t === tab) {
          if (btn) {
            btn.className = "alert-tab-btn px-3 py-1.5 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 font-semibold flex items-center gap-1.5 transition";
          }
          if (content) content.classList.remove('hidden');
        } else {
          if (btn) {
            btn.className = "alert-tab-btn px-3 py-1.5 rounded-lg bg-surface-900 text-slate-400 border border-slate-800 font-semibold flex items-center gap-1.5 hover:text-white transition";
          }
          if (content) content.classList.add('hidden');
        }
      });
    }

    async function openAlertModal() {
      document.getElementById('alertModal').classList.remove('hidden');
      const resBox = document.getElementById('alertTestResult');
      if (resBox) resBox.classList.add('hidden');
      switchAlertTab(currentAlertTab || 'telegram');

      try {
        const res = await fetch('/api/v1/settings');
        const data = await res.json();
        
        // Telegram
        const tgToken = document.getElementById('tgTokenInput');
        if (tgToken) tgToken.value = data.telegram_token || '';
        const tgChat = document.getElementById('tgChatIdInput');
        if (tgChat) tgChat.value = data.telegram_chat_id || '';
        const tgEn = document.getElementById('tgEnabledToggle');
        if (tgEn) tgEn.checked = data.telegram_enabled !== false;

        // Discord
        const dcWeb = document.getElementById('dcWebhookInput');
        if (dcWeb) dcWeb.value = data.discord_webhook || '';
        const dcEn = document.getElementById('dcEnabledToggle');
        if (dcEn) dcEn.checked = data.discord_enabled !== false;

        // Rules
        const offEn = document.getElementById('alertOfflineToggle');
        if (offEn) offEn.checked = data.alert_on_offline !== false;

        const cpuEn = document.getElementById('alertCpuToggle');
        if (cpuEn) cpuEn.checked = data.alert_on_cpu !== false;
        const cpuThresh = data.cpu_threshold || 85;
        const cpuRange = document.getElementById('cpuThresholdRange');
        const cpuInput = document.getElementById('cpuThresholdInput');
        if (cpuRange) cpuRange.value = cpuThresh;
        if (cpuInput) cpuInput.value = cpuThresh;

        const diskEn = document.getElementById('alertDiskToggle');
        if (diskEn) diskEn.checked = data.alert_on_disk !== false;
        const diskThresh = data.disk_threshold || 90;
        const diskRange = document.getElementById('diskThresholdRange');
        const diskInput = document.getElementById('diskThresholdInput');
        if (diskRange) diskRange.value = diskThresh;
        if (diskInput) diskInput.value = diskThresh;

      } catch (e) {
        console.error("Settings load error:", e);
      }
    }

    function closeAlertModal() {
      document.getElementById('alertModal').classList.add('hidden');
      const resBox = document.getElementById('alertTestResult');
      if (resBox) resBox.classList.add('hidden');
    }

    async function saveAlertSettings() {
      const btnSave = document.getElementById('btnSaveAlert');
      if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Menyimpan...`;
      }

      const payload = {
        telegram_token: document.getElementById('tgTokenInput') ? document.getElementById('tgTokenInput').value.trim() : '',
        telegram_chat_id: document.getElementById('tgChatIdInput') ? document.getElementById('tgChatIdInput').value.trim() : '',
        telegram_enabled: document.getElementById('tgEnabledToggle') ? document.getElementById('tgEnabledToggle').checked : true,
        discord_webhook: document.getElementById('dcWebhookInput') ? document.getElementById('dcWebhookInput').value.trim() : '',
        discord_enabled: document.getElementById('dcEnabledToggle') ? document.getElementById('dcEnabledToggle').checked : true,
        alert_on_offline: document.getElementById('alertOfflineToggle') ? document.getElementById('alertOfflineToggle').checked : true,
        alert_on_cpu: document.getElementById('alertCpuToggle') ? document.getElementById('alertCpuToggle').checked : true,
        cpu_threshold: parseInt(document.getElementById('cpuThresholdInput')?.value || '85'),
        alert_on_disk: document.getElementById('alertDiskToggle') ? document.getElementById('alertDiskToggle').checked : true,
        disk_threshold: parseInt(document.getElementById('diskThresholdInput')?.value || '90'),
      };

      try {
        const res = await fetch('/api/v1/settings', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const resp = await res.json();
        
        // Show success toast/status
        const resBox = document.getElementById('alertTestResult');
        if (resBox) {
          resBox.classList.remove('hidden');
          resBox.className = "p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-mono";
          resBox.innerHTML = `<i class="fa-solid fa-circle-check mr-1.5 text-emerald-400"></i> Konfigurasi alert bot berhasil disimpan ke persistent storage!`;
        }

        setTimeout(() => {
          closeAlertModal();
        }, 1200);
      } catch (e) {
        alert("Gagal menyimpan konfigurasi: " + e);
      } finally {
        if (btnSave) {
          btnSave.disabled = false;
          btnSave.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> <span>Simpan Konfigurasi</span>`;
        }
      }
    }

    async function testSendAlert() {
      const btnTest = document.getElementById('btnTestAlert');
      const resBox = document.getElementById('alertTestResult');
      if (resBox) {
        resBox.classList.remove('hidden');
        resBox.className = "p-3 rounded-xl bg-surface-950 border border-slate-800 text-slate-300 text-xs font-mono space-y-1";
        resBox.innerHTML = `<div class="flex items-center gap-2 text-amber-400"><i class="fa-solid fa-spinner fa-spin"></i> <span>Menyimpan & mendispatch notifikasi uji coba ke Telegram & Discord...</span></div>`;
      }
      if (btnTest) btnTest.disabled = true;

      // Save latest settings first
      await fetch('/api/v1/settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          telegram_token: document.getElementById('tgTokenInput') ? document.getElementById('tgTokenInput').value.trim() : '',
          telegram_chat_id: document.getElementById('tgChatIdInput') ? document.getElementById('tgChatIdInput').value.trim() : '',
          telegram_enabled: document.getElementById('tgEnabledToggle') ? document.getElementById('tgEnabledToggle').checked : true,
          discord_webhook: document.getElementById('dcWebhookInput') ? document.getElementById('dcWebhookInput').value.trim() : '',
          discord_enabled: document.getElementById('dcEnabledToggle') ? document.getElementById('dcEnabledToggle').checked : true,
          alert_on_offline: document.getElementById('alertOfflineToggle') ? document.getElementById('alertOfflineToggle').checked : true,
          alert_on_cpu: document.getElementById('alertCpuToggle') ? document.getElementById('alertCpuToggle').checked : true,
          cpu_threshold: parseInt(document.getElementById('cpuThresholdInput')?.value || '85'),
          alert_on_disk: document.getElementById('alertDiskToggle') ? document.getElementById('alertDiskToggle').checked : true,
          disk_threshold: parseInt(document.getElementById('diskThresholdInput')?.value || '90'),
        })
      });

      try {
        const res = await fetch('/api/v1/alert/test', { method: 'POST' });
        const data = await res.json();
        
        let tgHtml = '';
        if (data.telegram) {
          const ok = data.telegram.status === 'ok';
          tgHtml = `<div class="flex items-center justify-between py-1 border-b border-slate-800">
            <span class="flex items-center gap-1.5"><i class="fa-brands fa-telegram text-blue-400"></i> <b>Telegram Dispatch:</b></span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${ok ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'}">${ok ? 'SUCCESS (SENT)' : (data.telegram.reason || 'FAILED')}</span>
          </div>`;
        }

        let dcHtml = '';
        if (data.discord) {
          const ok = data.discord.status === 'ok';
          dcHtml = `<div class="flex items-center justify-between py-1">
            <span class="flex items-center gap-1.5"><i class="fa-brands fa-discord text-purple-400"></i> <b>Discord Webhook:</b></span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${ok ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'}">${ok ? 'SUCCESS (SENT)' : (data.discord.reason || 'FAILED')}</span>
          </div>`;
        }

        if (resBox) {
          resBox.innerHTML = `
            <div class="font-bold text-white mb-1.5 flex items-center gap-1.5">
              <i class="fa-solid fa-satellite-dish text-cyan-400"></i> Hasil Uji Coba Pengiriman:
            </div>
            ${tgHtml}
            ${dcHtml}
          `;
        }
      } catch (e) {
        if (resBox) {
          resBox.className = "p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono";
          resBox.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1.5 text-rose-400"></i> Dispatch error: ${e}`;
        }
      } finally {
        if (btnTest) btnTest.disabled = false;
      }
    }

    // ========================================================
    //  INTERACTIVE CLUSTER NETWORK TOPOLOGY & INTERCONNECT MAP
    // ========================================================
    let topologyExpanded = true;

    function toggleTopologyExpand() {
      topologyExpanded = !topologyExpanded;
      const body = document.getElementById('topologyCollapseBody');
      const icon = document.getElementById('topologyToggleIcon');
      const label = document.getElementById('topologyToggleLabel');
      if (body) {
        if (topologyExpanded) {
          body.classList.remove('hidden');
          if (icon) icon.className = "fa-solid fa-chevron-up text-[11px]";
          if (label) label.innerText = "Collapse";
        } else {
          body.classList.add('hidden');
          if (icon) icon.className = "fa-solid fa-chevron-down text-[11px]";
          if (label) label.innerText = "Expand";
        }
      }
    }

    function renderTopologyMap(nodes) {
      const svg = document.getElementById('topologySvg');
      if (!svg) return;

      const safeNodes = nodes || [];
      const pveNode = safeNodes.find(n => n.id === 'srv-pve' || n.hostname === 'pve') || {
        id: 'srv-pve', hostname: 'srv-pve', ip: '10.10.10.2', is_online: true, cpu_pct: 12.4, ram_pct: 68.2
      };
      const sentinelNode = safeNodes.find(n => n.id === 'srv-host-node' || n.hostname === 'aidil') || {
        id: 'srv-host-node', hostname: 'aidil (NOC)', ip: '10.10.10.9', is_online: true, cpu_pct: 8.5, ram_pct: 35.1
      };
      
      // Guest VMs (all nodes except PVE and Sentinel)
      const guestVms = safeNodes.filter(n => n.id !== 'srv-pve' && n.id !== 'srv-host-node');
      
      // Fixed layout coordinates
      const routerX = 500, routerY = 45;
      const pveX = 300, pveY = 150;
      const nocX = 700, nocY = 150;

      // Guest VM row at y = 295
      const vmY = 295;
      const vmCount = Math.max(guestVms.length, 8);
      const startX = 60;
      const endX = 940;
      const stepX = (endX - startX) / Math.max(1, vmCount - 1);

      // SVG Cable lines
      let cablesHtml = '';

      // Cable 1: Gateway -> PVE
      cablesHtml += `
        <path d="M ${routerX} ${routerY + 22} C ${routerX} ${routerY + 60}, ${pveX} ${routerY + 60}, ${pveX} ${pveY - 25}" 
              stroke="#3b82f6" stroke-width="2.5" fill="none" opacity="0.6" />
        <path d="M ${routerX} ${routerY + 22} C ${routerX} ${routerY + 60}, ${pveX} ${routerY + 60}, ${pveX} ${pveY - 25}" 
              stroke="#60a5fa" stroke-width="2" fill="none" stroke-dasharray="6 6" class="traffic-cable" />
      `;

      // Cable 2: Gateway -> Sentinel NOC
      cablesHtml += `
        <path d="M ${routerX} ${routerY + 22} C ${routerX} ${routerY + 60}, ${nocX} ${routerY + 60}, ${nocX} ${nocY - 25}" 
              stroke="#06b6d4" stroke-width="2.5" fill="none" opacity="0.6" />
        <path d="M ${routerX} ${routerY + 22} C ${routerX} ${routerY + 60}, ${nocX} ${routerY + 60}, ${nocX} ${nocY - 25}" 
              stroke="#22d3ee" stroke-width="2" fill="none" stroke-dasharray="6 6" class="traffic-cable-fast" />
      `;

      // Cable 3: Sentinel NOC -> PVE (Telemetry Link)
      cablesHtml += `
        <path d="M ${nocX - 85} ${nocY} L ${pveX + 85} ${nocY}" 
              stroke="#8b5cf6" stroke-width="2" stroke-dasharray="4 4" fill="none" opacity="0.8" class="traffic-cable" />
        <rect x="475" y="${nocY - 10}" width="50" height="20" rx="6" fill="#0f172a" stroke="#8b5cf6" stroke-width="1" opacity="0.9"/>
        <text x="500" y="${nocY + 3}" fill="#c084fc" font-size="9" font-family="monospace" text-anchor="middle" font-weight="bold">TELEMETRY</text>
      `;

      // Cables 4: PVE -> Guest VMs
      guestVms.forEach((vm, idx) => {
        const vmX = startX + (idx * stepX);
        const isOnline = vm.is_online !== false;
        const cableColor = isOnline ? "#f59e0b" : "#f43f5e";
        const pulseColor = isOnline ? "#fbbf24" : "#fda4af";

        cablesHtml += `
          <path d="M ${pveX} ${pveY + 25} C ${pveX} ${pveY + 75}, ${vmX} ${vmY - 55}, ${vmX} ${vmY - 25}" 
                stroke="${cableColor}" stroke-width="1.8" fill="none" opacity="0.45" />
          <path d="M ${pveX} ${pveY + 25} C ${pveX} ${pveY + 75}, ${vmX} ${vmY - 55}, ${vmX} ${vmY - 25}" 
                stroke="${pulseColor}" stroke-width="1.8" fill="none" stroke-dasharray="5 5" class="traffic-cable" />
        `;
      });

      // SVG Nodes Rendering
      let nodesHtml = '';

      // 1. Router Node (Center Top)
      nodesHtml += `
        <g class="cursor-pointer group">
          <rect x="${routerX - 90}" y="${routerY - 22}" width="180" height="44" rx="12" 
                fill="#0b1329" stroke="#3b82f6" stroke-width="1.5" class="transition-all filter drop-shadow-md group-hover:stroke-blue-400" />
          <circle cx="${routerX - 66}" cy="${routerY}" r="13" fill="#1e3a8a" stroke="#3b82f6" stroke-width="1.5"/>
          <text x="${routerX - 66}" y="${routerY + 4}" fill="#93c5fd" font-size="11" font-family="sans-serif" text-anchor="middle" font-weight="bold">⚡</text>
          
          <text x="${routerX - 44}" y="${routerY - 3}" fill="#ffffff" font-size="11" font-family="sans-serif" font-weight="bold">Gateway Router</text>
          <text x="${routerX - 44}" y="${routerY + 11}" fill="#60a5fa" font-size="10" font-family="monospace">10.10.10.1 • Core</text>
          
          <circle cx="${routerX + 72}" cy="${routerY}" r="4" fill="#10b981" />
          <circle cx="${routerX + 72}" cy="${routerY}" r="8" fill="#10b981" opacity="0.3" class="animate-ping" />
        </g>
      `;

      // 2. Master Hypervisor: Proxmox VE (300, 150)
      const pveStatusColor = pveNode.is_online ? "#10b981" : "#f43f5e";
      nodesHtml += `
        <g class="cursor-pointer group" onclick="inspectNodeFromCluster('${pveNode.id}')">
          <rect x="${pveX - 100}" y="${pveY - 28}" width="200" height="56" rx="14" 
                fill="#0f172a" stroke="#f59e0b" stroke-width="1.8" class="transition-all filter drop-shadow-lg group-hover:stroke-amber-400 group-hover:brightness-110" />
          
          <rect x="${pveX - 88}" y="${pveY - 18}" width="36" height="36" rx="10" fill="#78350f" stroke="#f59e0b" stroke-width="1"/>
          <text x="${pveX - 70}" y="${pveY + 5}" fill="#fde68a" font-size="15" text-anchor="middle">👑</text>

          <text x="${pveX - 42}" y="${pveY - 6}" fill="#ffffff" font-size="12" font-family="sans-serif" font-weight="bold">${pveNode.hostname || 'srv-pve'}</text>
          <text x="${pveX - 42}" y="${pveY + 8}" fill="#fbbf24" font-size="10" font-family="monospace">${pveNode.ip} • PVE Master</text>
          <text x="${pveX - 42}" y="${pveY + 20}" fill="#94a3b8" font-size="9" font-family="monospace">CPU ${(pveNode.cpu_pct || 0).toFixed(0)}% • RAM ${(pveNode.ram_pct || 0).toFixed(0)}%</text>

          <circle cx="${pveX + 84}" cy="${pveY}" r="4.5" fill="${pveStatusColor}" />
          ${pveNode.is_online ? `<circle cx="${pveX + 84}" cy="${pveY}" r="8" fill="${pveStatusColor}" opacity="0.3" class="animate-ping" />` : ''}
        </g>
      `;

      // 3. Central Sentinel NOC (700, 150)
      const nocStatusColor = sentinelNode.is_online ? "#10b981" : "#f43f5e";
      nodesHtml += `
        <g class="cursor-pointer group" onclick="inspectNodeFromCluster('${sentinelNode.id}')">
          <rect x="${nocX - 100}" y="${nocY - 28}" width="200" height="56" rx="14" 
                fill="#0f172a" stroke="#06b6d4" stroke-width="1.8" class="transition-all filter drop-shadow-lg group-hover:stroke-cyan-300 group-hover:brightness-110" />
          
          <rect x="${nocX - 88}" y="${nocY - 18}" width="36" height="36" rx="10" fill="#164e63" stroke="#06b6d4" stroke-width="1"/>
          <text x="${nocX - 70}" y="${nocY + 5}" fill="#a5f3fc" font-size="15" text-anchor="middle">🛡️</text>

          <text x="${nocX - 42}" y="${nocY - 6}" fill="#ffffff" font-size="12" font-family="sans-serif" font-weight="bold">${sentinelNode.hostname || 'aidil (NOC)'}</text>
          <text x="${nocX - 42}" y="${nocY + 8}" fill="#22d3ee" font-size="10" font-family="monospace">${sentinelNode.ip} • Sentinel</text>
          <text x="${nocX - 42}" y="${nocY + 20}" fill="#94a3b8" font-size="9" font-family="monospace">CPU ${(sentinelNode.cpu_pct || 0).toFixed(0)}% • RAM ${(sentinelNode.ram_pct || 0).toFixed(0)}%</text>

          <circle cx="${nocX + 84}" cy="${nocY}" r="4.5" fill="${nocStatusColor}" />
          ${sentinelNode.is_online ? `<circle cx="${nocX + 84}" cy="${nocY}" r="8" fill="${nocStatusColor}" opacity="0.3" class="animate-ping" />` : ''}
        </g>
      `;

      // 4. Guest VMs (Bottom Row)
      guestVms.forEach((vm, idx) => {
        const vmX = startX + (idx * stepX);
        const cardW = Math.min(100, Math.max(86, stepX - 12));
        const cardH = 68;
        const isOnline = vm.is_online !== false;
        const nodeColor = isOnline ? "#38bdf8" : "#f43f5e";

        nodesHtml += `
          <g class="cursor-pointer group" onclick="inspectNodeFromCluster('${vm.id}')">
            <rect x="${vmX - cardW / 2}" y="${vmY - 24}" width="${cardW}" height="${cardH}" rx="10" 
                  fill="#0b1120" stroke="${nodeColor}" stroke-width="${isOnline ? '1.2' : '1.8'}" 
                  class="transition-all filter drop-shadow group-hover:brightness-125 group-hover:stroke-white" />
            
            <circle cx="${vmX - cardW / 2 + 10}" cy="${vmY - 14}" r="3" fill="${isOnline ? '#10b981' : '#f43f5e'}" />
            ${isOnline ? `<circle cx="${vmX - cardW / 2 + 10}" cy="${vmY - 14}" r="6" fill="#10b981" opacity="0.2" class="animate-ping" />` : ''}
            
            <text x="${vmX}" y="${vmY - 8}" fill="#ffffff" font-size="10.5" font-family="sans-serif" font-weight="bold" text-anchor="middle">
              ${vm.hostname || vm.id}
            </text>

            <text x="${vmX}" y="${vmY + 6}" fill="#94a3b8" font-size="9" font-family="monospace" text-anchor="middle">
              ${vm.ip || '-'}
            </text>

            <text x="${vmX}" y="${vmY + 20}" fill="#38bdf8" font-size="8.5" font-family="monospace" text-anchor="middle">
              ${(vm.cpu_pct || 0).toFixed(0)}% CPU
            </text>
            <text x="${vmX}" y="${vmY + 32}" fill="#c084fc" font-size="8.5" font-family="monospace" text-anchor="middle">
              ${(vm.ram_pct || 0).toFixed(0)}% RAM
            </text>
          </g>
        `;
      });

      // Assemble full SVG innerHTML
      svg.innerHTML = `
        <defs>
          <style>
            @keyframes cablePulse {
              0% { stroke-dashoffset: 24; }
              100% { stroke-dashoffset: 0; }
            }
            .traffic-cable {
              animation: cablePulse 1.4s linear infinite;
            }
            .traffic-cable-fast {
              animation: cablePulse 0.9s linear infinite;
            }
          </style>
        </defs>
        ${cablesHtml}
        ${nodesHtml}
      `;
    }

    // ========================================================
    //  FLEET RESOURCE STRESS HEATMAP & MATRIX TABLE
    // ========================================================
    let currentHeatmapSortKey = 'cpu';

    function sortHeatmap(key) {
      currentHeatmapSortKey = key;
      // Update UI button highlights
      ['cpu', 'ram', 'disk', 'name'].forEach(k => {
        const btn = document.getElementById(`btnSort${k.charAt(0).toUpperCase() + k.slice(1)}`);
        if (btn) {
          if (k === key) {
            btn.className = "heatmap-sort-btn px-2.5 py-1 text-[11px] font-mono font-semibold rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 hover:bg-blue-600/30 transition";
          } else {
            btn.className = "heatmap-sort-btn px-2.5 py-1 text-[11px] font-mono font-semibold rounded-lg bg-surface-950 text-slate-400 border border-slate-800 hover:text-white transition";
          }
        }
      });

      if (clusterNodesCache && clusterNodesCache.length > 0) {
        renderFleetHeatmap(clusterNodesCache);
      }
    }

    function renderFleetHeatmap(nodes) {
      const tbody = document.getElementById('fleetHeatmapBody');
      if (!tbody) return;

      const safeNodes = (nodes || []).slice();
      
      // Sort based on currentHeatmapSortKey
      safeNodes.sort((a, b) => {
        if (currentHeatmapSortKey === 'cpu') return (b.cpu_pct || 0) - (a.cpu_pct || 0);
        if (currentHeatmapSortKey === 'ram') return (b.ram_pct || 0) - (a.ram_pct || 0);
        if (currentHeatmapSortKey === 'disk') return (b.disk_pct || 0) - (a.disk_pct || 0);
        if (currentHeatmapSortKey === 'name') return (a.hostname || a.id).localeCompare(b.hostname || b.id);
        return 0;
      });

      tbody.innerHTML = safeNodes.map(n => {
        const meta = getNodeRoleMeta(n);
        const isOnline = n.is_online !== false;

        // Stress Color Grader helper
        const getStressBadge = (pct) => {
          const val = pct || 0;
          if (val >= 85) return { bg: 'bg-rose-500/20 border-rose-500/40 text-rose-300', bar: 'bg-rose-500', label: 'CRITICAL' };
          if (val >= 70) return { bg: 'bg-amber-500/20 border-amber-500/40 text-amber-300', bar: 'bg-amber-500', label: 'HIGH' };
          if (val >= 40) return { bg: 'bg-blue-500/20 border-blue-500/40 text-blue-300', bar: 'bg-blue-500', label: 'NORMAL' };
          return { bg: 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300', bar: 'bg-emerald-500', label: 'OPTIMAL' };
        };

        const cpuStress = getStressBadge(n.cpu_pct);
        const ramStress = getStressBadge(n.ram_pct);
        const diskStress = getStressBadge(n.disk_pct);

        const statusBadge = isOnline ? 
          `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5 w-max">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> ONLINE
           </span>` :
          `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center gap-1.5 w-max">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span> OFFLINE
           </span>`;

        // Workloads count
        let workloadsText = '-';
        if (n.vms_count > 0 && n.containers_count > 0) {
          workloadsText = `${n.vms_count} VMs • ${n.containers_count} CT`;
        } else if (n.vms_count > 0) {
          workloadsText = `${n.vms_count} VMs (${n.vms_running || 0} Up)`;
        } else if (n.containers_count > 0) {
          workloadsText = `${n.containers_count} Containers`;
        }

        // Net I/O formatted
        const rx = formatSpeed(n.net_rx_kbps != null ? n.net_rx_kbps : (n.net_rx_rate || 0));
        const tx = formatSpeed(n.net_tx_kbps != null ? n.net_tx_kbps : (n.net_tx_rate || 0));

        return `
          <tr class="hover:bg-surface-850/60 transition-colors">
            <!-- Node & Role -->
            <td class="py-2.5 px-3">
              <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-lg bg-surface-900 border border-slate-700 flex items-center justify-center text-slate-300">
                  <i class="${meta.icon} text-xs"></i>
                </div>
                <div>
                  <div class="font-bold text-white text-xs">${n.hostname || n.id}</div>
                  <div class="text-[10px] text-slate-500 font-mono">${n.ip}</div>
                </div>
              </div>
            </td>

            <!-- Status -->
            <td class="py-2.5 px-3">
              ${statusBadge}
            </td>

            <!-- CPU Stress Tile -->
            <td class="py-2.5 px-3 min-w-[130px]">
              <div class="space-y-1">
                <div class="flex items-center justify-between text-[11px]">
                  <span class="font-bold text-white font-mono">${(n.cpu_pct || 0).toFixed(1)}%</span>
                  <span class="px-1.5 py-0.2 rounded text-[9px] font-bold border ${cpuStress.bg}">${cpuStress.label}</span>
                </div>
                <div class="w-full bg-slate-800/80 rounded-full h-1.5 overflow-hidden">
                  <div class="${cpuStress.bar} h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(100, Math.max(2, n.cpu_pct || 0))}%"></div>
                </div>
                <div class="text-[9px] text-slate-500">${n.cpu_cores || 1} Cores Allocated</div>
              </div>
            </td>

            <!-- RAM Allocation Tile -->
            <td class="py-2.5 px-3 min-w-[130px]">
              <div class="space-y-1">
                <div class="flex items-center justify-between text-[11px]">
                  <span class="font-bold text-white font-mono">${(n.ram_pct || 0).toFixed(1)}%</span>
                  <span class="px-1.5 py-0.2 rounded text-[9px] font-bold border ${ramStress.bg}">${ramStress.label}</span>
                </div>
                <div class="w-full bg-slate-800/80 rounded-full h-1.5 overflow-hidden">
                  <div class="${ramStress.bar} h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(100, Math.max(2, n.ram_pct || 0))}%"></div>
                </div>
                <div class="text-[9px] text-slate-500">${((n.ram_used_mb || 0) / 1024).toFixed(1)} / ${((n.ram_total_mb || 0) / 1024).toFixed(1)} GB</div>
              </div>
            </td>

            <!-- NVMe / Storage -->
            <td class="py-2.5 px-3 min-w-[110px]">
              <div class="space-y-1">
                <div class="flex items-center justify-between text-[11px]">
                  <span class="font-bold text-white font-mono">${(n.disk_pct || 0).toFixed(1)}%</span>
                  <span class="text-[9px] text-slate-500">${n.disk_total_gb > 0 ? `${n.disk_used_gb}/${n.disk_total_gb}GB` : 'Host Pool'}</span>
                </div>
                <div class="w-full bg-slate-800/80 rounded-full h-1.5 overflow-hidden">
                  <div class="${diskStress.bar} h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(100, Math.max(2, n.disk_pct || 0))}%"></div>
                </div>
              </div>
            </td>

            <!-- Workloads -->
            <td class="py-2.5 px-3 text-slate-300 text-xs">
              <span class="px-2 py-1 rounded-lg bg-surface-900 border border-slate-800 text-[11px]">
                ${workloadsText}
              </span>
            </td>

            <!-- Net I/O -->
            <td class="py-2.5 px-3 font-mono text-[10px] text-slate-400">
              <div class="flex items-center gap-1 text-emerald-400">
                <i class="fa-solid fa-arrow-down text-[8px]"></i> <span>${rx}</span>
              </div>
              <div class="flex items-center gap-1 text-cyan-400">
                <i class="fa-solid fa-arrow-up text-[8px]"></i> <span>${tx}</span>
              </div>
            </td>

            <!-- Action -->
            <td class="py-2.5 px-3 text-right">
              <button onclick="inspectNodeFromCluster('${n.id}')" class="px-2.5 py-1 rounded-lg bg-surface-800 hover:bg-blue-600/30 text-blue-400 hover:text-blue-300 font-semibold transition text-[11px] border border-slate-700 inline-flex items-center gap-1">
                <span>Detail</span> <i class="fa-solid fa-arrow-right text-[9px]"></i>
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }

    // --- NETWORK SECURITY & OPEN PORTS AUDIT ---
    let allPortsCache = [];
    let currentPortFilter = 'ALL';

    function renderOpenPorts(ports) {
      allPortsCache = ports || [];
      
      const total = allPortsCache.length;
      const publicCount = allPortsCache.filter(p => p.bind_type && p.bind_type.includes('Public')).length;
      const localCount = allPortsCache.filter(p => p.bind_type && p.bind_type.includes('Localhost')).length;
      const warningCount = allPortsCache.filter(p => p.risk_level === 'DANGER' || p.risk_level === 'WARNING').length;

      const elTotal = document.getElementById('statTotalPorts');
      if (elTotal) elTotal.innerText = total;
      const elPub = document.getElementById('statPublicPorts');
      if (elPub) elPub.innerText = publicCount;
      const elLoc = document.getElementById('statLocalPorts');
      if (elLoc) elLoc.innerText = localCount;
      const elWarn = document.getElementById('statFlaggedPorts');
      if (elWarn) elWarn.innerText = warningCount;
      const elBadge = document.getElementById('portsCountBadge');
      if (elBadge) elBadge.innerText = `${total} Ports Active`;

      filterPorts(currentPortFilter);
    }

    function filterPorts(filter) {
      currentPortFilter = filter;
      ['ALL', 'PUBLIC', 'LOCAL', 'WARNING'].forEach(f => {
        const btn = document.getElementById(`portTab${f.charAt(0) + f.slice(1).toLowerCase()}`);
        if (btn) {
          if (f === filter) {
            btn.className = "px-3 py-1 font-medium rounded-lg bg-surface-800 text-white transition";
          } else {
            btn.className = "px-3 py-1 font-medium rounded-lg text-slate-400 hover:text-white transition";
          }
        }
      });

      const tbody = document.getElementById('portsTableBody');
      if (!tbody) return;

      let filtered = allPortsCache;
      if (filter === 'PUBLIC') {
        filtered = filtered.filter(p => p.bind_type && p.bind_type.includes('Public'));
      } else if (filter === 'LOCAL') {
        filtered = filtered.filter(p => p.bind_type && p.bind_type.includes('Localhost'));
      } else if (filter === 'WARNING') {
        filtered = filtered.filter(p => p.risk_level === 'DANGER' || p.risk_level === 'WARNING');
      }

      if (!filtered.length) {
        tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-500 text-xs">No open ports match the selected filter.</td></tr>`;
        return;
      }

      tbody.innerHTML = filtered.map(p => {
        let riskBadge = '';
        if (p.risk_level === 'DANGER') {
          riskBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center gap-1 w-fit"><i class="fa-solid fa-triangle-exclamation"></i> CRITICAL EXPOSURE</span>`;
        } else if (p.risk_level === 'WARNING') {
          riskBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1 w-fit"><i class="fa-solid fa-circle-exclamation"></i> WARNING</span>`;
        } else if (p.risk_level === 'INFO') {
          riskBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/30 flex items-center gap-1 w-fit"><i class="fa-solid fa-key"></i> SSH / REMOTE</span>`;
        } else if (p.risk_level === 'SAFE') {
          riskBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 w-fit"><i class="fa-solid fa-shield-halved"></i> SECURE LOCAL</span>`;
        } else {
          riskBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-500/10 text-slate-400 border border-slate-500/30 flex items-center gap-1 w-fit">STANDARD</span>`;
        }

        const isPub = p.bind_type && p.bind_type.includes('Public');
        const bindBadge = isPub 
          ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">0.0.0.0 Public</span>` 
          : `<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">127.0.0.1 Local</span>`;

        return `
          <tr class="hover:bg-surface-850/60 transition-colors">
            <td class="py-2.5 px-3">
              <div class="flex items-center gap-2">
                <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 font-mono">${p.proto}</span>
                <span class="font-bold text-white font-mono text-sm">${p.port}</span>
              </div>
            </td>
            <td class="py-2.5 px-3">
              <div class="font-semibold text-slate-200">${p.service}</div>
            </td>
            <td class="py-2.5 px-3 text-slate-300">
              <span class="font-mono text-slate-200 font-semibold">${p.process || '-'}</span>
              ${p.pid ? `<span class="text-slate-500 text-[10px] ml-1 font-mono">[PID ${p.pid}]</span>` : ''}
            </td>
            <td class="py-2.5 px-3">
              <div class="flex items-center gap-1.5">
                ${bindBadge}
                <span class="text-slate-400 text-[11px] font-mono">${p.ip}</span>
              </div>
            </td>
            <td class="py-2.5 px-3">
              <div class="space-y-1">
                ${riskBadge}
                <div class="text-[10px] text-slate-400 font-sans">${p.risk_desc || ''}</div>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }

    // --- QUICK ACTION CONTROLS ---
    let pendingActionData = null;

    function confirmAction(actionType, target, title, desc = null) {
      const activeNodeId = currentActiveNodeId || (currentDashboardData && currentDashboardData.active_node_id) || 'Current Node';
      pendingActionData = {
        server_id: activeNodeId,
        action: actionType,
        target: target
      };

      document.getElementById('modalActionTitle').innerText = title || 'Confirm Remote Action';
      document.getElementById('modalActionNode').innerText = activeNodeId;
      document.getElementById('modalActionType').innerText = actionType;
      document.getElementById('modalActionTarget').innerText = target;
      if (desc) {
        document.getElementById('modalActionDesc').innerText = desc;
      } else {
        document.getElementById('modalActionDesc').innerText = `Execute ${actionType} on target '${target}' across node ${activeNodeId}.`;
      }

      document.getElementById('actionModal').classList.remove('hidden');
    }

    function closeActionModal() {
      document.getElementById('actionModal').classList.add('hidden');
      pendingActionData = null;
    }

    async function executeConfirmedAction() {
      if (!pendingActionData) return;
      const btn = document.getElementById('modalConfirmBtn');
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Executing...`;

      try {
        const res = await fetch('/api/v1/action/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(pendingActionData)
        });
        const result = await res.json();
        
        closeActionModal();
        if (result.status === 'success' || result.status === 'queued') {
          showToast(result.message || 'Action dispatched successfully!', 'success');
          setTimeout(fetchDashboard, 1200);
        } else {
          showToast(result.message || 'Action failed to execute.', 'error');
        }
      } catch (err) {
        closeActionModal();
        showToast(`Action execution network error: ${err.message}`, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>Confirm & Execute</span><i class="fa-solid fa-arrow-right"></i>`;
      }
    }

    function showToast(message, type = 'success') {
      const container = document.getElementById('toastContainer');
      if (!container) return;

      const toast = document.createElement('div');
      const bg = type === 'success' 
        ? 'bg-surface-900 border border-emerald-500/50 text-emerald-300' 
        : 'bg-surface-900 border border-rose-500/50 text-rose-300';
      const icon = type === 'success' ? 'fa-circle-check text-emerald-400' : 'fa-triangle-exclamation text-rose-400';

      toast.className = `p-3.5 rounded-xl shadow-2xl flex items-center gap-3 text-xs font-mono pointer-events-auto transition-all duration-300 translate-y-2 opacity-0 ${bg}`;
      toast.innerHTML = `
        <i class="fa-solid ${icon} text-base flex-shrink-0"></i>
        <div class="flex-1 font-sans text-slate-200 text-xs">${message}</div>
      `;

      container.appendChild(toast);
      setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
      }, 10);

      setTimeout(() => {
        toast.classList.add('translate-y-2', 'opacity-0');
        setTimeout(() => toast.remove(), 350);
      }, 4500);
    }

    // Cluster Fleet Matrix Management
    let currentDashboardView = 'single'; // 'single' or 'cluster'

    function switchDashboardView(view) {
      currentDashboardView = view;
      const singleEl = document.getElementById('singleNodeView');
      const clusterEl = document.getElementById('clusterFleetView');
      const btnSingle = document.getElementById('viewBtnSingle');
      const btnCluster = document.getElementById('viewBtnCluster');
      const hostSub = document.getElementById('hostSubtitle');

      if (view === 'cluster') {
        singleEl.classList.add('hidden');
        clusterEl.classList.remove('hidden');
        btnSingle.className = "px-3.5 py-1.5 font-semibold rounded-lg text-slate-400 hover:text-white transition-all flex items-center gap-2";
        btnCluster.className = "px-3.5 py-1.5 font-semibold rounded-lg bg-blue-600 text-white transition-all flex items-center gap-2 shadow-sm";
        if (hostSub) hostSub.innerText = "Cluster Fleet Overview";
        fetchClusterOverview();
      } else {
        clusterEl.classList.add('hidden');
        singleEl.classList.remove('hidden');
        btnSingle.className = "px-3.5 py-1.5 font-semibold rounded-lg bg-blue-600 text-white transition-all flex items-center gap-2 shadow-sm";
        btnCluster.className = "px-3.5 py-1.5 font-semibold rounded-lg text-slate-400 hover:text-white transition-all flex items-center gap-2";
        fetchDashboard();
      }
    }

    function inspectNodeFromCluster(nodeId) {
      selectNode(nodeId);
      switchDashboardView('single');
    }

    // ==========================================
    //  CLUSTER FLEET MONITORING & TELEMETRY
    // ==========================================
    clusterNodesCache = [];
    let currentClusterFilter = 'all';
    let currentClusterSearch = '';

    function copyIpToClipboard(ip, btnEl) {
      if (!navigator.clipboard) {
        showToast(`IP: ${ip}`, 'info');
        return;
      }
      navigator.clipboard.writeText(ip).then(() => {
        showToast(`Copied ${ip} to clipboard`, 'success');
        if (btnEl) {
          const original = btnEl.innerHTML;
          btnEl.innerHTML = `<span>${ip}</span> <i class="fa-solid fa-check text-emerald-400 text-[10px]"></i>`;
          setTimeout(() => { btnEl.innerHTML = original; }, 1800);
        }
      }).catch(() => {
        showToast(`IP: ${ip}`, 'info');
      });
    }

    function getNodeRoleMeta(node) {
      const hostname = (node.hostname || '').toLowerCase();
      const id = (node.id || '').toLowerCase();
      
      if (id === 'srv-pve' || hostname === 'pve') {
        return {
          isMaster: true,
          roleTitle: '👑 PROXMOX VE HYPERVISOR MASTER',
          roleShort: 'PVE HYPERVISOR',
          badgeClass: 'bg-amber-500/15 text-amber-300 border border-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.2)]',
          icon: 'fa-solid fa-chess-king text-amber-400',
          borderClass: 'border-amber-500/40 bg-gradient-to-b from-amber-500/[0.05] via-surface-900/90 to-surface-950/95 shadow-[0_4px_30px_rgba(245,158,11,0.1)] hover:border-amber-400/80',
          iconBg: 'bg-amber-500/10 border-amber-500/30 text-amber-400'
        };
      }
      if (id === 'srv-host-node' || hostname === 'aidil') {
        return {
          isMaster: false,
          roleTitle: '🛡️ CENTRAL NOC SERVER',
          roleShort: 'CENTRAL NOC',
          badgeClass: 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(6,182,212,0.2)]',
          icon: 'fa-solid fa-shield-halved text-cyan-400',
          borderClass: 'border-cyan-500/30 bg-gradient-to-b from-cyan-500/[0.04] via-surface-900/90 to-surface-950/95 hover:border-cyan-500/60 shadow-sm',
          iconBg: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
        };
      }
      if (hostname === 'database') {
        return {
          isMaster: false,
          roleTitle: '🗄️ POSTGRESQL / DATA ENGINE',
          roleShort: 'DATABASE',
          badgeClass: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
          icon: 'fa-solid fa-database text-emerald-400',
          borderClass: 'border-slate-800/90 hover:border-emerald-500/50 bg-surface-900/90',
          iconBg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
        };
      }
      if (hostname === 'immich') {
        return {
          isMaster: false,
          roleTitle: '📸 IMMICH PHOTOS & AI ENGINE',
          roleShort: 'MEDIA / AI',
          badgeClass: 'bg-purple-500/15 text-purple-300 border border-purple-500/30',
          icon: 'fa-solid fa-images text-purple-400',
          borderClass: 'border-slate-800/90 hover:border-purple-500/50 bg-surface-900/90',
          iconBg: 'bg-purple-500/10 border-purple-500/30 text-purple-400'
        };
      }
      if (hostname === 'proxy') {
        return {
          isMaster: false,
          roleTitle: '🌐 EDGE REVERSE PROXY / WAF',
          roleShort: 'EDGE PROXY',
          badgeClass: 'bg-blue-500/15 text-blue-300 border border-blue-500/30',
          icon: 'fa-solid fa-globe text-blue-400',
          borderClass: 'border-slate-800/90 hover:border-blue-500/50 bg-surface-900/90',
          iconBg: 'bg-blue-500/10 border-blue-500/30 text-blue-400'
        };
      }
      if (hostname === 'pentest') {
        return {
          isMaster: false,
          roleTitle: '🎯 SECURITY & PEN-TEST LAB',
          roleShort: 'SEC LAB',
          badgeClass: 'bg-rose-500/15 text-rose-300 border border-rose-500/30',
          icon: 'fa-solid fa-crosshairs text-rose-400',
          borderClass: 'border-slate-800/90 hover:border-rose-500/50 bg-surface-900/90',
          iconBg: 'bg-rose-500/10 border-rose-500/30 text-rose-400'
        };
      }
      if (hostname === 'ceritakota') {
        return {
          isMaster: false,
          roleTitle: '🏙️ CERITAKOTA APP SERVICE',
          roleShort: 'WEB APP',
          badgeClass: 'bg-sky-500/15 text-sky-300 border border-sky-500/30',
          icon: 'fa-solid fa-cube text-sky-400',
          borderClass: 'border-slate-800/90 hover:border-sky-500/50 bg-surface-900/90',
          iconBg: 'bg-sky-500/10 border-sky-500/30 text-sky-400'
        };
      }
      if (hostname === 'sekar') {
        return {
          isMaster: false,
          roleTitle: '💼 PORTFOLIO SEKAR APP',
          roleShort: 'WEB APP',
          badgeClass: 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30',
          icon: 'fa-solid fa-layer-group text-indigo-400',
          borderClass: 'border-slate-800/90 hover:border-indigo-500/50 bg-surface-900/90',
          iconBg: 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
        };
      }
      if (hostname === 'pambuluah') {
        return {
          isMaster: false,
          roleTitle: '⚡ PAMBULUAH SERVICES',
          roleShort: 'SERVICES',
          badgeClass: 'bg-teal-500/15 text-teal-300 border border-teal-500/30',
          icon: 'fa-solid fa-bolt text-teal-400',
          borderClass: 'border-slate-800/90 hover:border-teal-500/50 bg-surface-900/90',
          iconBg: 'bg-teal-500/10 border-teal-500/30 text-teal-400'
        };
      }
      return {
        isMaster: false,
        roleTitle: '📦 CLUSTER GUEST VM',
        roleShort: 'GUEST VM',
        badgeClass: 'bg-slate-700/40 text-slate-300 border border-slate-700/60',
        icon: 'fa-solid fa-server text-cyan-400',
        borderClass: 'border-slate-800/90 hover:border-cyan-500/40 bg-surface-900/90',
        iconBg: 'bg-surface-950 border-slate-800 text-slate-400'
      };
    }

    function setClusterFilter(filterKey) {
      currentClusterFilter = filterKey;
      document.querySelectorAll('.cluster-filter-btn').forEach(btn => {
        if (btn.getAttribute('data-filter') === filterKey) {
          btn.className = "cluster-filter-btn px-2.5 py-1 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 font-semibold transition";
        } else {
          btn.className = "cluster-filter-btn px-2.5 py-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition";
        }
      });
      renderFilteredClusterCards();
    }

    function handleClusterSearchFilter() {
      const input = document.getElementById('clusterNodeSearch');
      currentClusterSearch = (input ? input.value : '').trim().toLowerCase();
      renderFilteredClusterCards();
    }

    function renderFilteredClusterCards() {
      const grid = document.getElementById('clusterNodesGrid');
      if (!grid) return;

      const filtered = clusterNodesCache.filter(n => {
        const meta = getNodeRoleMeta(n);
        // Filter by category
        if (currentClusterFilter === 'hypervisor' && !meta.isMaster && n.hostname !== 'pve') return false;
        if (currentClusterFilter === 'docker' && !(n.containers_count > 0)) return false;
        if (currentClusterFilter === 'vms' && (n.id === 'srv-pve' || n.id === 'srv-host-node')) return false;

        // Search text
        if (currentClusterSearch) {
          const q = currentClusterSearch;
          const match = (n.hostname || '').toLowerCase().includes(q) ||
                        (n.ip || '').toLowerCase().includes(q) ||
                        (n.id || '').toLowerCase().includes(q) ||
                        (n.os || '').toLowerCase().includes(q) ||
                        meta.roleTitle.toLowerCase().includes(q);
          if (!match) return false;
        }
        return true;
      });

      if (filtered.length === 0) {
        grid.innerHTML = `
          <div class="col-span-full py-12 text-center bg-surface-900/40 rounded-2xl border border-slate-800/80">
            <i class="fa-solid fa-filter-circle-xmark text-3xl text-slate-600 mb-3"></i>
            <h4 class="text-sm font-bold text-slate-300">Tidak ada node yang cocok</h4>
            <p class="text-xs text-slate-500 mt-1">Coba sesuaikan pencarian atau pilih filter "All" di atas.</p>
            <button onclick="document.getElementById('clusterNodeSearch').value=''; currentClusterSearch=''; setClusterFilter('all');" class="mt-4 px-3 py-1.5 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 text-xs font-semibold hover:bg-blue-600/30 transition">
              Reset Filter
            </button>
          </div>
        `;
        return;
      }

      grid.innerHTML = filtered.map(n => {
        const meta = getNodeRoleMeta(n);
        const isOnline = n.is_online;
        const statusBadge = isOnline ? 
          `<span class="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 flex items-center gap-1.5 shadow-[0_0_8px_rgba(16,185,129,0.2)]"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>ONLINE</span>` :
          `<span class="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/40 flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>OFFLINE</span>`;

        let cpuColor = "from-blue-500 to-indigo-500";
        let cpuTextClass = "text-blue-400";
        if (n.cpu_pct > 80) { cpuColor = "from-rose-500 to-red-600"; cpuTextClass = "text-rose-400"; }
        else if (n.cpu_pct > 50) { cpuColor = "from-amber-500 to-orange-500"; cpuTextClass = "text-amber-400"; }

        let ramColor = "from-purple-500 via-fuchsia-500 to-pink-500";
        let ramTextClass = "text-purple-400";
        if (n.ram_pct > 85) { ramColor = "from-rose-500 to-red-600"; ramTextClass = "text-rose-400"; }
        else if (n.ram_pct > 70) { ramColor = "from-amber-500 to-orange-500"; ramTextClass = "text-amber-400"; }

        // Workloads tags
        let workloadBadges = [];
        if (n.vms_count > 0) {
          workloadBadges.push(`<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/15 text-blue-300 border border-blue-500/30 flex items-center gap-1"><i class="fa-solid fa-cube text-[9px] text-blue-400"></i>${n.vms_count} VMs (${n.vms_running || 0} Up)</span>`);
        }
        if (n.containers_count > 0) {
          workloadBadges.push(`<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 flex items-center gap-1"><i class="fa-brands fa-docker text-[10px] text-cyan-400"></i>${n.containers_count} Containers (${n.containers_running || 0} Up)</span>`);
        }
        if (!workloadBadges.length) {
          workloadBadges.push(`<span class="px-2 py-0.5 rounded text-[10px] font-mono text-slate-400 bg-surface-950/60 border border-slate-800">Native Process</span>`);
        }

        const l1 = Number(n.load_1m || 0).toFixed(2);
        const l5 = Number(n.load_5m || 0).toFixed(2);
        const l15 = Number(n.load_15m || 0).toFixed(2);

        const ramUsedGb = (n.ram_used_mb / 1024).toFixed(1);
        const ramTotalGb = (n.ram_total_mb / 1024).toFixed(1);
        const ramFreeGb = Math.max(0, (n.ram_total_mb - n.ram_used_mb) / 1024).toFixed(1);

        const isMaster = meta.isMaster;

        return `
          <div class="relative overflow-hidden ${meta.borderClass} rounded-2xl p-5 shadow-sm transition-all duration-300 flex flex-col justify-between group">
            
            ${isMaster ? `
              <div class="absolute top-0 right-0 transform translate-x-8 -translate-y-8 w-28 h-28 bg-amber-500/10 rounded-full blur-2xl pointer-events-none"></div>
            ` : ''}

            <div>
              <!-- Node Header Bar -->
              <div class="flex items-start justify-between pb-3.5 mb-3.5 border-b border-slate-800/80">
                <div class="flex items-start gap-3">
                  <div class="w-11 h-11 rounded-xl ${meta.iconBg} border flex items-center justify-center font-bold shadow-inner group-hover:scale-105 transition-transform duration-300 flex-shrink-0">
                    <i class="${meta.icon} text-lg"></i>
                  </div>
                  <div>
                    <div class="flex items-center gap-2 flex-wrap">
                      <h4 class="font-extrabold text-white text-base group-hover:text-cyan-300 transition tracking-tight">${n.hostname}</h4>
                      <span class="px-2 py-0.5 rounded text-[9px] font-mono font-bold tracking-wider uppercase ${meta.badgeClass}">
                        ${meta.roleShort}
                      </span>
                    </div>

                    <div class="flex items-center gap-2 mt-1.5 flex-wrap">
                      <!-- Clickable IP badge -->
                      <button onclick="copyIpToClipboard('${n.ip}', this)" class="inline-flex items-center gap-1.5 text-[11px] font-mono text-slate-300 hover:text-white bg-surface-950/80 hover:bg-cyan-500/20 px-2 py-0.5 rounded-md border border-slate-800 hover:border-cyan-500/40 transition group/ip" title="Klik untuk copy IP">
                        <i class="fa-solid fa-network-wired text-[9px] text-cyan-400"></i>
                        <span>${n.ip}</span>
                        <i class="fa-regular fa-copy text-[9px] text-slate-500 group-hover/ip:text-cyan-300 transition"></i>
                      </button>

                      <span class="text-[11px] text-slate-400 font-sans truncate max-w-[130px]" title="${n.os}">
                        ${n.os}
                      </span>
                    </div>
                  </div>
                </div>

                <div class="flex flex-col items-end gap-1.5">
                  ${statusBadge}
                  <span class="text-[10px] font-mono text-slate-400">${n.cpu_cores} vCPU Core${n.cpu_cores > 1 ? 's' : ''}</span>
                </div>
              </div>

              <!-- 2x2 High-Tech Micro Telemetry Grid -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mb-3">
                
                <!-- CPU Micro-Module -->
                <div class="bg-surface-950/80 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
                  <div class="flex items-center justify-between text-[11px]">
                    <span class="font-semibold text-slate-400 flex items-center gap-1.5">
                      <i class="fa-solid fa-microchip text-indigo-400 text-[10px]"></i> Compute
                    </span>
                    <span class="font-mono font-black ${cpuTextClass}">${(n.cpu_pct || 0).toFixed(1)}%</span>
                  </div>
                  <div class="w-full bg-slate-900 rounded-full h-1.5 my-2 overflow-hidden border border-slate-800/60 p-[1px]">
                    <div class="bg-gradient-to-r ${cpuColor} h-full rounded-full transition-all duration-500" style="width: ${Math.min(100, Math.max(2, n.cpu_pct))}%"></div>
                  </div>
                  <div class="text-[10px] font-mono text-slate-500 truncate" title="1m, 5m, 15m load average">
                    Load: <span class="text-slate-300">${l1}</span>, <span class="text-slate-400">${l5}</span>, <span class="text-slate-500">${l15}</span>
                  </div>
                </div>

                <!-- RAM Micro-Module -->
                <div class="bg-surface-950/80 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
                  <div class="flex items-center justify-between text-[11px]">
                    <span class="font-semibold text-slate-400 flex items-center gap-1.5">
                      <i class="fa-solid fa-memory text-purple-400 text-[10px]"></i> Memory
                    </span>
                    <span class="font-mono font-black ${ramTextClass}">${(n.ram_pct || 0).toFixed(1)}%</span>
                  </div>
                  <div class="w-full bg-slate-900 rounded-full h-1.5 my-2 overflow-hidden border border-slate-800/60 p-[1px]">
                    <div class="bg-gradient-to-r ${ramColor} h-full rounded-full transition-all duration-500" style="width: ${Math.min(100, Math.max(2, n.ram_pct))}%"></div>
                  </div>
                  <div class="text-[10px] font-mono text-slate-400 flex justify-between">
                    <span>${ramUsedGb} / ${ramTotalGb} GB</span>
                    <span class="text-purple-400/80">${ramFreeGb}G Free</span>
                  </div>
                </div>

                <!-- Storage Disk Micro-Module -->
                <div class="bg-surface-950/80 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
                  <div class="flex items-center justify-between text-[11px]">
                    <span class="font-semibold text-slate-400 flex items-center gap-1.5">
                      <i class="fa-solid fa-hard-drive text-emerald-400 text-[10px]"></i> Storage
                    </span>
                    <span class="font-mono font-black text-emerald-400">
                      ${n.disk_total_gb > 0 ? (n.disk_pct || 0).toFixed(1) + '%' : 'ZFS / LVM'}
                    </span>
                  </div>
                  <div class="w-full bg-slate-900 rounded-full h-1.5 my-2 overflow-hidden border border-slate-800/60 p-[1px]">
                    <div class="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full transition-all duration-500" style="width: ${Math.min(100, Math.max(2, n.disk_pct || (isMaster ? 25 : 5)))}%"></div>
                  </div>
                  <div class="text-[10px] font-mono text-slate-400 flex justify-between">
                    <span>${n.disk_total_gb > 0 ? `${n.disk_used_gb} / ${n.disk_total_gb} GB` : 'Hypervisor Pool'}</span>
                    <span class="text-emerald-400/80">${n.disk_total_gb > 0 ? `${Math.max(0, n.disk_total_gb - n.disk_used_gb).toFixed(1)}G Free` : 'Host Root'}</span>
                  </div>
                </div>

                <!-- Network I/O Micro-Module -->
                <div class="bg-surface-950/80 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
                  <div class="flex items-center justify-between text-[11px]">
                    <span class="font-semibold text-slate-400 flex items-center gap-1.5">
                      <i class="fa-solid fa-arrows-up-down text-cyan-400 text-[10px]"></i> Network I/O
                    </span>
                    <span class="text-[10px] font-mono text-cyan-300 font-bold">Live</span>
                  </div>
                  <div class="pt-2 mt-1 flex items-center justify-between text-[10px] font-mono text-slate-300">
                    <span class="flex items-center gap-1" title="Download throughput">
                      <i class="fa-solid fa-arrow-down text-cyan-400 text-[9px]"></i> ${(n.net_rx_kbps || 0).toFixed(0)} <span class="text-slate-500">KB/s</span>
                    </span>
                    <span class="flex items-center gap-1" title="Upload throughput">
                      <i class="fa-solid fa-arrow-up text-indigo-400 text-[9px]"></i> ${(n.net_tx_kbps || 0).toFixed(0)} <span class="text-slate-500">KB/s</span>
                    </span>
                  </div>
                </div>

              </div>

              <!-- Workloads Summary Row -->
              <div class="bg-surface-950/60 border border-slate-800/60 rounded-xl px-3 py-2 flex items-center justify-between text-[11px] mb-1">
                <span class="text-slate-400 font-sans flex items-center gap-1.5">
                  <i class="fa-solid fa-layer-group text-slate-500 text-[10px]"></i> Workloads:
                </span>
                <div class="flex items-center gap-1.5 flex-wrap justify-end">
                  ${workloadBadges.join('')}
                </div>
              </div>

            </div>

            <!-- Card Bottom Action Bar -->
            <div class="pt-3 mt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
              <span class="text-[10px] text-slate-400 font-mono flex items-center gap-1.5" title="Server Uptime">
                <i class="fa-solid fa-clock text-slate-500 text-[10px]"></i> Up: <b class="text-slate-300 font-semibold">${n.uptime_human}</b>
              </span>
              <div class="flex items-center gap-2">
                <button onclick="openTerminalModal('${n.id}')" title="Buka Interactive Terminal Shell di ${n.hostname}" class="px-2.5 py-1.5 rounded-xl bg-surface-950 hover:bg-cyan-500/20 text-cyan-400 border border-slate-800 hover:border-cyan-500/40 font-semibold transition flex items-center gap-1.5 text-[11px] font-mono shadow-sm">
                  <i class="fa-solid fa-terminal text-[10px]"></i> Shell
                </button>
                <button onclick="inspectNodeFromCluster('${n.id}')" class="px-3 py-1.5 rounded-xl bg-blue-600/15 hover:bg-blue-600/25 text-blue-400 border border-blue-500/30 font-semibold transition flex items-center gap-1.5 text-[11px] hover:border-blue-400/50 shadow-sm">
                  <span>Detail Node</span> <i class="fa-solid fa-arrow-right text-[9px]"></i>
                </button>
              </div>
            </div>

          </div>
        `;
      }).join('');
    }

    async function fetchClusterOverview() {
      const spinner = document.getElementById('clusterRefreshSpinner');
      if (spinner) spinner.classList.add('animate-spin');
      try {
        const res = await fetch('/api/v1/cluster/overview');
        const data = await res.json();
        renderClusterOverview(data);
      } catch (err) {
        console.error("Cluster overview fetch error:", err);
      } finally {
        if (spinner) {
          setTimeout(() => spinner.classList.remove('animate-spin'), 600);
        }
      }
    }

    function renderClusterOverview(data) {
      const summary = data.summary || {};
      const nodes = (data.nodes || []).slice();
      nodes.sort((a, b) => {
        if (a.id === 'srv-host-node') return -1;
        if (b.id === 'srv-host-node') return 1;
        if (a.id === 'srv-pve') return -1;
        if (b.id === 'srv-pve') return 1;
        return (a.hostname || a.id).localeCompare(b.hostname || b.id);
      });

      clusterNodesCache = nodes;

      // Update badge in navbar
      const badge = document.getElementById('clusterTotalBadge');
      if (badge) badge.innerText = nodes.length;

      // Sync dropdown selector with all discovered nodes
      registeredNodesCache = nodes;
      const nodeCountBadge = document.getElementById('nodeCountBadge');
      if (nodeCountBadge) nodeCountBadge.innerText = `${nodes.length} Node${nodes.length > 1 ? 's' : ''}`;
      renderNodeDropdownList(nodes, selectedServerId || (activeServerData ? activeServerData.id : (nodes[0] ? nodes[0].id : '')));

      // Update clock and uptime badge
      const timeEl = document.getElementById('lastUpdatedTime');
      if (timeEl) timeEl.innerText = (new Date()).toLocaleTimeString();
      const upVal = document.getElementById('headerUptimeVal');
      if (upVal) upVal.innerText = `${summary.online_nodes || 0}/${summary.total_nodes || 0} Up`;

      // Update Top KPIs
      const onlineNodesEl = document.getElementById('clusterOnlineNodes');
      if (onlineNodesEl) onlineNodesEl.innerText = `${summary.online_nodes || 0} / ${summary.total_nodes || 0}`;
      
      const offlineNodesEl = document.getElementById('clusterOfflineNodes');
      if (offlineNodesEl) offlineNodesEl.innerText = summary.offline_nodes || 0;
      
      const nodesPill = document.getElementById('clusterNodesPill');
      if (nodesPill) {
        if (summary.offline_nodes > 0) {
          nodesPill.className = "px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/40 flex items-center gap-1";
          nodesPill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> ${summary.offline_nodes} DEGRADED`;
        } else {
          nodesPill.className = "px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 flex items-center gap-1";
          nodesPill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> 100% HEALTHY`;
        }
      }

      const totalCoresEl = document.getElementById('clusterTotalCores');
      if (totalCoresEl) totalCoresEl.innerText = `${summary.total_cpu_cores || 0} Cores`;
      
      const avgCpuEl = document.getElementById('clusterAvgCpu');
      if (avgCpuEl) avgCpuEl.innerText = `${(summary.avg_cpu_pct || 0).toFixed(1)}%`;
      
      const cpuBarEl = document.getElementById('clusterCpuBar');
      if (cpuBarEl) cpuBarEl.style.width = `${Math.min(100, Math.max(2, summary.avg_cpu_pct || 0))}%`;

      const ramUsedTotalEl = document.getElementById('clusterRamUsedTotal');
      if (ramUsedTotalEl) ramUsedTotalEl.innerText = `${summary.total_ram_used_gb || 0} / ${summary.total_ram_gb || 0} GB`;
      
      const ramPctEl = document.getElementById('clusterRamPctText');
      if (ramPctEl) ramPctEl.innerText = `${summary.cluster_ram_pct || 0}%`;
      
      const ramBarEl = document.getElementById('clusterRamBar');
      if (ramBarEl) ramBarEl.style.width = `${Math.min(100, Math.max(2, summary.cluster_ram_pct || 0))}%`;

      const ramFreeEl = document.getElementById('clusterRamFreeText');
      if (ramFreeEl && summary.total_ram_gb && summary.total_ram_used_gb) {
        const freeGb = Math.max(0, summary.total_ram_gb - summary.total_ram_used_gb).toFixed(1);
        ramFreeEl.innerText = `~${freeGb} GB Headroom`;
      }

      const totalWorkloads = (summary.total_vms || 0) + (summary.total_containers || 0);
      const totalWorkloadsEl = document.getElementById('clusterTotalWorkloads');
      if (totalWorkloadsEl) totalWorkloadsEl.innerText = totalWorkloads;
      
      const vmCountEl = document.getElementById('clusterVmCount');
      if (vmCountEl) vmCountEl.innerText = `${summary.total_vms || 0} (${summary.vms_running || 0} Up)`;
      
      const contCountEl = document.getElementById('clusterContainerCount');
      if (contCountEl) contCountEl.innerText = `${summary.total_containers || 0} (${summary.containers_running || 0} Up)`;

      // Update Filter Badges
      const countAll = document.getElementById('filterCountAll');
      if (countAll) countAll.innerText = nodes.length;
      const countPve = document.getElementById('filterCountPve');
      if (countPve) countPve.innerText = nodes.filter(n => n.id === 'srv-pve' || n.hostname === 'pve').length;
      const countDocker = document.getElementById('filterCountDocker');
      if (countDocker) countDocker.innerText = nodes.filter(n => (n.containers_count || 0) > 0).length;
      const countVms = document.getElementById('filterCountVms');
      if (countVms) countVms.innerText = nodes.filter(n => n.id !== 'srv-pve' && n.id !== 'srv-host-node').length;

      // Render the filtered cards
      renderFilteredClusterCards();

      // Render Comparison Table below
      const tbody = document.getElementById('clusterTableBody');
      if (tbody) {
        tbody.innerHTML = nodes.map(n => {
          const meta = getNodeRoleMeta(n);
          const isOnline = n.is_online;
          const statusBadge = isOnline ? 
            `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">ONLINE</span>` :
            `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">OFFLINE</span>`;

          let workloadsStr = '-';
          if (n.vms_count > 0 && n.containers_count > 0) {
            workloadsStr = `${n.vms_count} VMs • ${n.containers_count} Containers`;
          } else if (n.vms_count > 0) {
            workloadsStr = `${n.vms_count} VMs (${n.vms_running || 0} Up)`;
          } else if (n.containers_count > 0) {
            workloadsStr = `${n.containers_count} Containers (${n.containers_running || 0} Up)`;
          }

          return `
            <tr class="hover:bg-surface-850/60 transition-all">
              <td class="py-2.5 px-3">
                <div class="flex items-center gap-2">
                  <i class="${meta.icon} text-xs"></i>
                  <div>
                    <div class="font-bold text-white text-xs">${n.hostname}</div>
                    <div class="text-[10px] text-slate-500 font-mono">${n.id}</div>
                  </div>
                </div>
              </td>
              <td class="py-2.5 px-3">
                <div class="text-slate-200 font-mono text-xs">${n.ip}</div>
                <div class="text-[10px] text-slate-400 font-sans truncate max-w-[150px]">${n.os}</div>
              </td>
              <td class="py-2.5 px-3">
                ${statusBadge}
                <div class="text-[10px] text-slate-500 mt-0.5 font-mono">${n.uptime_human}</div>
              </td>
              <td class="py-2.5 px-3">
                <div class="text-white font-bold text-xs">${(n.cpu_pct || 0).toFixed(1)}%</div>
                <div class="text-[10px] text-slate-400 font-sans">${n.cpu_cores} Cores</div>
              </td>
              <td class="py-2.5 px-3">
                <div class="text-purple-400 font-bold text-xs">${(n.ram_used_mb / 1024).toFixed(1)} / ${(n.ram_total_mb / 1024).toFixed(1)} GB</div>
                <div class="text-[10px] text-slate-400">${(n.ram_pct || 0).toFixed(1)}% Used</div>
              </td>
              <td class="py-2.5 px-3">
                <div class="text-emerald-400 font-bold text-xs">${n.disk_total_gb > 0 ? `${n.disk_used_gb} / ${n.disk_total_gb} GB` : 'ZFS Pool'}</div>
                <div class="text-[10px] text-slate-400">${n.disk_total_gb > 0 ? (n.disk_pct || 0).toFixed(1) + '% Used' : 'Host Root'}</div>
              </td>
              <td class="py-2.5 px-3 text-slate-300 text-xs">
                ${workloadsStr}
              </td>
              <td class="py-2.5 px-3 text-right space-x-1.5">
                <button onclick="openTerminalModal('${n.id}')" title="Terminal Shell" class="px-2.5 py-1 rounded-lg bg-surface-950 hover:bg-cyan-500/20 text-cyan-400 font-mono transition text-[11px] border border-slate-800">
                  <i class="fa-solid fa-terminal text-[10px]"></i>
                </button>
                <button onclick="inspectNodeFromCluster('${n.id}')" class="px-2.5 py-1 rounded-lg bg-surface-800 hover:bg-surface-700 text-blue-400 font-semibold transition text-[11px] border border-slate-700 flex items-center gap-1 inline-flex">
                  <span>Detail</span> <i class="fa-solid fa-arrow-right text-[9px]"></i>
                </button>
              </td>
            </tr>
          `;
        }).join('');
      }

      // Render Cluster Network Topology & Fleet Stress Heatmap
      try {
        renderTopologyMap(nodes);
        renderFleetHeatmap(nodes);
      } catch (err) {
        console.error("Topology/Heatmap render error:", err);
      }
    }

    // ==========================================
    //  HOMELAB ENDPOINTS / WEB PROBES LOGIC
    // ==========================================
    function openAddProbeModal() {
      document.getElementById('addProbeModal').classList.remove('hidden');
      document.getElementById('newProbeName').value = '';
      document.getElementById('newProbeUrl').value = '';
      document.getElementById('newProbeName').focus();
    }

    function closeAddProbeModal() {
      document.getElementById('addProbeModal').classList.add('hidden');
    }

    async function saveNewProbe() {
      const name = document.getElementById('newProbeName').value.trim();
      const url = document.getElementById('newProbeUrl').value.trim();
      if (!name || !url) {
        showToast('Please enter both service name and URL.', 'error');
        return;
      }
      try {
        const res = await fetch('/api/v1/probes', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({name, url})
        });
        const data = await res.json();
        if (data.status === 'success') {
          closeAddProbeModal();
          showToast(`Endpoint '${name}' added and verified.`, 'success');
          fetchDashboard();
        } else {
          showToast(data.message || 'Failed to add endpoint.', 'error');
        }
      } catch (err) {
        showToast('Network error adding endpoint.', 'error');
      }
    }

    async function deleteProbe(probeId, probeName) {
      if (!confirm(`Delete monitored endpoint '${probeName}'?`)) return;
      try {
        const res = await fetch(`/api/v1/probes/${probeId}`, {method: 'DELETE'});
        const data = await res.json();
        if (data.status === 'success') {
          showToast(`Endpoint '${probeName}' removed.`, 'success');
          fetchDashboard();
        }
      } catch (err) {
        showToast('Error deleting endpoint.', 'error');
      }
    }

    async function checkAllProbes() {
      showToast('Checking homelab endpoints and SSL certificates...', 'success');
      try {
        const res = await fetch('/api/v1/probes/check', {method: 'POST'});
        const probes = await res.json();
        renderWebProbes(probes);
      } catch (err) {
        console.error("Probes check error:", err);
      }
    }

    // ==========================================
    //  WAN QUALITY & SPEEDTEST LOGIC
    // ==========================================
    async function refreshNetworkQuality() {
      try {
        const res = await fetch('/api/v1/network/quality');
        const data = await res.json();
        renderNetworkQuality(data);
        showToast('Network latency hops updated.', 'success');
      } catch (err) {
        console.error("Quality fetch error:", err);
      }
    }

    function renderNetworkQuality(q) {
      if (!q) return;
      const pings = q.pings ? q.pings : q;
      const gw = pings.gateway || {};
      const cf = pings.cloudflare || {};
      const gg = pings.google || {};

      const setHop = (prefix, hop) => {
        const latEl = document.getElementById(`${prefix}Latency`);
        const stEl = document.getElementById(`${prefix}Status`);
        if (latEl && hop.latency_ms !== undefined) {
          latEl.innerText = (hop.latency_ms > 0) ? hop.latency_ms : '--';
        }
        if (stEl && hop.status) {
          const isOnline = (hop.status === 'ONLINE');
          stEl.className = isOnline ? 
            "px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" :
            "px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-red-500/10 text-red-400 border border-red-500/30";
          stEl.innerText = isOnline ? "ONLINE" : "TIMEOUT";
        }
      };

      setHop('gw', gw);
      setHop('cf', cf);
      setHop('gg', gg);

      if (q.download_mbps !== undefined && q.download_mbps > 0) {
        const dEl = document.getElementById('speedDownload');
        const uEl = document.getElementById('speedUpload');
        if (dEl) dEl.innerText = q.download_mbps;
        if (uEl) uEl.innerText = q.upload_mbps || (q.download_mbps * 0.42).toFixed(1);
        const tEl = document.getElementById('speedTime');
        if (tEl && q.last_tested) {
          tEl.innerText = `Tested at ${new Date(q.last_tested * 1000).toLocaleTimeString()}`;
        }
      }
    }

    async function runSpeedtest() {
      const btn = document.getElementById('runSpeedtestBtn');
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-[10px]"></i> Testing...`;
      }
      try {
        const res = await fetch('/api/v1/network/speedtest', {method: 'POST'});
        const data = await res.json();
        if (document.getElementById('speedDownload')) document.getElementById('speedDownload').innerText = data.download_mbps || '--';
        if (document.getElementById('speedUpload')) document.getElementById('speedUpload').innerText = data.upload_mbps || '--';
        if (document.getElementById('speedIsp')) document.getElementById('speedIsp').innerText = `ISP: ${data.isp || 'Cloudflare'}`;
        if (document.getElementById('speedTime')) {
          const now = new Date();
          document.getElementById('speedTime').innerText = `Tested at ${now.toLocaleTimeString()}`;
        }
        if (data.pings) renderNetworkQuality(data.pings);
        showToast(`Speedtest finished: ${data.download_mbps} Mbps Download.`, 'success');
      } catch (err) {
        showToast('Speedtest failed: ' + err.message, 'error');
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<i class="fa-solid fa-play text-[9px]"></i> Run Speedtest`;
        }
      }
    }

    // ==========================================
    //  IN-BROWSER WEB TERMINAL LOGIC
    // ==========================================
    let terminalHistory = [];
    let terminalHistoryIndex = -1;
    let activeTerminalTargetType = 'host';
    let activeTerminalTargetId = '';

    function openTerminalModal(targetNode, targetType = 'host', targetId = '') {
      const modal = document.getElementById('terminalModal');
      modal.classList.remove('hidden');
      activeTerminalTargetType = targetType;
      activeTerminalTargetId = targetId;

      const sel = document.getElementById('terminalNodeSelect');
      if (targetNode && sel) sel.value = targetNode;
      else if (selectedServerId && sel) sel.value = selectedServerId;

      updateTerminalPrompt();
      setTimeout(() => document.getElementById('terminalInput').focus(), 100);
    }

    function closeTerminalModal() {
      document.getElementById('terminalModal').classList.add('hidden');
    }

    function clearTerminalScreen() {
      const screen = document.getElementById('terminalScreen');
      screen.innerHTML = `
        <div class="text-slate-500 text-xs">
          <div>Sentinel Interactive Terminal • Cleared</div>
          <div class="text-slate-600">---------------------------------------------------------------------------------</div>
        </div>
      `;
    }

    function onTerminalTargetChange() {
      updateTerminalPrompt();
      document.getElementById('terminalInput').focus();
    }

    function updateTerminalPrompt() {
      const sel = document.getElementById('terminalNodeSelect');
      const nodeName = sel.options[sel.selectedIndex]?.text.split(' ')[0] || 'node';
      let promptText = `root@${nodeName}:~#`;
      if (activeTerminalTargetType === 'vm' && activeTerminalTargetId) {
        promptText = `root@vm-${activeTerminalTargetId}:~#`;
      } else if (activeTerminalTargetType === 'docker' && activeTerminalTargetId) {
        promptText = `root@docker-${activeTerminalTargetId.slice(0,8)}:~#`;
      }
      document.getElementById('terminalPromptPrefix').innerText = promptText;
    }

    function quickTerminalRun(cmd) {
      document.getElementById('terminalInput').value = cmd;
      submitTerminalCommand();
    }

    function handleTerminalKeyDown(e) {
      if (e.key === 'Enter') {
        submitTerminalCommand();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (terminalHistory.length && terminalHistoryIndex < terminalHistory.length - 1) {
          terminalHistoryIndex++;
          document.getElementById('terminalInput').value = terminalHistory[terminalHistory.length - 1 - terminalHistoryIndex];
        }
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (terminalHistoryIndex > 0) {
          terminalHistoryIndex--;
          document.getElementById('terminalInput').value = terminalHistory[terminalHistory.length - 1 - terminalHistoryIndex];
        } else if (terminalHistoryIndex === 0) {
          terminalHistoryIndex = -1;
          document.getElementById('terminalInput').value = '';
        }
      }
    }

    async function submitTerminalCommand() {
      const input = document.getElementById('terminalInput');
      const cmd = input.value.trim();
      if (!cmd) return;

      terminalHistory.push(cmd);
      terminalHistoryIndex = -1;
      input.value = '';

      const sel = document.getElementById('terminalNodeSelect');
      const nodeId = sel.value;
      const screen = document.getElementById('terminalScreen');
      const promptText = document.getElementById('terminalPromptPrefix').innerText;

      // Append command prompt
      const cmdLine = document.createElement('div');
      cmdLine.className = "flex items-baseline gap-2 font-bold text-slate-100";
      cmdLine.innerHTML = `<span class="text-cyan-400 select-none">${promptText}</span> <span>${escapeHtml(cmd)}</span>`;
      screen.appendChild(cmdLine);

      // Loading spinner line
      const loadingLine = document.createElement('div');
      loadingLine.className = "text-slate-500 italic flex items-center gap-2 text-xs py-1";
      loadingLine.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-cyan-400"></i> Executing on ${nodeId}...`;
      screen.appendChild(loadingLine);
      screen.scrollTop = screen.scrollHeight;

      try {
        const res = await fetch('/api/v1/terminal/exec', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            node_id: nodeId,
            command: cmd,
            target_type: activeTerminalTargetType,
            target_id: activeTerminalTargetId
          })
        });
        const data = await res.json();
        loadingLine.remove();

        const outLine = document.createElement('pre');
        outLine.className = `p-2 rounded-lg ${data.exit_code === 0 ? 'bg-surface-950 text-slate-200' : 'bg-red-950/20 text-rose-300 border border-red-900/30'} text-[11px] whitespace-pre-wrap font-mono leading-relaxed select-text`;
        
        let content = data.stdout || '';
        if (data.stderr) content += (content ? '\n' : '') + data.stderr;
        outLine.innerText = content || '[Process exited 0 with no stdout]';
        screen.appendChild(outLine);

        // Metadata footer line
        const metaLine = document.createElement('div');
        metaLine.className = "text-[10px] text-slate-500 flex justify-between font-mono pb-2";
        metaLine.innerHTML = `<span>Exit: ${data.exit_code}</span><span>${data.duration_ms || 0} ms</span>`;
        screen.appendChild(metaLine);

      } catch (err) {
        loadingLine.remove();
        const errLine = document.createElement('div');
        errLine.className = "text-rose-400 text-xs py-1";
        errLine.innerText = `Terminal exception: ${err.message}`;
        screen.appendChild(errLine);
      }

      screen.scrollTop = screen.scrollHeight;
      input.focus();
    }

    // ==========================================
    //  ONE-CLICK MAINTENANCE RUNBOOKS LOGIC
    // ==========================================
    let cachedRunbooks = [];

    async function openRunbooksModal(targetNode) {
      document.getElementById('runbooksModal').classList.remove('hidden');
      const sel = document.getElementById('runbookTargetNode');
      if (targetNode && sel) sel.value = targetNode;
      else if (selectedServerId && sel) sel.value = selectedServerId;
      document.getElementById('runbookResultDrawer').classList.add('hidden');
      loadRunbooks();
    }

    function closeRunbooksModal() {
      document.getElementById('runbooksModal').classList.add('hidden');
    }

    async function loadRunbooks() {
      const container = document.getElementById('runbooksListContainer');
      container.innerHTML = `<div class="p-6 text-center text-slate-500 text-xs"><i class="fa-solid fa-spinner fa-spin"></i> Loading operations runbook catalog...</div>`;
      try {
        const res = await fetch('/api/v1/runbooks');
        cachedRunbooks = await res.json();
        renderRunbooksList(cachedRunbooks);
      } catch (err) {
        container.innerHTML = `<div class="text-rose-400 p-4 text-center">Failed to load runbooks: ${err.message}</div>`;
      }
    }

    function renderRunbooksList(runbooks) {
      const container = document.getElementById('runbooksListContainer');
      if (!runbooks.length) {
        container.innerHTML = `<div class="p-6 text-center text-slate-500 text-xs">No runbooks available.</div>`;
        return;
      }

      container.innerHTML = runbooks.map(rb => `
        <div class="p-4 rounded-xl bg-surface-850 border border-slate-800 hover:border-slate-700 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <h4 class="font-bold text-white text-xs tracking-wide">${rb.title}</h4>
              <span class="px-2 py-0.2 rounded text-[9px] font-mono font-bold bg-blue-500/10 text-blue-400 border border-blue-500/25">
                ${rb.category}
              </span>
            </div>
            <p class="text-[11px] text-slate-400">${rb.desc}</p>
            <code class="text-[10px] font-mono text-cyan-400/80 bg-surface-950 px-2 py-0.5 rounded border border-slate-800/80 inline-block">${rb.cmd}</code>
          </div>
          <button onclick="executeRunbookAction('${rb.id}')" id="btnRunbook_${rb.id}" class="shrink-0 px-3.5 py-2 rounded-xl bg-surface-800 hover:bg-emerald-600/20 text-slate-200 hover:text-emerald-300 border border-slate-700 hover:border-emerald-500/40 text-xs font-semibold transition-all flex items-center gap-1.5 shadow-sm">
            <i class="fa-solid fa-play text-[10px] text-emerald-400"></i>
            <span>Execute</span>
          </button>
        </div>
      `).join('');
    }

    async function executeRunbookAction(runbookId) {
      const targetNode = document.getElementById('runbookTargetNode').value;
      const btn = document.getElementById(`btnRunbook_${runbookId}`);
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-[10px]"></i> Running...`;
      }

      const drawer = document.getElementById('runbookResultDrawer');
      const drawerTitle = document.getElementById('runbookResultTitle');
      const drawerDur = document.getElementById('runbookResultDuration');
      const drawerOut = document.getElementById('runbookResultOutput');

      drawer.classList.remove('hidden');
      drawerTitle.innerText = `Running ${runbookId} on ${targetNode}...`;
      drawerDur.innerText = "Executing...";
      drawerOut.innerText = "Please wait while the remote node executes task...";

      try {
        const res = await fetch('/api/v1/runbooks/execute', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({runbook_id: runbookId, node_id: targetNode})
        });
        const data = await res.json();
        drawerTitle.innerText = `${data.runbook} Result (${data.node_id}):`;
        drawerDur.innerText = `${data.duration_ms || 0} ms`;
        drawerOut.innerText = data.output || '[No output returned]';
        showToast(`Runbook '${data.runbook}' completed.`, data.status === 'success' ? 'success' : 'warning');
      } catch (err) {
        drawerOut.innerText = `Execution error: ${err.message}`;
        showToast(`Runbook failed: ${err.message}`, 'error');
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<i class="fa-solid fa-play text-[10px] text-emerald-400"></i> Execute`;
        }
      }
    }

    // ========================================================
    // 1. POWER & PLN ELECTRICITY COST ESTIMATOR
    // ========================================================
    let currentPlnTariff = 1445;
    let powerScope = 'cluster';
    let lastPowerData = null;

    function togglePowerScope() {
      powerScope = powerScope === 'cluster' ? 'node' : 'cluster';
      renderPowerEstimate(lastPowerData);
    }

    async function fetchPowerEstimate() {
      try {
        const targetId = (typeof selectedServerId !== 'undefined' && selectedServerId) ? selectedServerId : '';
        const url = `/api/v1/power/estimate${targetId ? '?node_id=' + encodeURIComponent(targetId) : ''}`;
        const res = await fetch(url);
        const data = await res.json();
        lastPowerData = data;
        renderPowerEstimate(data);
      } catch (err) {
        console.error("Error fetching power estimate:", err);
      }
    }

    function renderPowerEstimate(d) {
      if (!d) return;
      lastPowerData = d;
      currentPlnTariff = d.tariff_rate_kwh || 1445;

      const wattsEl = document.getElementById('powerWatts');
      const costEl = document.getElementById('powerCostMonthly');
      const dailyEl = document.getElementById('powerKwhDaily');
      const monthlyEl = document.getElementById('powerKwhMonthly');
      const tariffBadge = document.getElementById('powerTariffBadge');
      const co2El = document.getElementById('powerCo2Badge');
      const scopeLabel = document.getElementById('powerScopeLabel');
      const scopeSub = document.getElementById('powerScopeSub');

      const isNode = (powerScope === 'node') && d.selected_node;
      const watts = isNode ? d.selected_node.watts : d.total_watts;
      const costMonthly = isNode ? d.selected_node.cost_monthly_idr : d.cost_monthly_idr;
      const kwhDaily = isNode ? d.selected_node.kwh_daily : d.kwh_daily;
      const kwhMonthly = isNode ? d.selected_node.kwh_monthly : d.kwh_monthly;

      if (scopeLabel) scopeLabel.innerText = isNode ? 'Node' : 'Fleet';
      if (scopeSub) scopeSub.innerText = isNode ? `Node Aktif: ${d.selected_node.hostname}` : `Cluster Fleet (${d.active_nodes_count || 1} Nodes)`;

      if (wattsEl) wattsEl.innerText = watts ? Number(watts).toFixed(1) : '--';
      if (costEl) costEl.innerText = costMonthly ? Number(costMonthly).toLocaleString('id-ID') : '--';
      if (dailyEl) dailyEl.innerText = `${kwhDaily || 0} kWh/hari`;
      if (monthlyEl) monthlyEl.innerText = `${kwhMonthly || 0} kWh/bln`;
      if (tariffBadge) tariffBadge.innerText = `PLN: Rp ${Math.round(currentPlnTariff)}/kWh`;
      if (co2El) co2El.innerHTML = `<i class="fa-solid fa-leaf text-emerald-400 text-[10px] mr-1"></i>${d.co2_kg_monthly || 0} kg CO₂`;
    }

    function promptEditPlnTariff() {
      const input = document.getElementById('plnTariffInput');
      if (input) input.value = currentPlnTariff;
      document.getElementById('editPlnTariffModal').classList.remove('hidden');
    }

    function closePlnTariffModal() {
      document.getElementById('editPlnTariffModal').classList.add('hidden');
    }

    async function submitSavePlnTariff() {
      const input = document.getElementById('plnTariffInput');
      const val = parseFloat(input.value) || 1445;
      try {
        await fetch('/api/v1/power/settings', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({tariff_rate_kwh: val})
        });
        currentPlnTariff = val;
        closePlnTariffModal();
        showToast(`Tarif PLN diperbarui: Rp ${val}/kWh`, 'success');
        fetchPowerEstimate();
      } catch (err) {
        showToast(`Gagal menyimpan tarif: ${err.message}`, 'error');
      }
    }

    // ========================================================
    // 2. SSL / TLS CERTIFICATE EXPIRY TRACKER
    // ========================================================
    async function fetchSslCertificates() {
      try {
        const res = await fetch('/api/v1/ssl/certificates');
        const data = await res.json();
        renderSslCertificates(data.certificates || []);
      } catch (err) {
        console.error("Error fetching SSL certs:", err);
      }
    }

    function renderSslCertificates(certs) {
      const list = document.getElementById('sslCertificatesList');
      const totalBadge = document.getElementById('sslTotalMonitored');
      const globalStatus = document.getElementById('sslGlobalStatus');
      if (!list) return;

      if (totalBadge) totalBadge.innerText = `${certs.length} Certs Monitored`;

      if (!certs.length) {
        list.innerHTML = `<div class="p-3 text-center text-slate-500 text-xs font-sans">Belum ada domain yang dipantau. Klik '+ Add' untuk menambahkan.</div>`;
        return;
      }

      let hasCritical = false;
      let hasWarning = false;

      list.innerHTML = certs.map(c => {
        let badgeColor = "emerald";
        let statusText = `${c.days_left} Hari Tersisa`;
        let barWidth = Math.min(100, Math.round((c.days_left / 90) * 100));

        if (c.status === 'EXPIRED' || c.days_left <= 0) {
          badgeColor = "rose";
          statusText = "EXPIRED";
          hasCritical = true;
          barWidth = 100;
        } else if (c.days_left <= 7) {
          badgeColor = "rose";
          statusText = `KRITIS: ${c.days_left}h`;
          hasCritical = true;
        } else if (c.days_left <= 30) {
          badgeColor = "amber";
          statusText = `${c.days_left}h (Segera Expired)`;
          hasWarning = true;
        }

        const isSelfSigned = (c.issuer || '').includes('Self-Signed');
        const displayHost = c.port && c.port !== 443 ? `${c.host}:${c.port}` : c.host;

        return `
          <div class="p-2 rounded-xl bg-surface-950/70 border border-slate-800/60 flex items-center justify-between gap-2 text-xs">
            <div class="truncate max-w-[170px]">
              <div class="font-bold text-slate-200 font-mono flex items-center gap-1.5 truncate">
                <i class="fa-solid fa-lock text-[9px] text-${badgeColor}-400"></i>
                <span class="truncate">${displayHost}</span>
                ${isSelfSigned ? '<span class="px-1 py-0.2 text-[8px] rounded bg-cyan-500/10 text-cyan-400 font-mono">SELF</span>' : ''}
              </div>
              <div class="text-[10px] text-slate-500 font-sans truncate">${c.issuer || 'Standard CA'}</div>
            </div>
            <div class="text-right shrink-0">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-${badgeColor}-500/10 text-${badgeColor}-400 border border-${badgeColor}-500/25">
                ${statusText}
              </span>
              <div class="w-20 bg-surface-900 rounded-full h-1 mt-1 overflow-hidden">
                <div class="bg-${badgeColor}-500 h-1 rounded-full" style="width: ${barWidth}%"></div>
              </div>
            </div>
            <button onclick="deleteSslCert(${c.id})" title="Hapus domain" class="text-slate-500 hover:text-rose-400 p-1 transition">
              <i class="fa-solid fa-xmark text-xs"></i>
            </button>
          </div>
        `;
      }).join('');

      if (globalStatus) {
        if (hasCritical) {
          globalStatus.className = "text-rose-400 font-bold font-mono";
          globalStatus.innerText = "ATTENTION REQUIRED";
        } else if (hasWarning) {
          globalStatus.className = "text-amber-400 font-bold font-mono";
          globalStatus.innerText = "EXPIRING SOON";
        } else {
          globalStatus.className = "text-emerald-400 font-bold font-mono";
          globalStatus.innerText = "ALL VALID";
        }
      }
    }

    function openAddSslModal() {
      document.getElementById('sslNewHostInput').value = '';
      document.getElementById('addSslModal').classList.remove('hidden');
      setTimeout(() => document.getElementById('sslNewHostInput').focus(), 50);
    }

    function closeAddSslModal() {
      document.getElementById('addSslModal').classList.add('hidden');
    }

    async function submitAddSslDomain() {
      const hostInput = document.getElementById('sslNewHostInput');
      const portInput = document.getElementById('sslNewPortInput');
      const btn = document.getElementById('btnSubmitAddSsl');

      let host = hostInput.value.trim();
      let port = parseInt(portInput.value) || 443;
      if (!host) {
        showToast("Masukkan domain atau IP target!", "warning");
        return;
      }

      if (host.startsWith('http://') || host.startsWith('https://')) {
        try {
          const u = new URL(host);
          host = u.hostname;
          if (u.port) port = parseInt(u.port);
        } catch(e) {}
      }
      if (host.includes(':')) {
        const parts = host.split(':');
        host = parts[0];
        port = parseInt(parts[1]) || port;
      }

      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs"></i> Memeriksa...`;

      try {
        const res = await fetch('/api/v1/ssl/certificates', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({host, port})
        });
        const data = await res.json();
        if (!res.ok || data.status === 'error') {
          showToast(`Gagal: ${data.message || 'Tidak dapat menambahkan domain'}`, 'error');
          return;
        }
        closeAddSslModal();
        const cert = data.certificate || {};
        if (cert.status === 'ERROR') {
          showToast(`Domain ${host}:${port} ditambahkan, namun gagal handshake TLS.`, 'warning');
        } else {
          showToast(`Domain ${host}:${port} aktif! Sisa: ${cert.days_left} hari (${cert.issuer})`, 'success');
        }
        fetchSslCertificates();
      } catch (err) {
        showToast(`Gagal menambahkan domain: ${err.message}`, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-plus text-xs"></i> Tambah & Periksa`;
      }
    }

    async function deleteSslCert(certId) {
      if (!confirm("Hapus domain ini dari pemantauan SSL?")) return;
      try {
        await fetch(`/api/v1/ssl/certificates/${certId}`, {method: 'DELETE'});
        showToast("Domain dihapus dari SSL Monitor.", "success");
        fetchSslCertificates();
      } catch (err) {
        showToast(`Gagal menghapus: ${err.message}`, "error");
      }
    }

    async function checkAllSslCerts() {
      showToast("Memeriksa sertifikat SSL sekarang...", "info");
      try {
        const res = await fetch('/api/v1/ssl/check-now', {method: 'POST'});
        const data = await res.json();
        renderSslCertificates(data.certificates || []);
        showToast("Selesai memperbarui sertifikat SSL.", "success");
      } catch (err) {
        showToast(`Gagal memeriksa SSL: ${err.message}`, "error");
      }
    }

    // ========================================================
    // 3. PROXMOX VE BACKUP & SNAPSHOT SENTINEL
    // ========================================================
    async function fetchProxmoxBackups() {
      try {
        const res = await fetch('/api/v1/proxmox/backups');
        const data = await res.json();
        renderProxmoxBackups(data);
      } catch (err) {
        console.error("Error fetching Proxmox backups:", err);
      }
    }

    function renderProxmoxBackups(data) {
      const list = document.getElementById('proxmoxBackupsList');
      const sizeBadge = document.getElementById('backupTotalSize');
      const lastJobBadge = document.getElementById('backupLastJob');
      if (!list) return;

      const backups = data.backups || [];
      if (sizeBadge) sizeBadge.innerText = `Total: ${data.total_size_gb || 0} GB`;

      if (!backups.length) {
        list.innerHTML = `<div class="p-3 text-center text-slate-500 text-xs font-sans">Tidak ada arsip backup. Klik '+ Add' atau tombol sinkronisasi.</div>`;
        return;
      }

      const latest = backups[0];
      if (lastJobBadge && latest.backup_time) {
        const diffHrs = Math.max(0, Math.round((Date.now() / 1000 - latest.backup_time) / 3600));
        lastJobBadge.innerText = diffHrs <= 24 ? `Terakhir: ${diffHrs} jam lalu` : `Terakhir: ${Math.round(diffHrs / 24)} hari lalu`;
      }

      list.innerHTML = backups.map(b => {
        const sizeMb = (b.size_bytes / (1024 * 1024 * 1024)).toFixed(1);
        const icon = b.vm_type === 'lxc' ? 'fa-box' : 'fa-cube';
        const typeColor = b.vm_type === 'lxc' ? 'cyan' : 'blue';

        return `
          <div class="p-2 rounded-xl bg-surface-950/70 border border-slate-800/60 flex items-center justify-between gap-2 text-xs">
            <div class="truncate max-w-[150px]">
              <div class="font-bold text-slate-200 font-mono flex items-center gap-1.5 truncate">
                <i class="fa-solid ${icon} text-[9px] text-${typeColor}-400"></i>
                <span class="truncate">${b.vmid}: ${b.vm_name}</span>
              </div>
              <div class="text-[10px] text-slate-500 font-sans truncate">${b.storage} • ${sizeMb} GB</div>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
                ${b.status}
              </span>
              <button onclick="deleteProxmoxBackup('${b.id}')" title="Hapus catatan backup" class="text-slate-500 hover:text-rose-400 p-1 transition">
                <i class="fa-solid fa-xmark text-xs"></i>
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    function openAddProxmoxBackupModal() {
      document.getElementById('bkNewVmidInput').value = '';
      document.getElementById('bkNewNameInput').value = '';
      document.getElementById('bkNewStorageInput').value = 'local-zfs';
      document.getElementById('bkNewSizeInput').value = '5.0';
      document.getElementById('addProxmoxBackupModal').classList.remove('hidden');
      setTimeout(() => document.getElementById('bkNewVmidInput').focus(), 50);
    }

    function closeAddProxmoxBackupModal() {
      document.getElementById('addProxmoxBackupModal').classList.add('hidden');
    }

    async function submitAddProxmoxBackup() {
      const vmid = document.getElementById('bkNewVmidInput').value.trim();
      const vmName = document.getElementById('bkNewNameInput').value.trim();
      const vmType = document.getElementById('bkNewTypeSelect').value;
      const storage = document.getElementById('bkNewStorageInput').value.trim() || 'local-zfs';
      const sizeGb = parseFloat(document.getElementById('bkNewSizeInput').value) || 5.0;
      const btn = document.getElementById('btnSubmitAddBk');

      if (!vmid || !vmName) {
        showToast("Masukkan VM ID dan Nama VM/Container!", "warning");
        return;
      }

      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs"></i> Menyimpan...`;

      try {
        const res = await fetch('/api/v1/proxmox/backups', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({vmid, vm_name: vmName, vm_type: vmType, storage, size_gb: sizeGb, status: 'SUCCESS'})
        });
        const data = await res.json();
        closeAddProxmoxBackupModal();
        showToast(`Backup ${vmid}: ${vmName} berhasil disimpan!`, 'success');
        fetchProxmoxBackups();
      } catch (err) {
        showToast(`Gagal menyimpan backup: ${err.message}`, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-plus text-xs"></i> Simpan Backup`;
      }
    }

    async function deleteProxmoxBackup(backupId) {
      if (!confirm("Hapus catatan backup ini?")) return;
      try {
        await fetch(`/api/v1/proxmox/backups/${backupId}`, {method: 'DELETE'});
        showToast("Catatan backup dihapus.", "success");
        fetchProxmoxBackups();
      } catch (err) {
        showToast(`Gagal menghapus: ${err.message}`, "error");
      }
    }

    async function syncProxmoxBackups() {
      showToast("Menyinkronkan backup dengan VM Proxmox...", "info");
      try {
        const res = await fetch('/api/v1/proxmox/sync', {method: 'POST'});
        const data = await res.json();
        renderProxmoxBackups(data);
        showToast(`Sinkronisasi selesai! ${data.total_count || 0} VM terlacak.`, 'success');
      } catch (err) {
        showToast(`Gagal sinkronisasi Proxmox: ${err.message}`, "error");
      }
    }

    // ========================================================
    // 4. REALTIME SYSTEMD, DOCKER & KERNEL LOG STREAMER
    // ========================================================
    let logStreamInterval = null;
    let currentLogSource = "journal";
    let isLogPaused = false;
    let logSearchTimeout = null;

    function openLogsModal() {
      document.getElementById('logsStreamerModal').classList.remove('hidden');
      isLogPaused = false;
      fetchLogsStream(true);
      if (!logStreamInterval) {
        logStreamInterval = setInterval(() => {
          if (!isLogPaused && !document.getElementById('logsStreamerModal').classList.contains('hidden')) {
            fetchLogsStream(false);
          }
        }, 2000);
      }
    }

    function closeLogsModal() {
      document.getElementById('logsStreamerModal').classList.add('hidden');
      if (logStreamInterval) {
        clearInterval(logStreamInterval);
        logStreamInterval = null;
      }
    }

    function switchLogSource(src) {
      currentLogSource = src;
      ['journal', 'docker', 'kernel'].forEach(s => {
        const btn = document.getElementById(`logSource${s.charAt(0).toUpperCase() + s.slice(1)}`);
        if (btn) {
          if (s === src) {
            btn.className = "px-3 py-1 font-semibold rounded-lg bg-blue-600 text-white transition flex items-center gap-1.5";
          } else {
            btn.className = "px-3 py-1 font-semibold rounded-lg text-slate-400 hover:text-white transition flex items-center gap-1.5";
          }
        }
      });
      fetchLogsStream(true);
    }

    function toggleLogPause() {
      isLogPaused = !isLogPaused;
      const btn = document.getElementById('logPauseBtn');
      const icon = document.getElementById('logPauseIcon');
      const text = document.getElementById('logPauseText');
      if (isLogPaused) {
        btn.className = "px-2.5 py-1 rounded-lg bg-amber-600 text-white border border-amber-500 transition flex items-center gap-1 font-mono text-[11px]";
        icon.className = "fa-solid fa-play text-[10px]";
        text.innerText = "Resume";
      } else {
        btn.className = "px-2.5 py-1 rounded-lg bg-surface-800 hover:bg-surface-700 text-slate-300 border border-slate-700 transition flex items-center gap-1 font-mono text-[11px]";
        icon.className = "fa-solid fa-pause text-[10px]";
        text.innerText = "Pause";
      }
    }

    function debounceLogSearch() {
      clearTimeout(logSearchTimeout);
      logSearchTimeout = setTimeout(() => {
        fetchLogsStream(true);
      }, 350);
    }

    async function fetchLogsStream(forceScroll = false) {
      const container = document.getElementById('logsTerminalContainer');
      const level = document.getElementById('logLevelFilter').value;
      const search = document.getElementById('logSearchInput').value.trim();
      const statusEl = document.getElementById('logCountStatus');

      try {
        const url = `/api/v1/logs/query?source=${currentLogSource}&level=${level}&search=${encodeURIComponent(search)}&limit=70`;
        const res = await fetch(url);
        const data = await res.json();
        const logsList = data.logs || [];

        if (statusEl) statusEl.innerText = `Menampilkan ${logsList.length} entri (${data.source})`;

        if (!logsList.length) {
          container.innerHTML = `<div class="text-slate-500 py-8 text-center font-sans">Tidak ada entri log yang cocok dengan filter.</div>`;
          return;
        }

        container.innerHTML = logsList.map(l => {
          let lvlClass = "text-slate-400 bg-slate-800/40";
          if (l.level === "ERROR") lvlClass = "text-rose-400 bg-rose-500/10 border border-rose-500/30";
          else if (l.level === "WARN") lvlClass = "text-amber-400 bg-amber-500/10 border border-amber-500/30";
          else if (l.level === "INFO") lvlClass = "text-blue-400 bg-blue-500/10";

          return `
            <div class="hover:bg-white/[0.03] px-2 py-1 rounded flex items-start gap-2.5 transition">
              <span class="text-slate-500 text-[10px] shrink-0 select-none">${l.timestamp}</span>
              <span class="px-1.5 py-0.2 rounded text-[9px] font-bold ${lvlClass} shrink-0">${l.level}</span>
              <span class="text-cyan-400/90 text-[11px] font-semibold shrink-0 max-w-[120px] truncate" title="${l.source}">${l.source}:</span>
              <span class="text-slate-200 text-xs break-all flex-1 select-text">${escapeHtml(l.message)}</span>
            </div>
          `;
        }).join('');

        if (forceScroll || document.getElementById('logAutoScrollCheck').checked) {
          container.scrollTop = container.scrollHeight;
        }
      } catch (err) {
        console.error("Error fetching logs stream:", err);
      }
    }

    // ========================================================
    // 5. LAN DEVICE DISCOVERY & IP SUBNET SCANNER
    // ========================================================
    let lanDevicesCache = [];

    function openLanScannerModal() {
      document.getElementById('lanScannerModal').classList.remove('hidden');
      fetchLanDevices();
    }

    function closeLanScannerModal() {
      document.getElementById('lanScannerModal').classList.add('hidden');
    }

    async function fetchLanDevices() {
      try {
        const res = await fetch('/api/v1/network/lan-devices');
        const data = await res.json();
        lanDevicesCache = data.devices || [];
        renderLanDevices(lanDevicesCache);
      } catch (err) {
        console.error("Error fetching LAN devices:", err);
      }
    }

    async function triggerLanSubnetScan() {
      const btn = document.getElementById('lanScanNowBtn');
      const icon = document.getElementById('lanScanIcon');
      btn.disabled = true;
      icon.className = "fa-solid fa-spinner fa-spin text-[10px]";
      showToast("Memulai scan subnet 10.10.10.0/24...", "info");

      try {
        const res = await fetch('/api/v1/network/lan-scan', {method: 'POST'});
        const data = await res.json();
        lanDevicesCache = data.devices || [];
        renderLanDevices(lanDevicesCache);
        showToast(`Scan selesai! Ditemukan ${lanDevicesCache.length} perangkat aktif.`, "success");
      } catch (err) {
        showToast(`Gagal scan subnet: ${err.message}`, "error");
      } finally {
        btn.disabled = false;
        icon.className = "fa-solid fa-radar text-[10px]";
      }
    }

    function renderLanDevices(devices) {
      const tbody = document.getElementById('lanDevicesTableBody');
      const countEl = document.getElementById('lanTotalDevicesCount');
      if (!tbody) return;

      if (countEl) countEl.innerText = devices.length;

      if (!devices.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="py-6 text-center text-slate-500 font-sans">Belum ada perangkat yang terdeteksi di subnet. Klik 'Scan Subnet Now'.</td></tr>`;
        return;
      }

      tbody.innerHTML = devices.map(d => {
        const isOnline = d.status === "ONLINE";
        const statusBadge = isOnline 
          ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">ONLINE</span>`
          : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">OFFLINE</span>`;

        return `
          <tr class="hover:bg-white/[0.02] transition">
            <td class="py-2.5 px-3 font-bold text-white font-mono flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-slate-600'}"></span>
              ${d.ip}
            </td>
            <td class="py-2.5 px-3 text-slate-200">${d.hostname || '-'}</td>
            <td class="py-2.5 px-3 text-slate-400 uppercase">${d.mac || '-'}</td>
            <td class="py-2.5 px-3 text-cyan-300 font-sans">
              <span class="px-2 py-0.5 rounded bg-surface-900 border border-slate-800 text-[10px]">${d.vendor || 'Unknown'}</span>
            </td>
            <td class="py-2.5 px-3 text-slate-400">${d.interface || 'eth0'}</td>
            <td class="py-2.5 px-3 text-right">${statusBadge}</td>
          </tr>
        `;
      }).join('');
    }

    function filterLanDevicesTable() {
      const q = document.getElementById('lanDeviceSearchInput').value.toLowerCase().trim();
      if (!q) {
        renderLanDevices(lanDevicesCache);
        return;
      }
      const filtered = lanDevicesCache.filter(d => 
        (d.ip && d.ip.toLowerCase().includes(q)) ||
        (d.hostname && d.hostname.toLowerCase().includes(q)) ||
        (d.mac && d.mac.toLowerCase().includes(q)) ||
        (d.vendor && d.vendor.toLowerCase().includes(q))
      );
      renderLanDevices(filtered);
    }

    // Initialize Chart & High-frequency Polling
    window.addEventListener('load', () => {
      initCharts();
      fetchDashboard();
      fetchPowerEstimate();
      fetchSslCertificates();
      fetchProxmoxBackups();
      loadAiAudit(false);

      setInterval(() => {
        if (currentDashboardView === 'cluster') {
          fetchClusterOverview();
        } else {
          fetchDashboard();
        }
      }, 1500);

      setInterval(() => {
        fetchPowerEstimate();
      }, 5000);

      setInterval(() => {
        fetchSslCertificates();
        fetchProxmoxBackups();
        loadAiAudit(false);
      }, 30000);
    });
  
;
