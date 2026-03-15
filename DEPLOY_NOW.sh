#!/bin/bash
# BillingWatch Landing → Cloudflare Pages
# Run this in Terminal (GUI) — Keychain access required

set -e
echo "== BillingWatch CF Pages Deploy =="

# Read from Keychain (requires GUI context)
CF_API_TOKEN=$(security find-generic-password -a luckyai -s "BillingWatch-CF-Token" -w 2>/dev/null)
CF_ACCOUNT_ID=$(security find-generic-password -a luckyai -s "BillingWatch-CF-AccountID" -w 2>/dev/null)

if [ -z "$CF_API_TOKEN" ] || [ -z "$CF_ACCOUNT_ID" ]; then
  echo "ERROR: CF keys not found in Keychain"
  echo "Store them with:"
  echo "  security add-generic-password -a luckyai -s \"BillingWatch-CF-Token\" -w \"<TOKEN>\" -U"
  echo "  security add-generic-password -a luckyai -s \"BillingWatch-CF-AccountID\" -w \"<ACCOUNT_ID>\" -U"
  exit 1
fi

echo "Keys loaded from Keychain"
export CF_API_TOKEN CF_ACCOUNT_ID
cd ~/Projects/BillingWatch/landing
python3 deploy_cf.py
