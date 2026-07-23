// Returns health status of all cobalt instances
// Called by the frontend to display the instances bar

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

async function checkInstance(url) {
  const t0 = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  try {
    // Try both common info endpoints
    const endpoints = [`${url}/api/serverInfo`, `${url}/serverInfo`, `${url}/`];
    for (const ep of endpoints) {
      try {
        const res = await fetch(ep, {
          method: 'GET',
          headers: { Accept: 'application/json' },
          signal: controller.signal,
        });
        if (res.ok) {
          clearTimeout(timer);
          return { url, ok: true, ping: Date.now() - t0 };
        }
      } catch { continue; }
    }
    return { url, ok: false, ping: null };
  } catch {
    return { url, ok: false, ping: null };
  } finally {
    clearTimeout(timer);
  }
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'no-store');

  const results = await Promise.allSettled(INSTANCES.map(checkInstance));
  const data = results.map(r => r.status === 'fulfilled' ? r.value : { url: '?', ok: false, ping: null });
  const alive = data.filter(d => d.ok).length;

  return res.status(200).json({ instances: data, alive, total: INSTANCES.length });
}
