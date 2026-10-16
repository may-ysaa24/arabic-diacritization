# Utility scripts

The browser acceptance runner is `scripts/browser_acceptance.py`. It exercises the real Streamlit app using Playwright Chromium: manual prediction, TXT/CSV upload and download, and site navigation.

GitHub Actions workflow: `.github/workflows/browser-acceptance.yml`. A successful run uploads screenshots and the Streamlit server log for manual inspection.

The script requires a running app at `http://127.0.0.1:8501` (overridable using `STREAMLIT_URL`) and an installed Playwright Chromium browser. Dataset training scripts are **not** recreated from the research notebooks automatically.
