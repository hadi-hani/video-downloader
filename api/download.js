// Vercel Serverless Function — Cobalt API Proxy
// Tries each instance in order until one responds successfully.

const INSTANCES = [
  'https://cobalt.synklare.dev',
  'https://cobalt.api.timelessnesses.me',
  'https://api.cobalt.tools',
  'https://cobalt-api.thetechrobo.ca',
  'https://cobalt.canine.tools',
  'https://capi.7ws.me',
  'https://co.wuk.sh',
  'https://cobalt.ari.lt',
  'https://cobalt.drgns.space',
  'https://cobalt.perish.co',
];

const TIMEOUT_MS = 12000;

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function fetchWithTimeout(url, options, ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    return res;
  } finally {
    clearTimeout(timer);
  }
}

async function tryInstance(baseUrl, body) {
  // cobalt API v7+ uses /
  // cobalt API v9+ uses /api/json or POST /
  const endpoints = [`${baseUrl}/`, `${baseUrl}/api/json`];

  for (const endpoint of endpoints) {
    try {
      const res = await fetchWithTimeout(
        endpoint,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: JSON.stringify(body),
        },
        TIMEOUT_MS
      );

      // Accept 200 or even some 4xx that still return JSON with url
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch { continue; }

      // If it has a url or picker, it worked
      if (data && (data.url || data.picker)) {
        return { ok: true, data, instance: baseUrl };
      }

      // If it returned a known cobalt error, pass it through (don't try other instances for content errors)
      if (data && data.error) {
        const code = data.error?.code || '';
        const isContentError = [
          'error.api.youtube.login',
          'error.api.youtube.age',
          'error.api.youtube.private',
          'error.api.link.invalid',
          'error.api.link.unsupported',
          'error.api.content.too_long',
          'error.api.content.unavailable',
          'error.api.service.unsupported',
        ].some(e => code.startsWith(e.split('.').slice(0, 4).join('.')));

        if (isContentError) {
          return { ok: false, data, instance: baseUrl, fatal: true };
        }
      }

    } catch (err) {
      // timeout or network error — try next endpoint
      continue;
    }
  }
  return { ok: false, instance: baseUrl };
}

export default async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(204).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  let body;
  try {
    body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  } catch {
    return res.status(400).json({ error: 'Invalid JSON body' });
  }

  if (!body || !body.url) {
    return res.status(400).json({ error: 'Missing url in request body' });
  }

  // Try each instance in order
  for (const instance of INSTANCES) {
    const result = await tryInstance(instance, body);

    if (result.ok) {
      // Success — return the data with which instance was used
      return res.status(200).json({
        ...result.data,
        _instance: instance,
      });
    }

    if (result.fatal) {
      // Content-level error — no point trying other instances
      return res.status(200).json({
        ...result.data,
        _instance: instance,
      });
    }

    // Server-level failure — try next
  }

  // All instances failed
  return res.status(503).json({
    error: {
      code: 'error.api.all_instances_failed',
    },
    status: 'error',
    _triedInstances: INSTANCES.length,
  });
}
