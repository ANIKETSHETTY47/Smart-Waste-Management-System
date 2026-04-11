/**
 * app.js — Simple streaming dashboard
 * Fetches every 3 seconds, updates table + Chart.js line charts.
 */

// ── CONFIG ──────────────────────────────────────────────────────────
var API_URL = "https://8kw36z9amd.execute-api.us-east-1.amazonaws.com/prod/data";
var REFRESH = 3000;         // 3 seconds
var MAX_PTS = 20;           // max data points on charts

// ── REFERENCES ──────────────────────────────────────────────────────
var tbody = document.getElementById("bin-data");
var statusBar = document.getElementById("last-update");

// ── HISTORY ARRAYS ──────────────────────────────────────────────────
var labels = [];
var fillH = { bin_1: [], bin_2: [], bin_3: [], bin_4: [], bin_5: [] };
var tempH = { bin_1: [], bin_2: [], bin_3: [], bin_4: [], bin_5: [] };
var methH = { bin_1: [], bin_2: [], bin_3: [], bin_4: [], bin_5: [] };

// ── CHART COLORS ────────────────────────────────────────────────────
var COLORS = {
    bin_1: "#0000ff",
    bin_2: "#008000",
    bin_3: "#ff8c00",
    bin_4: "#ff0000",
    bin_5: "#800080"
};

// ── CREATE A CHART ──────────────────────────────────────────────────
function makeChart(id, yLabel, yMax) {
    var datasets = [];
    var bins = ["bin_1", "bin_2", "bin_3", "bin_4", "bin_5"];
    for (var i = 0; i < bins.length; i++) {
        datasets.push({
            label: bins[i],
            data: [],
            borderColor: COLORS[bins[i]],
            backgroundColor: "transparent",
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.3
        });
    }
    var opts = {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
            legend: { position: "bottom", labels: { font: { size: 10 }, boxWidth: 12 } }
        },
        scales: {
            x: { ticks: { font: { size: 9 }, maxRotation: 0 } },
            y: { beginAtZero: true, ticks: { font: { size: 10 } } }
        }
    };
    if (yMax) opts.scales.y.max = yMax;
    return new Chart(document.getElementById(id), {
        type: "line",
        data: { labels: [], datasets: datasets },
        options: opts
    });
}

var fillChart = makeChart("fillChart", "Fill %", 100);
var tempChart = makeChart("tempChart", "°C", null);
var methChart = makeChart("methaneChart", "ppm", null);

// ── HELPERS ─────────────────────────────────────────────────────────
function now() {
    var d = new Date();
    return d.toLocaleTimeString();
}

function statusClass(s) {
    if (s === "NORMAL") return "status-normal";
    if (s === "NEEDS_COLLECTION") return "status-collect";
    if (s === "GAS_ALERT") return "status-gas";
    if (s === "FIRE_RISK") return "status-fire";
    return "";
}

// ── RENDER TABLE ────────────────────────────────────────────────────
function renderTable(data) {
    var html = "";
    for (var i = 0; i < data.length; i++) {
        var b = data[i];
        html += "<tr>" +
            "<td><b>" + b.bin_id + "</b></td>" +
            "<td>" + b.fill_level + "%</td>" +
            "<td class='" + statusClass(b.status) + "'>" + b.status + "</td>" +
            "<td>" + b.temperature + "°C</td>" +
            "<td>" + b.methane_level + " ppm</td>" +
            "<td>" + b.weight + " kg</td>" +
            "<td>" + new Date(b.timestamp).toLocaleTimeString() + "</td>" +
            "</tr>";
    }
    tbody.innerHTML = html;
}

// ── UPDATE CHARTS ───────────────────────────────────────────────────
function updateCharts(data) {
    // Build a lookup map
    var map = {};
    for (var i = 0; i < data.length; i++) {
        map[data[i].bin_id] = data[i];
    }

    // Add time label
    labels.push(now());
    if (labels.length > MAX_PTS) labels.shift();

    // Push values
    var bins = ["bin_1", "bin_2", "bin_3", "bin_4", "bin_5"];
    for (var j = 0; j < bins.length; j++) {
        var b = bins[j];
        var d = map[b];
        fillH[b].push(d ? d.fill_level : null);
        tempH[b].push(d ? d.temperature : null);
        methH[b].push(d ? d.methane_level : null);
        if (fillH[b].length > MAX_PTS) { fillH[b].shift(); tempH[b].shift(); methH[b].shift(); }
    }

    // Set chart data
    fillChart.data.labels = labels.slice();
    tempChart.data.labels = labels.slice();
    methChart.data.labels = labels.slice();
    for (var k = 0; k < bins.length; k++) {
        fillChart.data.datasets[k].data = fillH[bins[k]].slice();
        tempChart.data.datasets[k].data = tempH[bins[k]].slice();
        methChart.data.datasets[k].data = methH[bins[k]].slice();
    }
    fillChart.update("none");
    tempChart.update("none");
    methChart.update("none");
}

// ── FETCH LOOP ──────────────────────────────────────────────────────
function fetchData() {
    fetch(API_URL)
        .then(function (r) {
            if (!r.ok) throw new Error("HTTP " + r.status);
            return r.json();
        })
        .then(function (data) {
            if (data && data.length > 0) {
                renderTable(data);
                updateCharts(data);
                statusBar.textContent = "Last update: " + now() + "  |  Streaming every 3s  |  " + data.length + " bins";
            }
        })
        .catch(function (e) {
            console.error("Fetch error:", e);
            statusBar.textContent = "Connection error — retrying… (" + e.message + ")";
        });
}

// ── START ────────────────────────────────────────────────────────────
fetchData();
setInterval(fetchData, REFRESH);
