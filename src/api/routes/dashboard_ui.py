"""Dashboard HTML UI — serves a Chart.js dashboard at /dashboard."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard-ui"])

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BillingWatch Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e1e4e8; }
  .header { background: #161b22; padding: 20px 32px; border-bottom: 1px solid #30363d; display: flex; align-items: center; justify-content: space-between; }
  .header h1 { font-size: 22px; font-weight: 600; }
  .header h1 span { color: #58a6ff; }
  .status-badge { padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; }
  .status-clear { background: #0d1117; border: 1px solid #238636; color: #3fb950; }
  .status-alert { background: #0d1117; border: 1px solid #da3633; color: #f85149; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; padding: 24px 32px; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
  .card .label { font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }
  .card .value { font-size: 32px; font-weight: 700; margin-top: 4px; }
  .card .sub { font-size: 13px; color: #8b949e; margin-top: 4px; }
  .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 0 32px 24px; }
  .chart-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
  .chart-card h3 { font-size: 14px; color: #8b949e; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.5px; }
  canvas { max-height: 300px; }
  .detector-list { padding: 0 32px 32px; }
  .detector-list h3 { font-size: 14px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
  .detector-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background: #161b22; border: 1px solid #30363d; border-radius: 6px; margin-bottom: 6px; }
  .detector-name { font-size: 14px; font-weight: 500; }
  .detector-count { font-size: 14px; font-weight: 700; padding: 2px 10px; border-radius: 12px; }
  .count-zero { color: #484f58; }
  .count-active { color: #f0883e; background: rgba(240,136,62,0.15); }
  .refresh-note { text-align: center; padding: 16px; font-size: 12px; color: #484f58; }
  @media (max-width: 768px) { .charts { grid-template-columns: 1fr; } .grid { grid-template-columns: 1fr 1fr; } }
</style>
</head>
<body>
<div class="header">
  <h1>Billing<span>Watch</span></h1>
  <div id="status-badge" class="status-badge status-clear">● Operational</div>
</div>

<div class="grid">
  <div class="card"><div class="label">Total Events</div><div class="value" id="total-events">—</div><div class="sub" id="window-label">last 24h</div></div>
  <div class="card"><div class="label">Charges</div><div class="value" id="charges-total">—</div><div class="sub" id="charge-detail">—</div></div>
  <div class="card"><div class="label">Failure Rate</div><div class="value" id="failure-rate">—</div><div class="sub">charge failures</div></div>
  <div class="card"><div class="label">Active Alerts</div><div class="value" id="alert-count">—</div><div class="sub" id="alert-detail">—</div></div>
  <div class="card"><div class="label">Uptime</div><div class="value" id="uptime">—</div><div class="sub">since last restart</div></div>
  <div class="card"><div class="label">All-Time Events</div><div class="value" id="alltime">—</div><div class="sub">lifetime processed</div></div>
</div>

<div class="charts">
  <div class="chart-card">
    <h3>Detector Activity</h3>
    <canvas id="detectorChart"></canvas>
  </div>
  <div class="chart-card">
    <h3>Alert Severity</h3>
    <canvas id="severityChart"></canvas>
  </div>
</div>

<div class="detector-list">
  <h3>Detectors</h3>
  <div id="detector-rows"></div>
</div>

<div class="refresh-note">Auto-refreshes every 30 seconds • <span id="last-update">—</span></div>

<script>
let detectorChart, severityChart;

async function fetchDashboard() {
  try {
    const res = await fetch('/dashboard/summary?window_hours=24');
    const d = await res.json();

    // Cards
    const ch = d.events.charges_1h || d.events;
    document.getElementById('total-events').textContent = (d.events.last_1h || d.events.total || 0).toLocaleString();
    document.getElementById('charges-total').textContent = ((ch.succeeded || 0) + (ch.failed || 0)).toLocaleString();
    document.getElementById('charge-detail').textContent = (ch.succeeded || 0) + ' ok / ' + (ch.failed || 0) + ' failed';
    document.getElementById('failure-rate').textContent = ch.failure_rate_pct || '0.0%';
    document.getElementById('alert-count').textContent = d.alerts.total || 0;
    document.getElementById('alert-detail').textContent = (d.alerts.critical || 0) + ' critical, ' + (d.alerts.high || 0) + ' high';
    document.getElementById('uptime').textContent = d.health ? (d.health.uptime_human || '—') : '—';
    document.getElementById('alltime').textContent = (d.events.all_time || 0).toLocaleString();

    // Status badge
    const badge = document.getElementById('status-badge');
    if (d.status === 'alert' || (d.alerts.critical > 0 || d.alerts.high > 0)) {
      badge.className = 'status-badge status-alert';
      badge.textContent = '● Alert';
    } else {
      badge.className = 'status-badge status-clear';
      badge.textContent = '● Operational';
    }

    // Detector chart — handle nested breakdown structure
    const detBreakdown = d.detectors.breakdown || d.detectors || {};
    const detectors = Object.keys(detBreakdown);
    const counts = detectors.map(k => typeof detBreakdown[k] === 'object' ? (detBreakdown[k].total_alerts || 0) : detBreakdown[k]);
    const colors = counts.map(c => c > 0 ? '#f0883e' : '#30363d');

    if (detectorChart) detectorChart.destroy();
    detectorChart = new Chart(document.getElementById('detectorChart'), {
      type: 'bar',
      data: {
        labels: detectors.map(n => n.replace(/_/g, ' ')),
        datasets: [{ data: counts, backgroundColor: colors, borderRadius: 4 }]
      },
      options: {
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: '#21262d' }, ticks: { color: '#8b949e' } },
          y: { grid: { display: false }, ticks: { color: '#c9d1d9', font: { size: 11 } } }
        }
      }
    });

    // Severity chart
    const sevData = [d.alerts.critical || 0, d.alerts.high || 0, d.alerts.medium || 0, d.alerts.low || 0];
    const sevColors = ['#da3633', '#f0883e', '#d29922', '#3fb950'];
    if (severityChart) severityChart.destroy();
    severityChart = new Chart(document.getElementById('severityChart'), {
      type: 'doughnut',
      data: {
        labels: ['Critical', 'High', 'Medium', 'Low'],
        datasets: [{ data: sevData.some(v => v > 0) ? sevData : [0, 0, 0, 1], backgroundColor: sevColors, borderWidth: 0 }]
      },
      options: {
        plugins: {
          legend: { position: 'bottom', labels: { color: '#8b949e', padding: 16 } }
        }
      }
    });

    // Detector rows
    const rows = detectors.map(name => {
      const raw = detBreakdown[name];
      const count = typeof raw === 'object' ? (raw.total_alerts || 0) : (raw || 0);
      const cls = count > 0 ? 'count-active' : 'count-zero';
      return '<div class="detector-row"><span class="detector-name">' +
        name.replace(/_/g, ' ') + '</span><span class="detector-count ' + cls + '">' +
        count + '</span></div>';
    }).join('');
    document.getElementById('detector-rows').innerHTML = rows;

    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
  } catch (e) {
    console.error('Dashboard fetch failed:', e);
  }
}

fetchDashboard();
setInterval(fetchDashboard, 30000);
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the live dashboard UI."""
    return DASHBOARD_HTML
