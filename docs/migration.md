# Migration plan and verification ledger

## Source of truth

Original code and artifact source: private GitHub `may-ysaa24/diakritisasi-arab` and authorized Google Drive folder `BiLSTM-CRF`.

## Status

- [x] Initialize dedicated professional repository.
- [x] Create safe migration branch.
- [x] Copy original Streamlit UI and historical mapping/configuration/evaluation artifacts.
- [x] Preserve original backend implementation, changing only its project-root derivation after placing it inside `src/`.
- [x] Add public package entry points and compatibility import for existing UI.
- [ ] Migrate and verify fine-tuned model checkpoint (`best_finetuned_model.pt`).
- [ ] Migrate other checkpoints and research notebooks.
- [ ] Test actual inference on the new checkpoint and compare outputs with the original repository.
- [ ] Extract implementation from `_reference_engine.py` into independent modules after regression tests.
- [ ] Verify Streamlit manual, TXT, CSV, and download workflows interactively.
- [ ] Merge reviewed changes to `main`.

## Verification constraints

1. Do not change existing trained weights, mappings, experiment figures, or scientific conclusions.
2. Preserve architecture and existing prediction/output contracts.
3. A passing package smoke test does not prove inference equivalence.
4. No assertion of complete migration until missing artifacts are present and functional tests pass.
