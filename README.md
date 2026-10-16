# Arabic Diacritization with BiLSTM–CRF

Proyek skripsi **Diakritisasi Otomatis Teks Arab Gundul pada Kitab Fathul Qorib Menggunakan Model Bidirectional Long Short-Term Memory (BiLSTM) dan Conditional Random Field (CRF)**.

## Status migrasi

**Dalam pengembangan, belum dinyatakan selesai.** Backend rujukan, UI, mapping, konfigurasi, metrik historis, dan checkpoint *fine-tuned* sudah disimpan pada branch migrasi. SHA-256 checkpoint sudah cocok dengan sumber dan pengujian inferensi dasar berhasil. Seluruh 10 notebook asli dan tiga checkpoint terpilih sudah dipindahkan dengan hash identik. Dataset mentah tetap berada di Drive. Pengujian browser Streamlit secara interaktif dan evaluasi ulang penelitian belum dilakukan.

**Sumber kode** tetap tersimpan pada repositori privat `may-ysaa24/diakritisasi-arab`. Penelitian menggunakan dua jalur model: baseline di Fathul Qorib, serta model pretrain Tashkeela lalu fine-tune Fathul Qorib.

## Jalankan di VS Code (setelah branch migrasi digabungkan)

```powershell
git clone https://github.com/may-ysaa24/arabic-diacritization.git
cd arabic-diacritization
git switch migration/reference-code-and-artifacts
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e . -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m streamlit run streamlit_app/app.py
```

## Arsitektur kode

- `src/arabic_diacritization/_reference_engine.py`: backend penelitian yang dipertahankan untuk uji kesetaraan. Perubahan hanya pada penentuan akar direktori paket.
- `src/arabic_diacritization/model.py`: kelas dan lapisan BiLSTM–CRF.
- `src/arabic_diacritization/preprocessing.py`: fungsi pembersihan dan validasi teks.
- `src/arabic_diacritization/inference.py`: pemuatan checkpoint, prediksi dan rekonstruksi harakat.
- `src/arabic_diacritization/file_processing.py`: pengolahan TXT/CSV dan unduhan.
- `src/arabic_diacritization/config.py`: path model/mapping dan batas file.
- `src/arabic_diacritization/evaluation.py`: pembacaan metrik yang tersimpan.
- `streamlit_app/`: aplikasi, desain alternatif, dan shim kompatibilitas lama.
- `models/`, `mappings/`, `evaluation/`: tiga checkpoint asli, mapping, konfigurasi, dan keluaran penelitian dari repositori referensi.
- `tests/`: pengujian fungsi, sumber artefak, dan integrasi. Pengujian checkpoint dilewati secara eksplisit jika file belum tersedia.

Implementasi model, preprocessing, inferensi, dan pemrosesan TXT/CSV kini dipisah dalam modul independen. `_reference_engine.py` tetap dipertahankan sebagai pembanding pengujian regresi dan tidak digunakan aplikasi.

## Batas hasil

Metrik dalam `evaluation/comparison/` adalah hasil tersimpan dari penelitian sebelumnya, **bukan** hasil evaluasi ulang migrasi. Jangan mengklaim keluaran identik atau model siap produksi sebelum perbandingan checkpoint dan pengujian end-to-end selesai. Dataset mentah dan OCR tetap pada Drive terkontrol sampai perizinan diperiksa.
