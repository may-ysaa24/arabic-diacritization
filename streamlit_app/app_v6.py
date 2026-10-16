

"""Streamlit UI v6 akademik. Memakai API inference_engine asli tanpa modifikasi.

Prototipe terpisah dari app.py v5. Notebook sumber: 07_build_streamlit_ui_v6.ipynb.
"""

from hashlib import sha256
from html import escape
from importlib import import_module
from io import BytesIO
from math import isfinite
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Diakritisasi Arab | BiLSTM-CRF",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "assets" / "logo_unimal.png"
PAGES = ("Beranda", "Diakritisasi", "Contoh Teks", "Tentang Model")
# Disalin dari contoh yang sudah ada di app.py asli; bukan label referensi.
EXAMPLES = (
    "قال الشيخ الإمام العالم العلامة شمس الدين",
    "الحمد لله رب العالمين",
    "وأسأله الهداية إلى سواء السبيل",
)

CSS = """
<style>
:root {
 --forest:#064937; --forest2:#075c42; --green:#087e4e; --jade:#e7f4ed;
 --gold:#d4a127; --ink:#173d35; --muted:#617971; --line:#dae8df;
 --cream:#fbfcfa; --light:#f3f8f4; --serif:Georgia,"Times New Roman",serif;
 --sans:"Segoe UI",Inter,Arial,sans-serif;
 --arabic:"Noto Naskh Arabic",Amiri,"Traditional Arabic",serif;
}
.stApp {background:#f9fbf9;color:var(--ink);font-family:var(--sans)}
.block-container,.stMainBlockContainer {max-width:1500px;padding:1.3rem 2rem 3rem}
[data-testid="stSidebar"] {background:linear-gradient(150deg,#f4f9f5 0%,#eef7f0 65%,#f8faf7 100%);border-right:1px solid #d9e8de}
[data-testid="stSidebar"] > div:first-child {padding-top:1.5rem}
[data-testid="stSidebar"] img {object-fit:contain;filter:drop-shadow(0 5px 8px #0d4a2110)}
.sidebar-university {text-align:center;color:#07523d;font:700 1.35rem/1.25 var(--serif);margin:0 0 .3rem}
.sidebar-gold {height:3px;width:42px;background:var(--gold);border-radius:9px;margin:.9rem auto 1.5rem}
.sidebar-kicker {font-size:.71rem;letter-spacing:.16em;font-weight:700;color:#6d8279;margin:0 0 .55rem}
.sidebar-title {font:700 1.6rem/1.2 var(--serif);color:#084c3c;margin:0 0 1.6rem}
.st-key-nav [role="radiogroup"]{gap:.3rem}
.st-key-nav [role="radiogroup"]>label {padding:.73rem 1rem;min-height:48px;border:1px solid transparent;border-radius:13px;margin:0;transition:background .2s ease}
.st-key-nav [role="radiogroup"]>label:has(input:checked) {background:#dceee2;border-color:#cde7d7;color:#007e4f;font-weight:700}
.st-key-nav [role="radiogroup"]>label:hover {background:#e7f4ed}
.st-key-nav [role="radiogroup"]>label p {font-size:.99rem}
.sidebar-model {background:#e4f3e9;border:1px solid #d3e8d8;border-radius:14px;padding:1rem;color:#124c39;margin-top:2rem;line-height:1.6}
.sidebar-model strong{font-weight:750}.sidebar-model small{color:#62776b}
.sidebar-dot {display:inline-block;vertical-align:middle;width:11px;height:11px;margin-right:.5rem;background:#008c50;border:3px solid #cbe8d5;border-radius:50%}
.sidebar-footer {margin-top:1.2rem;border-top:1px solid #d4e5da;padding-top:1rem;color:#698078;font-size:.85rem}
.topbar {display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding:.4rem .2rem 1rem;margin-bottom:1.3rem;color:#52766a;font-size:.9rem}
.topbar span{display:flex;align-items:center;gap:.4rem}.crumb-icon{color:var(--green);font-size:1.15rem}
.hero {position:relative;isolation:isolate;overflow:hidden;background:radial-gradient(ellipse at 80% 15%,#fff7e4 0%,transparent 40%),linear-gradient(135deg,#fcfffb 0%,#f4faf5 67%,#e7f4ec 100%);border:1px solid #e4ebe4;border-radius:21px;min-height:380px;text-align:center;padding:2.5rem 2.6rem 3.1rem;margin-bottom:1rem}
.hero::before,.page-banner::before {content:"";pointer-events:none;position:absolute;inset:0;opacity:.17;background-image:repeating-conic-gradient(from 45deg at 50% 50%,transparent 0deg 22deg,#a0c8b1 23deg 24deg,transparent 25deg 45deg);background-size:100px 100px;mask-image:linear-gradient(90deg,#000 0%,transparent 22%,transparent 80%,#000)}
.hero::after {content:"";position:absolute;z-index:-1;left:-8%;right:-8%;bottom:-78px;height:190px;background:linear-gradient(110deg,#afdbc6,#eaf4e8 55%,#c6e9d7);border-radius:52% 48% 0 0/50% 50% 0 0;opacity:.66;transform:rotate(-2deg);border-top:2px solid #e3ba56}
.hero-kicker {font-size:.78rem;font-weight:800;letter-spacing:.19em;color:#be8a19;margin:.6rem auto 1rem}
.small-rule {width:48px;height:3px;background:var(--gold);border-radius:8px;margin:0 auto 1.3rem}
.hero h1 {font:700 clamp(2rem,3.45vw,3.35rem)/1.14 var(--serif);color:#064835;margin:0 auto 1.05rem;max-width:1020px;letter-spacing:-.018em}
.hero p {font-size:1.04rem;line-height:1.8;color:#526d64;max-width:820px;margin:0 auto 1rem}
.hero-note {font-size:.83rem;color:#6d8278}
.st-key-home_buttons {display:flex;justify-content:center;gap:.5rem;margin:-6.1rem 0 4.4rem;position:relative;z-index:2}
.st-key-home_buttons button {min-height:52px;min-width:190px}
.st-key-home_buttons [data-testid="stBaseButton-primary"] {box-shadow:0 8px 20px #005a3530}
.section-head {display:flex;justify-content:space-between;align-items:center;gap:.5rem;margin:1.25rem 0 .9rem}
.section-head h2 {font:700 1.55rem var(--serif);color:#084b39;margin:0}
.section-head .under {display:block;width:38px;height:3px;background:var(--gold);margin-top:.45rem;border-radius:10px}
.steps-wrap {border:1px solid #e0e9e2;border-radius:20px;box-shadow:0 8px 28px #194f2610;background:#fff;padding:1rem 1.35rem 1.5rem}
.steps-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1.3rem}
.step-card {padding:1.2rem;border-radius:15px;border:1px solid #e3ebe5;background:#fcfefc;min-height:178px}
.step-index {display:inline-flex;justify-content:center;align-items:center;width:44px;height:44px;border-radius:50%;background:#e1f2e8;color:#057447;font-weight:800;font-size:1.2rem;font-family:var(--serif)}
.step-icon{font-size:1.6rem;margin-left:.85rem;vertical-align:middle;color:#08784a}
.step-card h3{font:700 1.12rem var(--serif);color:#064a38;margin:.75rem 0 .35rem}
.step-card p{font-size:.86rem;line-height:1.65;color:#64786d;margin:0}
.page-banner {position:relative;overflow:hidden;border-radius:20px;border:1px solid #e2ebe4;background:radial-gradient(ellipse at 82% 40%,#fff7e1,transparent 47%),linear-gradient(100deg,#f7fbf7,#e7f4e9);padding:1.55rem 1.8rem 1.7rem;margin-bottom:1.3rem}
.page-banner h1{position:relative;font:700 clamp(2rem,3vw,2.75rem)/1.18 var(--serif);color:#064835;margin:.35rem 0 .45rem}
.page-banner p{position:relative;font-size:.96rem;max-width:830px;line-height:1.6;color:#59756a;margin:0}
.status-pill{display:inline-flex;align-items:center;gap:.5rem;padding:.4rem .8rem;border-radius:40px;color:#087746;background:#e0f4e6;font-size:.79rem;font-weight:700;border:1px solid #d5ebdb}
.status-pill.muted {background:#f2f5f2;color:#748279}
.panel-heading{font:700 1.25rem/1.3 var(--serif);color:#0a4a38;padding:.1rem 0 .35rem;margin:0 0 1rem}
.panel-heading::after{content:"";display:block;height:3px;width:39px;margin-top:.55rem;background:var(--gold);border-radius:20px}
.st-key-input_panel,.st-key-output_panel,.st-key-example_panel_1,.st-key-example_panel_2,.st-key-example_panel_3,.st-key-status_panel {background:#fff;border:1px solid #dfebe2;border-radius:18px;padding:1.2rem;box-shadow:0 5px 18px #124d2510}
.st-key-input_panel textarea{direction:rtl;text-align:right;font:1.7rem/2 var(--arabic);background:#fff;border-color:#cadfd2}
.arabic-text{direction:rtl;unicode-bidi:plaintext;text-align:right;font:1.7rem/2.15 var(--arabic);white-space:pre-wrap;overflow-wrap:anywhere;padding:.3rem .15rem}
.arabic-result {background:#f2faf5;border:1px solid #cce6d4;border-radius:13px;min-height:190px;max-height:500px;overflow-y:auto;padding:1rem 1.2rem;font:1.95rem/2.15 var(--arabic);direction:rtl;unicode-bidi:plaintext;text-align:right;white-space:pre-wrap;overflow-wrap:anywhere}
.empty-output{display:flex;align-items:center;justify-content:center;text-align:center;min-height:190px;background:#f9fcf9;border-radius:13px;border:1px dashed #c6dfcc;color:#6d8173;padding:1.5rem}
.empty-output p{font-size:.88rem;line-height:1.55;max-width:300px}
.stat-row {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.8rem;margin:1rem 0}
.stat-tile {border:1px solid #e1e9e3;border-radius:14px;background:#fff;padding:.95rem 1.05rem;box-shadow:0 4px 12px #17502a0a}
.stat-tile .label {font-size:.77rem;color:#657a70}.stat-tile strong{display:block;color:#084b39;font:700 1.45rem var(--serif);margin:.25rem 0}
.detail-wrap{background:#fff;border:1px solid #e0e9e2;padding:1rem 1.2rem;border-radius:14px;margin-top:.65rem}
.detail-row{display:flex;flex-wrap:wrap;justify-content:space-between;gap:.8rem}
.detail-item{font-size:.83rem;color:#59786a;padding:.4rem 0}.detail-item strong{display:block;color:#087847;margin-top:.2rem}
.site-foot{border-top:1px solid #dce8df;color:#71857a;font-size:.76rem;margin-top:2rem;padding:1rem 0}
[data-testid="stTabs"] button[role="tab"]{padding:.65rem 1.2rem;border-radius:10px;margin-right:.4rem}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"]{background:#087a49;color:#fff!important}
[data-testid="stTabs"] [data-baseweb="tab-highlight"]{background-color:transparent!important}
[data-testid="stBaseButton-primary"] {background:#087949;border-color:#087949;border-radius:10px;font-weight:700}
[data-testid="stBaseButton-primary"]:hover{background:#08633d;border-color:#08633d}
[data-testid="stBaseButton-secondary"] {border-color:#a9cbb7;color:#09523d;border-radius:10px}
[data-testid="stBaseButton-secondary"]:hover{border-color:#087949;color:#087949;background:#f2faf4}
[data-testid="stMetricValue"]{color:var(--forest)}
.st-key-csv_feedback {border:1px solid #e4e9d9}
button {min-height:40px}
button:focus-visible,a:focus-visible {outline:3px solid #d3a22c!important;outline-offset:3px}
@media(max-width:1050px){.block-container,.stMainBlockContainer{padding:1.2rem 1.1rem 2rem}.stat-row{grid-template-columns:repeat(2,minmax(0,1fr))}.steps-grid{gap:.6rem}}
@media(max-width:650px){.hero{min-height:430px;padding:1.3rem .9rem 4.5rem}.hero h1{font-size:2.05rem}.hero p{font-size:.91rem}.st-key-home_buttons {margin:-6rem auto 3rem;flex-wrap:wrap}.steps-grid{grid-template-columns:1fr}.page-banner{padding:1.1rem}.stat-row{grid-template-columns:repeat(2,minmax(0,1fr))}.topbar{font-size:.76rem}.arabic-result{font-size:1.55rem}.st-key-input_panel textarea{font-size:1.45rem}}
@media(prefers-reduced-motion:no-preference){[data-testid="stBaseButton-primary"]{transition:background-color .2s ease,transform .2s ease}[data-testid="stBaseButton-primary"]:hover{transform:translateY(-1px)}}
@media print{[data-testid="stSidebar"],[data-testid="stHeader"]{display:none}.arabic-result{max-height:none;overflow:visible}}
</style>
"""
st.html(CSS)


@st.cache_resource(show_spinner="Memeriksa kesiapan model…")
def load_backend():
    """Hanya panggil API asli. Tidak ada pengganti prediksi atau metrik."""
    try:
        backend = import_module("inference_engine")
        return backend, backend.health_check()
    except Exception as error:
        return None, {"success": False, "message": str(error), "model": None, "metrics": None}


engine, health = load_backend()
READY = bool(health.get("success")) and engine is not None
model_info = health.get("model") or {}
metrics_data = health.get("metrics") or {}

# Nilai persisten terpisah dari key widget agar tetap tersedia setelah navigasi.
for state_key, default in {
    "page": "Beranda", "manual_input": "", "manual_result": None,
    "manual_result_input": None, "upload_snapshot": None,
    "file_result": None, "file_result_signature": None,
    "csv_column": None, "example_results": {}, "uploader_generation": 0,
}.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default


def navigate(page, example=None):
    st.session_state.page = page
    if example is not None:
        st.session_state.manual_input = example
        st.session_state["_manual_input"] = example
        st.session_state.manual_result = None
        st.session_state.manual_result_input = None


def manual_changed():
    st.session_state.manual_input = st.session_state["_manual_input"]
    st.session_state.manual_result = None
    st.session_state.manual_result_input = None


def reset_manual():
    st.session_state.manual_input = ""
    st.session_state["_manual_input"] = ""
    st.session_state.manual_result = None
    st.session_state.manual_result_input = None


def reset_file():
    st.session_state.upload_snapshot = None
    st.session_state.file_result = None
    st.session_state.file_result_signature = None
    st.session_state.csv_column = None
    st.session_state.uploader_generation += 1


def upload_changed(widget_key):
    uploaded = st.session_state.get(widget_key)
    st.session_state.file_result = None
    st.session_state.file_result_signature = None
    st.session_state.csv_column = None
    if uploaded is None:
        st.session_state.upload_snapshot = None
        return
    data = uploaded.getvalue()
    # Ukuran file sudah dibatasi oleh backend; hindari menahan file terlalu besar di state UI.
    limit = int(getattr(engine, "MAX_FILE_SIZE", 5 * 1024 * 1024))
    st.session_state.upload_snapshot = {
        "name": uploaded.name, "size": len(data),
        "data": data if len(data) <= limit else None,
        "digest": sha256(data).hexdigest(),
    }


def column_changed():
    st.session_state.csv_column = st.session_state["_csv_column"]
    st.session_state.file_result = None
    st.session_state.file_result_signature = None


def uploaded_copy(snapshot):
    """BytesIO baru setiap panggilan, sesuai antarmuka file backend."""
    file = BytesIO(snapshot["data"])
    file.name = snapshot["name"]
    return file


def heading(kicker, title, description):
    st.html(
        f'<header class="page-heading"><div class="eyebrow">{escape(kicker)}</div>'
        f'<h1>{escape(title)}</h1><p>{escape(description)}</p></header>'
    )


def arabic(text, result=False):
    class_name = "arabic-text arabic-result" if result else "arabic-text"
    st.html(f'<div class="{class_name}" lang="ar" dir="rtl">{escape(str(text))}</div>')


def empty_output():
    st.html('<div class="empty-output"><strong>Hasil akan tampil di sini</strong>'
            '<p>Masukkan teks Arab, kemudian pilih Proses Diakritisasi. '
            'Hasil dapat disalin atau diunduh setelah pemrosesan.</p></div>')


def processing_call(function, *args, **kwargs):
    bar = st.progress(0.0)
    progress_text = st.empty()

    def callback(current, total):
        if total > 0:
            bar.progress(min(1.0, max(0.0, current / total)))
            progress_text.caption(f"Memproses bagian {current} dari {total}…")

    try:
        with st.spinner("Model sedang memproses teks…"):
            return function(*args, progress_callback=callback, **kwargs)
    except Exception as error:
        return {"success": False, "message": f"Pemrosesan gagal: {error}"}
    finally:
        bar.empty()
        progress_text.empty()


def unknown_warning(result):
    unknown = result.get("unknown_characters") or []
    if unknown:
        st.warning("Karakter di luar kosakata ditemukan dan dipetakan ke <UNK>.")
        st.text("Karakter: " + ", ".join(repr(char) for char in unknown))


def show_prediction(result, key):
    """Keluaran manual; seluruh angka diambil dari API asli, bukan contoh statis."""
    if not result.get("success"):
        st.error(result.get("message", "Pemrosesan belum berhasil."))
        return
    arabic(result["prediction"], result=True)
    st.html('<span class="status-pill">✓ &nbsp;Prediksi selesai</span>')
    st.caption("Prediksi otomatis. Periksa kembali ketepatan harakat sebelum digunakan.")
    unknown_warning(result)
    if result.get("had_diacritics"):
        st.info("Harakat pada masukan dihapus sebelum diprediksi ulang.")
    st.download_button(
        "↓  Unduh TXT", result["prediction"].encode("utf-8"),
        file_name="hasil_diakritisasi.txt", mime="text/plain; charset=utf-8",
        key=f"download_{key}", type="primary",
    )
    with st.expander("📋 Salin hasil (ikon salin tersedia di kotak berikut)"):
        st.code(result["prediction"], language=None, wrap_lines=True)
    with st.expander("Detail teknis segmentasi"):
        st.write({
            "Karakter masukan bersih": result.get("total_characters"),
            "Huruf Arab": result.get("arabic_letters"),
            "Jumlah segmen": result.get("total_chunks"),
            "Panjang tiap segmen": result.get("chunk_lengths"),
        })


def render_home():
    st.html(
        '<section class="hero">'
        '<div class="hero-kicker">PENELITIAN NATURAL LANGUAGE PROCESSING</div>'
        '<div class="small-rule"></div>'
        '<h1>Diakritisasi Otomatis Teks Arab Gundul<br>'
        'pada Kitab Fathul Qorib menggunakan BiLSTM-CRF</h1>'
        '<p>Sistem ini memprediksi harakat pada teks Arab tanpa harakat secara otomatis '
        'menggunakan model BiLSTM-CRF yang telah dilatih pada data Kitab Fathul Qorib.</p>'
        '</section>'
    )
    with st.container(horizontal=True, key="home_buttons"):
        st.button("➜  Mulai Diakritisasi", type="primary", key="home_cta",
                  on_click=navigate, args=("Diakritisasi",))
        st.button("▤  Lihat Contoh", key="home_examples", on_click=navigate,
                  args=("Contoh Teks",))
    st.html(
        '<section class="steps-wrap">'
        '<div class="section-head"><div><h2>Cara Menggunakan Sistem</h2>'
        '<span class="under"></span></div></div>'
        '<div class="steps-grid">'
        '<div class="step-card"><span class="step-index">01</span>'
        '<span class="step-icon">▤</span><h3>Masukkan Teks Arab</h3>'
        '<p>Ketik atau tempel teks Arab, atau unggah berkas TXT maupun CSV.</p></div>'
        '<div class="step-card"><span class="step-index">02</span>'
        '<span class="step-icon">⚙</span><h3>Proses Diakritisasi</h3>'
        '<p>Model BiLSTM-CRF memprediksi harakat pada teks yang dimasukkan.</p></div>'
        '<div class="step-card"><span class="step-index">03</span>'
        '<span class="step-icon">✓</span><h3>Lihat Hasil</h3>'
        '<p>Tinjau hasil prediksi, kemudian salin atau unduh berkas TXT/CSV.</p></div>'
        '</div></section>'
    )
    st.caption("Hasil diakritisasi merupakan prediksi otomatis dan dapat mengandung kesalahan harakat.")


def render_manual():
    if "_manual_input" not in st.session_state:
        st.session_state["_manual_input"] = st.session_state.manual_input
    left, right = st.columns([1, 1], gap="medium")
    with left:
        with st.container(key="input_panel"):
            st.html('<h2 class="panel-heading">Teks Masukan</h2>')
            text = st.text_area(
                "Teks Arab", key="_manual_input", height=226,
                placeholder=EXAMPLES[0], on_change=manual_changed,
                label_visibility="collapsed",
            )
            st.caption("Masukkan teks Arab tanpa huruf Latin. Teks berharakat akan diprediksi ulang.")
            clear_col, process_col = st.columns([1, 1.65], gap="small")
            with clear_col:
                st.button("Bersihkan", key="reset_manual", on_click=reset_manual,
                          use_container_width=True)
            with process_col:
                process = st.button("▶  Proses Diakritisasi", key="process_manual", type="primary",
                                    disabled=not READY, use_container_width=True)
            if process:
                st.session_state.manual_input = text
                st.session_state.manual_result = processing_call(engine.predict_long_text, text)
                st.session_state.manual_result_input = text
    with right:
        with st.container(key="output_panel"):
            st.html('<h2 class="panel-heading">Hasil Diakritisasi</h2>')
            result = st.session_state.manual_result
            if result and st.session_state.manual_result_input == text:
                show_prediction(result, "manual")
            else:
                empty_output()
    result = st.session_state.manual_result
    if result and st.session_state.manual_result_input == text and result.get("success"):
        def stat(label, value):
            return f'<div class="stat-tile"><span class="label">{escape(label)}</span><strong>{escape(str(value))}</strong></div>'
        st.html('<section class="stat-row">'
                + stat("Karakter masukan", result.get("total_characters", "–"))
                + stat("Huruf Arab", result.get("arabic_letters", "–"))
                + stat("Jumlah segmen", result.get("total_chunks", "–"))
                + stat("Status", "Berhasil") + '</section>')
        st.html('<div class="detail-wrap">'
                '<h2 class="panel-heading">Detail Pemrosesan</h2>'
                '<div class="detail-row"><div class="detail-item">✓ Validasi input'
                '<strong>Lulus</strong></div><div class="detail-item">✓ Teks Arab'
                '<strong>Terproses</strong></div><div class="detail-item">✓ Segmentasi'
                f'<strong>{escape(str(result.get("total_chunks", "–")))} segmen</strong></div>'
                '</div></div>')
    else:
        st.info("Ketik teks Arab, lalu klik Proses Diakritisasi untuk melihat statistik dan hasil.")


def render_file_result(result):
    if not result.get("success"):
        st.error(result.get("message", "Berkas belum berhasil diproses."))
        return
    summary = result.get("status_summary") or {}
    successful = summary.get("berhasil", 0)
    if successful:
        st.success(result.get("message", "Berkas selesai diproses."))
    else:
        st.info("Berkas telah dibaca. Tidak ada baris yang diprediksi; data lain dipertahankan.")
    if summary:
        stat_labels = {"berhasil": "Diprediksi", "kosong": "Kosong, dipertahankan",
                       "non_arab": "Non-Arab, dipertahankan", "campuran": "Arab–Latin, dipertahankan",
                       "gagal": "Gagal diproses"}
        st.html('<div class="section-head"><div><h2>Ringkasan Pemrosesan</h2>'
                '<span class="under"></span></div></div>')
        st.dataframe(pd.DataFrame([
            {"Status": stat_labels.get(name, name), "Jumlah": count}
            for name, count in summary.items()
        ]), hide_index=True, use_container_width=True)
    unknown_warning(result)
    for warning in result.get("warnings") or []:
        st.warning(f"Baris {warning['line']}: {warning['note']}")
    st.html('<div class="section-head"><div><h2>Hasil Berkas</h2><span class="under"></span></div></div>')
    if result["input_type"] == "txt":
        arabic(result["prediction"], result=True)
        with st.expander("Salin hasil TXT (melalui ikon pada kotak teks)"):
            st.code(result["prediction"], language=None, wrap_lines=True)
        mime = "text/plain; charset=utf-8"
    else:
        st.dataframe(result["dataframe"], hide_index=True, use_container_width=True)
        mime = "text/csv; charset=utf-8"
    st.download_button(
        "↓  Unduh hasil " + result["input_type"].upper(),
        result["download_bytes"], file_name=result["output_filename"], mime=mime,
        key="download_file", type="primary",
    )
    st.caption("Unduhan menyimpan keluaran asli backend. Ketepatan harakat tetap perlu diperiksa.")


def render_file():
    st.html('<div class="section-head"><div><h2>Unggah Berkas</h2>'
            '<span class="under"></span></div></div>')
    st.caption("Format TXT atau CSV, maksimal 5 MB. Baris Latin, campuran, atau kosong dipertahankan sesuai aturan backend.")
    widget_key = f"_upload_{st.session_state.uploader_generation}"
    st.file_uploader("Pilih berkas TXT / CSV", type=["txt", "csv"], key=widget_key,
                     max_upload_size=5, disabled=not READY,
                     on_change=upload_changed, args=(widget_key,))
    snapshot = st.session_state.upload_snapshot
    if snapshot is None:
        st.info("Pilih berkas untuk menampilkan pratinjau sebelum diproses.")
        return
    st.caption(f"Berkas aktif: {snapshot['name']} • {snapshot['size'] / 1024:.1f} KB")
    st.button("Hapus berkas", key="reset_file", on_click=reset_file)
    if snapshot["data"] is None:
        st.error("Ukuran berkas melebihi batas 5 MB. Pilih berkas yang lebih kecil.")
        return
    if not READY:
        st.warning("Model belum siap; pengunggahan tidak dapat diproses.")
        return
    suffix = Path(snapshot["name"]).suffix.lower()
    selected_column = None
    if suffix == ".csv":
        try:
            preview = engine.read_csv_file(uploaded_copy(snapshot))
            if not preview["success"]:
                st.error(preview["message"])
                return
            frame = preview["dataframe"]
            candidates = engine.detect_arabic_columns(frame)
            detected = [item["column"] for item in candidates]
            others = [column for column in frame.columns if column not in detected]
            # Kolom berjudul teks_* diutamakan dari kolom numerik/id ketika isi semuanya Latin.
            def column_rank(column):
                name = str(column).lower().strip()
                preferred = any(tag in name for tag in ("arab", "teks", "text", "kalimat", "sentence", "content"))
                identifier = name in ("id", "no", "nomor", "index", "number")
                return (0 if preferred else 1, 2 if identifier else 0)
            options = detected + sorted(others, key=column_rank)
            if not options:
                st.error("CSV tidak memiliki kolom untuk diproses.")
                return
            with st.expander("Pratinjau CSV", expanded=True):
                st.dataframe(frame.head(10), hide_index=True, use_container_width=True)
            # Jangan otomatis memakai kolom pertama jika tidak ada bukti teks Arab.
            if st.session_state.csv_column not in options:
                st.session_state.csv_column = detected[0] if detected else None
            # None adalah placeholder eksplisit; pengguna harus memilih kolom.
            choices = [None] + options
            st.session_state["_csv_column"] = st.session_state.csv_column
            selected_column = st.selectbox(
                "Pilih kolom teks yang akan diproses", choices,
                format_func=lambda value: "-- Pilih kolom --" if value is None else str(value),
                key="_csv_column", on_change=column_changed,
            )
            if detected:
                st.caption("Terdeteksi mengandung huruf Arab: " + ", ".join(map(str, detected)))
            else:
                st.warning("Belum ditemukan huruf Arab. Pilih sendiri kolom teks; jangan pilih ID.")
            if selected_column is not None:
                sample = frame[selected_column].dropna().astype(str).head(4)
                if not any(any('\u0600' <= ch <= '\u06ff' for ch in value) for value in sample):
                    st.info("Kolom terpilih tidak terlihat mengandung huruf Arab pada sampel awal. "
                            "Jika memang berisi Latin, isinya akan dipertahankan.")
        except Exception as error:
            st.error(f"Berkas tidak dapat dibaca: {error}")
            return
    else:
        decoded = engine.decode_text_bytes(snapshot["data"])
        if not decoded["success"]:
            st.error(decoded["message"])
            return
        with st.expander("Pratinjau TXT"):
            st.text(decoded["text"][:4000])
            st.caption("Pratinjau hanya 4.000 karakter; pemrosesan tetap menggunakan seluruh isi berkas.")
    signature = (snapshot["name"], snapshot["digest"], selected_column)
    invalid_choice = suffix == ".csv" and selected_column is None
    if st.button("▶  Proses Berkas", type="primary", key="process_file",
                 disabled=(not READY or invalid_choice)):
        st.session_state.file_result = processing_call(
            engine.process_uploaded_file, uploaded_copy(snapshot), text_column=selected_column,
        )
        st.session_state.file_result_signature = signature
    result = st.session_state.file_result
    if result and st.session_state.file_result_signature == signature:
        st.divider()
        render_file_result(result)


def render_diakritisasi():
    status = ('<span class="status-pill">● &nbsp;Model siap digunakan</span>'
              if READY else '<span class="status-pill muted">Model belum tersedia</span>')
    st.html('<section class="page-banner">' + status
            + '<h1>Diakritisasi Teks Arab</h1>'
            + '<p>Masukkan teks Arab tanpa harakat secara langsung atau unggah berkas TXT / CSV '
              'untuk memperoleh hasil prediksi menggunakan model BiLSTM-CRF.</p></section>')
    manual_tab, file_tab = st.tabs(["✎  Input Manual", "⇧  Unggah TXT / CSV"])
    with manual_tab:
        render_manual()
    with file_tab:
        render_file()


def render_examples():
    st.html('<section class="page-banner"><span class="status-pill">Contoh penggunaan</span>'
            '<h1>Contoh Teks Arab</h1><p>Pilih salah satu teks untuk dimasukkan otomatis ke area kerja. '
            'Contoh ini bukan acuan ketepatan harakat.</p></section>')
    for index, text in enumerate(EXAMPLES, start=1):
        with st.container(key=f"example_panel_{index}"):
            st.caption(f"CONTOH {index:02d} • TEKS TANPA HARAKAT")
            arabic(text)
            st.button("Gunakan Contoh →", key=f"use_example_{index}",
                      on_click=navigate, args=("Diakritisasi", text), type="primary")
        st.write("")


def format_percent(value):
    try:
        numeric = float(value)
        if not isfinite(numeric) or not 0 <= numeric <= 100:
            return "Tidak tersedia"
        return f"{numeric:.2f}".replace(".", ",") + "%"
    except (TypeError, ValueError):
        return "Tidak tersedia"


def render_about():
    st.html('<section class="page-banner"><span class="status-pill">Informasi penelitian</span>'
            '<h1>Tentang Model BiLSTM-CRF</h1>'
            '<p>Arsitektur, pendekatan pelatihan, hasil evaluasi, dan keterbatasan sistem '
            'diakritisasi teks Arab gundul.</p></section>')
    st.html('<div class="section-head"><div><h2>Arsitektur Model</h2><span class="under"></span></div></div>')
    st.write("Model menggunakan embedding karakter, BiLSTM untuk mempelajari konteks dua arah, "
             "lapisan linear untuk menghasilkan skor label, serta CRF untuk menentukan urutan harakat. "
             "Prediksi disusun kembali menjadi teks Arab berharakat.")
    st.html('<div class="detail-wrap"><div class="detail-row">'
            '<div class="detail-item">01 • Masukan<strong>Teks Arab</strong></div>'
            '<div class="detail-item">02 • Representasi<strong>Embedding</strong></div>'
            '<div class="detail-item">03 • Konteks<strong>BiLSTM</strong></div>'
            '<div class="detail-item">04 • Label<strong>Linear + CRF</strong></div>'
            '<div class="detail-item">05 • Keluaran<strong>Harakat</strong></div>'
            '</div></div>')
    st.write("Model menggunakan pretraining pada korpus Tashkeela, kemudian fine-tuning "
             "pada korpus Kitab Fathul Qorib. Aplikasi menggunakan checkpoint fine-tuned.")
    st.html('<div class="section-head"><div><h2>Hasil Evaluasi Data Uji</h2><span class="under"></span></div></div>')
    st.caption("Metrik berasal dari berkas evaluasi penelitian, bukan tingkat keyakinan satu prediksi.")
    fine = metrics_data.get("fine_tuned") if isinstance(metrics_data, dict) else None
    if isinstance(fine, dict):
        cols = st.columns(3)
        for col, label, key in zip(cols, ["Accuracy", "DER", "WER"],
                                   ["accuracy_percent", "der_percent", "wer_percent"]):
            col.metric(label, format_percent(fine.get(key)))
        st.caption("Accuracy: ketepatan label karakter valid. DER: kesalahan harakat pada huruf Arab. "
                   "WER: kata yang berbeda dari referensi.")
        baseline = metrics_data.get("baseline")
        if isinstance(baseline, dict):
            with st.expander("Perbandingan baseline dan fine-tuned"):
                st.dataframe(pd.DataFrame([
                    {"Model": name, "Accuracy": format_percent(data.get("accuracy_percent")),
                     "DER": format_percent(data.get("der_percent")),
                     "WER": format_percent(data.get("wer_percent"))}
                    for name, data in [("Baseline", baseline), ("Fine-tuned", fine)]
                ]), hide_index=True, use_container_width=True)
    else:
        st.info("Berkas evaluasi model belum tersedia.")
    with st.expander("Konfigurasi model aktif"):
        if model_info:
            fields = {
                "Kosakata karakter": "vocab_size", "Kelas label": "num_labels",
                "Dimensi embedding": "embedding_dim", "Unit tersembunyi per arah": "hidden_per_direction",
                "Dimensi keluaran BiLSTM": "hidden_dim", "Lapisan BiLSTM": "num_layers",
                "Dropout": "dropout", "Maksimal karakter per segmen": "max_len",
                "Jumlah parameter": "total_parameters", "Epoch checkpoint": "checkpoint_epoch",
                "Perangkat inferensi": "device",
            }
            st.dataframe(pd.DataFrame([
                {"Komponen": label, "Konfigurasi": str(model_info.get(key, "Tidak tersedia"))}
                for label, key in fields.items()
            ]), hide_index=True, use_container_width=True)
        else:
            st.info("Informasi konfigurasi belum tersedia karena backend belum siap.")
    st.html('<div class="section-head"><div><h2>Keterbatasan Sistem</h2><span class="under"></span></div></div>')
    st.info("Hasil bersifat prediktif, dapat mengandung kesalahan harakat, dan tidak "
            "menggantikan pemeriksaan nahwu, sharaf, atau pembacaan oleh pengguna.")
    st.write("Evaluasi penelitian menggunakan data uji Kitab Fathul Qorib. Kemampuan "
             "generalisasi ke teks Arab lain belum dijamin. Karakter di luar kosakata "
             "ditandai melalui peringatan, dan teks panjang diproses per segmen.")


with st.sidebar:
    st.write("")
    if LOGO_PATH.exists():
        logo_left, logo_center, logo_right = st.columns([1, 1, 1])
        with logo_center:
            st.image(str(LOGO_PATH), width=88)
    st.html('<div class="sidebar-university">Universitas Malikussaleh</div>'
            '<div class="sidebar-gold"></div>'
            '<div class="sidebar-kicker">PENELITIAN NLP</div>'
            '<div class="sidebar-title">Sistem Diakritisasi<br>Teks Arab Gundul</div>')
    with st.container(key="nav"):
        nav_icons = {"Beranda": "⌂", "Diakritisasi": "▤", "Contoh Teks": "▣", "Tentang Model": "ⓘ"}
        st.radio("Navigasi utama", PAGES, key="page", label_visibility="collapsed",
                 format_func=lambda name: f"{nav_icons.get(name, '')}    {name}")
    status_label = "Model siap digunakan" if READY else "Model belum tersedia"
    st.html('<div class="sidebar-model"><span class="sidebar-dot"></span>'
            f'<strong>{escape(status_label)}</strong><br>'
            '<small>BiLSTM-CRF Fine-tuned</small></div>'
            '<div class="sidebar-footer">Universitas Malikussaleh · Penelitian NLP</div>')
    if not READY:
        with st.expander("Detail kesiapan model"):
            st.text(health.get("message", "Backend belum tersedia."))
            if st.button("Periksa ulang", key="reload_backend"):
                load_backend.clear()
                st.rerun()

st.html('<header class="topbar">'
        f'<span><span class="crumb-icon">⌂</span> / {escape(st.session_state.page)}</span>'
        '<span>▤ &nbsp; Kitab Fathul Qorib</span>'
        '</header>')
if not READY:
    st.warning("Model belum siap. Antarmuka bisa ditinjau; prediksi tersedia setelah model berhasil dimuat.")
page = st.session_state.page
if page == "Beranda":
    render_home()
elif page == "Diakritisasi":
    render_diakritisasi()
elif page == "Contoh Teks":
    render_examples()
elif page == "Tentang Model":
    render_about()
st.html('<footer class="site-foot">Diakritisasi Otomatis Teks Arab Gundul pada Kitab Fathul Qorib'
        ' • Model BiLSTM-CRF • Universitas Malikussaleh • UI v6.0</footer>')
