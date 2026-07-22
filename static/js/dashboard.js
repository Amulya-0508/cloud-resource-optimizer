// ==========================================================================
// AI-POWERED CLOUD RESOURCE OPTIMIZER - DASHBOARD CLIENT CONTROLLER
// ==========================================================================

let liveChart = null;
let forecastChart = null;
let selectedNodeId = "local-host-node";
let selectedForecastNodeId = "inst-aws-web-01";
let liveHistoryData = { labels: [], cpu: [], memory: [], network: [] };

document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initCharts();
    fetchInstances();
    fetchLiveMetrics();
    fetchRecommendations();
    fetchScalingLogs();
    initChatbot();
    initAuthModal();

    // Start 3-second live update loop
    setInterval(() => {
        fetchLiveMetrics();
    }, 3000);
});

// --- NAVIGATION & TABS ---
function initNavigation() {
    const navItems = document.querySelectorAll(".sidebar-nav .nav-item");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const pageTitle = document.getElementById("page-title");

    const titles = {
        "overview": "Live Resource Telemetry Stream",
        "fleet": "Multi-Cloud Virtual Machine Fleet",
        "forecasting": "Machine Learning Demand Forecast Engine",
        "recommendations": "AI Rightsizing & Cost Savings",
        "scaling-logs": "Auto-Scaling Audit History"
    };

    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const tab = item.getAttribute("data-tab");

            navItems.forEach(n => n.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            item.classList.add("active");
            document.getElementById(`tab-${tab}`).classList.add("active");
            pageTitle.textContent = titles[tab] || "Cloud Optimizer";

            if (tab === "forecasting") {
                fetchForecast(selectedForecastNodeId);
            } else if (tab === "recommendations") {
                fetchRecommendations();
            } else if (tab === "scaling-logs") {
                fetchScalingLogs();
            }
        });
    });

    document.getElementById("node-select").addEventListener("change", (e) => {
        selectedNodeId = e.target.value;
        liveHistoryData = { labels: [], cpu: [], memory: [], network: [] };
        fetchHistoryForNode(selectedNodeId);
    });

    document.getElementById("forecast-node-select").addEventListener("change", (e) => {
        selectedForecastNodeId = e.target.value;
        fetchForecast(selectedForecastNodeId);
    });

    document.getElementById("btn-trigger-spike").addEventListener("click", () => {
        triggerSpike(selectedNodeId);
    });

    document.getElementById("btn-retrain-ml").addEventListener("click", retrainMLModel);
}

// --- CHART INITIALIZATION ---
function initCharts() {
    // 1. Live Telemetry Line Chart
    const ctxLive = document.getElementById("liveTelemetryChart").getContext("2d");
    liveChart = new Chart(ctxLive, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'CPU Utilization (%)',
                    data: [],
                    borderColor: '#00f2fe',
                    backgroundColor: 'rgba(0, 242, 254, 0.1)',
                    borderWidth: 2,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 3
                },
                {
                    label: 'RAM Memory (%)',
                    data: [],
                    borderColor: '#9d4edd',
                    backgroundColor: 'rgba(157, 78, 221, 0.08)',
                    borderWidth: 2,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 2
                },
                {
                    label: 'Network RX (MB/s)',
                    data: [],
                    borderColor: '#f59e0b',
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                    tension: 0.2,
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 400 },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8c9ba stroke', font: { size: 11 } }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8c9ba stroke', font: { size: 11 } }
                }
            },
            plugins: {
                legend: { labels: { color: '#f0f4fc', font: { size: 12 } } }
            }
        }
    });

    // 2. ML Forecast Chart
    const ctxForecast = document.getElementById("mlForecastChart").getContext("2d");
    forecastChart = new Chart(ctxForecast, {
        type: 'line',
        data: {
            labels: ['Current', '+15m', '+1h', '+6h', '+24h'],
            datasets: [
                {
                    label: 'Predicted CPU Demand (%)',
                    data: [0, 0, 0, 0, 0],
                    borderColor: '#00f2fe',
                    backgroundColor: 'rgba(0, 242, 254, 0.15)',
                    borderWidth: 3,
                    tension: 0.3,
                    fill: true,
                    pointRadius: 5
                },
                {
                    label: 'Upper Confidence Bound (+6.5%)',
                    data: [0, 0, 0, 0, 0],
                    borderColor: 'rgba(255, 0, 127, 0.5)',
                    borderDash: [5, 5],
                    borderWidth: 1.5,
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: 'Predicted RAM Usage (%)',
                    data: [0, 0, 0, 0, 0],
                    borderColor: '#9d4edd',
                    borderWidth: 2,
                    fill: false,
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#f0f4fc' } },
                y: { min: 0, max: 100, grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#f0f4fc' } }
            },
            plugins: { legend: { labels: { color: '#f0f4fc' } } }
        }
    });
}

// --- FETCH DATA ---
async function fetchInstances() {
    try {
        const res = await fetch("/api/instances");
        const instances = await res.json();
        
        const nodeSelect = document.getElementById("node-select");
        const forecastSelect = document.getElementById("forecast-node-select");
        const fleetContainer = document.getElementById("fleet-container");

        nodeSelect.innerHTML = "";
        forecastSelect.innerHTML = "";
        fleetContainer.innerHTML = "";

        document.getElementById("nav-fleet-count").textContent = instances.length;

        instances.forEach((inst, idx) => {
            // Populate select dropdowns
            const opt1 = document.createElement("option");
            opt1.value = inst.id;
            opt1.textContent = `${inst.name} (${inst.provider})`;
            if (inst.id === selectedNodeId) opt1.selected = true;
            nodeSelect.appendChild(opt1);

            const opt2 = document.createElement("option");
            opt2.value = inst.id;
            opt2.textContent = `${inst.name} (${inst.provider})`;
            if (inst.id === selectedForecastNodeId) opt2.selected = true;
            forecastSelect.appendChild(opt2);

            // Render Fleet Card
            const providerClass = `badge-${inst.provider.toLowerCase()}`;
            const card = document.createElement("div");
            card.className = "fleet-card glass-card";
            card.innerHTML = `
                <div class="fleet-card-header">
                    <div class="instance-title">
                        <h4>${inst.name}</h4>
                        <span class="instance-sub">${inst.id} • ${inst.region}</span>
                    </div>
                    <span class="provider-badge ${providerClass}">${inst.provider}</span>
                </div>
                <div class="fleet-stats-grid">
                    <div class="fleet-stat-item">
                        <label>Current Tier</label>
                        <span>${inst.tier}</span>
                    </div>
                    <div class="fleet-stat-item">
                        <label>Hourly Cost</label>
                        <span class="text-cyan">$${inst.hourly_cost}/hr</span>
                    </div>
                    <div class="fleet-stat-item">
                        <label>Live CPU</label>
                        <span id="fleet-cpu-${inst.id}">${inst.latest_cpu}%</span>
                    </div>
                    <div class="fleet-stat-item">
                        <label>Live RAM</label>
                        <span id="fleet-ram-${inst.id}">${inst.latest_mem}%</span>
                    </div>
                </div>
                <div class="fleet-card-actions">
                    <button class="btn btn-secondary btn-sm" onclick="toggleAutoscale('${inst.id}')">
                        <i class="fa-solid fa-sliders"></i> Auto-Scale: <strong>${inst.auto_scale ? 'ON' : 'OFF'}</strong>
                    </button>
                    <button class="btn btn-warning btn-sm" onclick="triggerSpike('${inst.id}')">
                        <i class="fa-solid fa-bolt"></i> Spike
                    </button>
                </div>
            `;
            fleetContainer.appendChild(card);
        });

        // Load history for initial node
        fetchHistoryForNode(selectedNodeId);
    } catch (err) {
        console.error("Error fetching instances:", err);
    }
}

async function fetchLiveMetrics() {
    try {
        const res = await fetch("/api/metrics/live");
        const data = await res.json();
        const liveData = data.live_data;
        const summary = data.summary;

        // Update Header Stats
        document.getElementById("hdr-monthly-burn").textContent = `$${summary.monthly_cloud_burn}`;
        document.getElementById("hdr-potential-savings").textContent = `$${summary.potential_monthly_savings}`;
        document.getElementById("total-banner-savings").textContent = `$${summary.potential_monthly_savings} / month`;
        document.getElementById("nav-rec-count").textContent = summary.pending_recommendations_count;

        // Update selected node live chart & gauge cards
        if (liveData[selectedNodeId]) {
            const m = liveData[selectedNodeId];

            document.getElementById("metric-cpu-val").textContent = `${m.cpu}%`;
            document.getElementById("metric-ram-val").textContent = `${m.memory}%`;
            document.getElementById("metric-disk-val").textContent = `${m.disk}%`;
            document.getElementById("metric-net-val").textContent = `${m.network_rx} MB/s`;

            document.getElementById("progress-cpu").style.width = `${m.cpu}%`;
            document.getElementById("progress-ram").style.width = `${m.memory}%`;

            // Append to chart stream
            if (liveChart) {
                liveChart.data.labels.push(m.timestamp);
                liveChart.data.datasets[0].data.push(m.cpu);
                liveChart.data.datasets[1].data.push(m.memory);
                liveChart.data.datasets[2].data.push(m.network_rx);

                if (liveChart.data.labels.length > 25) {
                    liveChart.data.labels.shift();
                    liveChart.data.datasets[0].data.shift();
                    liveChart.data.datasets[1].data.shift();
                    liveChart.data.datasets[2].data.shift();
                }
                liveChart.update();
            }
        }

        // Update fleet node cards
        for (const instId in liveData) {
            const elCpu = document.getElementById(`fleet-cpu-${instId}`);
            const elRam = document.getElementById(`fleet-ram-${instId}`);
            if (elCpu) elCpu.textContent = `${liveData[instId].cpu}%`;
            if (elRam) elRam.textContent = `${liveData[instId].memory}%`;
        }

    } catch (err) {
        console.error("Error fetching live metrics:", err);
    }
}

async function fetchHistoryForNode(nodeId) {
    try {
        const res = await fetch(`/api/metrics/history/${nodeId}?limit=20`);
        const history = await res.json();
        if (liveChart && history.length > 0) {
            liveChart.data.labels = history.map(h => h.timestamp);
            liveChart.data.datasets[0].data = history.map(h => h.cpu);
            liveChart.data.datasets[1].data = history.map(h => h.memory);
            liveChart.data.datasets[2].data = history.map(h => h.network_rx);
            liveChart.update();
        }
    } catch (err) {
        console.error("Error fetching history:", err);
    }
}

async function fetchForecast(nodeId) {
    try {
        const res = await fetch(`/api/ml/forecast/${nodeId}`);
        const forecasts = await res.json();
        if (forecastChart && forecasts.length > 0) {
            const currentCpu = parseFloat(document.getElementById("metric-cpu-val").textContent) || 35.0;
            const currentMem = parseFloat(document.getElementById("metric-ram-val").textContent) || 40.0;

            forecastChart.data.labels = ['Current', ...forecasts.map(f => f.horizon)];
            forecastChart.data.datasets[0].data = [currentCpu, ...forecasts.map(f => f.predicted_cpu)];
            forecastChart.data.datasets[1].data = [currentCpu + 6.5, ...forecasts.map(f => f.cpu_upper_bound)];
            forecastChart.data.datasets[2].data = [currentMem, ...forecasts.map(f => f.predicted_mem)];
            forecastChart.update();
        }
    } catch (err) {
        console.error("Error fetching forecast:", err);
    }
}

async function fetchRecommendations() {
    try {
        const res = await fetch("/api/recommendations");
        const data = await res.json();
        const recs = data.recommendations;
        const container = document.getElementById("recommendations-container");
        container.innerHTML = "";

        if (recs.length === 0) {
            container.innerHTML = `<div class="glass-card" style="padding: 24px; text-align: center; color: var(--text-secondary);">
                <i class="fa-solid fa-circle-check text-emerald" style="font-size: 32px; margin-bottom: 10px;"></i>
                <p>All cloud instances are currently perfectly sized! No rightsizing waste detected.</p>
            </div>`;
            return;
        }

        recs.forEach(r => {
            const badgeClass = r.recommendation_type === "RIGHTSIZE_DOWN" ? "badge-down" : "badge-up";
            const badgeText = r.recommendation_type === "RIGHTSIZE_DOWN" ? "RIGHTSIZE DOWN (SAVE COST)" : "UPSIZE TIER (PERFORMANCE)";
            const savingsDisplay = r.estimated_monthly_savings > 0 
                ? `<span class="rec-savings-val">+$${r.estimated_monthly_savings}/mo</span>`
                : `<span class="rec-savings-val" style="color: var(--accent-amber);">$${Math.abs(r.estimated_monthly_savings)}/mo cost delta</span>`;

            const card = document.createElement("div");
            card.className = "rec-card glass-card";
            card.innerHTML = `
                <div class="rec-details">
                    <div class="rec-header">
                        <h4>${r.instance_name}</h4>
                        <span class="rec-badge ${badgeClass}">${badgeText}</span>
                    </div>
                    <p class="rec-reason">${r.reason}</p>
                    <div style="font-size: 12px; color: var(--primary-cyan);">
                        Target: <strong>${r.current_tier} ($${r.current_hourly_cost}/hr)</strong> ➜ <strong>${r.suggested_tier} ($${r.new_hourly_cost}/hr)</strong>
                    </div>
                </div>
                <div class="rec-impact">
                    ${savingsDisplay}
                    <button class="btn btn-primary btn-sm" onclick="applyRecommendation(${r.id})">
                        <i class="fa-solid fa-check"></i> Apply Optimization
                    </button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        console.error("Error fetching recommendations:", err);
    }
}

async function applyRecommendation(recId) {
    try {
        const res = await fetch(`/api/recommendations/apply/${recId}`, { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
            alert(data.message);
            fetchRecommendations();
            fetchInstances();
            fetchScalingLogs();
        } else {
            alert(`Error: ${data.message}`);
        }
    } catch (err) {
        console.error("Error applying recommendation:", err);
    }
}

async function fetchScalingLogs() {
    try {
        const res = await fetch("/api/scaling/logs");
        const logs = await res.json();
        const tbody = document.getElementById("scaling-logs-tbody");
        tbody.innerHTML = "";

        logs.forEach(l => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${l.timestamp}</td>
                <td><strong>${l.instance_name}</strong></td>
                <td><span class="badge ${l.action.includes('UP') ? 'badge-warning' : 'badge-info'}">${l.action}</span></td>
                <td>${l.previous_tier}</td>
                <td>${l.new_tier}</td>
                <td class="${l.cost_impact_monthly >= 0 ? 'text-emerald' : 'text-amber'}">$${l.cost_impact_monthly}/mo</td>
                <td style="font-size: 12px; color: var(--text-secondary);">${l.trigger_reason}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Error fetching logs:", err);
    }
}

async function toggleAutoscale(instanceId) {
    try {
        const res = await fetch(`/api/scaling/toggle-autoscale/${instanceId}`, { method: "POST" });
        const data = await res.json();
        fetchInstances();
    } catch (err) {
        console.error("Error toggling autoscale:", err);
    }
}

async function triggerSpike(instanceId) {
    try {
        const res = await fetch(`/api/simulate-spike/${instanceId}`, { method: "POST" });
        const data = await res.json();
        alert(data.message);
        fetchLiveMetrics();
    } catch (err) {
        console.error("Error triggering spike:", err);
    }
}

async function retrainMLModel() {
    const btn = document.getElementById("btn-retrain-ml");
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Training...`;
    try {
        const res = await fetch("/api/ml/train", { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
            document.getElementById("ml-cpu-r2").textContent = data.cpu_r2;
            document.getElementById("ml-cpu-mae").textContent = `${data.cpu_mae}%`;
            alert(`ML Models retrained successfully! Trained on ${data.samples_trained} historical telemetry points. R² Score: ${data.cpu_r2}`);
        }
    } catch (err) {
        console.error("Error retraining ML:", err);
    } finally {
        btn.innerHTML = `<i class="fa-solid fa-rotate"></i> Train ML Model`;
    }
}

// --- CHATBOT DRAWER ---
function initChatbot() {
    const drawer = document.getElementById("chatbot-drawer");
    const openBtn = document.getElementById("btn-open-chatbot");
    const closeBtn = document.getElementById("btn-close-chatbot");
    const sendBtn = document.getElementById("btn-send-chat");
    const chatInput = document.getElementById("chat-input");
    const messages = document.getElementById("chat-messages");

    openBtn.addEventListener("click", () => drawer.classList.add("open"));
    closeBtn.addEventListener("click", () => drawer.classList.remove("open"));

    async function sendMessage(text) {
        if (!text.trim()) return;

        // User bubble
        const userDiv = document.createElement("div");
        userDiv.className = "chat-bubble user-bubble";
        userDiv.textContent = text;
        messages.appendChild(userDiv);
        chatInput.value = "";
        messages.scrollTop = messages.scrollHeight;

        // Fetch AI reply
        try {
            const res = await fetch("/api/chatbot/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: text })
            });
            const data = await res.json();

            const botDiv = document.createElement("div");
            botDiv.className = "chat-bubble bot-bubble";
            botDiv.innerHTML = data.reply.replace(/\n/g, "<br>");
            messages.appendChild(botDiv);
            messages.scrollTop = messages.scrollHeight;
        } catch (err) {
            console.error("Chat error:", err);
        }
    }

    sendBtn.addEventListener("click", () => sendMessage(chatInput.value));
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendMessage(chatInput.value);
    });

    document.querySelectorAll(".pill-btn").forEach(btn => {
        btn.addEventListener("click", () => sendMessage(btn.getAttribute("data-query")));
    });
}

// --- AUTH MODAL ---
function initAuthModal() {
    const modal = document.getElementById("login-modal");
    const openBtn = document.getElementById("btn-login-modal");
    const closeBtn = document.getElementById("btn-close-modal");
    const form = document.getElementById("login-form");

    openBtn.addEventListener("click", () => modal.classList.add("open"));
    closeBtn.addEventListener("click", () => modal.classList.remove("open"));

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("input-username").value;
        const password = document.getElementById("input-password").value;

        try {
            const res = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (data.status === "success") {
                document.getElementById("user-display").textContent = `Admin: ${data.username}`;
                modal.classList.remove("open");
                alert("Login successful!");
            } else {
                alert(data.message);
            }
        } catch (err) {
            console.error("Login error:", err);
        }
    });
}
