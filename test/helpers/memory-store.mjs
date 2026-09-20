// A stand-in for a Netlify Blobs store: the handful of calls the functions use, kept in a Map.
export function memoryStore({ failWrites = false } = {}) {
  const m = new Map();
  return {
    m,
    async setJSON(key, value) { if (failWrites) throw new Error('blobs unavailable'); m.set(key, JSON.stringify(value)); },
    async get(key, opts = {}) { const v = m.get(key); return v === undefined ? null : opts.type === 'json' ? JSON.parse(v) : v; },
    async delete(key) { m.delete(key); },
    async list() { return { blobs: [...m.keys()].map((key) => ({ key })) }; },
  };
}
