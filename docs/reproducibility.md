# Batas reproduksibilitas

Notebook bersumber dari eksperimen Google Colab/Drive. Sebagian masih berisi path Colab dan belum diuji sebagai pipeline lokal end-to-end. Dataset mentah dan PDF OCR tidak didistribusikan karena perlu pemeriksaan hak pakai. Angka metrik di README berasal dari file evaluasi penelitian sebelumnya, bukan pelatihan atau evaluasi ulang selama migrasi.

Jangan menggunakan test set untuk seleksi model atau tuning hiperparameter. Gunakan checkpoint `.pt` hanya dari sumber terpercaya. Loader inferensi menggunakan `torch.load(..., weights_only=True)`.
