# Arsitektur

- `streamlit_app/app.py` adalah aplikasi utama.
- `streamlit_app/inference_engine.py` berisi preprocessing, segmentasi, BiLSTM-CRF, Viterbi decoding, dan pemrosesan TXT/CSV.
- `models/finetuned/best_finetuned_model.pt` adalah checkpoint inferensi yang tersimpan.
- `mappings/` berisi 55 karakter dan 15 label harakat.
- `evaluation/comparison/` menyediakan hasil evaluasi yang sudah tersimpan.

UI v6 dan v7 merupakan prototipe alternatif, bukan entrypoint rilis resmi. Struktur path backend relatif terhadap akar repositori dengan opsi `BILSTM_CRF_PROJECT_ROOT`.
