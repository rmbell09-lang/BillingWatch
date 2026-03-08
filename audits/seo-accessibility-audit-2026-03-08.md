# BillingWatch Landing Page — SEO & Accessibility Audit
Date: 2026-03-08 | Auditor: Lucky (direct analysis of index.html, 830 lines)

---

## CRITICAL (Fix Now)

1. Missing Open Graph tags — No og:title, og:description, og:image, og:url. Social shares show nothing.
2. Missing canonical URL — No <link rel="canonical"> tag. Risk of duplicate content penalty.
3. Email input missing label — The signup form has <input type="email" id="email-input"> but no associated <label for="email-input">. Screen readers cannot identify the field. Accessibility fail.

---

## IMPORTANT (Fix Soon)

4. No Twitter Card meta tags — twitter:card, twitter:title, twitter:description missing. Kills Twitter/X share previews.
5. No schema.org structured data — No JSON-LD for SoftwareApplication or Product. Missing rich snippets in search.

---

## WHAT IS ALREADY GOOD

- Title tag: BillingWatch — Real-time Stripe Anomaly Detection (53 chars, specific) PASS
- Meta description: present, descriptive, ~160 chars PASS
- H1: present, strong copy PASS
- H2 structure: 6 logical section headings PASS
- lang=en on html element PASS
- meta viewport set PASS
- Email input has required + autocomplete=email PASS
- No images (no alt text concerns) PASS
- Semantic HTML structure PASS

---

## RECOMMENDED FIXES

Add to <head>:
  <link rel="canonical" href="https://billingwatch.io/">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://billingwatch.io/">
  <meta property="og:title" content="BillingWatch — Real-time Stripe Anomaly Detection">
  <meta property="og:description" content="BillingWatch watches your Stripe account 24/7.">
  <meta property="og:image" content="https://billingwatch.io/og-image.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="BillingWatch — Real-time Stripe Anomaly Detection">

Add label for email input:
  <label for="email-input" class="sr-only">Work email</label>

Add sr-only CSS class:
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
