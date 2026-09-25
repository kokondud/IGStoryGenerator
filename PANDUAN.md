# Panduan Pemasangan — KISI Story Generator (versi perbaikan)

## 1. Cloudflare Worker baru
1. Buka dash.cloudflare.com → **Workers & Pages** → **Create** → **Create Worker**.
2. Nama: **kisi-story-data** → **Deploy**.
3. **Edit code** → hapus isi bawaan → tempel seluruh isi `worker/kisi-story-data.js` → **Deploy**.
4. Tes: buka `https://kisi-story-data.kho-xaverius.workers.dev/?part=morning` — harus muncul teks JSON berisi angka.
5. Kalau alamat worker berbeda, ganti `DATA_WORKER_URL` di `index.html`.
6. **Jangan hapus worker lama (kisi-yahoo-proxy)** — worker baru memakainya untuk komoditas, breadth & sektor.

## 2. GitHub
1. Upload semua file & folder: `index.html`, `data/`, `scripts/`, `worker/`, `public/`, `.github/workflows/`.
2. Hapus file lama: `fetch_idx.py` dan `.github/workflows/idx-market.yml`.
3. **Settings → Actions → General → Workflow permissions → Read and write** → Save.
4. Pastikan GitHub Pages aktif. Generator harus dibuka dari alamat GitHub Pages (bukan file lokal).
5. Tab **Actions → Data IDX (Wrap & Kalender) → Run workflow**: jalankan sekali mode `wrap`, sekali mode `calendar`.

Jadwal otomatis (WIB): kalender 05:00 (Senin–Jumat), data Wrap 16:45 dan 17:20.

## 3. Perawatan rutin
- **Daftar saham / RD KISI berubah:** ganti `data/Daftar_Saham_IDX.xlsx` atau `data/RD_kisi.xlsx` di GitHub. Workflow "Update daftar saham & RD" otomatis membuat ulang `stocks.js` / `rd_kisi.js`.
- **Akhir tahun:** perbarui `data/macro.js` (jadwal RDG BI, FOMC, rilis BPS tahun berikutnya).
- **Jadwal BPS 2026** belum terisi — isi dari bps.go.id/id/arc (contoh format ada di file).

## 4. Kalau ada yang gagal
- Tombol fetch merah → coba lagi; kalau tetap gagal pakai "✎ Isi manual" dan cek angka dengan sumber resmi.
- Workflow merah di tab Actions → buka log, screenshot, kirim untuk diperbaiki.
- Kalender emiten kosong terus → cek `public/calendar-raw.json` (isi mentah dari situs IDX).
