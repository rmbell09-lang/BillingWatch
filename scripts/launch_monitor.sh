#!/bin/bash
# BillingWatch Launch Monitor — run during HN/IH launch windows
# Usage: bash scripts/launch_monitor.sh

set -euo pipefail
API="http://localhost:8000"

echo "========================================"
echo " BillingWatch Launch Monitor"
echo " $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "========================================"
echo

# Health check
echo "--- Health ---"
health=$(curl -sf "$API/health" 2>/dev/null || echo '{"error":"API unreachable"}')
echo "$health" | python3 -m json.tool 2>/dev/null || echo "$health"
echo

# Beta signups
echo "--- Beta Signups ---"
if command -v sqlite3 &>/dev/null && [ -f ~/Projects/BillingWatch/billingwatch.db ]; then
    count=$(sqlite3 ~/Projects/BillingWatch/billingwatch.db "SELECT COUNT(*) FROM subscribers;" 2>/dev/null || echo "0")
    echo "Total subscribers: $count"
    echo "Last 5:"
    sqlite3 -header -column ~/Projects/BillingWatch/billingwatch.db \
        "SELECT email, created_at FROM subscribers ORDER BY created_at DESC LIMIT 5;" 2>/dev/null || echo "  (no subscribers table or empty)"
else
    echo "  (sqlite3 not available or db not found)"
fi
echo

# Beta feedback
echo "--- Beta Feedback ---"
feedback=$(curl -sf "$API/beta/feedback/summary" 2>/dev/null || echo '{"error":"endpoint unavailable"}')
echo "$feedback" | python3 -m json.tool 2>/dev/null || echo "$feedback"
echo

# Anomaly stats
echo "--- Anomaly Stats (24h) ---"
metrics=$(curl -sf "$API/metrics/detectors?window_hours=24" 2>/dev/null || echo '{"error":"endpoint unavailable"}')
echo "$metrics" | python3 -m json.tool 2>/dev/null || echo "$metrics"
echo

# Process uptime
echo "--- Process ---"
ps aux | grep -E 'uvicorn|billingwatch' | grep -v grep || echo "  No BillingWatch process found"
echo

echo "========================================"
echo " Monitor complete"
echo "========================================"
