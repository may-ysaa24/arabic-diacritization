# Streamlit UI

Main application: `streamlit_app/app.py`. The alternative UI files `app_v6.py` and `app_studio_v7.py` are preserved as research prototypes. `inference_engine.py` is a backward-compatible import facade into the modular Python package.

Start from the repository root after installing requirements:

```powershell
.venv\Scripts\python.exe -m streamlit run streamlit_app/app.py
```

The `scripts/browser_acceptance.py` Chromium test exercises the main app end-to-end, including manual prediction, TXT/CSV upload and downloaded files. The model-backed functions have been checked against the archived reference on selected cases. Layout still benefits from manual visual review on Windows and mobile-sized screens.
