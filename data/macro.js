// =====================================================================
// AGENDA MAKRO TETAP — dipakai halaman "Kalender Hari Ini" (KISI Morning)
// =====================================================================
// Semua jam dalam WIB. time:null = jam tidak dicantumkan (tampil sepanjang hari itu).
// Acara yang jatuh dini hari (00:00–06:59 WIB) otomatis tampil di Morning HARI SEBELUMNYA,
// karena itulah agenda yang dinanti pasar malam itu.
//
// Perbarui file ini SETIAP AKHIR TAHUN (± 1–2 jam kerja):
//   • RDG Bank Indonesia  : bi.go.id → Publikasi → Kalender (jadwal RDG tahun berikutnya, rilis ± Desember)
//   • FOMC The Fed        : federalreserve.gov → FOMC Calendar
//   • Rilis BPS           : bps.go.id/id/arc (Rencana Terbit) — inflasi, neraca perdagangan, PDB
//   • CPI & NFP AS        : sudah diambil OTOMATIS dari kalender resmi BLS oleh GitHub Action
//                           (public/calendar.json). Baris AS di bawah hanya cadangan.
//
// Konversi jam AS → WIB: saat AS musim panas (EDT, ± Maret–awal Nov) tambah 11 jam,
// selain itu (EST) tambah 12 jam. Contoh: CPI 08:30 EDT = 19:30 WIB; 08:30 EST = 20:30 WIB.
// =====================================================================
window.MACRO_EVENTS = [
  // ---- Bank Indonesia: pengumuman hasil RDG (hari ke-2). Sumber: jadwal RDG 2026 BI (rilis 23 Des 2025)
  {date:'2026-01-21', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},
  {date:'2026-02-19', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},
  {date:'2026-03-17', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},
  {date:'2026-04-22', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},
  {date:'2026-05-20', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},
  {date:'2026-06-18', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},
  {date:'2026-07-22', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},
  {date:'2026-08-19', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},
  {date:'2026-09-23', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},
  {date:'2026-10-21', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},
  {date:'2026-11-18', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},
  {date:'2026-12-16', time:null, country:'ID', event:'Pengumuman hasil RDG Bank Indonesia'},

  // ---- The Fed: keputusan suku bunga FOMC (14:00 ET hari ke-2 = dini hari WIB)
  {date:'2026-01-29', time:'02:00', country:'US', event:'Keputusan suku bunga FOMC (The Fed)'},
  {date:'2026-03-19', time:'01:00', country:'US', event:'Keputusan suku bunga FOMC (The Fed)'},
  {date:'2026-04-30', time:'01:00', country:'US', event:'Keputusan suku bunga FOMC (The Fed)'},
  {date:'2026-06-18', time:'01:00', country:'US', event:'Keputusan suku bunga FOMC (The Fed)'},
  {date:'2026-07-30', time:'01:00', country:'US', event:'Keputusan suku bunga FOMC (The Fed)'},
  {date:'2026-09-17', time:'01:00', country:'US', event:'Keputusan suku bunga FOMC (The Fed)'},
  {date:'2026-10-29', time:'01:00', country:'US', event:'Keputusan suku bunga FOMC (The Fed)'},
  {date:'2026-12-10', time:'02:00', country:'US', event:'Keputusan suku bunga FOMC (The Fed)'},

  // ---- AS: cadangan jadwal BLS (versi otomatis ada di public/calendar.json)
  {date:'2026-10-02', time:'19:30', country:'US', event:'Data tenaga kerja AS (Non-Farm Payrolls)'},
  {date:'2026-10-14', time:'19:30', country:'US', event:'Inflasi AS (CPI)'},
  {date:'2026-11-06', time:'20:30', country:'US', event:'Data tenaga kerja AS (Non-Farm Payrolls)'},
  {date:'2026-11-10', time:'20:30', country:'US', event:'Inflasi AS (CPI)'},
  {date:'2026-12-04', time:'20:30', country:'US', event:'Data tenaga kerja AS (Non-Farm Payrolls)'},
  {date:'2026-12-10', time:'20:30', country:'US', event:'Inflasi AS (CPI)'},

  // ---- BPS: isi dari bps.go.id/id/arc. Contoh format (hapus // di depan setelah tanggal dicek):
  // {date:'2026-11-02', time:'11:00', country:'ID', event:'Rilis inflasi Oktober (BPS)'},
  // {date:'2026-11-16', time:'11:00', country:'ID', event:'Rilis neraca perdagangan Oktober (BPS)'},
  // {date:'2026-11-05', time:'11:00', country:'ID', event:'Rilis PDB kuartal III (BPS)'},
];
