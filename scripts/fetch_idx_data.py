"""
Ambil data gratis untuk KISI Story Generator. Dijalankan oleh GitHub Actions.

    python scripts/fetch_idx_data.py wrap       -> public/wrap.json
    python scripts/fetch_idx_data.py calendar   -> public/calendar.json (+ public/calendar-raw.json)

wrap     : ringkasan penutupan resmi IDX — IHSG (close, high, low, volume, nilai),
           indeks sektoral, dan harga penutupan semua saham (untuk breadth & % kontribusi).
calendar : agenda emiten dari kalender IDX (corporate action, RUPS, public expose, IPO)
           + jadwal rilis CPI & NFP dari kalender resmi BLS (AS).

IDX dilindungi Cloudflare, jadi data diambil lewat browser sungguhan (Playwright).
Kalau IDX memblok, script berhenti dengan error dan file lama TIDAK ditimpa.
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
WIB = ZoneInfo("Asia/Jakarta")

IDX_HOME = "https://www.idx.co.id/id/data-pasar/data-saham/ringkasan-perdagangan/ringkasan-saham/"
IDX_STOCK_API = "https://www.idx.co.id/primary/TradingSummary/GetStockSummary?length=9999&start=0"
IDX_INDEX_API = "https://www.idx.co.id/primary/TradingSummary/GetIndexSummary?length=9999&start=0"
IDX_CALENDAR_PAGES = [
    "https://www.idx.co.id/id/berita/kalender/",
    "https://www.idx.co.id/id/perusahaan-tercatat/aksi-korporasi/",
]
BLS_ICS = "https://www.bls.gov/schedule/news_release/bls.ics"

SECTORS = {
    "IDXENERGY": "Energi", "IDXBASIC": "Barang Baku", "IDXINDUST": "Perindustrian",
    "IDXNONCYC": "Konsumen Primer", "IDXCYCLIC": "Konsumen Non-Primer", "IDXHEALTH": "Kesehatan",
    "IDXFINANCE": "Keuangan", "IDXPROPERT": "Properti", "IDXTECHNO": "Teknologi",
    "IDXINFRA": "Infrastruktur", "IDXTRANS": "Transportasi",
}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")


# ---------------------------------------------------------------- helpers
def num(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def pick(row, *keys):
    low = {k.lower(): v for k, v in row.items()}
    for k in keys:
        if k.lower() in low:
            return low[k.lower()]
    return None


def rows_of(payload):
    rows = payload.get("Result") or payload.get("data") or payload.get("Data") or []
    if isinstance(rows, dict):
        rows = rows.get("data") or rows.get("rows") or []
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("Data IDX kosong / format berubah")
    return rows


def write(name, obj):
    PUBLIC.mkdir(exist_ok=True)
    (PUBLIC / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ public/{name} ditulis")


def open_browser(p):
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(locale="id-ID", user_agent=UA, viewport={"width": 1440, "height": 1000},
                              timezone_id="Asia/Jakarta")
    return browser, ctx.new_page()


def fetch_in_page(page, url):
    """Fetch dari dalam halaman IDX supaya cookie/clearance Cloudflare ikut terpakai."""
    last = None
    for attempt in range(1, 4):
        res = page.evaluate("""async (url) => {
            const r = await fetch(url, {credentials:'include',
              headers:{'Accept':'application/json, text/plain, */*','X-Requested-With':'XMLHttpRequest'}});
            return {status:r.status, text: await r.text()};
        }""", url)
        if res["status"] == 200:
            try:
                return json.loads(res["text"])
            except json.JSONDecodeError:
                last = f"bukan JSON (kemungkinan diblok Cloudflare): {res['text'][:200]}"
        else:
            last = f"HTTP {res['status']}: {res['text'][:200]}"
        page.wait_for_timeout(4000 * attempt)
    raise RuntimeError(f"Gagal ambil {url} — {last}")


# ---------------------------------------------------------------- wrap
def wrap():
    with sync_playwright() as p:
        browser, page = open_browser(p)
        try:
            page.goto(IDX_HOME, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(8000)
            stock_rows = rows_of(fetch_in_page(page, IDX_STOCK_API))
            index_rows = rows_of(fetch_in_page(page, IDX_INDEX_API))
        finally:
            browser.close()

    stocks, dates = {}, set()
    for r in stock_rows:
        code = str(pick(r, "StockCode", "Code", "KodeSaham") or "").strip().upper()
        if not code:
            continue
        d = str(pick(r, "Date") or "")[:10]
        if d:
            dates.add(d)
        stocks[code] = [num(pick(r, "Close")), num(pick(r, "Previous", "Prev")),
                        num(pick(r, "Change")), num(pick(r, "Volume")), num(pick(r, "Value"))]

    indices = {}
    for r in index_rows:
        code = str(pick(r, "IndexCode", "Code") or "").strip().upper()
        if not code:
            continue
        d = str(pick(r, "Date") or "")[:10]
        if d:
            dates.add(d)
        prev, close, chg = num(pick(r, "Previous", "Prev")), num(pick(r, "Close")), num(pick(r, "Change"))
        if chg is None and prev and close is not None:
            chg = close - prev
        indices[code] = {
            "close": close, "prev": prev, "change": chg,
            "pct": (chg / prev * 100) if (chg is not None and prev) else None,
            "high": num(pick(r, "Highest", "High")), "low": num(pick(r, "Lowest", "Low")),
            "volume": num(pick(r, "Volume")), "value": num(pick(r, "Value")),
            "frequency": num(pick(r, "Frequency")),
        }

    comp = indices.get("COMPOSITE")
    if not comp or comp["close"] is None:
        raise RuntimeError("Baris COMPOSITE (IHSG) tidak ditemukan di ringkasan indeks IDX")
    if not comp.get("volume"):
        comp["volume"] = sum((s[3] or 0) for s in stocks.values())
    if not comp.get("value"):
        comp["value"] = sum((s[4] or 0) for s in stocks.values())

    if len(dates) != 1:
        print("⚠ Tanggal data IDX tidak seragam:", sorted(dates))
    trade_date = max(dates) if dates else None

    sectors = [{"code": c, "name": n, "pct": indices[c]["pct"]}
               for c, n in SECTORS.items() if c in indices and indices[c]["pct"] is not None]

    write("wrap.json", {
        "ok": True, "source": "IDX (ringkasan penutupan resmi)",
        "date": trade_date, "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "ihsg": comp, "sectors": sectors,
        "stocks": {k: v[:4] for k, v in stocks.items()},   # [close, prev, change, volume]
    })


# ---------------------------------------------------------------- calendar
def find_record_lists(obj, out):
    """Cari semua list berisi dict di dalam JSON (struktur IDX bisa bersarang)."""
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj):
            out.append(obj)
        for x in obj:
            find_record_lists(x, out)
    elif isinstance(obj, dict):
        for v in obj.values():
            find_record_lists(v, out)
    return out


DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})|(\d{1,2})/(\d{1,2})/(\d{4})")


def parse_date(v):
    m = DATE_RE.search(str(v or ""))
    if not m:
        return None
    if m.group(1):
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return f"{m.group(6)}-{int(m.group(5)):02d}-{int(m.group(4)):02d}"


def classify(text):
    t = text.lower()
    if "public expose" in t or "paparan publik" in t:
        return "PUBEX"
    if "rups" in t or "rapat umum" in t:
        return "RUPS"
    if "ipo" in t or "pencatatan perdana" in t or "penawaran umum perdana" in t:
        return "IPO"
    if any(k in t for k in ("dividen", "cum", "ex date", "recording", "pembayaran", "stock split",
                            "pemecahan", "hmetd", "rights", "saham bonus", "reverse")):
        return "CA"
    return None


def normalize(rec):
    low = {k.lower(): v for k, v in rec.items()}
    date = None
    for k, v in low.items():
        if "date" in k or "tanggal" in k:
            date = parse_date(v)
            if date:
                break
    code = next((str(low[k]).strip().upper() for k in
                 ("code", "kode", "stockcode", "kodeemiten", "ticker", "kode_emiten") if low.get(k)), "")
    title = next((str(low[k]).strip() for k in
                  ("description", "keterangan", "agenda", "title", "judul", "step", "event", "kegiatan",
                   "jenis", "type", "nama") if low.get(k)), "")
    time = None
    for k, v in low.items():
        if any(x in k for x in ("time", "jam", "hour", "waktu")):
            m = re.search(r"(\d{1,2})[:.](\d{2})", str(v or ""))
            if m:
                time = f"{int(m.group(1)):02d}:{m.group(2)}"
                break
    cat = classify(" ".join(str(v) for v in rec.values() if isinstance(v, (str, int, float))))
    if not (date and cat and (code or title)):
        return None
    if code and not re.fullmatch(r"[A-Z]{4}", code):
        m = re.search(r"\b([A-Z]{4})\b", code)
        code = m.group(1) if m else code[:6]
    return {"date": date, "code": code, "category": cat, "title": title[:80], "time": time}


def bls_events():
    """CPI & NFP dari kalender resmi BLS (.ics), jam dikonversi ke WIB."""
    req = urllib.request.Request(BLS_ICS, headers={"User-Agent": UA, "Accept": "text/calendar,*/*"})
    text = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    text = re.sub(r"\r?\n[ \t]", "", text)  # unfold baris .ics
    events = []
    for block in text.split("BEGIN:VEVENT")[1:]:
        summ = re.search(r"^SUMMARY[^:]*:(.*)$", block, re.M)
        dt = re.search(r"^DTSTART(;[^:]*)?:(\d{8}T\d{4,6}Z?)$", block, re.M)
        if not (summ and dt):
            continue
        s = summ.group(1).strip()
        if s.startswith("Consumer Price Index"):
            label = "Inflasi AS (CPI)"
        elif s.startswith("Employment Situation"):
            label = "Data tenaga kerja AS (Non-Farm Payrolls)"
        else:
            continue
        raw = dt.group(2)
        base = datetime.strptime(raw[:13], "%Y%m%dT%H%M")
        if raw.endswith("Z"):
            when = base.replace(tzinfo=timezone.utc)
        else:
            tz = re.search(r"TZID=([^;:]+)", dt.group(1) or "")
            try:
                zone = ZoneInfo(tz.group(1).strip('"')) if tz else ZoneInfo("America/New_York")
            except Exception:
                zone = ZoneInfo("America/New_York")  # BLS memakai Eastern Time
            when = base.replace(tzinfo=zone)
        w = when.astimezone(WIB)
        events.append({"date": w.strftime("%Y-%m-%d"), "time": w.strftime("%H:%M"),
                       "country": "US", "event": label, "source": "BLS"})
    return events


def calendar():
    captured = []
    with sync_playwright() as p:
        browser, page = open_browser(p)

        def on_response(resp):
            try:
                if "json" in (resp.headers.get("content-type") or "") and "idx.co.id" in resp.url:
                    captured.append({"url": resp.url, "json": resp.json()})
            except Exception:
                pass

        page.on("response", on_response)
        try:
            for url in IDX_CALENDAR_PAGES:
                try:
                    page.goto(url, wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(5000)
                except Exception as e:
                    print("⚠ Gagal buka", url, e)
        finally:
            browser.close()

    write("calendar-raw.json", [{"url": c["url"], "sample": str(c["json"])[:3000]} for c in captured])

    today = datetime.now(WIB).date()
    horizon = today + timedelta(days=14)
    items, seen = [], set()
    for c in captured:
        for lst in find_record_lists(c["json"], []):
            for rec in lst:
                n = normalize(rec)
                if not n:
                    continue
                d = datetime.strptime(n["date"], "%Y-%m-%d").date()
                if not (today - timedelta(days=1) <= d <= horizon):
                    continue
                key = (n["date"], n["code"], n["category"], n["title"])
                if key not in seen:
                    seen.add(key)
                    items.append(n)

    try:
        macro = bls_events()
    except Exception as e:
        print("⚠ Kalender BLS gagal:", e)
        macro = []

    print(f"Agenda emiten: {len(items)} | agenda AS (BLS): {len(macro)}")
    write("calendar.json", {
        "ok": True, "generatedAt": datetime.now(timezone.utc).isoformat(),
        "idx": sorted(items, key=lambda x: (x["date"], x["category"], x["code"])),
        "macro": macro,
        "note": "Agenda emiten dibaca otomatis dari situs IDX; cek public/calendar-raw.json bila kosong.",
    })


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "wrap"
    {"wrap": wrap, "calendar": calendar}[mode]()
