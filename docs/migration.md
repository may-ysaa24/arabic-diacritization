# Migration and verification

## Source of truth

Existing private GitHub repository: `may-ysaa24/diakritisasi-arab`.

## Guardrails

- Preserve original code and artifacts in the source repository.
- Do not edit trained weight tensors, label dictionaries, or historical experiment results.
- Introduce the Python package in small, reviewable steps.
- Establish input-output regression tests against reference inference.
- Confirm Streamlit functionality and GitHub Actions success before completion.

## Progress

- [x] Repository scaffold created.
- [ ] Reference implementation audited.
- [ ] Model/preprocessing/inference modules migrated.
- [ ] Existing checkpoints and mappings validated.
- [ ] Streamlit migrated and verified.
- [ ] Equivalence and integration tests passed.
