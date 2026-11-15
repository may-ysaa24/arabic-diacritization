# Streamlit Community Cloud

Deploy repository `may-ysaa24/arabic-diacritization`, branch
`feature/streamlit-ui-redesign`, entrypoint `streamlit_app/app.py`.
Select **Python 3.12** in Advanced settings. The root `requirements.txt`
contains the tested Streamlit and CPU-only PyTorch versions. No secrets or
external OCR services are needed. Configuration is `.streamlit/config.toml`.

The project owner confirmed permission to use the required dataset for hosting
on 15 November 2026. The deployment includes only the existing translation
runtime sources, with their original bytes and manifest hashes:

- `references/fathul_qorib/dataset_version.json`;
- `references/fathul_qorib/original/translations.jsonl` (AI-assisted drafts);
- the 17 catalog-listed `data/demo_fathul_qorib_per_bab/CSV/*.csv` files;
- the 17 matching `Referensi_Berharakat/*.csv` files;
- `Laporan_Audit/PETA_PARAGRAF.csv` and
  `Laporan_Audit/Sumber/dataset_drive.csv` under the same demo directory.

These 38 files are required by the current matching and integrity checks,
including books without translations so ambiguous text remains ambiguous.
Do not trim columns or records: byte hashes and source offsets are validated.
PDFs, TXT demo copies, archives, OCR tools/models, caches, environments and
additional research datasets are not part of this runtime data bundle.

Inference requires `models/finetuned/best_finetuned_model.pt`, its
`finetuning_config.json`, the tracked mappings, and tracked evaluation metadata.
These files already belong to the repository. No model or preprocessing changes
are needed for deployment.

The package is small, but concurrent inference and large multi-file uploads can
consume substantially more RAM than the checkpoint size. Keep the existing
upload/export limits and cached model. Local smoke measurements do not guarantee
Community Cloud capacity; inspect the app logs after its first cloud launch.

For verification, run tests from an independent checkout with only tracked
sources and the declared dependencies, rather than the development working tree.
Optional browser tests additionally require `requirements-browser.txt` and a
Playwright browser. Their artifacts remain ignored.

Official deployment and dependency instructions:
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
