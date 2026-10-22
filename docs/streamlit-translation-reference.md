# Terjemahan Mandiri V3

Aplikasi yang didukung tetap `streamlit_app/app.py`. Panel **Lihat Terjemahan Mandiri** menggunakan prediksi Arab yang sudah tersimpan untuk CSV demonstrasi dan menampilkan terjemahan Indonesia buatan penulis, satu kali per paragraf. Membuka panel tidak menjalankan inferensi. Terjemahan tidak ditambahkan ke unduhan hasil model TXT/CSV/ZIP.

Identitas 17 CSV (16 kitab dan pendahuluan) dipertahankan pada `references/fathul_qorib/dataset_version.json`, tanpa URL atau katalog internet. Dataset dan referensi Arab tetap berada di folder demo semula, tanpa perubahan. Versi V3 mengikat hash CSV asli, fingerprint baris, hash referensi berharakat, peta paragraf dan sumber Arab. Nama berkas, judul, atau kemiripan kalimat tidak menjadi kunci pasangan.

Panel membaca satu berkas lokal: `references/fathul_qorib/original/translations.jsonl`, yang kini disiapkan untuk penyimpanan Git secara eksplisit sebagai draf belum diverifikasi. Berkas ini kini berisi **317 draf paragraf untuk seluruh 328 segmen Thaharah** (FQDEMO_01_00001–00328), disusun langsung dari teks Arab lokal oleh asisten AI. Sebanyak 242 entri lama untuk 252 segmen dipertahankan identik; 75 entri baru menyelesaikan segmen 00253–00328. Pemeriksaan internal setelah 00300 berhasil sebelum pengisian dilanjutkan sampai akhir. Pasangan 00027–00028, 00043–00044, 00061–00062, 00065–00066, 00110–00111, 00122–00123, 00229–00230, 00247–00248, 00250–00252 dan 00327–00328 masing-masing memiliki satu terjemahan paragraf, tanpa duplikasi. Semuanya `draft_needs_review`; tidak ada yang verified. Tidak ada formulir, registry izin situs, atau pengambilan terjemahan internet.

Setelah memproses CSV Thaharah asli, buka **Lihat Terjemahan Mandiri** lalu centang **Pratinjau draf lokal (belum diverifikasi)**. Pilihan ini awalnya mati dan hanya berlaku pada widget berkas aktif. Saat aktif, tampil label **Draf terjemahan berbantuan AI, belum diverifikasi** pada panel dan setiap kartu draf. Arab di kolom kiri tetap hasil prediksi tersimpan; Indonesia di kolom kanan berasal dari JSONL. Mode default/final tetap hanya menampilkan referensi terverifikasi. Mengaktifkan pratinjau tidak mempromosikan status, mengubah hasil model, menambah inferensi, atau memasukkan terjemahan ke unduhan.

Panel menggunakan pagination tetap 10 paragraf per halaman. Untuk 317 paragraf Thaharah tersedia 32 halaman; halaman terakhir berisi tujuh paragraf. Pemilih Halaman terjemahan dan posisi Paragraf 1-10 dari 317 mengikuti daftar yang telah lolos pemeriksaan referensi dan prediksi. Slicing dilakukan sebelum kartu Streamlit dibuat, bukan menyembunyikan 317 kartu dengan CSS. Paragraf dengan beberapa segmen tetap satu kartu utuh. Pergantian halaman hanya membaca prediksi tersimpan dalam fragment. Pergantian file (termasuk melalui TXT), mode, atau cakupan pasangan mereset posisi ke halaman pertama; indeks yang tidak valid juga dikembalikan ke awal. Gate draf/final dan data JSONL tidak berubah.

Setiap baris JSONL menyimpan:

- `schema_version`: `3.0`; `unit_id`: `FQTR3_` + paragraph_id; `dataset_version`: versi pada manifest.
- `paragraph_id`, `section` (nama bagian yang ditulis penulis, boleh kosong).
- `targets`: seluruh segmen satu paragraf dalam urutan sumber, dihasilkan melalui `translation_reference.target_for(id, context)`. Setiap target mengikat ID, paragraph_id, chunk_id, halaman, nomor baris sumber, span sumber dan hash teks Arab berharakat/gundul.
- `target_digest`: `translation_reference.fingerprint(targets)`.
- `translation`: `origin=original` atau `ai_assisted_original`, `text_indonesian`, `translator` (identitas penyusun).
- `verification`: `status`, `reviewer`, `reviewed_at` (ISO dengan zona waktu), `reviewed_text_sha256`, `reviewed_target_digest`. Untuk `draft_needs_review`, seluruh field review selain status harus `null`; status ini hanya dibaca pada pratinjau eksplisit dan origin harus `ai_assisted_original`. Status `draft`/`needs_review` lama tetap tidak ditampilkan.
- `source_note` opsional: catatan batas paragraf, fragmen dan istilah untuk pemeriksa.

Penulis memulai dari draf; pemeriksa manusia menilai makna, istilah fikih dan cakupan seluruh paragraf sebelum mengisi status verified, identitas/tanggal review dan hash teks/target yang diperiksa. Mengisi teks tidak memberi status verified. Perubahan teks atau target memerlukan pemeriksaan baru. Nilai hash membuktikan integritas, bukan mutu pemeriksaan; berkas lokal dikendalikan pengelola tepercaya.

Pada mode final, hanya unit verified yang cocok dengan seluruh identitas/hash serta review manusia lengkap ditampilkan. Pratinjau menambahkan draf berlabel tanpa melonggarkan identitas dataset, target, span atau hash. Review kedaluwarsa, ID ganda, paragraf tidak lengkap, perubahan sumber, asal non-original dan unit rusak tetap ditolak. Unit valid lain tetap tersedia. Semua segmen paragraf harus memiliki prediksi berhasil yang terikat ke CSV aktif; hasil segmen ditampilkan terpisah agar batas kata tidak disambung keliru. Judul identik pada ID 00002 dan 00009 tetap dua paragraf.

Jika tidak tersedia pasangan, tampil **Terjemahan belum tersedia**. Seluruh sepuluh paragraf awal utuh menurut batas ekspor lokal dan masing-masing memiliki satu chunk, tetapi ID 00003 berhenti di tengah daftar dan 00010 merupakan pengantar kutipan yang dimulai pada 00011. Bagian di luar batas tersebut tidak dikarang atau ditambahkan. ID 00007 mempertahankan definisi bahasa/syariat dan daftar perbuatan dalam satu terjemahan. ID 00008 menerjemahkan keterangan damah dan sisa air tanpa menganggapnya otomatis air musta‘mal; perbedaan harakat pada referensi lokal dijelaskan dalam catatan. Seluruhnya perlu pemeriksaan manusia atas makna dan istilah fikih.

Catatan batch pertama tetap dipertahankan; paragraf 00011 kini tersedia sebagai unit tersendiri. Pada tambahan ini, fragmen matan/penjelasan pada 00014, 00024, 00025 dan pengantar daftar 00050 tidak dilengkapi dengan kalimat dari paragraf lain. Prioritas pemeriksaan manusia: syarat musta‘mal dan perubahan hissi/taqdiri (00027–00029), satuan qullah/ritl tanpa konversi modern (00031–00034), istilah penyamakan serta negasi tentang janin (00038–00040), lapisan/tambalan bejana (00043–00045), dan azm serta perbedaan pendapat tentang siwak (00048–00050). Catatan rinci berada di `source_note` unit terkait; bukan laporan atau berkas versi tambahan.

Rincian pengantar 00050 kini tersedia pada 00051–00053 tanpa mengulang pengantarnya atau mengubah catatan batch lama. Sambungan 00063/00065, 00088/00090 dan 00095/00098 tetap mengikuti paragraph_id berbeda serta urutan matan/penjelasan yang berselang-seling. Catatan baru membedakan azm berawal hamzah (00051) dari ‘azm berawal ‘ain, yaitu tekad (00060); siku (00067) dari pergelangan (00075); membasuh dari mengusap; dan sunah dari wajib. Prioritas ahli: niat 00060–00062, batas wajah/janggut 00063–00066, khuf dan tertib, istilah anatomi siwak/telinga, serta syarat istinja 00094–00100. Pada 00080, pembacaan lam yurid untuk draf berbeda dari harakat lokal lam yarudda dan perlu konfirmasi bahasa Arab/PDF. Pada 00098, istilah at-tatslits dipertahankan karena penerapannya setelah menambah usapan belum jelas; tidak ditebak menjadi pengganjilan. Semua catatan ini tetap memerlukan pemeriksaan manusia.

Pada tambahan 00101–00150, batas 00100/00101 memisahkan syarat istinja dari adab arah kiblat. Batas 00150/00151 memisahkan daftar matan mandi sunah dari syarah sunah mandi sebelumnya; daftar tujuh belas tidak dilengkapi dengan teks rekaan. Prioritas ahli: redaksi lokal yang tidak lancar pada 00110, angka enam pada matan 00112 versus lima pada syarah 00114, pengecualian mani/khuntsa pada 00115 dan 00128–00129, batas telapak/lingkar dubur pada 00122–00123, perbedaan tarjih basuhan hadas/najis pada 00140/00143, serta istilah anatomi pada 00145. Rincian pemeriksaan tersimpan dalam source_note draf baru, tanpa mengubah 96 draf lama.

Pada tambahan 00151-00200 terdapat 50 paragraf tersendiri, tanpa gabungan baru. Batas 00150/00151 memisahkan matan daftar mandi sunah dari syarah dalk; batas 00200/00201 memisahkan matan syarat tayamum yang belum lengkap dari definisi dalam syarah. Sambungan 00176/00178, 00183/00185, dan 00190/00193 tetap mengikuti paragraph_id berbeda. Prioritas ahli: wajib/sunah mandi pada 00164-00166, batas dan kelayakan khuf pada 00178-00183, niat khuf berlapis pada 00183/00185, perhitungan masa pada 00187-00189, serta batas permukaan usapan pada 00190/00193. Catatan rinci ada pada draf baru; seluruh 144 draf lama tetap identik.

Pada tambahan target 00201-00250, batas 00200/00201 memisahkan daftar matan dari definisi tayamum. Paragraf P056_PAR002 dimulai pada 00250 dan baru selesai pada 00252, sehingga 00251-00252 disertakan dalam satu draf lengkap, tanpa duplikasi untuk tahap berikutnya. Gabungan baru lainnya adalah 00229-00230 dan 00247-00248. Fragmen 00215/00217, 00232/00234 dan 00248/00250 tetap mengikuti paragraph_id berbeda. Prioritas ahli: campuran tanah dan perbedaan pendapat An-Nawawi pada 00210-00213; niat, tertib dan istibahah pada 00215-00219; melihat air pada 00229-00230; jabirah dan pengulangan salat pada 00234-00240; serta definisi najis pada 00247-00252. Kutipan lokal la yahrumu minha pada 00250 berbeda dari la li-hurmatiha pada 00247 dan perlu pemeriksaan Arab/PDF; tidak dikoreksi berdasarkan dugaan. Semua 194 draf lama tetap identik.

Penyelesaian 00253-00328 menambah 48 paragraf sampai 00300 lalu 27 paragraf sisanya. Pemeriksaan internal pada 00300 memastikan 290 paragraf/300 ID tanpa duplikasi sebelum melanjutkan. Batas 00252/00253 dan 00300/00301 berbeda paragraph_id; paragraf terakhir 00327-00328 diterjemahkan sekali. Fragmen 00269/00274, 00273/00277, 00293/00302 dan 00301/00305 tetap mengikuti matan-syarah yang berselang-seling. Prioritas Arab/PDF/fikih: rumusan nutrisi anak pada 00257, tujuh aliran tanpa tanah pada 00270, air basuhan pada 00272, sifat darah dan tambahan ba pada 00282-00288, serta redaksi fawqahuma pada 00318. Batas haid/nifas, usia haid dan angka kehamilan 00303/00306 adalah uraian kitab yang tetap memerlukan pemeriksaan ahli, bukan verifikasi medis modern. Rincian mushaf, masjid dan anak mumayyiz pada 00311-00328 juga diberi catatan review. Seluruh 242 draf sebelumnya tetap identik.

Pengujian yang dipertahankan:

```powershell
.venv/Scripts/python.exe -B -m pytest tests -q -p no:cacheprovider
.venv/Scripts/python.exe -B scripts/browser_translation_panel.py
```

Runner browser disiapkan untuk Edge, CSV Thaharah asli dan seluruh 317 draf paragraf/328 segmen dari berkas produksi, tanpa mengganti pembaca atau path referensi. Instrumentasi tes hanya menghitung panggilan backend. Runner menelusuri seluruh 32 halaman dan memeriksa maksimum 10 kartu pada DOM, posisi halaman, setiap prediksi dan terjemahan, serta reset posisi setelah berganti file. Bukti desktop/mobile memakai tangkapan viewport agar tidak membuat gambar sepanjang seluruh kitab. Runner menguji multi-file, hasil tersimpan, ID salah, opt-in awal mati, mode final tanpa draf, setiap prediksi Arab dan pasangan Indonesia, paragraf gabungan, desktop/mobile serta CSV/ZIP yang identik. Pengujian pagination memakai tes integritas, AppTest pada CSV asli dan runner Edge untuk seluruh kitab; kode yang berubah hanya panel/navigasi, sedangkan model, inferensi, dataset dan isi terjemahan tetap identik. Hasil eksekusi terbaru tersimpan pada artefak tes, bukan sebagai status verifikasi terjemahan. Tes juga memastikan satu paragraf tidak ditampilkan jika satu prediksinya gagal/kosong, sementara paragraf lain tetap tersedia. Artefak tes menggunakan direktori tetap `test-results/translation-panel/` yang diabaikan Git, tanpa folder audit/snapshot baru.

Riwayat penyebab: sebelum pagination, tes data/AppTest dapat menyiapkan 317 paragraf/328 segmen, tetapi Edge berhenti saat mengirim seluruh kartu sekaligus. Log diagnostik mencatat TEST_ONLY websocket send failed; queue_size=500. Implementasi Streamlit/Starlette terpasang melempar SessionClientDisconnectedError ketika antrean penuh; menambah waktu tunggu saja tidak menyelesaikannya. CSV nyata berisi 328 prediksi berhasil, dan tidak ditemukan kesalahan sumber/pemetaan. Perbaikan membatasi render menjadi 10 kartu per halaman; batas antrean server dan gate verifikasi tetap asli, tanpa menonaktifkan perlindungan atau mengubah data terjemahan. Artefak pengujian terbaru menggunakan direktori test-results yang sama.

Validasi pagination: 294 tes regresi lulus. Edge 155.0.4283.62 menelusuri seluruh 32 halaman pada CSV Thaharah asli dan memeriksa 317 paragraf/328 segmen, maksimum 10 kartu per halaman, serta tujuh kartu pada halaman terakhir. Navigasi maju/mundur, reset file/mode, paragraf multisegmen, desktop/mobile, nol inferensi tambahan saat membuka/navigasi panel, dan CSV/ZIP identik lulus. Isi translations.jsonl tetap identik; 317 draf tetap draft_needs_review dan tidak ada yang verified.

## Penyimpanan selektif dan pemulihan V3

Aturan `references/fathul_qorib/.gitignore` hanya mengizinkan berkas aturan itu sendiri, `dataset_version.json`, dan `original/translations.jsonl`. Berkas lain di direktori referensi ini tetap diabaikan, termasuk calon artefak V2, bukti izin, dan draf lain. Pengecualian hanya membuat berkas layak dipilih; tidak melakukan staging, commit, atau push dan tidak mengubah status verifikasi.

Daftar berkas yang perlu disimpan bersama:

- `streamlit_app/app.py`
- `streamlit_app/translation_panel.py`
- `streamlit_app/translation_reference.py`
- `streamlit_app/translation_prediction.py`
- `scripts/browser_multifile.py`
- `scripts/browser_translation_panel.py`
- `scripts/translation_test_fixture.py`
- `tests/test_translation_reference.py`
- `tests/test_translation_prediction.py`
- `tests/test_ui_translation_panel.py`
- `docs/streamlit-translation-reference.md`
- `references/fathul_qorib/.gitignore`
- `references/fathul_qorib/dataset_version.json`
- `references/fathul_qorib/original/translations.jsonl`

JSONL memuat 317 draf paragraf dengan cakupan tepat 328 ID Thaharah; semua `draft_needs_review`, tanpa review manusia atau referensi final terverifikasi. Identitas penyusunnya menyatakan draf berbantuan AI dari Arab lokal. Pemeriksaan struktur dan pola sensitif tidak menemukan kredensial, kontak pribadi, bukti izin, URL terjemahan internet atau metadata izin V2 pada payload. Pemeriksaan ini bukan pembuktian forensik keaslian maupun validasi makna; seluruh draf tetap memerlukan tinjauan bahasa Arab dan fikih.

Setelah daftar tersebut benar-benar di-commit dan di-push, repository dapat memulihkan teks seluruh draf beserta metadata dan kode pembacanya. Sebelum itu, belum ada salinan baru di GitHub. Pemulihan aplikasi demonstrasi penuh tetap membutuhkan data/model lokal yang sengaja tidak disertakan. Untuk Thaharah, pembaca membutuhkan `CSV/01_Thaharah.csv`, `Referensi_Berharakat/01_Thaharah.csv`, `Laporan_Audit/PETA_PARAGRAF.csv`, dan `Laporan_Audit/Sumber/dataset_drive.csv` di bawah `data/demo_fathul_qorib_per_bab/`, dengan hash persis sesuai manifest. Manifest hash tidak menggantikan isi sumber. Inferensi juga membutuhkan model dan dependensi aplikasi yang sesuai.

Sepuluh notebook yang berubah, kedua folder data lokal, model/checkpoint, hasil evaluasi, log, screenshot, dan artefak pengujian tidak termasuk daftar commit. Jangan memakai pemilihan seluruh working tree. Fixture sintetis pada skrip/tes sengaja dipisahkan dari data produksi dan bukan terjemahan kitab terverifikasi.
