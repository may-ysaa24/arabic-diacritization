# Trained checkpoints

The three selected original checkpoints were transferred intact from the archived research repo and checked against the source Git blob hashes.

- `baseline/best_model.pt`: baseline Fathul Qorib model.
- `pretrained/best_pretrained_model.pt`: Tashkeela pretrained model.
- `finetuned/best_finetuned_model.pt`: fine-tuned model used by the Streamlit application.

The Streamlit app currently loads the fine-tuned checkpoint; the other two are retained for research comparison and audit. No retraining occurred during migration. File-level hash verification does not itself reproduce academic evaluation metrics.
