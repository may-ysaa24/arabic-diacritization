# Audit reproducibility: baseline resume (read-only)

Sumber: `notebooks/02_train_baseline.ipynb`, sel 10 dan 10B.

## Temuan
- Sel 10B membaca `best_model.pt` dan memulai dari `checkpoint["epoch"] + 1`, padahal riwayat CSV mungkin sudah mencatat epoch selanjutnya. Ini berisiko membuat nomor epoch duplikat.
- Sel 10B mereset `patience_counter` menjadi 0, sehingga tidak memulihkan kondisi early stopping.
- Checkpoint terakhir historis: epoch **83**, epoch terbaik **78**, validation loss **0.19209198289504262**. Lima epoch setelah 78 tanpa peningkatan yang memenuhi `MIN_DELTA=0.0001` berarti early stopping telah tercapai (`PATIENCE=5`).
- `final_checkpoint.pt` menyimpan model, optimizer, dan history, tetapi **tidak** menyimpan RNG Python/NumPy/PyTorch atau state generator DataLoader. Exact replay belum dapat dijanjikan.

## Keamanan eksperimen

**Jangan menjalankan ulang sel training notebook pada path Drive historis.** Sel tersebut menulis checkpoint, CSV history, dan evaluasi ke path penelitian asli. Tidak diperlukan pelatihan lanjutan pada baseline yang sudah early-stopped.

Untuk eksperimen baru, gunakan direktori output terpisah, misalnya `artifacts/reproduction_trials/run_001/`. Simpan checkpoint terakhir setiap epoch dengan model/optimizer/epoch/riwayat/patience dan RNG state lengkap. Resume dari `last_epoch + 1`, bukan epoch terbaik. Uji kesetaraan interrupted vs continuous training di dataset sintetis sebelum menggunakan data penelitian.

## Audit tanpa menulis file

```powershell
py -3.12 scripts/check_resume_readiness.py --checkpoint "D:\\BiLSTM-CRF\\models\\baseline\\final_checkpoint.pt" --history "D:\\BiLSTM-CRF\\models\\baseline\\training_history.csv"
```

Sesuaikan lokasi file. Hanya gunakan checkpoint dari sumber terpercaya. Pemeriksa ini membaca checkpoint dan CSV, tidak mengubahnya dan tidak menjalankan training.
