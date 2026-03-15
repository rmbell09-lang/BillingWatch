"""Dashboard HTML UI — visual status page served at GET /dashboard"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from ...storage.event_store import EventStore

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_store = EventStore()

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BillingWatch Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0f1117;
      color: #e2e8f0;
      min-height: 100vh;
      padding: 24px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }
    .logo { font-size: 1.4rem; font-weight: 700; color: #fff; }
    .logo span { color: #6366f1; }
    .status-badge {
      padding: 6px 14px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .status-healthy  { background: #14532d; color: #4ade80; }
    .status-warning  { background: #713f12; color: #fbbf24; }
    .status-critical { background: #7f1d1d; color: #f87171; }
    .status-no_data  { background: #1e293b; color: #94a3b8; }
    .refresh-info { font-size: 0.75rem; color: #64748b; margin-top: 4px; text-align: right; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .card {
      background: #1e2130;
      border: 1px solid #2d3347;
      border-radius: 12px;
      padding: 20px;
    }
    .card-label { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; }
    .card-value { font-size: 2rem; font-weight: 700; color: #fff; }
    .card-value.critical { color: #f87171; }
    .card-value.warning  { color: #fbbf24; }
    .card-value.good     { color: #4ade80; }
    .card-sub { font-size: 0.8rem; color: #64748b; margin-top: 6px; }
    .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
    @media (max-width: 768px) { .charts { grid-template-columns: 1fr; } }
    .chart-card {
      background: #1e2130;
      border: 1px solid #2d3347;
      border-radius: 12px;
      padding: 20px;
    }
    .chart-title { font-size: 0.85rem; font-weight: 600; color: #cbd5e1; margin-bottom: 16px; }
    .chart-wrap { position: relative; height: 220px; }
    .alert-latest {
      background: #1e2130;
      border: 1px solid #2d3347;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 24px;
    }
    .alert-latest h3 { font-size: 0.85rem; font-weight: 600; color: #cbd5e1; margin-bottom: 12px; }
    .alert-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: #151824;
      border-radius: 8px;
      font-size: 0.85rem;
    }
    .sev-critical { color: #f87171; font-weight: 600; }
    .sev-high     { color: #fbbf24; font-weight: 600; }
    .sev-medium   { color: #60a5fa; }
    .sev-low      { color: #94a3b8; }
    .no-alert { color: #64748b; font-style: italic; font-size: 0.85rem; }
    footer { text-align: center; font-size: 0.75rem; color: #374151; padding-top: 12px; }
    .loading { color: #64748b; font-size: 0.9rem; }
  </style>
</head>
<body>
  <header>
    <div>
      <div class="logo">Billing<span>Watch</span></div>
    </div>
    <div>
      <div id="statusBadge" class="status-badge status-no_data">Loading…</div>
      <div class="refresh-info" id="lastRefresh">—</div>
    </div>
  </header>

  <div class="grid" id="statsGrid">
    <div class="card"><div class="card-label">Events (1h)</div><div class="card-value loading" id="ev1h">…</div></div>
    <div class="card"><div class="card-label">All-Time Events</div><div class="card-value loading" id="evAll">…</div></div>
    <div class="card"><div class="card-label">Failure Rate (1h)</div><div class="card-value loading" id="failRate">…</div></div>
    <div class="card"><div class="card-label">Total Alerts</div><div class="card-value loading" id="totalAlerts">…</div></div>
    <div class="card"><div class="card-label">Critical Alerts</div><div class="card-value loading" id="critAlerts">…</div></div>
    <div class="card"><div class="card-label">High Alerts</div><div class="card-value loading" id="highAlerts">…</div></div>
  </div>

  <div class="charts">
    <div class="chart-card">
      <div class="chart-title">Detector Alert Counts (24h)</div>
      <div class="chart-wrap"><canvas id="detectorChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Alert Severity Breakdown (24h)</div>
      <div class="chart-wrap"><canvas id="severityChart"></canvas></div>
    </div>
  </div>

  <div class="alert-latest">
    <h3>Latest Alert</h3>
    <div id="latestAlert" class="no-alert">No alerts recorded yet.</div>
  </div>

  <footer>BillingWatch v1.0 — self-hosted Stripe anomaly detection</footer>

  <script>
    let detChart = null;
    let sevChart = null;

    function friendlyDetector(name) {
      const map = {
        charge_failure_spike: 'Charge Failure Spike',
        duplicate_charge:     'Duplicate Charge',
        fraud_spike:          'Fraud Spike',
        negative_invoice:     'Negative Invoice',
        revenue_drop:         'Revenue Drop',
        silent_lapse:         'Silent Lapse',
        webhook_lag:          'Webhook Lag',
        currency_mismatch:    'Currency Mismatch',
        timezone_billing_error:'Timezone Billing Error',
        plan_downgrade_data_loss: 'Plan Downgrade Loss',
      };
      return map[name] || name;
    }

    function severityClass(sev) {
      return 'sev-' + (sev || 'low');
    }

    async function refresh() {
      try {
        const [summary, detectors] = await Promise.all([
          fetch('/dashboard/summary').then(r => r.json()),
          fetch('/metrics/detectors?window_hours=24').then(r => r.json()),
        ]);

        // Status badge
        const badge = document.getElementById('statusBadge');
        badge.textContent = summary.status.replace('_', ' ').toUpperCase();
        badge.className = 'status-badge status-' + summary.status;

        // Stat cards
        document.getElementById('ev1h').textContent = summary.events.last_1h.toLocaleString();
        document.getElementById('evAll').textContent = summary.events.all_time.toLocaleString();

        const fr = summary.events.charges_1h.failure_rate_pct;
        const frEl = document.getElementById('failRate');
        frEl.textContent = fr;
        const fNum = summary.events.charges_1h.failure_rate;
        frEl.className = 'card-value ' + (fNum > 0.15 ? 'critical' : fNum > 0.05 ? 'warning' : 'good');

        const ta = summary.alerts.total;
        document.getElementById('totalAlerts').textContent = ta;

        const ca = summary.alerts.critical;
        const caEl = document.getElementById('critAlerts');
        caEl.textContent = ca;
        caEl.className = 'card-value ' + (ca > 0 ? 'critical' : 'good');

        const ha = summary.alerts.high;
        const haEl = document.getElementById('highAlerts');
        haEl.textContent = ha;
        haEl.className = 'card-value ' + (ha > 0 ? 'warning' : 'good');

        // Latest alert
        const latestEl = document.getElementById('latestAlert');
        if (summary.alerts.latest) {
          const a = summary.alerts.latest;
          latestEl.innerHTML = '<div class="alert-row"><span>' + friendlyDetector(a.detector) + '</span>' +
            '<span class="' + severityClass(a.severity) + '">' + (a.severity || '—').toUpperCase() + '</span>' +
            '<span style="color:#64748b;font-size:0.8rem">' + (a.triggered_at || '—') + '</span></div>';
        } else {
          latestEl.innerHTML = '<span class="no-alert">No alerts recorded yet.</span>';
        }

        // Detector bar chart
        const dets = detectors.detectors;
        const labels = Object.keys(dets).map(friendlyDetector);
        const counts = Object.values(dets).map(d => d.total_alerts);

        const barColors = counts.map(c => c === 0 ? '#2d3347' : c >= 5 ? '#f87171' : '#6366f1');

        if (!detChart) {
          detChart = new Chart(document.getElementById('detectorChart'), {
            type: 'bar',
            data: { labels, datasets: [{ label: 'Alerts', data: counts, backgroundColor: barColors, borderRadius: 4 }] },
            options: {
              responsive: true, maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: {
                x: { ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { color: '#1e2130' } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: '#2d3347' }, beginAtZero: true, precision: 0 }
              }
            }
          });
        } else {
          detChart.data.datasets[0].data = counts;
          detChart.data.datasets[0].backgroundColor = barColors;
          detChart.update();
        }

        // Severity doughnut
        const sevData = [
          detectors.summary.critical,
          detectors.summary.high,
          detectors.summary.medium,
          detectors.summary.low,
        ];
        const total = sevData.reduce((a, b) => a + b, 0);

        if (!sevChart) {
          sevChart = new Chart(document.getElementById('severityChart'), {
            type: 'doughnut',
            data: {
              labels: ['Critical', 'High', 'Medium', 'Low'],
              datasets: [{ data: total > 0 ? sevData : [0, 0, 0, 1],
                backgroundColor: ['#f87171', '#fbbf24', '#60a5fa', '#4b5563'],
                borderColor: '#0f1117', borderWidth: 3 }]
            },
            options: {
              responsive: true, maintainAspectRatio: false,
              plugins: { legend: { labels: { color: '#94a3b8', font: { size: 11 } } } },
              cutout: '65%'
            }
          });
        } else {
          sevChart.data.datasets[0].data = total > 0 ? sevData : [0, 0, 0, 1];
          sevChart.update();
        }

        document.getElementById('lastRefresh').textContent =
          'Last updated: ' + new Date().toLocaleTimeString();

      } catch (e) {
        console.error('Dashboard refresh error:', e);
        document.getElementById('statusBadge').textContent = 'ERROR';
        document.getElementById('statusBadge').className = 'status-badge status-critical';
      }
    }

    refresh();
    setInterval(refresh, 30000);
  </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_ui():
    """
    Visual HTML dashboard — Chart.js detector breakdown, failure rate, alert counts.
    Auto-refreshes every 30 seconds. Ideal for screenshots and demos.
    """
    return HTMLResponse(content=_DASHBOARD_HTML)


@router.get("/summary")
async def dashboard_summary():
    """
    Combined health snapshot merging metrics, anomaly summary, and per-detector stats.

    Designed for:
    - Status page widgets
    - External uptime monitors (Uptime Robot, Better Uptime)
    - Morning brief health checks

    Returns a single payload with overall status, event counts, and detector breakdown.
    """
    # --- Event metrics (last hour + all time) ---
    window_sec_1h = 3600
    charge_failed_1h = _store.get_event_count(window_sec_1h, event_type="charge.failed")
    charge_succeeded_1h = _store.get_event_count(window_sec_1h, event_type="charge.succeeded")
    total_charges_1h = charge_failed_1h + charge_succeeded_1h
    failure_rate_1h = (charge_failed_1h / total_charges_1h) if total_charges_1h else 0.0
    events_1h = _store.get_event_count(window_sec_1h)
    all_time = _store.total_count()

    # --- Alert log stats ---
    try:
        from ..routes.webhooks import _alert_log
        log_total = len(_alert_log)
        critical_alerts = [a for a in _alert_log if a.get("severity") == "critical"]
        high_alerts = [a for a in _alert_log if a.get("severity") == "high"]
        latest_alert = _alert_log[-1] if _alert_log else None
    except ImportError:
        log_total = 0
        critical_alerts = []
        high_alerts = []
        latest_alert = None

    # --- Per-detector stats (last 24h) ---
    try:
        from ..routes.metrics import _detector_stats
        detector_window_h = 24.0
        det_stats = _detector_stats(_alert_log if log_total else [], window_hours=detector_window_h)
        top_detector = max(det_stats.items(), key=lambda kv: kv[1]["total_alerts"], default=(None, None))
        top_detector_name = top_detector[0] if top_detector[0] and top_detector[1]["total_alerts"] > 0 else None
    except Exception:
        det_stats = {}
        top_detector_name = None

    # --- Overall status determination ---
    if critical_alerts:
        overall_status = "critical"
    elif high_alerts:
        overall_status = "warning"
    elif events_1h == 0:
        overall_status = "no_data"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "service": "BillingWatch",
        "events": {
            "last_1h": events_1h,
            "all_time": all_time,
            "charges_1h": {
                "succeeded": charge_succeeded_1h,
                "failed": charge_failed_1h,
                "failure_rate": round(failure_rate_1h, 4),
                "failure_rate_pct": f"{failure_rate_1h:.1%}",
            },
        },
        "alerts": {
            "total": log_total,
            "critical": len(critical_alerts),
            "high": len(high_alerts),
            "latest": {
                "detector": latest_alert.get("detector") if latest_alert else None,
                "severity": latest_alert.get("severity") if latest_alert else None,
                "triggered_at": latest_alert.get("triggered_at") if latest_alert else None,
            } if latest_alert else None,
        },
        "detectors": {
            "window_hours": 24,
            "top_firing": top_detector_name,
            "breakdown": det_stats,
        },
    }
