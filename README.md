# Arabic Diacritization with BiLSTM–CRF

Proyek skripsi **Diakritisasi Otomatis Teks Arab Gundul pada Kitab Fathul Qorib Menggunakan Model Bidirectional Long Short-Term Memory (BiLSTM) dan Conditional Random Field (CRF)**.

## Status migrasi

**Dalam pengembangan, belum siap sebagai aplikasi inferensi lengkap.** Kode UI dan backend rujukan, mapping, konfigurasi, dan metrik historis telah disusun pada branch migrasi. Checkpoint `.pt` harus dipindahkan dan diverifikasi sebelum hasil inferensi dapat diuji. Notebook training asli dan dataset mentah belum dipindahkan.

**Sumber kode** tetap tersimpan pada repositori privat `may-ysaa24/diakritisasi-arab`. Penelitian menggunakan dua jalur model: baseline di Fathul Qorib, serta model pretrain Tashkeela lalu fine-tune Fathul Qorib.

## Jalankan di VS Code (setelah checkpoint tersedia)

```powershell
git clone https://github.com/may-ysaa24/arabic-diacritization.git
cd arabic-diacritization
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e . -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m streamlit run streamlit_app/app.py
```

## Arsitektur kode

- `src/arabic_diacritization/_reference_engine.py`: backend penelitian yang dipertahankan untuk uji kesetaraan. Perubahan hanya pada penentuan akar direktori paket.
- `src/arabic_diacritization/model.py`: antarmuka kelas BiLSTM–CRF.
- `src/arabic_diacritization/preprocessing.py`: antarmuka pembersihan dan validasi teks.
- `src/arabic_diacritization/inference.py`: antarmuka prediksi dan rekonstruksi harakat.
- `src/arabic_diacritization/file_processing.py`: antarmuka unggahan TXT/CSV.
- `src/arabic_diacritization/evaluation.py`: pembacaan metrik yang tersimpan.
- `streamlit_app/`: aplikasi, desain alternatif, dan shim kompatibilitas lama.
- `models/`, `mappings/`, `evaluation/`: konfigurasi dan keluaran penelitian dari repositori referensi.
- `tests/`: pengujian fungsi, sumber artefak, dan integrasi. Pengujian checkpoint dilewati secara eksplisit jika file belum tersedia.

Implementasi model belum dipisahkan sepenuhnya dari engine referensi; modul di atas pada tahap ini adalah *public API wrappers* demi migrasi bertahap tanpa perubahan algoritma.

## Batas hasil

Metrik dalam `evaluation/comparison/` adalah hasil tersimpan dari penelitian sebelumnya, **bukan** hasil evaluasi ulang migrasi. Jangan mengklaim keluaran identik atau model siap produksi sebelum perbandingan checkpoint dan pengujian end-to-end selesai. Dataset mentah dan OCR tetap pada Drive terkontrol sampai perizinan diperiksa.
