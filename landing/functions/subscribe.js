/**
 * BillingWatch Beta Signup Handler
 * CF Pages Function — handles POST /subscribe
 *
 * Setup in Cloudflare Pages:
 *   1. Create a KV namespace named "billingwatch_signups" in CF dashboard
 *   2. Bind it to this Pages project with variable name: SIGNUPS
 *   3. Deploy — the /subscribe endpoint goes live automatically
 *
 * KV keys: email addresses → JSON value with metadata
 * View signups: CF Dashboard → KV → billingwatch_signups → Keys
 */

export async function onRequestPost(context) {
  const { request, env } = context;

  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
  };

  try {
    let body;
    const contentType = request.headers.get('content-type') || '';

    if (contentType.includes('application/json')) {
      body = await request.json();
    } else if (contentType.includes('application/x-www-form-urlencoded')) {
      const text = await request.text();
      const params = new URLSearchParams(text);
      body = Object.fromEntries(params);
    } else {
      body = await request.json().catch(() => ({}));
    }

    const email = (body.email || '').trim().toLowerCase();
    const name = (body.name || '').trim();

    if (!email || !email.includes('@')) {
      return new Response(
        JSON.stringify({ ok: false, error: 'Valid email required.' }),
        { status: 400, headers }
      );
    }

    const signup = {
      email,
      name: name || null,
      ts: new Date().toISOString(),
      ip: request.headers.get('CF-Connecting-IP') || null,
      country: request.headers.get('CF-IPCountry') || null,
    };

    if (env && env.SIGNUPS) {
      const existing = await env.SIGNUPS.get(email);
      if (existing) {
        return new Response(
          JSON.stringify({ ok: true, message: "You're already on the list!" }),
          { status: 200, headers }
        );
      }
      await env.SIGNUPS.put(email, JSON.stringify(signup));
    } else {
      console.log('[BillingWatch Signup]', JSON.stringify(signup));
    }

    return new Response(
      JSON.stringify({ ok: true, message: "You're on the list! We'll reach out soon." }),
      { status: 200, headers }
    );

  } catch (err) {
    console.error('[BillingWatch Signup Error]', err.message);
    return new Response(
      JSON.stringify({ ok: false, error: 'Something went wrong. Try again.' }),
      { status: 500, headers }
    );
  }
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}
