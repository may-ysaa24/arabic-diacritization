# Streamlit UI — identitas Universitas Malikussaleh

Dokumen ini menjelaskan UI aktif dan prosedur verifikasinya. Perubahan dibatasi pada presentasi, state UI, validasi unggahan, dan keamanan ekspor; tidak menyatakan status PR atau CI terbaru.

## Apa yang berubah

- Identitas hijau-putih UNIMAL: hijau utama `#009344`, hijau tua `#006F34`, latar terang, aksen emas `#E2A313`, dan teks berkontras. Sidebar desktop sekitar 284 px; logo proporsional.
- Empat halaman: Beranda, Diakritisasi, Contoh Teks, dan Tentang Model. Kartu 01 masukan dan 02 hasil tetap vertikal. Panel perbandingan dapat berdampingan pada desktop dan bertumpuk pada ponsel.
- RTL, font Arab, line-height, spasi, dan baris baru diperhatikan. Perbandingan serta editor koreksi berada dalam expander agar hasil tidak terlalu padat.
- Hasil asli model, koreksi yang diterapkan, dan draf editor dipisahkan. Ringkasan serta aksi ekspor mengikuti hasil aktif; input berubah menginvalidasi hasil terkait.
- Auto-scroll hanya setelah keberhasilan proses, mengikuti preferensi reduced motion. Timer mengukur panggilan pemrosesan, bukan waktu training, akurasi, atau confidence.
- Konfigurasi resmi berada di `.streamlit/config.toml` pada root. Salinan subfolder tetap kompatibel dan kesamaan opsinya diuji. Pengaman aplikasi menegakkan opsi native `client.disableDataExport` dengan rerun inisialisasi sebelum UI dirender; unduhan CSV resmi tetap memakai serializer aman.

## Kompatibilitas

Tidak mengubah modul `src/arabic_diacritization/`, pemetaan, notebook, checkpoint atau hasil evaluasi. Backend tetap dipanggil melalui `streamlit_app/inference_engine.py`.

Alur pengguna yang harus tetap berhasil:
1. Beranda -> Mulai Diakritisasi -> input manual -> prediksi -> unduh TXT.
2. Upload TXT -> validasi -> proses -> unduh TXT; baris non-Arab tidak diprediksi dan dapat dinormalisasi sesuai backend.
3. Upload CSV -> pratinjau -> pilih kolom -> proses -> unduh CSV.
4. Navigasi Beranda, Diakritisasi, Contoh Teks, Tentang Model.

## Bukti pengujian

Jalankan pytest, pemeriksa byte notebook, serta `scripts/browser_acceptance.py`. Runner menggunakan Playwright pada browser sungguhan, menguji desktop 1440 px dan viewport ponsel 390 px. CSV diuji dengan parsing quoted fields dan pemeriksaan nilai formula, bukan pencarian header mentah. Ekspor/copy bawaan harus tidak tersedia, sementara pratinjau tetap memuat nilai asli.

Periksa pula startup root, salinan subfolder, direktori tanpa konfigurasi, dan override ekspor `false`. Jangan menganggap pengujian lokal sama dengan CI yang sudah sukses, audit metodologi penelitian, uji spreadsheet, atau pengujian ponsel fisik.

## Cara menjalankan

```powershell
.venv\Scripts\python.exe -m pip install -e . -r requirements-dev.txt
.venv\Scripts\python.exe -m streamlit run streamlit_app/app.py
```

Jalankan dari root repository. Instalasi/aktivasi virtual environment, browser opsional, keamanan berkas, dan penghentian aplikasi dijelaskan di [README utama](../README.md). Jangan mengubah notebook atau artefak penelitian untuk menguji UI.

Penutupan sidebar mobile memiliki listener interaksi dan penanganan navigasi setelah rerun/fokus. Keduanya memeriksa keadaan drawer sebelum menekan kontrol native. Pertahankan keduanya selama tidak ada konflik yang direproduksi; uji navigasi, pembukaan kembali, dan rerun sebelum mengubah mekanismenya.
