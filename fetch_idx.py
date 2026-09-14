import json, os, time
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

IDX_PAGE = "https://www.idx.co.id/id/data-pasar/data-saham/ringkasan-perdagangan/ringkasan-saham/"
IDX_API = "https://www.idx.co.id/primary/TradingSummary/GetStockSummary?length=5000&start=0"

def num(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return None

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="id-ID",
            user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"),
            viewport={"width": 1440, "height": 1000},
        )
        page = context.new_page()
        page.goto(IDX_PAGE, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)

        # Fetch from the IDX origin inside the real browser context so
        # cookies/challenge clearance are automatically reused.
        result = None
        last = None
        for attempt in range(1, 4):
            result = page.evaluate("""async (url) => {
              const r = await fetch(url, {
                method: 'GET',
                credentials: 'include',
                headers: {
                  'Accept': 'application/json, text/plain, */*',
                  'X-Requested-With': 'XMLHttpRequest'
                }
              });
              const text = await r.text();
              return {status: r.status, contentType: r.headers.get('content-type') || '', text};
            }""", IDX_API)
            if result["status"] == 200:
                break
            last = result
            page.wait_for_timeout(5000 * attempt)

        if not result or result["status"] != 200:
            status = result["status"] if result else "unknown"
            text = result.get("text","") if result else ""
            raise RuntimeError(f"IDX HTTP {status}: {text[:500]}")

        try:
            payload=json.loads(result["text"])
        except Exception as e:
            raise RuntimeError(f"IDX returned non-JSON: {result['text'][:500]}") from e

        rows = payload.get("Result") or payload.get("data") or payload.get("Data") or []
        if isinstance(rows, dict):
            rows = rows.get("data") or rows.get("rows") or []
        if not isinstance(rows, list):
            raise RuntimeError("IDX JSON rows not found")

        up=down=flat=no_trans=skipped=0
        volume=value=frequency=0.0

        for row in rows:
            if not isinstance(row, dict):
                skipped += 1
                continue
            change = num(row.get("Change") if "Change" in row else row.get("change"))
            vol = num(row.get("Volume") if "Volume" in row else row.get("volume"))
            val = num(row.get("Value") if "Value" in row else row.get("value"))
            freq = num(row.get("Frequency") if "Frequency" in row else row.get("frequency"))

            if vol is not None:
                volume += vol
            if val is not None:
                value += val
            if freq is not None:
                frequency += freq

            if change is None:
                skipped += 1
            elif vol is not None and vol == 0:
                no_trans += 1
            elif change > 0:
                up += 1
            elif change < 0:
                down += 1
            else:
                flat += 1

        expected = payload.get("recordsFiltered")
        if expected is None:
            expected = payload.get("recordsTotal")
        expected_num = int(expected) if str(expected or "").isdigit() else None

        out = {
            "ok": True,
            "source": "IDX Browser Session",
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "recordsReceived": len(rows),
            "recordsExpected": expected_num,
            "complete": expected_num is None or len(rows) >= expected_num,
            "breadth": {
                "up": up, "down": down, "flat": flat,
                "noTrans": no_trans,
                "total": up + down + flat + no_trans,
                "skipped": skipped,
            },
            "market": {
                "volume": volume,
                "value": value,
                "frequency": frequency,
            },
        }
        Path("public").mkdir(exist_ok=True)
        Path("public/market-summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        browser.close()

if __name__ == "__main__":
    main()
