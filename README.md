# Arabic Diacritization with BiLSTM–CRF

Proyek skripsi **Diakritisasi Otomatis Teks Arab Gundul pada Kitab Fathul Qorib Menggunakan Model Bidirectional Long Short-Term Memory (BiLSTM) dan Conditional Random Field (CRF)**.

## Status implementasi

Kode penelitian telah direstrukturisasi secara modular tanpa melatih ulang model. Ketiga checkpoint dan sepuluh notebook penelitian disalin dengan hash Git identik dengan repositori sumber. Implementasi refaktor diverifikasi terhadap backend referensi pada sekumpulan input Arab, teks panjang, kasus tepi, dan TXT/CSV.

**Hasil pengujian otomatis pada migrasi:**
- **29 tes Python lulus**, termasuk kesetaraan hasil referensi/modular, integritas artefak, navigasi dan prediksi Streamlit melalui AppTest. [Lihat run](https://github.com/may-ysaa24/arabic-diacritization/actions/runs/38960160756).
- **4 perjalanan pengguna lulus dengan Chromium sungguhan**: prediksi manual, unggah/unduh TXT, unggah/unduh CSV, dan navigasi halaman. [Lihat run dan tangkapan layar](https://github.com/may-ysaa24/arabic-diacritization/actions/runs/38960889522).

**Batas bukti:** pengujian berlangsung di Linux GitHub Actions dengan Chromium *headless*, bukan pemeriksaan visual manual di Windows. Tidak ada training maupun evaluasi ulang dataset penelitian; angka metrik historis tidak berubah.

Repositori sumber [`may-ysaa24/diakritisasi-arab`](https://github.com/may-ysaa24/diakritisasi-arab) tetap disimpan privat dan tidak diubah. Dataset mentah dan dokumen OCR tetap di Google Drive sampai izin redistribusinya dipastikan.

## Persyaratan dan instalasi

Target lingkungan aplikasi adalah **Python 3.12** dengan Streamlit **1.63.0**. Dependensi aplikasi tercatat di `requirements.txt`; `requirements-dev.txt` menambahkan pytest. Tidak perlu training ulang untuk menjalankan UI.

Buka terminal VS Code pada **root repository** (`arabic-diacritization`), lalu:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e . -r requirements.txt
```

Jika aktivasi PowerShell tidak tersedia, gunakan `.venv\Scripts\python.exe` secara langsung; aktivasi bukan syarat tersembunyi. Di Linux/macOS, gunakan `python3.12 -m venv .venv`, `source .venv/bin/activate`, lalu perintah instalasi yang sama.

## Startup resmi: dari root repository

Jalankan dari direktori yang memuat README ini, **bukan dengan berpindah ke subfolder aplikasi**:

```powershell
.venv\Scripts\python.exe -m streamlit run streamlit_app/app.py
```

Bila virtual environment aktif, perintah yang sama dapat ditulis `python -m streamlit run streamlit_app/app.py`. Buka URL yang ditampilkan terminal, biasanya `http://localhost:8501`. Hentikan aplikasi dengan **Ctrl+C** pada terminal server; gunakan `deactivate` untuk keluar dari virtual environment.

Konfigurasi resmi adalah **`.streamlit/config.toml` pada root repository**. Streamlit mencari konfigurasi berdasarkan direktori kerja saat startup, bukan lokasi `app.py`. Konfigurasi `streamlit_app/.streamlit/config.toml` tetap disimpan sebagai salinan kompatibilitas dengan opsi yang sama; kesetaraannya diperiksa oleh tes. Tidak diperlukan konfigurasi global komputer pengguna. Restart server setelah mengubah konfigurasi keamanan.

Aplikasi juga menegakkan `client.disableDataExport = true` sebelum menampilkan UI, dengan satu rerun inisialisasi per sesi agar frontend menerima kebijakan tersebut. Pengaman ini tetap berlaku saat aplikasi utama dijalankan dari direktori lain atau opsi ekspor bawaan diubah melalui CLI/environment. Gunakan startup resmi agar tema dan seluruh konfigurasi juga termuat. `app_v6.py` dan `app_studio_v7.py` adalah prototipe historis, bukan entrypoint aplikasi yang didukung.

Unduhan CSV pada kedua prototipe tersebut masih memakai byte backend tanpa serializer UI aman. Jangan gunakan prototipe untuk berkas CSV pengguna; arahkan shortcut atau konfigurasi peluncuran ke `streamlit_app/app.py`. Prototipe dipertahankan tanpa perubahan untuk konteks historis.

## Penggunaan dan keamanan berkas

- **Input Teks:** masukkan teks Arab, lalu pilih Proses Diakritisasi. Hasil, waktu pemrosesan, perbandingan, Salin, dan Unduh TXT tersedia setelah prediksi berhasil. Perubahan input membuat hasil sebelumnya tidak berlaku; mengetik tidak menjalankan inferensi otomatis.
- **Koreksi Hasil:** editor menyimpan draf sampai Terapkan Koreksi dipilih. Setelah diterapkan, Salin dan Unduh TXT menggunakan **Koreksi Pengguna**. **Prediksi Model** asli tetap terpisah dan dapat diakses atau dipulihkan melalui kontrol yang tersedia. Menyunting koreksi tidak menjalankan model kembali.
- **Unggah TXT/CSV:** maksimal **5 MiB (5 × 1024 × 1024 byte; UI menulis 5 MB)**. TXT diperiksa setelah decoding; karakter kontrol terlarang ditolak tanpa penghapusan diam-diam. Gunakan UTF-8 atau UTF-16 dengan BOM. CSV diperiksa dan ditampilkan dalam pratinjau sebelum pengguna memilih kolom teks Arab dan memprosesnya.
- Berkas aktif dan cache parsing disimpan privat dalam sesi. Hapus Berkas membersihkan hasil dan cache terkait. Baris kosong, non-Arab, dan campuran tidak diprediksi; teksnya dapat dinormalisasi sesuai aturan backend. Label ini tidak berarti setiap karakter dipertahankan secara identik.
- **Unduh CSV** resmi memakai UTF-8 BOM dan quoted fields; nilai/header berisiko formula diberi awalan tab. Bilangan negatif ASCII murni tetap dipertahankan. Pratinjau dan keluaran backend tidak dimutasi. Ekspor dan copy bawaan tabel dinonaktifkan melalui opsi Streamlit, bukan CSS.

Mitigasi CSV berlaku pada unduhan resmi aplikasi, bukan jaminan kompatibilitas seluruh spreadsheet atau hasil setelah disimpan ulang oleh aplikasi lain. Data yang ditampilkan tetap dapat dilihat melalui browser; menonaktifkan ekspor bawaan bukan pembatasan akses data. Jangan memasukkan berkas pengguna, `.env`, atau `secrets.toml` ke Git.

## Pengujian

Dari root repository:

```powershell
.venv\Scripts\python.exe -m pip install -e . -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```

Untuk acceptance browser, pasang dependensi opsional dan Chromium:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-browser.txt
.venv\Scripts\python.exe -m playwright install chromium
```

Biarkan server startup resmi berjalan pada terminal pertama. Pada terminal kedua di root repository:

```powershell
.venv\Scripts\python.exe scripts/browser_acceptance.py
```

Jika Chrome sudah terpasang, gunakan `$env:PLAYWRIGHT_CHANNEL='chrome'` sebagai alternatif instalasi Chromium. `msedge` juga dapat dipilih jika tersedia. Default runner dan CI tetap Chromium bawaan Playwright. Gunakan `STREAMLIT_URL` untuk port lain dan `BROWSER_SCREENSHOTS` untuk direktori artefak lain. Output default `results/browser-acceptance/` diabaikan Git. Dependensi browser tidak diperlukan untuk menjalankan aplikasi biasa.

Runner memeriksa hasil model, koreksi dan invalidasi, TXT/CSV, nilai ekspor yang telah diamankan, absennya ekspor/copy bawaan, serta navigasi desktop 1440 px dan viewport ponsel 390 px. Jalankan ulang terhadap server dengan `--client.disableDataExport=false` dan dari direktori tanpa konfigurasi untuk memeriksa pertahanan tambahan. Hasil hanya boleh dinyatakan lulus setelah runner benar-benar selesai tanpa kegagalan; pengujian viewport bukan pengujian ponsel fisik.

Workflow `Real browser acceptance` memakai matriks startup root, root dengan override ekspor `false`, serta direktori eksternal tanpa konfigurasi. Setiap kasus menjalankan runner yang sama dengan Chromium. Menambahkan workflow bukan bukti bahwa run GitHub Actions terbaru telah lulus.

## Struktur penting

- `src/arabic_diacritization/config.py`: lokasi konfigurasi, mapping dan artefak model.
- `src/arabic_diacritization/model.py`: arsitektur BiLSTM–CRF dan komponen PyTorch.
- `src/arabic_diacritization/preprocessing.py`: normalisasi, pembersihan dan validasi teks Arab.
- `src/arabic_diacritization/inference.py`: pemuatan checkpoint, decoding dan rekonstruksi harakat.
- `src/arabic_diacritization/file_processing.py`: pengolahan TXT/CSV, pratinjau dan unduhan.
- `src/arabic_diacritization/evaluation.py`: pembacaan metrik historis.
- `src/arabic_diacritization/_reference_engine.py`: salinan backend lama untuk pengujian kesetaraan **saja**.
- `streamlit_app/`: UI utama (`app.py`), dua prototipe UI dan *compatibility shim*.
- `models/`, `mappings/`, `evaluation/`: checkpoint, peta karakter/label, dan data evaluasi tersimpan.
- `notebooks/`: sepuluh notebook penelitian asli, tidak dijalankan ulang saat migrasi.
- `tests/`: pengujian Python; `scripts/browser_acceptance.py`: pengujian Chromium.
- `docs/`: catatan migrasi, keterulangan penelitian, dan prosedur penerimaan UI.

## Ketentuan ilmiah

Metrik pada `evaluation/comparison/` berasal dari eksperimen terdahulu. CI dan uji browser **tidak menghasilkan ulang accuracy, DER, maupun WER**. Prediksi berharakat merupakan keluaran model yang perlu ditinjau kembali oleh pengguna; batas generalisasi pada teks selain Kitab *Fathul Qorib* belum diukur di repositori ini.
