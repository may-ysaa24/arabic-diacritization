# Streamlit UI overhaul: Academic Research Studio

Status: **Draft Pull Request**. Perubahan ini khusus presentasi dan pengalaman pengguna.

## Apa yang berubah

- Desain ulang menyeluruh gaya aplikasi aktif `streamlit_app/app.py`: identitas visual navy, aksen teal dan emas, panel terang, hierarki teks lebih jelas, layout responsif.
- Sidebar navigasi empat halaman dengan status model; halaman Beranda ditata ulang sebagai hero editorial dengan kartu masukan bahasa Arab, panduan langkah, dan ringkasan kapabilitas.
- Workspace tetap memuat input manual berarah kanan-ke-kiri, hasil prediksi, unduhan TXT, serta upload TXT/CSV dan pemilihan kolom.
- Pesan input kosong diperjelas; informasi panjang input dan definisi metrik di halaman Tentang Model diperbaiki agar tidak disalahpahami.
- Konfigurasi tema Streamlit diselaraskan.
- Tambahan tes UI dengan AppTest dan aktivasi browser acceptance Playwright/Chromium untuk PR yang mengubah Streamlit.

## Kompatibilitas

Tidak mengubah modul `src/arabic_diacritization/`, pemetaan, notebook, checkpoint atau hasil evaluasi. Backend tetap dipanggil melalui `streamlit_app/inference_engine.py`.

Alur pengguna yang harus tetap berhasil:
1. Beranda -> Mulai Diakritisasi -> input manual -> prediksi -> unduh TXT.
2. Upload TXT -> proses -> unduh TXT, termasuk mempertahankan baris non-Arab.
3. Upload CSV -> pratinjau -> pilih kolom -> proses -> unduh CSV.
4. Navigasi Beranda, Diakritisasi, Contoh Teks, Tentang Model.

## Bukti pengujian

Lihat status `Python checks`, `Windows notebook byte integrity`, dan `Real browser acceptance` pada PR. Jangan menganggap screenshot/tes browser lulus sebelum run CI berstatus **success**.

## Cara menjalankan

```powershell
py -3.12 -m pip install -e . -r requirements-dev.txt
py -3.12 -m streamlit run streamlit_app/app.py
```

Untuk meninjau desain sebelum merge, checkout cabang `ui/academic-studio-redesign-20261017` terlebih dahulu. Kode historis dan hasil penelitian tetap utuh.
