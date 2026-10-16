# Migration plan and verification ledger

## Source of truth

Original code and artifact source: private GitHub `may-ysaa24/diakritisasi-arab` and authorized Google Drive folder `BiLSTM-CRF`.

## Status

- [x] Initialize dedicated professional repository.
- [x] Create safe migration branch.
- [x] Copy original Streamlit UI and historical mapping/configuration/evaluation artifacts.
- [x] Preserve original backend implementation, changing only its project-root derivation after placing it inside `src/`.
- [x] Add public package entry points and compatibility import for existing UI.
- [x] Migrate and verify fine-tuned model checkpoint (`best_finetuned_model.pt`): 3,321,819 bytes, SHA-256 `47e7e35f090fbc1e0a3fc0fb06501112cfc67ae9daba0f094bb220f0baf69637`.
- [x] Migrate original baseline and pretrained checkpoints, verified by matching Git blob SHA-1.
- [x] Migrate all 10 research notebooks, preserving exact Git blob hashes and original cell content.
- [x] Test inference via GitHub Actions using the migrated checkpoint (6 tests passed).
- [ ] Compare full output with original reference deployment and verify end-to-end results.
- [ ] Extract implementation from `_reference_engine.py` into independent modules after regression tests.
- [ ] Verify Streamlit manual, TXT, CSV, and download workflows interactively; automated checks cover the input/output contracts but not browser workflows.
- [ ] Merge reviewed changes to `main`.

## Verification constraints

1. Do not change existing trained weights, mappings, experiment figures, or scientific conclusions.
2. Preserve architecture and existing prediction/output contracts.
3. A passing package smoke test does not prove inference equivalence.
4. No assertion of complete migration until missing artifacts are present and functional tests pass.
