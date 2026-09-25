/**
 * KISI Story Data — Cloudflare Worker
 * ------------------------------------------------------------------
 * Dipakai oleh KISI Story Generator (index.html):
 *   ?part=morning   → penutupan TERAKHIR yang sudah selesai (IHSG, indeks global,
 *                     USD/IDR, minyak WTI, emas) + 20 penutupan IHSG untuk grafik
 *                     + komoditas (timah, batu bara, CPO, nikel) dari worker lama.
 *   ?part=halftime  → IHSG sesi 1 (harga, %, high, low), market breadth, sektor.
 *   ?part=ping      → cek worker hidup.
 *
 * Worker lama (kisi-yahoo-proxy) TETAP dipakai untuk komoditas, breadth, dan sektor,
 * karena kodenya tidak ada di repo. Jangan hapus worker lama.
 * Kalau alamat worker lama berubah, ubah OLD_WORKER di bawah, atau isi variabel
 * OLD_WORKER_URL di Settings → Variables pada dashboard Cloudflare.
 */

const OLD_WORKER = 'https://kisi-yahoo-proxy.kho-xaverius.workers.dev/';

const YAHOO = {
  ihsg: '^JKSE', djia: '^DJI', ndq: '^IXIC', sp: '^GSPC',
  nk: '^N225', hsi: '^HSI', idr: 'IDR=X', oil: 'CL=F', gold: 'GC=F',
};
const COMMODITIES = { tin: 'TIN_BI', coal: 'COAL_BI', cpo: 'FCPO_MY', ni: 'NICKEL_BI' };
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store',
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS });
    const url = new URL(request.url);
    const part = url.searchParams.get('part') || 'ping';
    const oldWorker = (env && env.OLD_WORKER_URL) || OLD_WORKER;
    try {
      let body;
      if (part === 'morning') body = await morning(oldWorker);
      else if (part === 'halftime') body = await halftime(oldWorker);
      else if (part === 'ping') body = { ok: true, now: new Date().toISOString() };
      else return json({ error: `part tidak dikenal: ${part}` }, 400);
      return json(body);
    } catch (e) {
      return json({ error: String(e && e.message || e) }, 502);
    }
  },
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: CORS });
}

async function getJSON(url, opts = {}, timeoutMs = 12000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { ...opts, signal: ctrl.signal });
    if (!r.ok) throw new Error(`HTTP ${r.status} dari ${new URL(url).host}`);
    return await r.json();
  } finally {
    clearTimeout(t);
  }
}

async function yahooChart(symbol, range, interval) {
  const u = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}` +
    `?range=${range}&interval=${interval}&includePrePost=false`;
  const d = await getJSON(u, { headers: { 'User-Agent': UA, 'Accept': 'application/json' } });
  const res = d && d.chart && d.chart.result && d.chart.result[0];
  if (!res) throw new Error(`Yahoo tidak mengembalikan data untuk ${symbol}`);
  return res;
}

/** Tanggal (YYYY-MM-DD) sebuah timestamp di zona waktu bursanya. */
function dateAt(ts, gmtoffset) {
  return new Date((ts + (gmtoffset || 0)) * 1000).toISOString().slice(0, 10);
}

/**
 * Ambil candle harian yang SUDAH SELESAI.
 * Candle hari ini dibuang kalau sesi bursanya belum tutup,
 * jadi hasilnya selalu "penutupan terakhir" walau di-fetch saat bursa sedang buka.
 */
function completedDaily(res) {
  const ts = res.timestamp || [];
  const closes = (res.indicators && res.indicators.quote && res.indicators.quote[0].close) || [];
  const rows = ts.map((t, i) => ({ t, close: closes[i] })).filter(r => r.close != null);
  const reg = res.meta && res.meta.currentTradingPeriod && res.meta.currentTradingPeriod.regular;
  const now = Date.now() / 1000;
  if (rows.length && reg) {
    const last = rows[rows.length - 1];
    if (last.t >= reg.start - 60 && now < reg.end) rows.pop();
  }
  return rows;
}

async function morning(oldWorker) {
  const quotes = {};
  const errors = {};
  await Promise.all(Object.entries(YAHOO).map(async ([key, sym]) => {
    try {
      const res = await yahooChart(sym, '1mo', '1d');
      const rows = completedDaily(res);
      if (rows.length < 2) throw new Error('data penutupan kurang dari 2 hari');
      const a = rows[rows.length - 1], b = rows[rows.length - 2];
      quotes[key] = {
        close: a.close, prevClose: b.close,
        changePct: (a.close - b.close) / b.close * 100,
        date: dateAt(a.t, res.meta.gmtoffset),
      };
      if (key === 'ihsg') quotes[key].spark = rows.slice(-20).map(r => r.close);
    } catch (e) { errors[key] = String(e.message || e); }
  }));

  const commodities = {};
  try {
    const u = `${oldWorker}?symbols=${encodeURIComponent(Object.values(COMMODITIES).join(','))}`;
    const d = await getJSON(u);
    for (const [key, sym] of Object.entries(COMMODITIES)) {
      const x = d[sym];
      if (!x || x.error || x.price == null || x.prevClose == null) { errors[key] = (x && x.error) || 'tidak tersedia'; continue; }
      commodities[key] = { close: x.price, prevClose: x.prevClose, changePct: (x.price - x.prevClose) / x.prevClose * 100, date: x.date || null };
    }
  } catch (e) {
    for (const key of Object.keys(COMMODITIES)) errors[key] = 'worker lama: ' + String(e.message || e);
  }
  return { ok: true, fetchedAt: new Date().toISOString(), quotes, commodities, errors };
}

async function halftime(oldWorker) {
  const [breadthRes, summaryRes, intraday] = await Promise.all([
    getJSON(`${oldWorker}?market=idx&part=idx`, {}, 25000),
    getJSON(`${oldWorker}?market=idx&part=summary`, {}, 25000),
    yahooChart('^JKSE', '1d', '5m').catch(e => ({ error: String(e.message || e) })),
  ]);
  if (breadthRes.error) throw new Error('Breadth: ' + breadthRes.error);
  if (summaryRes.error) throw new Error('Ringkasan IHSG: ' + summaryRes.error);

  // High & low sesi 1: candle 5 menit IHSG sampai akhir sesi 1 (12:00 WIB; Jumat 11:30).
  let high = null, low = null, hlSource = null;
  if (intraday && !intraday.error) {
    const off = intraday.meta.gmtoffset || 25200;
    const q = intraday.indicators.quote[0];
    (intraday.timestamp || []).forEach((t, i) => {
      const local = new Date((t + off) * 1000);
      const mins = local.getUTCHours() * 60 + local.getUTCMinutes();
      const endS1 = local.getUTCDay() === 5 ? 11 * 60 + 30 : 12 * 60;
      if (mins < 9 * 60 || mins >= endS1) return;
      if (q.high[i] != null) high = high == null ? q.high[i] : Math.max(high, q.high[i]);
      if (q.low[i] != null) low = low == null ? q.low[i] : Math.min(low, q.low[i]);
    });
    hlSource = 'Yahoo 5m';
    if (high == null && intraday.meta) {
      high = intraday.meta.regularMarketDayHigh ?? null;
      low = intraday.meta.regularMarketDayLow ?? null;
      hlSource = 'Yahoo meta';
    }
  }

  const m = summaryRes.market || {};
  return {
    ok: true,
    fetchedAt: new Date().toISOString(),
    ihsg: {
      price: m.ihsg ? m.ihsg.price : null,
      changePct: m.ihsg ? m.ihsg.changePct : null,
      high, low, hlSource,
    },
    breadth: breadthRes.breadth || null,
    breadthSource: breadthRes.source || null,
    complete: !!breadthRes.complete,
    masterUniverse: breadthRes.masterUniverse || null,
    recordsReceived: breadthRes.recordsReceived || null,
    sectors: Array.isArray(m.sectors) ? m.sectors : [],
  };
}
