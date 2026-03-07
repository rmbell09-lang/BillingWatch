# BillingWatch: Stripe Webhook Events + API Research
*Researched: 2026-03-05 | Source: docs.stripe.com*

---

## Core Architecture

Stripe webhooks use a POST to HTTPS endpoint model. Key behaviors:
- Return 200 immediately before processing (fire-and-forget receiver)
- Stripe retries failed deliveries (non-2xx) with exponential backoff
- Events have unique IDs — always store and deduplicate by event ID
- Use stripe.Webhook.construct_event() to verify signature with STRIPE_WEBHOOK_SECRET

---

## Critical Events for BillingWatch

### Charge Events
- charge.succeeded — Charge successful → Duplicate charge detection, fraud spike detection
- charge.failed — Charge failed → Charge failure spike detector
- charge.refunded — Charge refunded → Revenue tracking
- charge.dispute.created — Customer disputes charge → Fraud alerting
- charge.dispute.closed — Dispute resolved (lost/won) → Chargeback tracking

### Invoice Events
- invoice.payment_succeeded — Invoice paid → Revenue tracking, silent lapse resolution
- invoice.payment_failed — Invoice payment failed → Dunning tracking, failure spike
- invoice.finalized — Invoice finalized → NEGATIVE INVOICE detection
- invoice.created — Invoice created → Revenue forecasting

### Subscription Events
- customer.subscription.updated — Sub status/amount changed → Silent lapse trigger, plan change tracking
- customer.subscription.deleted — Sub cancelled → Churn detection, revenue drop signal
- customer.subscription.created — New subscription → MRR tracking
- customer.subscription.trial_will_end — Trial ending in 3 days → Conversion tracking

### Customer Events
- customer.created — New customer → Growth tracking
- customer.deleted — Customer deleted → Data cleanup signal
- customer.discount.created — Coupon applied → Discount abuse monitoring

---

## Stripe API Queries for Detectors

### List Recent Charges (Duplicate/Fraud Detection)


### Get Subscription Status (Silent Lapse)


### List All Active Subscriptions (Periodic Scan)


### Revenue Aggregation (Drop Detection)


---

## Detector Event Mapping

| Detector | Primary Events | API Supplement |
|---|---|---|
| Charge Failure Spike | charge.failed, invoice.payment_failed | None (event-driven) |
| Silent Subscription Lapse | customer.subscription.updated, invoice.payment_succeeded | Subscription.list(status=active) periodic scan |
| Revenue Anomaly | invoice.payment_succeeded, customer.subscription.deleted | Invoice.list(status=paid) daily rollup |
| Duplicate Charge | charge.succeeded | Charge.list(customer=x, created.gte=5_min_ago) |
| Negative Invoice | invoice.finalized | None (event-driven) |
| Webhook Processing Lag | Internal queue depth | N/A |
| Fraud Spike | charge.succeeded | card fingerprint from payment_method_details.card.fingerprint |

---

## Event Object Key Fields

### charge.succeeded / charge.failed
- id: Charge ID (ch_xxx)
- customer: Customer ID (cus_xxx) or null
- amount: Amount in cents
- status: succeeded | failed | pending
- failure_code: e.g. card_declined, insufficient_funds
- failure_message: Human-readable failure reason
- payment_method_details.card.fingerprint: For fraud detection
- created: Unix timestamp

### invoice.payment_succeeded / invoice.payment_failed
- id: Invoice ID (in_xxx)
- customer: Customer ID
- subscription: Subscription ID (sub_xxx) or null
- amount_due: Total due in cents
- amount_paid: Amount actually paid
- total: Pre-tax total (CAN BE NEGATIVE — promo bug signal)
- status: paid | open | void | draft

### customer.subscription.updated
- id: Subscription ID (sub_xxx)
- customer: Customer ID
- status: active | past_due | canceled | trialing | unpaid
- current_period_start / current_period_end: Billing period
- cancel_at_period_end: bool

---

## Webhook Registration — Events to Subscribe

Register BillingWatch endpoint in Stripe Dashboard > Developers > Webhooks:
- URL: https://billingwatch.yourdomain.com/api/webhooks/stripe
- Events to subscribe:
  - charge.succeeded
  - charge.failed
  - invoice.payment_succeeded
  - invoice.payment_failed
  - invoice.finalized
  - customer.subscription.updated
  - customer.subscription.deleted
  - customer.discount.created

---

## Implementation Notes

### Idempotency (Critical)
- Store each event by id (Stripe event ID) as primary key
- Stripe may send the same event twice — always check if already processed
- Use DB constraint: stripe_events.id TEXT PRIMARY KEY

### Retry Behavior
Stripe retries on non-2xx: 5s, 5min, 30min, 2h, 5h, 10h then stops.
Always return 200 immediately, process async via queue.

### Rate Limits
- Stripe API: 100 req/sec in live mode, 25 in test mode
- For bulk scans, use auto_paging_iter() and limit to ~10 req/s

### Webhook Security Checklist
- Verify Stripe-Signature header on every request
- Use raw bytes for signature check (not parsed JSON)
- Store webhook secret in env var, never hardcode
- Reject events older than 5 minutes (replay attack protection)
- Require HTTPS in production

---

## Stripe CLI for Local Testing

stripe listen --forward-to localhost:8000/api/webhooks/stripe
stripe trigger charge.succeeded
stripe trigger invoice.payment_failed

---

## Additional Resources
- Full event types: https://docs.stripe.com/api/events/types
- Webhook guide: https://docs.stripe.com/webhooks
- Python SDK: https://github.com/stripe/stripe-python

---

*Research complete. See SPEC.md for how this maps to the 7 BillingWatch detectors.*
