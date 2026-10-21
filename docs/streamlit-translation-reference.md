# Panel Terjemahan Referensi Fathul Qorib V2

Pengembangan 22 Oktober 2026 pada `feature/translation-reference`. Fitur ini menampilkan referensi manusia secara opsional pada hasil CSV demonstrasi. Terjemahan bukan keluaran BiLSTM–CRF, bukan sasaran evaluasi, dan bukan tambahan metrik penelitian. Pilot asli tetap 10 unit `needs_review`, teks Indonesia `null`, izin `user_reported_unverified`.

## Perubahan antarmuka

Setelah CSV berstruktur demonstrasi berhasil diproses menggunakan kolom `teks_gundul`, area hasil menyediakan expander tertutup **Lihat Terjemahan Referensi**. Membukanya menjalankan fragment pembaca referensi, bukan fungsi inferensi. Saat tidak ada referensi yang memenuhi syarat, tampil **Terjemahan belum tersedia dalam aplikasi**. CSV umum, kolom lain, TXT, dan input manual mempertahankan alur sebelumnya.

CSV Thaharah asli yang dikenali melalui hash versi dataset juga menyediakan **Baca Terjemahan di Sumber Referensi**, menuju URL sumber utama yang sudah diperiksa. Tautan diberi keterangan referensi eksternal dan terbuka pada tab baru tanpa rerun aplikasi. Tautan ini tidak membuktikan terjemahan telah disimpan atau diverifikasi; gate izin/verifikasi lokal tetap berlaku. Aplikasi tidak mengambil konten situs. Tidak disediakan tautan untuk CSV kitab lain atau berkas yang hanya meniru nama/ID Thaharah.

Pengujian tambahan tautan: 9 tes UI panel lulus; suite aplikasi `tests/` menghasilkan **243 passed, 1 skipped** (symlink Windows tidak tersedia), tanpa mengulang 38 tes workflow offline yang kodenya tidak berubah. Browser Edge 155.0.4283.62 lulus pada putaran akhir, termasuk atribut URL/tab baru, multi-file dan CSV/TXT/ZIP yang tetap berfungsi serta byte unduhan identik sebelum/sesudah panel. Dua putaran awal tertahan oleh sinkronisasi callback unggahan/dropdown pada runner browser; penantian dan pemilihan ulang dibatasi pada kode tes, tanpa mengubah antrean aplikasi. Situs tujuan tidak dibuka/diunduh oleh tes. Log regresi berada di `test-results/translation-source-link/`; bukti browser akhir di `test-results/translation-panel/browser_20261022_044713/`. Tidak ada audit ulang atau formulir baru untuk perubahan tautan ini.

Panel tidak menerima unggahan berkas referensi. Teks ditampilkan dengan `st.text`, sehingga markup sumber tidak dieksekusi. Referensi tidak dimasukkan ke hasil model, CSV, TXT, ZIP, session state hasil, atau cache bersama. Tidak ada pengambil terjemahan daring, generator terjemahan, atau promosi otomatis menjadi `verified`.

## Pemisahan draf dan persetujuan tampilan

Draf V2 `.local/units.jsonl` **tidak dibaca oleh panel**. Skema, workflow pengisian, `publication_ready=false`, serta seluruh artefak pilot V1/V2 dipertahankan. Flag tersebut tetap merupakan hold kanal persiapan V2; ia tidak diubah atau dijadikan persetujuan tampilan. Kanal tampilan baru memerlukan keputusan manusia terpisah yang mengikat satu salinan unit yang sudah terverifikasi ke hash berkasnya. Keputusan ini hanya mengizinkan pembacaan oleh panel; tidak mengaktifkan redistribusi atau ekspor.

Tidak ada manifest atau salinan unit tampilan yang dibuat oleh implementasi ini. Sesudah bukti izin dan pemeriksaan manusia benar-benar selesai, pengelola dapat menyiapkan secara lokal:

```text
references/fathul_qorib/pilot_thaharah_10_v2/.local/
  permission_registry.json
  evidence/<bukti-izin>
  display/manifest.json
  display/units/<unit-yang-disetujui>.json
```

Kontrak `display/manifest.json`:

| Field | Syarat |
|---|---|
| `schema_version` | `1.0` |
| `dataset_version` | versi lokal Thaharah yang dipatok pembaca |
| `csv_sha256` | hash byte CSV demonstrasi asli yang dipatok pembaca |
| `permission_registry_digest` | fingerprint kanonik registry izin V2 terkini |
| `approvals` | 1–100 keputusan unik menurut `unit_id` |
| `approvals[].unit_id` | ID unit V2 yang sama dengan berkas unit |
| `approvals[].file` | path relatif `units/<nama>.json`, harus tetap di `display/units/` setelah resolve |
| `approvals[].sha256` | SHA-256 persis byte JSON unit yang ditinjau |
| `approvals[].decision` | `approved_for_display`, keputusan eksplisit manusia |
| `approvals[].reviewer` | identitas pemeriksa persetujuan tampilan |
| `approvals[].reviewed_at` | timestamp ISO dengan zona waktu |

Setiap berkas unit tetap mengikuti skema V2 asli, termasuk `publication_ready=false`. Unit harus memiliki teks yang telah diperiksa, penerjemah, provenance, review keselarasan lengkap, `verification.status=verified` oleh manusia, serta hash review teks/target/sumber yang masih sesuai. Alur `fill` lama tetap mereset verifikasi ke `needs_review`; mengisi formulir saja tidak cukup. Jangan mengubah status atau mengisi bukti hanya agar panel tampil.

Registry harus `documented`, lengkap identitas pemberi izin/kewenangan, tanggal/teks persetujuan, pemeriksa dokumentasi dan bukti lokal yang hash-nya cocok. **Kedua scope `storage` dan `display` harus `allowed`**. Scope redistribusi tidak diasumsikan dan panel tidak menyediakan ekspor terjemahan. Hash bukti membuktikan integritas berkas, bukan keaslian izin atau kewenangan pemberinya.

Persetujuan manifest, registry, bukti, dan unit adalah konfigurasi lokal tepercaya yang harus diperiksa manusia. Bukan mekanisme autentikasi multi-pengguna atau tanda tangan digital. Orang yang dapat mengubah semua berkas lokal tersebut berada di luar batas keamanan pembaca ini.

## Pencocokan dan perilaku saat gagal

1. Bentuk CSV dan kolom dipakai hanya untuk menentukan visibilitas panel. Nama berkas, judul, atau ID saja tidak memberi hak menampilkan referensi.
2. Hash byte unggahan harus tepat sama dengan CSV `01_Thaharah.csv` versi pilot (`e14c1c70…42e03`). Pembaca menolak CSV yang disimpan ulang, dipotong, atau berubah walaupun nama/ID masih sama. Versi tetap `fqdemo-792a1dcaed5818be82452479129e6ce2d4c3a25015634f389baac44634c794b5`.
3. Registry dan bukti izin diperiksa sebelum membaca manifest atau berkas unit. Draf yang belum disetujui tidak pernah dibuka. Setelah pembacaan, registry/bukti diperiksa lagi; tidak ada cache teks atau izin yang mempertahankan persetujuan lama.
4. Lima sumber versi dataset lokal divalidasi hash melalui workflow V2. Seluruh ID dan nilai asli `teks_gundul`, `chunk_id`, halaman dicocokkan dengan katalog sumber. `paragraph_id` diambil dari referensi lokal tepercaya, karena CSV demonstrasi tidak memuat kolom itu. Teks prediksi tidak digunakan untuk pencocokan.
5. Unit harus mencakup seluruh segmen satu paragraf dalam urutan sumber, beserta batas paragraf dan hash teks Arab persis tanpa trim, normalisasi, atau perubahan tatweel. Satu terjemahan ditampilkan sekali untuk seluruh `targets[]`; judul berulang tetap dibedakan menurut ID/paragraf.
6. Berkas unit rusak/tidak memenuhi syarat dilewati; unit lain yang valid tetap tersedia. Manifest ganda, versi salah, sumber lokal berubah, izin tidak lengkap/dicabut, atau dependensi/konteks lokal tidak tersedia menghasilkan pesan tidak tersedia tanpa membocorkan teks atau detail bukti. Ringkasan panel menyatakan bahwa segmen lainnya belum tersedia.

Pembaca membatasi setiap JSON 256 KiB, katalog 100 unit, dan bukti izin 10 MiB. Membuka panel melakukan validasi IO lokal lagi untuk mencegah penggunaan cache izin lama. Batas ini bukan pembatas keras seluruh RSS proses. Pencabutan izin berlaku pada interaksi berikutnya; konten yang sudah dikirim ke browser tidak dapat ditarik kembali secara retroaktif.

## Keamanan Git dan cakupan perubahan

Sebelum perpindahan, kedua branch berada pada commit `a9d004354c6e2abb5a5142b122f50b8145777e42`, index kosong, dan tree tujuan identik. Snapshot hash 564 berkas lama dicatat sebelum `git switch feature/translation-reference`. Pemeriksaan sesudah switch menunjukkan tidak ada perubahan byte. Snapshot mencakup 10 notebook yang sebelumnya termodifikasi, kedua folder data, berkas tracked lain, serta seluruh referensi pilot. Pengecualian eksplisit: subtree dependensi biner `data/ocr_ulang_fathul_qorib/tools/` yang sebelumnya tidak terbaca; subtree itu tidak digunakan atau diubah.

Perubahan produksi hanya enam baris wiring `streamlit_app/app.py` dan dua modul UI/pembaca baru. Berkas baru lainnya adalah dua modul tes, runner browser, serta dokumen ini. Tidak ada perubahan workflow/skema V2, dataset, ZIP demonstrasi, notebook, model, checkpoint, algoritma inferensi, metrik, atau `upload_queue.py`. Tidak ada commit, push, add/staging, reset, restore, atau clean.

Layak disimpan di Git: kode UI, tes, runner browser, dokumen ini, dan kode/skema/tes/dokumentasi V2 yang sebelumnya di-allowlist. Tetap lokal: seluruh `.local/`, bukti izin, manifest tampilan, unit terjemahan, V1, snapshot hash, log tes, unduhan uji, serta tangkapan browser. Pola ignore yang sudah ada melindungi `.local/` dan `test-results/`; implementasi tidak mengubah ignore atau mengunggah artefak.

## Pengujian

Perintah regresi dari root menggunakan `.venv`, bytecode/cache dinonaktifkan:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.venv/Scripts/python.exe -B -m pytest tests references/fathul_qorib/pilot_thaharah_10_v2/tests/test_workflow.py -q -p no:cacheprovider --basetemp=test-results/translation-panel/regression-tmp --junitxml=test-results/translation-panel/regression.xml
.venv/Scripts/python.exe -B scripts/browser_translation_panel.py
```

Tes positif memakai sentinel `TEST_DATA_NOT_A_TRANSLATION`, konteks metadata ASCII sintetis dan gate izin yang dimock secara eksplisit. Fixture ini tidak menciptakan terjemahan atau izin nyata. AppTest menghitung pemanggilan backend nyata untuk memastikan buka/tutup panel tidak mengulang inferensi. Tes browser memakai unggahan native, klik expander/fragment, unduhan, dan CSV Thaharah lokal; panel nyata diharapkan tidak tersedia.

Hasil eksekusi:

| Pemeriksaan | Hasil yang benar-benar dijalankan |
|---|---|
| Regresi lengkap `tests/` + workflow V2 | **275 passed, 1 skipped**, 94,22 detik; mencakup 192 tes aplikasi sebelumnya, 38 tes workflow V2, 45 tes baru lulus dan 1 tes baru dilewati |
| Tes unit pembaca | 42 passed, 1 skipped; versi/ID/hash/paragraf, review kedaluwarsa, provenance, izin/manifest, pembacaan draf terblokir, traversal, batas ukuran, korupsi, kegagalan parsial, dan pencabutan izin |
| Tes UI tambahan | 3 passed; lazy panel, jumlah inferensi tidak bertambah saat dibuka/ditutup, satu terjemahan per paragraf, teks ditampilkan literal, hasil/ZIP tidak berubah, multi-file, Proses Semua, TXT, input manual, dan penghapusan |
| Skip | Satu tes pembuatan symlink: hak Windows tidak tersedia. Tes traversal path tetap lulus; skenario symlink OS belum diuji penuh |
| Browser Edge headless | **PASS**, versi 155.0.4283.62; unggah native campuran, pemilihan kolom, penambahan/retensi hasil, kegagalan validasi parsial, navigasi, hapus satu/semua, TXT/CSV/ZIP dan sanitasi ekspor |
| Panel browser pada CSV Thaharah asli | Seluruh 328 baris diproses; panel awal tertutup, buka/tutup berulang, pesan tidak tersedia terbaca, hasil CSV dan ZIP identik byte sebelum/sesudah panel, TXT tanpa panel, hasil tetap saat pindah berkas |
| Browser mobile 390 px | Panel/pesan tersedia tanpa overflow halaman; tangkapan desktop/mobile diperiksa sebagai bukti lokal |
| Integritas berkas lama | 564 berkas diperiksa; hanya `streamlit_app/app.py` berubah; 563 lainnya identik; HEAD tetap, index kosong, branch `feature/translation-reference` |

Browser dijalankan dua kali: putaran kedua memperkuat pemeriksaan pesan berada dalam viewport dan menuntaskan animasi sebelum tangkapan layar. Kedua putaran lulus; server sementara dihentikan. Artefak lokal terbaru ada di `test-results/translation-panel/browser_20261022_041627/` (`results.json`, `panel_unavailable.png`, `panel_mobile.png`, unduhan pembanding, log server). Regresi tersimpan di `test-results/translation-panel/regression.xml`/`.log`; snapshot/integritas di `before.json`, `switched.json`, `final.json`. Seluruhnya diabaikan Git.

**Keputusan:** aplikasi siap mendemonstrasikan diakritisasi dan panel referensi kosong yang aman. Belum siap mendemonstrasikan isi terjemahan kitab: seluruh pilot asli masih `needs_review`, teks `null`, dan izin `user_reported_unverified`; manifest tampilan nyata belum dibuat. Jalur positif pembaca/UI sudah diuji dengan fixture sintetis, tetapi tampilan terjemahan kitab yang benar-benar terverifikasi belum dapat diuji di browser tanpa bahan dan izin yang sah. Pemetaan runtime baru mencakup versi Thaharah yang dipatok; kitab/versi lain memerlukan perluasan katalog yang ditinjau terpisah. Integrasi ini tidak menggantikan pemeriksaan pasangan/izin oleh manusia dan konsultasi pembimbing mengenai fitur tambahan di luar batasan skripsi.
