"""UI v7: studio penelitian diakritisasi Arab. Backend asli tidak dimodifikasi.

Dibuat sebagai prototipe terpisah dari app.py, app_v6.py, dan notebook UI lama.
Hanya memanggil API inference_engine yang sudah tersedia di proyek.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
from importlib import import_module
from io import BytesIO
from math import isfinite
from pathlib import Path
import re

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Ruang Diakritisasi | UNIMAL",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "assets" / "logo_unimal.png"
PAGES = ("Beranda", "Diakritisasi", "Contoh Teks", "Tentang Model")
EXAMPLES = (
    ("Pengantar Kitab", "قال الشيخ الإمام العالم العلامة شمس الدين"),
    ("Kalimat Pendek", "الحمد لله رب العالمين"),
    ("Doa dan Petunjuk", "وأسأله الهداية إلى سواء السبيل"),
)

# Identitas visual sengaja berbeda total dari UI v5/v6: header horizontal,
# editor lebar penuh, panel keluaran 2/3, panel informasi 1/3, tema navy-teal.
CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&family=Noto+Naskh+Arabic:wght@400;500;600;700&display=swap');
:root {
  --night:#142438; --night2:#20364e; --teal:#0b938a; --teal2:#0c746f;
  --sea:#dff5f1; --canvas:#f5f7fa; --paper:#fff; --ink:#192d41;
  --mute:#65758a; --stroke:#e2e8ef; --amber:#f4ba66;
  --sans:'DM Sans','Manrope',Arial,sans-serif;
  --arab:'Noto Naskh Arabic','Amiri','Traditional Arabic',serif;
}
.stApp{background:var(--canvas);color:var(--ink);font-family:var(--sans)}
[data-testid="stSidebar"], [data-testid="collapsedControl"]{display:none!important}
.stMainBlockContainer,.block-container{max-width:1440px;padding:1.15rem 2.2rem 4rem}
[data-testid="stHeader"]{background:transparent;min-height:0}
.st-key-top_header {background:#fff;border:1px solid var(--stroke);border-radius:20px;padding:.78rem 1.25rem;margin:.3rem 0 1.5rem;box-shadow:0 7px 25px rgba(28,43,65,.035)}
.st-key-top_header [data-testid="stImage"] img {object-fit:contain}
.st-key-top_header button{border-radius:11px;font-size:.86rem;min-height:44px;font-weight:650;white-space:nowrap;padding:.5rem .65rem}
.st-key-top_header [data-testid="stBaseButton-primary"]{background:var(--night);border-color:var(--night)}
.st-key-top_header [data-testid="stBaseButton-secondary"]{background:transparent;border-color:transparent;box-shadow:none;color:#576b7d}
.st-key-top_header [data-testid="stBaseButton-secondary"]:hover{background:#eff6f6;border-color:#eff6f6;color:#0a7470}
.mini-label{font-size:.66rem;letter-spacing:.145em;font-weight:800;color:#68818a;text-transform:uppercase}
.header-name{font-weight:850;font-size:1.04rem;letter-spacing:-.025em;color:var(--night);line-height:1.18}
.brand-uni{font-size:.72rem;color:#697c88;margin-top:2px}
.header-ready{font-size:.82rem;color:#087b72;font-weight:750;text-align:right}
.header-ready i{background:#12a698;width:9px;height:9px;display:inline-block;border-radius:100%;margin-right:5px}
.header-notready{font-size:.82rem;color:#a25c24;font-weight:700;text-align:right}
.st-key-hero_home {background:radial-gradient(circle at 80% 20%,#2c5670 0%,transparent 42%),linear-gradient(120deg,#101d31 0%,#1e3a53 100%);padding:2.9rem 3rem 2.3rem;border-radius:27px;box-shadow:0 20px 40px rgba(25,47,65,.12);margin-bottom:1.5rem;overflow:hidden}
.st-key-hero_home p,.st-key-hero_home h1{color:#fff}
.hero-brow{color:#8ee3d4!important;font-size:.76rem;letter-spacing:.17em;font-weight:800;margin-bottom:1.1rem}
.hero-title{font-family:var(--sans);font-weight:850;letter-spacing:-.045em;font-size:clamp(2.3rem,3.6vw,3.95rem);line-height:1.17;margin:0 0 1.4rem;color:#fff}
.hero-desc{font-size:1.04rem;color:#c5d9e6!important;line-height:1.85;max-width:640px}
.hero-visual{background:#ffffff0d;border:1px solid #ffffff2b;padding:1.4rem;border-radius:22px;min-height:305px}
.pipeline-step{background:#ffffff16;border:1px solid #ffffff1b;border-radius:14px;padding:.7rem .9rem;margin-bottom:9px;color:white;display:flex;align-items:center;justify-content:space-between;gap:1rem}
.pipeline-step .tag{font-size:.66rem;color:#9feadd;letter-spacing:.07em;font-weight:700}
.pipeline-step strong{font-family:var(--arab);font-size:24px;color:white}
.pipeline-flow{display:flex;justify-content:center;letter-spacing:.25em;color:#9ddecf;font-size:.85rem;margin:5px}
.pipeline-caption{font-size:.72rem;color:#b9cdd8;margin-top:10px}
.st-key-hero_home button {margin-top:.8rem;min-height:52px;border-radius:12px}
.st-key-hero_home [data-testid="stBaseButton-primary"]{background:var(--teal);border-color:var(--teal);color:white;font-weight:800}
.st-key-hero_home [data-testid="stBaseButton-secondary"]{background:transparent;border-color:#ffffff60;color:white;font-weight:750}
.page-title{font-weight:850;color:var(--night);font-size:clamp(2rem,3.0vw,2.8rem);line-height:1.18;letter-spacing:-.04em;margin:0}
.page-sub{color:var(--mute);max-width:730px;line-height:1.72;margin:.4rem 0 1.1rem}
.section-kicker{color:var(--teal2);font-weight:800;font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;margin-bottom:.45rem}
.panel-title{color:var(--night);font-size:1.17rem;font-weight:800;letter-spacing:-.025em;margin-bottom:.25rem}
.panel-sub{color:var(--mute);font-size:.86rem;line-height:1.58}
[class*="st-key-summary_tile_"], .st-key-sample_card_1, .st-key-sample_card_2, .st-key-sample_card_3,
.st-key-process_entry, .st-key-editor_panel, .st-key-result_main,
.st-key-result_side, .st-key-file_input_box, .st-key-file_results,
.st-key-about_summary, .st-key-about_pipeline,
.st-key-metric_model, .st-key-tips_panel {background:#fff;border:1px solid var(--stroke);border-radius:20px;padding:1.2rem 1.4rem;box-shadow:0 8px 26px rgba(25,41,63,.035)}
.st-key-editor_panel {padding:1.4rem 1.6rem 1.2rem}
.st-key-editor_panel textarea{background:#fbfcfe;border:1px solid #dce5ea!important;border-radius:13px!important;direction:rtl;text-align:right;unicode-bidi:plaintext;font:500 27px/2.05 var(--arab);min-height:235px}
.st-key-editor_panel textarea:focus{border-color:var(--teal)!important;box-shadow:0 0 0 2px #0b938a1f!important}
.st-key-result_main {padding:1.4rem 1.55rem}
.arabic-display{direction:rtl;unicode-bidi:plaintext;text-align:right;white-space:pre-wrap;overflow-wrap:anywhere;font:500 28px/2.2 var(--arab);color:#182c3e;background:#f7fafb;border:1px solid #e2eaf0;border-radius:15px;padding:1.4rem 1.65rem;min-height:170px;max-height:450px;overflow-y:auto}
.arabic-mini{direction:rtl;text-align:right;white-space:pre-wrap;overflow-wrap:anywhere;font:500 23px/2 var(--arab);color:#223449}
.arabic-before{background:#f5f7fa;border-radius:13px;padding:.75rem 1.1rem;margin-top:.6rem;direction:rtl;text-align:right;white-space:pre-wrap;overflow-wrap:anywhere;font:500 21px/1.9 var(--arab)}
.empty-placeholder{border:1.5px dashed #ccd7e1;border-radius:15px;background:#f7fafc;padding:2.5rem 1.3rem;color:#758596;text-align:center;min-height:180px}
.tile-number{font-size:1.6rem;letter-spacing:-.04em;font-weight:850;color:var(--night);margin:.25rem 0}
.tile-label{color:var(--mute);font-size:.78rem}
.step-num{font-size:.73rem;font-weight:850;background:#d9f2ec;color:#09776d;padding:.35rem .55rem;border-radius:10px;display:inline-block;margin-bottom:.8rem}
.callout{background:#e9f7f4;color:#136b62;border-radius:12px;padding:.8rem 1rem;font-size:.82rem;line-height:1.55;margin:.8rem 0}
.soft-note{color:#7b8998;font-size:.81rem;line-height:1.7}
.stButton>button,.stDownloadButton>button{min-height:44px;border-radius:11px;font-weight:750;font-size:.85rem}
[data-testid="stBaseButton-primary"]{background:var(--teal);border-color:var(--teal)}
[data-testid="stBaseButton-primary"]:hover{background:#087b74;border-color:#087b74}
[data-testid="stBaseButton-secondary"]{border-color:#d3e1e6;color:var(--night);background:#fff}
[data-testid="stBaseButton-secondary"]:hover{border-color:#119489;color:#087c73;background:#f3faf8}
.stTabs [data-baseweb="tab-list"]{background:white;padding:.3rem .4rem;border:1px solid var(--stroke);border-radius:13px;gap:.25rem;max-width:max-content}
.stTabs [data-baseweb="tab"]{border-radius:9px;padding:.6rem 1rem;font-weight:700}
.stTabs [aria-selected="true"]{background:#e8f7f4;color:#07756d}
.st-key-file_input_box [data-testid="stFileUploader"]{border-radius:14px}
[data-testid="stMetricValue"] {color:var(--night);font-weight:850;font-size:1.55rem}
[data-testid="stMetricLabel"] p{color:#778596;font-size:.83rem}
.stDataFrame{border-radius:12px;overflow:hidden}
.st-key-about_pipeline {background:#15263a;color:white}
.st-key-about_pipeline .panel-title{color:white}
.route-chain {display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin:.4rem 0 1rem}
.route-chip{background:#ffffff16;color:white;padding:.8rem .9rem;border:1px solid #ffffff22;border-radius:11px;font-size:.85rem;font-weight:650}
.route-arrow{color:#8ee3d4;font-size:1.25rem}
.st-key-sample_card_1,.st-key-sample_card_2,.st-key-sample_card_3{min-height:265px}
footer{font-size:.76rem;text-align:center;color:#9aa6b3;border-top:1px solid #e1e7ee;padding:1.5rem;margin-top:3rem}
@media(max-width:1100px){.stMainBlockContainer,.block-container{padding:1rem 1.1rem 3rem}.st-key-top_header button{font-size:.75rem;padding:.4rem .4rem}}
@media(max-width:780px){.st-key-hero_home{padding:1.5rem}.hero-title{font-size:2.1rem}.st-key-top_header [data-testid="stHorizontalBlock"]{flex-wrap:wrap}.st-key-top_header [data-testid="stColumn"]{min-width:105px}.st-key-editor_panel textarea{font-size:24px}.arabic-display{font-size:24px}.stMainBlockContainer,.block-container{padding:.6rem .8rem 2rem}}
@media(prefers-reduced-motion:reduce){*,*::after,*::before{scroll-behavior:auto!important;transition:none!important}}
</style>
"""
st.html(CSS)


@st.cache_resource(show_spinner="Menghubungkan model BiLSTM-CRF…")
def load_backend():
    try:
        engine = import_module("inference_engine")
        return engine, engine.health_check()
    except Exception as error:
        return None, {"success": False, "message": str(error), "model": {}, "metrics": {}}


engine, health = load_backend()
READY = bool(engine is not None and health.get("success"))
model_info = health.get("model") or {}
metrics = health.get("metrics") or {}

DEFAULTS = {
    "route": "Beranda",
    "mode": "Teks langsung",
    "manual_text": "",
    "manual_result": None,
    "manual_result_source": None,
    "uploaded_snapshot": None,
    "file_result": None,
    "file_result_signature": None,
    "upload_generation": 0,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def goto(page: str, example: str | None = None):
    st.session_state.route = page
    if example is not None:
        st.session_state.mode = "Teks langsung"
        st.session_state.manual_text = example
        st.session_state.manual_result = None
        st.session_state.manual_result_source = None


def manual_modified():
    st.session_state.manual_result = None
    st.session_state.manual_result_source = None


def clear_manual():
    st.session_state.manual_text = ""
    st.session_state.manual_result = None
    st.session_state.manual_result_source = None


def upload_modified(widget_key):
    uploaded = st.session_state.get(widget_key)
    st.session_state.file_result = None
    st.session_state.file_result_signature = None
    if uploaded is None:
        st.session_state.uploaded_snapshot = None
        return
    content = uploaded.getvalue()
    size_limit = int(getattr(engine, "MAX_FILE_SIZE", 5 * 1024 * 1024))
    st.session_state.uploaded_snapshot = {
        "name": uploaded.name,
        "digest": sha256(content).hexdigest(),
        "size": len(content),
        "data": content if len(content) <= size_limit else None,
    }


def clear_file():
    st.session_state.uploaded_snapshot = None
    st.session_state.file_result = None
    st.session_state.file_result_signature = None
    st.session_state.upload_generation += 1


def make_upload(snapshot):
    item = BytesIO(snapshot["data"])
    item.name = snapshot["name"]
    return item


def arabic_display(text: str, *, mini=False):
    css_class = "arabic-mini" if mini else "arabic-display"
    st.html(f'<div class="{css_class}" lang="ar" dir="rtl">{escape(str(text))}</div>')


def section_intro(tag: str, title: str, subtitle: str):
    st.html(f'<div class="section-kicker">{escape(tag)}</div>'
            f'<h1 class="page-title">{escape(title)}</h1>'
            f'<p class="page-sub">{escape(subtitle)}</p>')


def run_processing(fn, *args, **kwargs):
    bar = st.progress(0, text="Menyiapkan pemrosesan…")

    def callback(current, total):
        if total:
            progress = min(100, max(0, round(current / total * 100)))
            bar.progress(progress, text=f"Memproses segmen {current} dari {total}")
    try:
        with st.spinner("Memproses dengan model asli…"):
            return fn(*args, progress_callback=callback, **kwargs)
    except Exception as error:
        return {"success": False, "message": f"Pemrosesan gagal: {error}"}
    finally:
        bar.empty()


def show_unknowns(result):
    unknown = result.get("unknown_characters") or []
    if unknown:
        st.warning("Ada karakter di luar kosakata model (dipetakan menjadi <UNK>): "
                   + ", ".join(repr(x) for x in unknown))


def file_status_table(summary):
    friendly = {
        "berhasil": "Diprediksi", "kosong": "Kosong (dipertahankan)",
        "non_arab": "Non-Arab (dipertahankan)",
        "campuran": "Arab dan Latin (dipertahankan)", "gagal": "Gagal",
    }
    data = [{"Kategori": friendly.get(k, k), "Baris": int(v)} for k, v in summary.items()]
    if data:
        st.dataframe(pd.DataFrame(data), hide_index=True, width="stretch")


def render_header():
    with st.container(key="top_header"):
        logo, nav, badge = st.columns([1.65, 4.5, 1.18], gap="small", vertical_alignment="center")
        with logo:
            a, b = st.columns([.24, .76], vertical_alignment="center", gap="small")
            with a:
                if LOGO_PATH.exists():
                    st.image(str(LOGO_PATH), width=43)
                else:
                    st.markdown("### ◈")
            with b:
                st.html('<div class="header-name">Ruang Diakritisasi</div>'
                        '<div class="brand-uni">Universitas Malikussaleh</div>')
        with nav:
            cols = st.columns(4, gap="small")
            for col, page in zip(cols, PAGES):
                with col:
                    st.button(page, type="primary" if st.session_state.route == page else "secondary",
                              key="nav_" + page.lower().replace(" ", "_"),
                              on_click=goto, args=(page,), use_container_width=True)
        with badge:
            if READY:
                st.html('<div class="header-ready"><i></i>Model siap</div>')
            else:
                st.html('<div class="header-notready">● Model belum siap</div>')


def render_home():
    with st.container(key="hero_home"):
        left, right = st.columns([1.22, .9], gap="large", vertical_alignment="center")
        with left:
            st.html('<div class="hero-brow">LABORATORIUM NLP · PROYEK SKRIPSI</div>'
                    '<h1 class="hero-title">Satu ruang kerja untuk teks Arab yang lebih mudah dibaca.</h1>'
                    '<p class="hero-desc">Diakritisasi otomatis pada Kitab <i>Fathul Qorib</i> '
                    'dengan model Bidirectional LSTM dan Conditional Random Field. '
                    'Ketik teks atau proses berkas TXT dan CSV, lalu tinjau hasil prediksi.</p>')
            x, y = st.columns([1, 1], gap="small")
            with x:
                st.button("Buka ruang kerja  →", type="primary", key="go_studio",
                          on_click=goto, args=("Diakritisasi",), use_container_width=True)
            with y:
                st.button("Lihat contoh", key="go_examples", on_click=goto,
                          args=("Contoh Teks",), use_container_width=True)
        with right:
            st.html('''<div class="hero-visual">
              <div class="mini-label" style="color:#91d8d5;margin-bottom:1rem">ALUR SISTEM</div>
              <div class="pipeline-step"><span class="tag">01 · INPUT</span><strong>الحمد لله رب العالمين</strong></div>
              <div class="pipeline-flow">↓</div>
              <div class="pipeline-step"><span class="tag">02 · MODEL</span><span>Embedding → BiLSTM → CRF</span></div>
              <div class="pipeline-flow">↓</div>
              <div class="pipeline-step"><span class="tag">03 · OUTPUT</span><span>Prediksi harakat</span></div>
              <div class="pipeline-caption">Hasil prediksi tetap perlu pemeriksaan linguistik.</div>
            </div>''')
    st.html('<div class="section-kicker">MULAI DENGAN MUDAH</div><h2 class="page-title" style="font-size:1.75rem">Tiga langkah, satu alur kerja.</h2>')
    cols = st.columns(3, gap="medium")
    cards = [
        ("01", "Siapkan teks", "Masukkan teks Arab melalui editor atau unggah file TXT dan CSV."),
        ("02", "Jalankan inferensi", "Model BiLSTM-CRF memprediksi label harakat berdasarkan konteks karakter."),
        ("03", "Tinjau & ekspor", "Periksa hasil, pahami status tiap baris, salin atau unduh file hasil."),
    ]
    for col, (num, title, desc) in zip(cols, cards):
        with col:
            with st.container(key=f"summary_tile_{num}"):
                st.html(f'<span class="step-num">{num}</span><div class="panel-title">{escape(title)}</div>'
                        f'<p class="panel-sub">{escape(desc)}</p>')
    st.html('<div class="callout">Model ini adalah alat bantu diakritisasi. '
            'Ketepatan harakat tidak dijamin untuk setiap kalimat.</div>')


def render_manual():
    with st.container(key="editor_panel"):
        top, side = st.columns([3.0, 1.0], vertical_alignment="center")
        with top:
            st.html('<div class="panel-title">Editor teks Arab</div>'
                    '<div class="panel-sub">Tempel atau ketik teks, lalu jalankan model.</div>')
        with side:
            st.caption("Teks berharakat akan diprediksi ulang.")
        text = st.text_area("Teks yang ingin diproses", key="manual_text", height=235,
                            placeholder="قال الشيخ الإمام العالم العلامة شمس الدين",
                            on_change=manual_modified)
        st.caption(f"{len(text)} karakter masukan · teks panjang akan dibagi otomatis menjadi segmen")
        buttons = st.columns([1.15, 1.1, 2.1], gap="small")
        with buttons[0]:
            process = st.button("✦ Proses teks", type="primary", disabled=not READY,
                                key="manual_submit", use_container_width=True)
        with buttons[1]:
            st.button("Bersihkan", key="manual_clear", on_click=clear_manual,
                      use_container_width=True)
        if process:
            st.session_state.manual_result = run_processing(engine.predict_long_text, text)
            st.session_state.manual_result_source = text
    result = st.session_state.manual_result
    if result and st.session_state.manual_result_source == st.session_state.get("manual_text", ""):
        if not result.get("success"):
            st.error(result.get("message", "Teks gagal diproses."))
            return
    else:
        result = None
    st.write("")
    main, diag = st.columns([2.55, 1], gap="medium", vertical_alignment="top")
    with main:
        with st.container(key="result_main"):
            st.html('<div class="section-kicker">KELUARAN SISTEM</div>'
                    '<div class="panel-title">Hasil diakritisasi</div>')
            if result:
                arabic_display(result["prediction"])
                st.caption("Prediksi model, bukan teks referensi yang telah diverifikasi.")
                st.html('<div class="mini-label" style="margin:.9rem 0 .4rem">SEBELUM DIPROSES</div>')
                st.html(f'<div class="arabic-before" dir="rtl">{escape(str(result.get("clean_text",text)))}</div>')
                dl, _ = st.columns([1.2, 1])
                with dl:
                    st.download_button("↓ Unduh hasil TXT", result["prediction"].encode("utf-8"),
                                       file_name="hasil_diakritisasi.txt", mime="text/plain; charset=utf-8",
                                       use_container_width=True, key="manual_download")
                with st.expander("Salin hasil prediksi"):
                    st.code(result["prediction"], language=None, wrap_lines=True)
                if result.get("had_diacritics"):
                    st.info("Harakat masukan dihapus sebelum model melakukan prediksi ulang.")
                show_unknowns(result)
            else:
                st.html('<div class="empty-placeholder">✦<br><b>Menunggu hasil prediksi</b>'
                        '<br>Masukkan teks Arab dan klik Proses teks.</div>')
    with diag:
        with st.container(key="result_side"):
            st.html('<div class="section-kicker">RINGKASAN</div>'
                    '<div class="panel-title">Info pemrosesan</div>')
            if result:
                st.metric("Karakter bersih", result.get("total_characters", "—"))
                st.metric("Huruf Arab", result.get("arabic_letters", "—"))
                st.metric("Segmen diproses", result.get("total_chunks", "—"))
                st.success("Pemrosesan selesai")
                lengths = result.get("chunk_lengths") or []
                if lengths:
                    with st.expander("Panjang tiap segmen"):
                        st.text(", ".join(str(x) for x in lengths))
            else:
                st.write("Statistik pemrosesan akan tampil setelah model menghasilkan prediksi.")
            st.caption("Tidak tersedia skor keyakinan per prediksi. Metrik model dapat dilihat pada Tentang Model.")


def plausible_text_columns(df):
    """Urutkan kolom kandidat; angka murni tidak jadi pilihan default."""
    detected = engine.detect_arabic_columns(df) or []
    arabic_cols = [item["column"] for item in detected if item.get("column") in df.columns]
    textlike = []
    for name in df.columns:
        if name in arabic_cols:
            continue
        if pd.api.types.is_numeric_dtype(df[name]):
            continue
        sample = df[name].dropna().astype(str).head(40)
        sample_text = " ".join(sample.tolist())
        if (any(c.isalpha() for c in sample_text)
                or re.search(r"teks|arab|text|kalimat|sentence|content", str(name), re.I)):
            textlike.append(name)
    trailing = [x for x in df.columns if x not in arabic_cols and x not in textlike]
    return arabic_cols + textlike + trailing, arabic_cols, textlike


def render_file():
    with st.container(key="file_input_box"):
        st.html('<div class="panel-title">Masukkan berkas sumber</div>'
                '<div class="panel-sub">TXT untuk baris teks, CSV untuk tabel. Maksimal 5 MB per berkas.</div>')
        uploader_key = f"upload_file_v7_{st.session_state.upload_generation}"
        st.file_uploader("Unggah TXT atau CSV", type=("txt", "csv"),
                         key=uploader_key, max_upload_size=5, disabled=not READY,
                         on_change=upload_modified, args=(uploader_key,))
        snapshot = st.session_state.uploaded_snapshot
        if snapshot is None:
            st.info("Pilih berkas untuk melihat pratinjau dan opsi pemrosesan.")
            return
        meta, remove = st.columns([3, 1], vertical_alignment="center")
        with meta:
            st.caption(f"Berkas: {snapshot['name']} · {snapshot['size'] / 1024:.1f} KB")
        with remove:
            st.button("Hapus berkas", key="clear_uploaded_file", on_click=clear_file,
                      use_container_width=True)
        if snapshot["data"] is None:
            st.error("Ukuran berkas melebihi batas 5 MB.")
            return
        extension = Path(snapshot["name"]).suffix.lower()
        text_column = None
        if extension == ".csv":
            try:
                preview = engine.read_csv_file(make_upload(snapshot))
                if not preview.get("success"):
                    st.error(preview.get("message", "CSV tidak dapat dibaca."))
                    return
                dataframe = preview["dataframe"]
                options, arabic_cols, textlike = plausible_text_columns(dataframe)
            except Exception as error:
                st.error(f"Gagal membuka berkas CSV: {error}")
                return
            st.html('<div class="mini-label" style="margin:.6rem 0">PRATINJAU TABEL</div>')
            st.dataframe(dataframe.head(8), hide_index=True, width="stretch")
            if not options:
                st.error("CSV tidak memiliki kolom yang dapat dipilih.")
                return
            preferred = arabic_cols[0] if arabic_cols else (textlike[0] if len(textlike) == 1 else None)
            initial_index = options.index(preferred) if preferred in options else None
            text_column = st.selectbox("Pilih kolom berisi teks yang hendak diproses",
                                       options=options, index=initial_index,
                                       placeholder="Pilih kolom teks...",
                                       key=f"csv_select_{snapshot['digest'][:16]}")
            if text_column is not None and pd.api.types.is_numeric_dtype(dataframe[text_column]):
                st.warning("Kolom yang dipilih terlihat berupa angka/ID. Pastikan ini memang kolom teks yang dimaksud.")
            elif not arabic_cols:
                st.info("Tidak terdeteksi teks Arab dalam pratinjau. Pilih kolom teks secara sadar; data Latin tetap dipertahankan.")
        else:
            try:
                decoded = engine.decode_text_bytes(snapshot["data"])
            except Exception as error:
                st.error(f"Berkas TXT tidak bisa dibaca: {error}")
                return
            if not decoded.get("success"):
                st.error(decoded.get("message", "Berkas TXT tidak valid."))
                return
            with st.expander("Lihat pratinjau TXT"):
                st.text(decoded["text"][:4000])
                st.caption("Pratinjau hanya 4.000 karakter; pemrosesan memakai seluruh isi berkas.")
        signature = (snapshot["name"], snapshot["digest"], text_column)
        disabled = (not READY) or (extension == ".csv" and text_column is None)
        click = st.button("✦ Proses berkas", key="process_uploaded_file_v7", type="primary",
                          disabled=disabled)
        if click:
            st.session_state.file_result = run_processing(engine.process_uploaded_file,
                                                           make_upload(snapshot), text_column=text_column)
            st.session_state.file_result_signature = signature
    result = st.session_state.file_result
    if not result or st.session_state.file_result_signature != signature:
        return
    st.write("")
    with st.container(key="file_results"):
        if not result.get("success"):
            st.error(result.get("message", "Berkas gagal diproses."))
            return
        st.html('<div class="section-kicker">HASIL PEMROSESAN BERKAS</div>'
                '<div class="panel-title">Pratinjau keluaran</div>')
        status = result.get("status_summary") or {}
        if status and int(status.get("berhasil", 0)) == 0:
            st.info("Berkas terbaca, tetapi tidak ada baris yang menghasilkan prediksi Arab. Baris dipertahankan sesuai statusnya.")
        else:
            st.success(result.get("message", "Berkas selesai diproses."))
        if status:
            file_status_table(status)
        for warning in result.get("warnings") or []:
            st.warning(f"Baris {warning.get('line','?')}: {warning.get('note','Perlu diperiksa')}")
        show_unknowns(result)
        if result["input_type"] == "csv":
            st.dataframe(result["dataframe"], hide_index=True, width="stretch")
        else:
            arabic_display(result["prediction"])
            with st.expander("Salin hasil TXT"):
                st.code(result["prediction"], language=None, wrap_lines=True)
        st.download_button("↓ Unduh berkas hasil", result["download_bytes"],
                           file_name=result["output_filename"],
                           mime="text/csv; charset=utf-8" if result["input_type"] == "csv" else "text/plain; charset=utf-8",
                           key="file_download_v7")
        st.caption("Prediksi otomatis dapat mengandung kesalahan harakat.")


def render_studio():
    section_intro("STUDIO / 01", "Ruang kerja diakritisasi",
                  "Editor dan hasil dirancang sebagai ruang kerja sederhana. "
                  "Pilih sumber teks, jalankan prediksi, lalu periksa keluarannya.")
    if not READY:
        st.error("Model belum siap: " + str(health.get("message", "Tidak ada keterangan.")))
        return
    with st.container(key="process_entry"):
        st.radio("Pilih sumber masukan", ("Teks langsung", "Unggah berkas"),
                 key="mode", horizontal=True)
    st.write("")
    if st.session_state.mode == "Teks langsung":
        render_manual()
    else:
        render_file()


def render_examples():
    section_intro("PERPUSTAKAAN / 02", "Koleksi contoh teks",
                  "Tiga contoh Arab gundul untuk mencoba fungsi aplikasi. "
                  "Contoh bukan referensi kebenaran prediksi.")
    cols = st.columns(3, gap="medium")
    for i, (title, sample) in enumerate(EXAMPLES, start=1):
        with cols[i - 1]:
            with st.container(key=f"sample_card_{i}"):
                st.html(f'<span class="step-num">CONTOH {i:02d}</span>'
                        f'<div class="panel-title">{escape(title)}</div>')
                arabic_display(sample, mini=True)
                st.write("")
                st.button("Gunakan di ruang kerja →", key=f"sample_use_{i}",
                          on_click=goto, args=("Diakritisasi", sample),
                          use_container_width=True)
    st.html('<div class="callout">Setiap contoh akan disalin ke editor. '
            'Prediksi dijalankan hanya setelah Anda menekan tombol proses.</div>')


def pct(value):
    try:
        number = float(value)
        if not isfinite(number) or number < 0 or number > 100:
            return "Tidak tersedia"
        return f"{number:.2f}%".replace(".", ",")
    except (ValueError, TypeError):
        return "Tidak tersedia"


def render_about():
    section_intro("RISET / 03", "Di balik model",
                  "Informasi penelitian, arsitektur model, hasil evaluasi, dan batas penggunaan sistem.")
    with st.container(key="about_pipeline"):
        st.html('''<div class="section-kicker" style="color:#8ee3d4">ARSITEKTUR PEMODELAN</div>
           <div class="panel-title">Dari karakter menuju urutan harakat</div>
           <div class="route-chain">
             <span class="route-chip">Karakter</span><span class="route-arrow">→</span>
             <span class="route-chip">Embedding</span><span class="route-arrow">→</span>
             <span class="route-chip">BiLSTM</span><span class="route-arrow">→</span>
             <span class="route-chip">Linear</span><span class="route-arrow">→</span>
             <span class="route-chip">CRF</span><span class="route-arrow">→</span>
             <span class="route-chip">Rekonstruksi harakat</span>
           </div>
           <div class="pipeline-caption">Pretraining pada Tashkeela, fine-tuning pada Kitab Fathul Qorib. Aplikasi menggunakan model fine-tuned.</div>''')
    st.write("")
    st.html('<div class="section-kicker">HASIL EVALUASI</div><div class="panel-title">Metrik pada data uji penelitian</div>')
    fine = metrics.get("fine_tuned") if isinstance(metrics, dict) else None
    if isinstance(fine, dict):
        cs = st.columns(3)
        for col, label, key in zip(cs, ("Accuracy", "Diacritic Error Rate", "Word Error Rate"),
                                   ("accuracy_percent", "der_percent", "wer_percent")):
            with col:
                with st.container(key="metric_model"):
                    st.metric(label, pct(fine.get(key)))
        st.caption("Angka berasal dari berkas evaluasi, bukan skor kepercayaan hasil per teks.")
    else:
        st.info("Metrik evaluasi belum dapat dimuat dari backend.")
    left, right = st.columns([1.1, 1], gap="medium")
    with left:
        with st.container(key="about_summary"):
            st.html('<div class="panel-title">Konfigurasi aktif</div>')
            fields = (("Checkpoint epoch", "checkpoint_epoch"),
                      ("Ukuran kosakata", "vocab_size"),
                      ("Jumlah label", "num_labels"),
                      ("Maksimum segmen", "max_len"),
                      ("Perangkat inferensi", "device"))
            table = pd.DataFrame([{"Parameter": title, "Nilai": str(model_info.get(field, "Tidak tersedia"))}
                                  for title, field in fields])
            st.dataframe(table, hide_index=True, width="stretch")
            baseline = metrics.get("baseline") if isinstance(metrics, dict) else None
            if isinstance(fine, dict) and isinstance(baseline, dict):
                with st.expander("Lihat perbandingan baseline dan fine-tuned"):
                    data = []
                    for label, item in (("Baseline", baseline), ("Fine-tuned", fine)):
                        data.append({"Model": label,
                                     "Accuracy": pct(item.get("accuracy_percent")),
                                     "DER": pct(item.get("der_percent")),
                                     "WER": pct(item.get("wer_percent"))})
                    st.dataframe(pd.DataFrame(data), hide_index=True, width="stretch")
    with right:
        with st.container(key="tips_panel"):
            st.html('<div class="panel-title">Batasan penggunaan</div>')
            st.markdown(
                "- Diakritisasi adalah **prediksi**, bukan validasi nahwu atau sharaf.\n"
                "- Hasil evaluasi berasal dari data uji penelitian, bukan semua kitab Arab.\n"
                "- Teks panjang dibagi menjadi segmen sebelum direkonstruksi.\n"
                "- Karakter di luar kosakata dapat dipetakan ke token tidak dikenal.\n"
                "- Berkas campuran Arab–Latin dapat dipertahankan tanpa prediksi sesuai aturan backend."
            )


render_header()
current = st.session_state.route
if current == "Beranda":
    render_home()
elif current == "Diakritisasi":
    render_studio()
elif current == "Contoh Teks":
    render_examples()
elif current == "Tentang Model":
    render_about()
st.html('<footer>UNIVERSITAS MALIKUSSALEH · PENELITIAN DIAKRITISASI TEKS ARAB · BiLSTM-CRF<br>'
        'Antarmuka prototipe v7 · Prediksi otomatis memerlukan pemeriksaan ulang.</footer>')