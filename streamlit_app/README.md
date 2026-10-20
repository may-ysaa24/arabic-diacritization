# Streamlit UI — UNIMAL

Aplikasi utama adalah `streamlit_app/app.py`, dengan identitas hijau-putih Universitas Malikussaleh dan aksen emas. `app_v6.py` serta `app_studio_v7.py` dipertahankan sebagai prototipe historis, bukan entrypoint yang didukung. `inference_engine.py` adalah facade kompatibilitas ke backend modular.

Ekspor CSV prototipe masih menggunakan byte backend tanpa serializer aman aplikasi utama. Gunakan `app.py` untuk berkas pengguna dan jangan arahkan shortcut startup ke prototipe.

Ikuti instalasi Python 3.12 pada [README utama](../README.md). **Startup resmi selalu dari root repository**:

```powershell
.venv\Scripts\python.exe -m streamlit run streamlit_app/app.py
```

Konfigurasi resmi adalah `../.streamlit/config.toml` relatif terhadap folder ini. Konfigurasi lokal `.streamlit/config.toml` memiliki opsi yang sama untuk kompatibilitas; tidak membutuhkan konfigurasi global pengguna. Pengaman aplikasi menonaktifkan ekspor/copy bawaan tabel sebelum UI ditampilkan, termasuk pada startup tanpa konfigurasi. Gunakan tombol Unduh CSV resmi yang melewati serializer aman. Hentikan server dengan Ctrl+C.

Input Teks mendukung prediksi, perbandingan, koreksi, Salin, dan Unduh TXT. Koreksi baru menjadi hasil aktif setelah Terapkan Koreksi; prediksi model tetap tersimpan terpisah. Unggah TXT/CSV mendukung validasi ukuran/isi, pemilihan kolom, pratinjau, ringkasan, dan unduhan. Batasan encoding, mitigasi formula CSV, dependensi Playwright, dan langkah acceptance dijelaskan di README utama.

Harakat hasil model perlu diperiksa kembali. Pengujian kesetaraan backend pada sampel tidak membuktikan akurasi atau generalisasi penelitian secara menyeluruh.
