# Arabic Diacritization with BiLSTM–CRF

Proyek skripsi **Diakritisasi Otomatis Teks Arab Gundul pada Kitab Fathul Qorib Menggunakan Model Bidirectional Long Short-Term Memory (BiLSTM) dan Conditional Random Field (CRF)**.

## Status implementasi

Kode penelitian telah direstrukturisasi secara modular tanpa melatih ulang model. Ketiga checkpoint dan sepuluh notebook penelitian disalin dengan hash Git identik dengan repositori sumber. Implementasi refaktor diverifikasi terhadap backend referensi pada sekumpulan input Arab, teks panjang, kasus tepi, dan TXT/CSV.

**Hasil pengujian otomatis pada migrasi:**
- **29 tes Python lulus**, termasuk kesetaraan hasil referensi/modular, integritas artefak, navigasi dan prediksi Streamlit melalui AppTest. [Lihat run](https://github.com/may-ysaa24/arabic-diacritization/actions/runs/38960160756).
- **4 perjalanan pengguna lulus dengan Chromium sungguhan**: prediksi manual, unggah/unduh TXT, unggah/unduh CSV, dan navigasi halaman. [Lihat run dan tangkapan layar](https://github.com/may-ysaa24/arabic-diacritization/actions/runs/38960889522).

**Batas bukti:** pengujian berlangsung di Linux GitHub Actions dengan Chromium *headless*, bukan pemeriksaan visual manual di Windows. Tidak ada training maupun evaluasi ulang dataset penelitian; angka metrik historis tidak berubah.

Repositori sumber [`may-ysaa24/diakritisasi-arab`](https://github.com/may-ysaa24/diakritisasi-arab) tetap disimpan privat dan tidak diubah. Dataset mentah dan dokumen OCR tetap di Google Drive sampai izin redistribusinya dipastikan.

## Menjalankan di Windows dengan VS Code (Python 3.12)

```powershell
git clone https://github.com/may-ysaa24/arabic-diacritization.git
cd arabic-diacritization
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e . -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m streamlit run streamlit_app/app.py
```

Buka URL yang ditampilkan Streamlit (biasanya `http://localhost:8501`). Unduhan hasil prediksi TXT/CSV dapat diuji langsung dari UI.

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
