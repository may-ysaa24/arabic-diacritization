# Arabic Diacritization with BiLSTM–CRF

Research software for automatic Arabic diacritization of *Fathul Qorib* text using a Bidirectional Long Short-Term Memory (BiLSTM) model and Conditional Random Field (CRF).

> **Status:** Repository initialization. Original research code, trained checkpoints, and evaluation artifacts have **not** yet been migrated or validated here.

## Repository organization

- `src/arabic_diacritization/`: reusable Python modules (to be migrated and verified).
- `streamlit_app/`: user interface (to be migrated and verified).
- `configs/`: experiment configuration.
- `scripts/`: controlled training, evaluation, and inference entry points.
- `tests/`: regression and functionality tests.
- `docs/`: architecture, migration, and reproducibility notes.
- `data/`: documentation and local data placement; do not commit restricted datasets.
- `models/`: model artifact documentation; checkpoints will only be migrated after verification.
- `results/`: experiment outputs and published comparisons.
- `notebooks/`: research notebooks (to be migrated separately).

## Migration policy

The existing private repository [`may-ysaa24/diakritisasi-arab`](https://github.com/may-ysaa24/diakritisasi-arab) is retained untouched as the reference implementation. Refactoring must preserve preprocessing semantics, model architecture, label mappings, and checkpoint compatibility. Numerical equivalence will be claimed only after regression tests pass. Do not retrain merely to reorganize files.

## Next steps

1. Audit source interfaces and the checkpoint dependencies.
2. Port modules and artifacts through a reviewable migration commit.
3. Compare reference and migrated inference on identical input.
4. Validate Streamlit startup and CI before marking the migration complete.
