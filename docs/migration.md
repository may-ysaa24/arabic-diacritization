# Verification ledger: BiLSTM–CRF repository migration

## Source

- Original archived repo: `may-ysaa24/diakritisasi-arab` (private; left untouched).
- Original study materials: authorized Google Drive `BiLSTM-CRF` folder.
- Destination: `may-ysaa24/arabic-diacritization`.

## Completed

- [x] Initialize independent research repository and safeguard original.
- [x] Migrate the original Streamlit applications, logo and metadata.
- [x] Migrate 3 checkpoints (baseline, pretrained, fine-tuned) with matching source Git blob hashes.
- [x] Migrate 10 research notebooks with matching source Git blob hashes.
- [x] Preserve original character/label mappings, configs, and historical metrics.
- [x] Extract real implementations for model, preprocessing, inference, file handling, configuration and evaluation.
- [x] Preserve a reference backend for regression tests, not as the production execution path.
- [x] Test regression and parity on selected Arabic samples, diacritized text, long text, invalid inputs, TXT and CSV.
- [x] Python CI: **29 passed**, `38960160756`.
- [x] Real Chromium acceptance: 4 scenarios passed, `38960889522` (manual inference and download; TXT upload/download; CSV upload/download; navigation).
- [x] Store browser screenshots and server logs as GitHub Actions artifacts.

## Remaining external checks

- [ ] Confirm Windows VS Code installation on the user's machine (GitHub Actions ran on Linux).
- [ ] Perform manual visual review of layout at different desktop/mobile sizes with the final browser environment.
- [ ] Recalculate research metrics only if a separately authorized reproducibility experiment with the original datasets is planned.

## Integrity and scientific limits

1. Checkpoint bytes, notebook code, mapping and historical evaluation figures were not modified.
2. Regression tests establish equality for tested input cases, **not** a proof for every possible Arabic input.
3. Browser tests are real Chromium runs in GitHub Actions, not an inspection of a user's local Windows installation.
4. No data training or original test-set evaluation was repeated. Historical accuracy/DER/WER must remain labeled as such.
5. Keep the original private repository as archive until the new project is independently accepted.
