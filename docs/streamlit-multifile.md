# Pemrosesan banyak berkas dalam sesi Streamlit

Perubahan pada 22 Oktober 2026, branch kerja `finalize/unimal-ui-security`. Entry point tetap `streamlit_app/app.py`. Ini merupakan pengembangan UI dan pengelolaan sesi; backend penelitian dan aturan inferensi tidak diubah.

## Cara menggunakan

1. Buka **Diakritisasi → Unggah TXT / CSV**. Pilih beberapa TXT/CSV sekaligus atau tambahkan batch berikutnya.
2. Batch dipindahkan ke daftar berkas sesi; pemilih unggahan dikosongkan kembali untuk melepaskan buffer. Berkas yang sudah masuk dan hasilnya tetap tersimpan. Mengosongkan pemilih tidak menghapus daftar sesi.
3. Daftar menampilkan nama, format, ukuran, validitas, status, dan ringkasan. Pilih berkas aktif untuk melihat pratinjau, memilih kolom CSV, memproses ulang, atau mengunduh hasilnya.
4. **Proses Semua** memproses berurutan berkas valid yang belum berhasil. Hasil yang sudah berhasil dilewati. Gunakan **Proses Ulang Berkas** pada berkas aktif untuk mengulangi inferensi secara eksplisit. Kegagalan satu berkas tidak menghentikan berkas berikutnya.
5. Pada CSV, pilihan awal memprioritaskan nama persis `teks_gundul`; jika tidak ada, urutan kandidat lama tetap berlaku. Pilihan manual tersimpan per berkas. Mengubah kolom membatalkan hanya hasil berkas tersebut dan ZIP lama.
6. Hasil per berkas menyediakan pratinjau dan unduhan dalam format asalnya. **Siapkan ZIP → Unduh Semua (ZIP)** mengemas seluruh hasil berhasil beserta `ringkasan_status.csv` yang juga mencatat berkas tidak valid, gagal, dan belum diproses. ZIP disiapkan hanya atas tindakan pengguna.
7. **Hapus Berkas** menghapus berkas aktif beserta parse dan hasilnya. **Hapus Semua** mengosongkan koleksi dan ZIP, tanpa menghapus input/hasil manual.

Unggahan dengan nama dan isi persis sama tidak digandakan. Nama sama dengan isi berbeda menjadi dua entri terpisah. Identitas internal menggunakan UUID, sehingga callback dari entri yang sudah dihapus tidak dapat memulihkan state lama. Hasil tetap tersedia saat berpindah halaman dalam sesi yang sama; ini bukan penyimpanan permanen dan tidak bertahan setelah sesi berakhir atau server dimulai ulang.

## Batas dan keamanan

| Batas per sesi/berkas | Nilai |
|---|---|
| Jumlah berkas tersimpan | 20 |
| Ukuran satu berkas | 5 MiB |
| Total byte masukan tersimpan | 20 MiB |
| TXT | 250.000 karakter, 10.000 baris |
| CSV | 1.000.000 karakter, 10.000 baris data, 100 kolom, 100.000 sel |
| Estimasi payload data sesi tersimpan | 128 MiB |
| Ekspor gabungan sebelum kompresi | 32 MiB; penyimpanan hasil menyisakan 1 MiB untuk ringkasan |

Batas UI diperiksa sebelum inferensi. Preflight CSV membatasi bentuk tabel sebelum pembacaan pandas, kemudian bentuk hasil pembacaan diperiksa kembali. Teks yang melampaui batas ditolak dengan pesan; tidak ada pemotongan atau penghapusan karakter untuk membuatnya lolos. TXT tetap menggunakan validasi kontrol dan decoding backend yang sudah ada. Batas tambahan dapat menolak berkas besar yang dahulu masih di bawah 5 MiB; pengguna perlu membaginya secara wajar.

Anggaran memori merupakan estimasi payload per sesi, bukan batas keras RSS proses. Model bersama, objek sementara pandas/serialisasi, salinan unduhan yang dikelola Streamlit, serta buffer transport unggahan tidak seluruhnya tercakup. Banyak sesi bersamaan tetap memerlukan kapasitas server dan pembatasan operasional. Proses berurutan menghindari banyak inferensi serentak dalam satu batch; durasi batch bergantung pada isi dan perangkat. Belum ada antrean latar belakang, pembatalan, atau pemulihan batch setelah server terhenti.

Nama unduhan dibuat sebagai basename yang aman; karakter kontrol, path, dan nama perangkat Windows ditangani. Anggota ZIP diberi nomor urut agar tidak bentrok, termasuk nama asli sama. Ekspor CSV per berkas, CSV di ZIP, dan ringkasan ZIP menggunakan `spreadsheet_safe_csv`; pratinjau dan keluaran backend tidak dimutasi. Ekspor/copy bawaan tabel tetap dinonaktifkan. Mitigasi spreadsheet memiliki batas kompatibilitas yang sama dengan aplikasi sebelumnya.

Tidak ditambahkan Accuracy, DER, WER, atau tingkat keyakinan per berkas. Penanganan tatweel tidak diubah.

## Berkas implementasi dan bukti

- `streamlit_app/app.py`: integrasi koleksi dengan panel aktif, callback, proses berurutan, dan kontrol ZIP.
- `streamlit_app/upload_queue.py`: state koleksi, batas sumber daya, penamaan aman, dan pembentukan ZIP.
- `tests/test_ui_multifile.py`: pengujian koleksi dan integrasi AppTest dengan backend asli; kegagalan inferensi sengaja disimulasikan pada tes isolasi kegagalan.
- `scripts/browser_multifile.py`: unggahan campuran, penambahan berikutnya, pilihan kolom, unduhan native per berkas/ZIP, navigasi, penghapusan, dan viewport mobile melalui browser.
- Dokumen ini menjelaskan perilaku dan keterbatasan; data dan laporan demonstrasi lama tidak diubah.

Bukti lokal disimpan di `test-results/multifile/` (diabaikan Git), mencakup snapshot hash sebelum perubahan, JUnit/log regresi, hasil unduhan, dan tangkapan layar. Snapshot tidak mencakup distribusi biner OCR dalam `data/ocr_ulang_fathul_qorib/tools/`, yang sebagian tidak dapat dibaca oleh sandbox; direktori tersebut tidak diedit atau dipakai untuk pekerjaan ini.

Perintah regresi:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.\.venv\Scripts\python.exe -B -m pytest tests -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B scripts/browser_multifile.py
```

Runner browser membuka server lokal sementara pada port kosong, memakai Edge headless secara default (`PLAYWRIGHT_CHANNEL` dapat menggantinya), dan menghentikan server miliknya setelah selesai.

## Hasil verifikasi yang benar-benar dijalankan

- Baseline sebelum perubahan: **170 tes lulus**, tidak ada tes gagal atau dilewati.
- Suite lengkap versi akhir: **192 tes lulus**, 0 gagal, 0 error, 0 dilewati; durasi 95,96 detik. Ini mencakup seluruh 170 tes lama tanpa mengubah berkas tes lama, ditambah 22 tes baru. Bukti: `test-results/multifile/final.xml` dan `final.log`.
- Seluruh **17 CSV demonstrasi** dibuka dalam koleksi, lolos validasi, dan memiliki default `teks_gundul`. Pemeriksaan ini tidak mengulang OCR atau pembuatan dataset, serta tidak menjalankan ulang inferensi seluruh kitab.
- AppTest dengan backend asli memproses batch campuran, mempertahankan hasil pada penambahan/navigasi, melewati hasil berhasil pada Proses Semua berikutnya, dan mengulang satu berkas secara eksplisit. Tes tambahan memeriksa kegagalan inferensi yang disimulasikan, validasi gagal, callback lama, pemilihan kolom, isolasi sesi, sanitasi CSV, nama ZIP, bentrok nama, penghapusan, batas ukuran/jumlah/bentuk tabel, serta penolakan saat anggaran memori/ekspor terlampaui.
- Browser nyata: **PASS**, Edge headless versi `155.0.4283.62`. Batch awal TXT + CSV + TXT tidak valid, disusul TXT tambahan, menghasilkan tiga hasil berhasil dan satu entri tidak valid dalam ringkasan ZIP. Hasil CSV sebelum/sesudah penambahan identik; isi ZIP cocok dengan unduhan per berkas. Pilihan kolom manual, navigasi, penghapusan satu/semua, unggah ulang tanpa hasil lama, serta absennya ekspor CSV bawaan juga diperiksa.
- Pemeriksaan viewport 390 px tidak menemukan overflow halaman. Ini pengujian viewport, bukan perangkat ponsel fisik. Screenshot desktop/mobile dan unduhan ada di `test-results/multifile/browser/`; status browser terdapat pada `results.json` dan log akhir `../browser_console_final.log`. Server sementara telah dihentikan.
- Percobaan awal runner browser gagal pada locator/kesiapan popup kontrol native dan nama tombol yang memuat ikon. Locator runner diperbaiki; eksekusi akhir selesai dengan exit code 0. Tidak ada perubahan logika aplikasi untuk melewati pemeriksaan browser tersebut.
- Snapshot akhir membandingkan **495 berkas lama** dengan kondisi sebelum pekerjaan. Hanya `streamlit_app/app.py` berubah; tidak ada perubahan tak terduga pada berkas snapshot. Status modified notebook yang sudah ada sebelum pekerjaan dipertahankan, tanpa mengubah isinya. Bukti: `test-results/multifile/scope_result.json`.

**Keputusan:** fitur multi-file siap dipakai untuk demonstrasi lokal dalam batas yang didokumentasikan. Tidak ada perubahan pada dataset asli, kedua folder data yang dilindungi, model/checkpoint, notebook, pemrosesan backend, pelatihan, mapping, atau evaluasi penelitian. Tidak dilakukan commit, push, reset, restore, clean, atau merge. Kapasitas banyak sesi serentak dan pemulihan setelah server terhenti belum diuji; hasil sesi tidak menjadi penyimpanan permanen.
