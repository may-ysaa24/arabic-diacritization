
"""UI akademik BiLSTM-CRF. Backend asli diimpor tanpa modifikasi.

Sumber notebook: 07_build_streamlit_ui_akademik.ipynb, Cell 4.
Perubahan tampilan tidak mengganti hasil atau aturan inferensi backend.
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
    initial_sidebar_state="auto",
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
  color-scheme: light;
  --ink:#172941;
  --ink-2:#32455c;
  --muted:#697b8c;
  --navy:#10263c;
  --navy-light:#183850;
  --teal:#0b7775;
  --teal-deep:#075e5b;
  --teal-pale:#e9f5f3;
  --gold:#d6ad70;
  --canvas:#f5f7f8;
  --paper:#fff;
  --border:#e0e7e9;
  --arabic:"Noto Naskh Arabic","Amiri","Scheherazade New","Traditional Arabic","DejaVu Sans",serif;
  --sans:"Inter","Segoe UI",system-ui,Arial,sans-serif;
  --serif:"Cambria","Iowan Old Style","Georgia",serif;
}
html,body,[class*="css"] {font-family:var(--sans)}
.stApp {background:var(--canvas);color:var(--ink);font-family:var(--sans)}
[data-testid="stHeader"] {background:transparent}
.stMainBlockContainer {max-width:1370px;padding:3.2rem 3rem 3rem}
[data-testid="stSidebar"] {
  background:var(--navy);
  border-right:1px solid #19384d;
}
[data-testid="stSidebar"] > div:first-child {padding:2.15rem 1.1rem 1rem}
[data-testid="stSidebar"] [data-testid="stImage"] {margin:.25rem 0 .55rem}
.brand-kicker,.eyebrow {
  color:var(--teal);
  font-weight:750;
  font-size:.71rem;
  line-height:1.45;
  letter-spacing:.13em;
  text-transform:uppercase;
  margin:0 0 .65rem;
}
.brand-kicker {color:#a6cfcd;font-size:.68rem;margin-top:.35rem}
.brand-rule {width:40px;height:2px;border-radius:3px;background:var(--gold);margin:1rem 0}
.brand-title {font:700 1.55rem/1.2 var(--serif);color:white;letter-spacing:-.015em}
.brand-subtitle {font-size:.84rem;line-height:1.65;color:#b8c9d4;margin:.55rem 0 2.15rem}
.st-key-nav [role="radiogroup"] {gap:.35rem}
.st-key-nav [role="radiogroup"] > label {
  min-height:48px;width:100%;margin:0;border-radius:10px;
  padding:.62rem .78rem;border:1px solid transparent;
  transition:background-color .17s,border-color .17s;
}
.st-key-nav [role="radiogroup"] > label p {font-size:.88rem;font-weight:630;color:#c4d5dd}
.st-key-nav [role="radiogroup"] > label:has(input:checked) {background:#214758;border-color:#376876}
.st-key-nav [role="radiogroup"] > label:has(input:checked) p {color:white}
.st-key-nav [role="radiogroup"] > label:hover {background:#203d50}
.st-key-nav [role="radiogroup"] > label [data-testid="stMarkdownContainer"] {color:inherit}
.st-key-nav [role="radiogroup"] > label [data-testid="stWidgetLabel"] {color:#d7e5ea}
.sidebar-note {border-top:1px solid #365063;margin:2rem .2rem 0;padding-top:1.25rem;color:#c5d4de}
.sidebar-note p {font-size:.76rem;line-height:1.8;color:#aebfcc;margin:.6rem 0}
.status-line {display:flex;align-items:center;gap:.6rem;font-size:.81rem;font-weight:650;color:#edf8f7}
.status-dot {display:inline-block;width:9px;height:9px;border-radius:50%;background:#ea9e82;box-shadow:0 0 0 4px #d86f4533}
.status-dot.ready {background:#59c9a6;box-shadow:0 0 0 4px #59c9a622}
[data-testid="stSidebar"] [data-testid="stExpander"] {color:#dde9ef}
.topline {
  display:flex;align-items:center;justify-content:space-between;gap:1rem;
  flex-wrap:wrap;color:var(--muted);font-size:.78rem;line-height:1.5;
  border-bottom:1px solid var(--border);margin-bottom:1.65rem;padding-bottom:1rem;
}
.topline strong {font-size:.73rem;letter-spacing:.13em;color:var(--teal);font-weight:800}
.page-heading {padding:.2rem 0 1.2rem}
.page-heading h1 {font:700 clamp(1.8rem,3vw,2.5rem)/1.18 var(--serif);letter-spacing:-.035em;color:var(--ink);margin:.2rem 0 .6rem}
.page-heading p {color:var(--muted);font-size:.96rem;line-height:1.76;max-width:800px;margin:0}
.st-key-home_hero {
  background:var(--navy);border:1px solid #1d4356;border-radius:22px;
  padding:2.4rem 2.15rem 1.65rem;position:relative;overflow:hidden;
  box-shadow:0 15px 42px #18304812;
}
.st-key-home_hero:before {
  content:"";position:absolute;inset:0 auto auto 0;height:4px;width:100%;
  background:linear-gradient(90deg,var(--gold),#6caba2 50%,#1f5465);
}
.st-key-home_hero [data-testid="stHorizontalBlock"] {position:relative}
.hero .eyebrow {color:#92c8c7;font-size:.72rem}
.hero h1 {
  font:700 clamp(2.55rem,4vw,4.25rem)/1.08 var(--serif);
  letter-spacing:-.045em;margin:.85rem 0 .7rem;color:#fff;max-width:740px;
}
.hero .research-subtitle {
  font-size:1.05rem;font-weight:650;line-height:1.6;color:#aee1d7;margin-bottom:.9rem;
}
.hero p {color:#c4d6df;font-size:.95rem;line-height:1.82;max-width:600px;margin:0 0 1.2rem}
.hero-note {font-size:.77rem;color:#bad4dc;margin-top:.1rem;line-height:1.7}
.research-card {
  min-height:265px;padding:1.55rem;border:1px solid #548079;
  border-radius:16px;background:#f5f9f7;
  display:flex;flex-direction:column;justify-content:space-between;
  box-shadow:0 22px 60px #00000018;
}
.research-card .card-kicker {font-size:.72rem;letter-spacing:.13em;font-weight:800;color:var(--teal)}
.research-card .arabic-text {font-size:30px;line-height:2.15;color:var(--ink);padding:.6rem 0;min-height:120px}
.research-card .card-caption {font-size:.78rem;color:var(--muted);line-height:1.7}
.research-card .gold-line {height:3px;width:45px;border-radius:3px;background:var(--gold);margin-top:1rem}
.st-key-home_hero [data-testid="stBaseButton-primary"] {
  color:var(--navy)!important;background:#d6eadf!important;border-color:#d6eadf!important;
}
.st-key-home_hero [data-testid="stBaseButton-secondary"] {
  color:white!important;background:#ffffff19!important;border-color:#ffffff40!important;
}
.home-section {display:flex;align-items:end;justify-content:space-between;gap:1rem;margin:2.1rem 0 .95rem}
.home-section h2 {font:700 1.65rem/1.3 var(--serif);color:var(--ink);margin:0}
.home-section p {font-size:.82rem;color:var(--muted);margin:0}
.guide-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem;margin-bottom:1.5rem}
.guide-item {background:var(--paper);padding:1.35rem 1.25rem;border:1px solid var(--border);border-radius:14px;min-height:155px}
.guide-item .number {font-size:.71rem;letter-spacing:.11em;font-weight:750;color:var(--teal);margin-bottom:.7rem}
.guide-item h3 {font-size:1rem;color:var(--ink);font-weight:700;margin:0 0 .45rem}
.guide-item p {font-size:.83rem;line-height:1.7;color:var(--muted);margin:0}
.evidence-strip {display:grid;grid-template-columns:repeat(3,1fr);gap:.7rem;margin:1rem 0}
.evidence-card {background:#fff;padding:1rem;border:1px solid var(--border);border-radius:12px}
.evidence-number {font:700 1.55rem/1.3 var(--serif);color:var(--ink)}
.evidence-label {font-size:.74rem;color:var(--muted);line-height:1.55;margin-top:.25rem}
.work-label {color:var(--teal);font-size:.72rem;letter-spacing:.12em;font-weight:800;margin:0 0 .8rem}
.arabic-text {
  direction:rtl;unicode-bidi:plaintext;text-align:right;
  font-family:var(--arabic);font-size:28px;line-height:2.1;
  white-space:pre-wrap;overflow-wrap:anywhere;word-break:normal;letter-spacing:normal;
}
.arabic-result {
  padding:1.25rem 1.45rem;border:1px solid #c8deda;border-radius:13px;
  min-height:230px;max-height:510px;overflow-y:auto;
  background:#f0f8f6;box-shadow:inset 0 1px 4px #095d4d06;
}
.empty-output {
  border:1.5px dashed #b8c9d1;background:#fff;min-height:230px;border-radius:13px;
  display:flex;flex-direction:column;justify-content:center;align-items:flex-start;
  padding:2rem;color:var(--muted);
}
.empty-output strong {color:var(--ink);font-size:1.08rem;margin-bottom:.55rem}
.empty-output p {max-width:360px;font-size:.85rem;line-height:1.8;margin:0}
.st-key-workspace {margin-top:.45rem}
.st-key-workspace [data-testid="stColumn"] {min-width:0}
.st-key-arabic_input textarea {
  direction:rtl;text-align:right;unicode-bidi:plaintext;
  font-family:var(--arabic);font-size:26px;line-height:2.1;letter-spacing:normal;
  border:1px solid #cad7df;border-radius:12px;padding:1rem;background:#fff;
}
.st-key-file_arabic textarea {direction:rtl;text-align:right;font:24px/2 var(--arabic)}
.st-key-arabic_copy pre,.st-key-arabic_copy code {direction:rtl;unicode-bidi:plaintext;text-align:right;font:23px/2 var(--arabic)}
.st-key-workspace [data-testid="stTextArea"] textarea:focus {border-color:var(--teal)}
[data-testid="stTabs"] [role="tablist"] {border-bottom:1px solid var(--border);gap:.55rem}
[data-testid="stTabs"] button[role="tab"] {font-weight:650;padding:.75rem 1.15rem}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {color:var(--teal);border-color:var(--teal)}
[data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] {
  border-color:var(--border);border-radius:12px;
}
[data-testid="stFileUploader"] section {border-color:#bad4d8;border-radius:12px;background:#fff}
[data-testid="stMetric"] {background:white;border:1px solid var(--border);border-radius:13px;padding:.85rem 1rem}
[data-testid="stMetricLabel"] p {color:var(--muted);font-size:.84rem}
[data-testid="stMetricValue"] {color:var(--ink);font-weight:750}
[data-testid="stBaseButton-primary"] {background:var(--teal);border-color:var(--teal);color:#fff;border-radius:10px}
[data-testid="stBaseButton-primary"]:hover {background:var(--teal-deep);border-color:var(--teal-deep);color:#fff}
[data-testid="stBaseButton-secondary"],[data-testid="stDownloadButton"] button {border-radius:10px}
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button {min-height:43px;font-weight:650;transition:border-color .16s,background .16s}
[data-testid="stAlert"] {border-radius:11px}
.footer-note {border-top:1px solid var(--border);margin:2.6rem 0 .2rem;padding:1.1rem 0;color:var(--muted);font-size:.76rem;line-height:1.8}
button:focus-visible,a:focus-visible,textarea:focus-visible {outline:3px solid #2a9798!important;outline-offset:2px}
@media(max-width:1050px){
  .stMainBlockContainer {padding:3rem 1.6rem 2rem}
  .st-key-home_hero {padding:2rem 1.45rem 1.35rem}
}
@media(max-width:780px){
  .stMainBlockContainer {padding:4.6rem 1.1rem 1.5rem}
  .st-key-home_hero [data-testid="stHorizontalBlock"],
  .st-key-workspace [data-testid="stHorizontalBlock"] {flex-wrap:wrap}
  .st-key-home_hero [data-testid="stColumn"],
  .st-key-workspace [data-testid="stColumn"] {flex:1 1 100%;min-width:100%}
  .hero h1 {font-size:clamp(2.15rem,8vw,3rem)}
  .guide-grid {grid-template-columns:1fr;gap:.65rem}
  .home-section {align-items:flex-start;flex-direction:column}
  .evidence-strip {grid-template-columns:repeat(3,minmax(0,1fr))}
}
@media(max-width:520px){
  .stMainBlockContainer {padding:4.4rem .8rem 1.1rem}
  .st-key-home_hero {padding:1.45rem 1rem}
  .hero h1 {font-size:2.1rem}
  .research-card {min-height:180px}
  .arabic-text {font-size:24px}
  .st-key-arabic_input textarea {font-size:23px}
  .evidence-strip {grid-template-columns:1fr}
  .topline {font-size:.7rem}
}
@media(prefers-reduced-motion:reduce){
  *,*:before,*:after {scroll-behavior:auto!important;animation:none!important;transition:none!important}
}
@media print{
  [data-testid="stSidebar"],[data-testid="stHeader"],[data-testid="stToolbar"] {display:none!important}
  .stApp{background:white}
  .stMainBlockContainer{max-width:none;padding:0}
  .arabic-result{max-height:none;overflow:visible}
}
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
    if not result.get("success"):
        st.error(result.get("message", "Pemrosesan belum berhasil."))
        return
    arabic(result["prediction"], result=True)
    st.caption("Prediksi otomatis; periksa kembali ketepatan harakat sebelum digunakan.")
    unknown_warning(result)
    if result.get("had_diacritics"):
        st.info("Harakat pada masukan dihapus sebelum prediksi ulang.")
    st.download_button(
        "Unduh hasil TXT", result["prediction"].encode("utf-8"),
        file_name="hasil_diakritisasi.txt", mime="text/plain; charset=utf-8",
        key=f"download_{key}", icon=":material/download:",
    )
    with st.expander("Salin hasil teks"):
        st.caption("Gunakan ikon salin di sudut kotak berikut. Isi sama dengan hasil prediksi.")
        with st.container(key="arabic_copy"):
            st.code(result["prediction"], language=None, wrap_lines=True)
    with st.expander("Detail pemrosesan"):
        st.write({
            "Karakter masukan bersih": result.get("total_characters"),
            "Huruf Arab": result.get("arabic_letters"),
            "Jumlah segmen": result.get("total_chunks"),
            "Panjang tiap segmen": result.get("chunk_lengths"),
        })


def render_home():
    with st.container(key="home_hero"):
        introduction, sample = st.columns([1.55, 1], gap="large", vertical_alignment="center")
        with introduction:
            st.html(
                '<section class="hero">'
                '<div class="eyebrow">Sistem penelitian NLP bahasa Arab</div>'
                '<h1>Diakritisasi Teks Arab Gundul</h1>'
                '<div class="research-subtitle">pada Kitab Fathul Qorib menggunakan BiLSTM-CRF</div>'
                '<p>Masukkan teks Arab tanpa harakat untuk memperoleh prediksi harakat secara otomatis '
                'sebagai alat bantu pembacaan.</p>'
                '</section>'
            )
            with st.container(key="home_actions", horizontal=True):
                st.button("Mulai Diakritisasi", type="primary", icon=":material/arrow_forward:",
                          key="home_cta", on_click=navigate, args=("Diakritisasi",))
                st.button("Lihat Contoh", key="home_examples", on_click=navigate,
                          args=("Contoh Teks",))
            st.html('<div class="hero-note">Mendukung masukan langsung serta berkas TXT dan CSV.</div>')
        with sample:
            st.html(
                '<div class="research-card">'
                '<div><div class="card-kicker">CONTOH MASUKAN · TANPA HARAKAT</div>'
                f'<div class="arabic-text" lang="ar" dir="rtl">{escape(EXAMPLES[0])}</div>'
                '<div class="card-caption">Teks contoh berasal dari program. Hasil diakritisasi '
                'ditampilkan setelah model memproses masukan.</div></div>'
                '<div class="gold-line"></div></div>'
            )
    st.html(
        '<div class="home-section"><h2>Cara menggunakan sistem</h2>'
        '<p>Tiga langkah utama</p></div>'
        '<div class="guide-grid">'
        '<div class="guide-item"><div class="number">01 · MASUKAN</div>'
        '<h3>Masukkan teks Arab</h3><p>Ketik atau tempel teks, atau unggah berkas TXT dan CSV.</p></div>'
        '<div class="guide-item"><div class="number">02 · PROSES</div>'
        '<h3>Jalankan diakritisasi</h3><p>Model BiLSTM-CRF memprediksi label harakat pada setiap karakter.</p></div>'
        '<div class="guide-item"><div class="number">03 · HASIL</div>'
        '<h3>Periksa hasil prediksi</h3><p>Tinjau teks berharakat, kemudian salin atau unduh hasilnya.</p></div>'
        '</div>'
    )
    st.html('<div class="evidence-strip">'
        '<div class="evidence-card"><div class="evidence-number">BiLSTM–CRF</div><div class="evidence-label">Model berbasiskan urutan karakter</div></div>'
        '<div class="evidence-card"><div class="evidence-number">TXT / CSV</div><div class="evidence-label">Input dan unduhan dokumen</div></div>'
        '<div class="evidence-card"><div class="evidence-number">RTL</div><div class="evidence-label">Ruang baca teks Arab yang nyaman</div></div>'
        '</div>')
    st.caption("Hasil diakritisasi merupakan prediksi model dan masih perlu diperiksa kembali oleh pengguna.")


def render_manual():
    if "_manual_input" not in st.session_state:
        st.session_state["_manual_input"] = st.session_state.manual_input
    with st.container(key="workspace"):
        left, right = st.columns([1, 1], gap="large")
        with left:
            st.html('<div class="work-label">01 / MASUKAN</div>')
            with st.container(key="arabic_input"):
                text = st.text_area(
                    "Teks Arab", key="_manual_input", height=250,
                    placeholder=EXAMPLES[0], on_change=manual_changed,
                )
            st.caption("Teks Arab dibaca dari kanan ke kiri. Harakat pada masukan akan dihapus dan diprediksi ulang.")
            st.caption(f"Panjang masukan: {len(text):,} karakter".replace(",", "."))
            with st.container(horizontal=True):
                process = st.button("Proses Diakritisasi", key="process_manual", type="primary",
                                    disabled=not READY, icon=":material/auto_stories:")
                st.button("Bersihkan", key="reset_manual", on_click=reset_manual)
            if process:
                st.session_state.manual_input = text
                if not text.strip():
                    st.session_state.manual_result = {
                        "success": False,
                        "message": "Masukkan teks Arab terlebih dahulu sebelum memproses.",
                    }
                else:
                    st.session_state.manual_result = processing_call(engine.predict_long_text, text)
                st.session_state.manual_result_input = text
            with st.expander("Panduan masukan"):
                st.write("Gunakan teks Arab tanpa campuran huruf Latin. "
                         "Teks panjang dibagi otomatis menjadi segmen maksimal 300 karakter, "
                         "lalu hasilnya digabungkan kembali sesuai urutan.")
        with right:
            st.html('<div class="work-label">02 / HASIL PREDIKSI</div>')
            result = st.session_state.manual_result
            if result and st.session_state.manual_result_input == text:
                show_prediction(result, "manual")
            else:
                empty_output()


def render_file_result(result):
    if not result.get("success"):
        st.error(result.get("message", "Berkas belum berhasil diproses."))
        return
    st.success(result["message"])
    summary = result.get("status_summary") or {}
    if summary:
        with st.expander("Ringkasan status pemrosesan", expanded=True):
            labels = {"berhasil": "Diprediksi", "kosong": "Kosong; dipertahankan",
                      "non_arab": "Non-Arab; dipertahankan", "campuran": "Arab–Latin; dipertahankan",
                      "gagal": "Gagal diproses"}
            st.dataframe(pd.DataFrame([
                {"Status": labels.get(name, name), "Jumlah": count}
                for name, count in summary.items()
            ]), hide_index=True, width="stretch")
    unknown_warning(result)
    for warning in result.get("warnings") or []:
        st.warning(f"Baris {warning['line']}: {warning['note']}")
    if result["input_type"] == "txt":
        arabic(result["prediction"], result=True)
        with st.expander("Salin hasil TXT"):
            with st.container(key="file_arabic"):
                st.text_area("Teks hasil TXT", value=result["prediction"], height=220,
                             key="_file_text_output", disabled=True)
        mime = "text/plain; charset=utf-8"
    else:
        st.dataframe(result["dataframe"], hide_index=True, width="stretch")
        mime = "text/csv; charset=utf-8"
    st.download_button("Unduh hasil " + result["input_type"].upper(),
                       result["download_bytes"], file_name=result["output_filename"], mime=mime,
                       key="download_file", type="primary", icon=":material/download:")
    st.caption("Unduhan memuat hasil pemrosesan berkas. Periksa kembali ketepatan harakat.")


def render_file():
    st.write("Unggah teks Arab sebagai berkas, periksa isinya, lalu jalankan prediksi.")
    st.caption("Format TXT atau CSV, maksimal 5 MB. Baris kosong dan non-Arab dipertahankan.")
    widget_key = f"_upload_{st.session_state.uploader_generation}"
    st.file_uploader("Pilih berkas TXT atau CSV", type=["txt", "csv"], key=widget_key,
                     max_upload_size=5, disabled=not READY,
                     on_change=upload_changed, args=(widget_key,))
    snapshot = st.session_state.upload_snapshot
    if snapshot is None:
        st.caption("Belum ada berkas yang dipilih.")
        return
    st.text(f"Berkas aktif: {snapshot['name']} · {snapshot['size'] / 1024:.1f} KB")
    st.button("Hapus berkas", key="reset_file", on_click=reset_file)
    if snapshot["data"] is None:
        st.error("Ukuran berkas melebihi batas 5 MB. Pilih berkas yang lebih kecil.")
        return
    if not READY:
        st.info("Model belum siap; pemrosesan berkas dinonaktifkan.")
        return
    suffix = Path(snapshot["name"]).suffix.lower()
    selected_column = None
    if suffix == ".csv":
        try:
            preview = engine.read_csv_file(uploaded_copy(snapshot))
            if not preview["success"]:
                st.error(preview["message"])
                return
            dataframe = preview["dataframe"]
            candidates = engine.detect_arabic_columns(dataframe)
            names = [item["column"] for item in candidates]
            options = names + [col for col in dataframe.columns if col not in names]
            if not options:
                st.error("CSV tidak memiliki kolom yang dapat dipilih.")
                return
            with st.expander("Pratinjau CSV", expanded=True):
                st.dataframe(dataframe.head(10), hide_index=True, width="stretch")
            if st.session_state.csv_column not in options:
                st.session_state.csv_column = options[0]
            st.session_state["_csv_column"] = st.session_state.csv_column
            selected_column = st.selectbox("Pilih kolom teks Arab", options,
                                            key="_csv_column", on_change=column_changed)
            if names:
                st.caption("Kolom berpotensi mengandung teks Arab: " + ", ".join(map(str, names)))
        except Exception as error:
            st.error(f"Berkas tidak dapat dibaca: {error}")
            return
    else:
        # Pembacaan pratinjau tetap menggunakan utilitas backend asli.
        decoded = engine.decode_text_bytes(snapshot["data"])
        if not decoded["success"]:
            st.error(decoded["message"])
            return
        with st.expander("Pratinjau TXT"):
            st.text(decoded["text"][:4000])
            st.caption("Pratinjau dibatasi 4.000 karakter; pemrosesan menggunakan seluruh berkas.")
    signature = (snapshot["name"], snapshot["digest"], selected_column)
    if st.button("Proses Berkas", type="primary", key="process_file", disabled=not READY):
        st.session_state.file_result = processing_call(
            engine.process_uploaded_file, uploaded_copy(snapshot), text_column=selected_column,
        )
        st.session_state.file_result_signature = signature
    result = st.session_state.file_result
    if result and st.session_state.file_result_signature == signature:
        st.divider()
        render_file_result(result)


def render_diakritisasi():
    heading("Area kerja", "Diakritisasi Teks Arab",
            "Masukkan teks secara langsung atau unggah berkas. Tinjau hasil prediksi sebelum digunakan.")
    manual_tab, file_tab = st.tabs(["Input Manual", "Unggah TXT / CSV"])
    with manual_tab:
        render_manual()
    with file_tab:
        render_file()


def render_examples():
    heading("Contoh penggunaan", "Contoh Teks Arab",
            "Contoh masukan dari program asli untuk mencoba alur diakritisasi. "
            "Contoh ini bukan teks referensi berharakat atau bukti akurasi model.")
    for index, text in enumerate(EXAMPLES, start=1):
        with st.container(border=True, key=f"example_panel_{index}"):
            st.caption(f"CONTOH {index:02d} · TANPA HARAKAT")
            arabic(text)
            with st.container(horizontal=True):
                st.button("Gunakan di area kerja", key=f"use_example_{index}",
                          on_click=navigate, args=("Diakritisasi", text))
                process = st.button("Prediksi contoh", key=f"process_example_{index}", disabled=not READY)
            if process:
                st.session_state.example_results[index] = processing_call(engine.predict_long_text, text)
            result = st.session_state.example_results.get(index)
            if result:
                if result.get("success"):
                    st.caption("HASIL PREDIKSI MODEL — BUKAN REFERENSI")
                    arabic(result["prediction"], result=True)
                    unknown_warning(result)
                else:
                    st.error(result.get("message", "Pemrosesan belum berhasil."))


def format_percent(value):
    try:
        numeric = float(value)
        if not isfinite(numeric) or not 0 <= numeric <= 100:
            return "Tidak tersedia"
        return f"{numeric:.2f}".replace(".", ",") + "%"
    except (TypeError, ValueError):
        return "Tidak tersedia"


def render_about():
    heading("Informasi penelitian", "Tentang Model",
            "Ruang lingkup, konfigurasi, dan hasil evaluasi model yang digunakan dalam aplikasi.")
    st.subheader("Ruang lingkup", anchor=False)
    st.write("Aplikasi ini merupakan implementasi penelitian diakritisasi otomatis teks Arab gundul "
             "pada Kitab Fathul Qorib menggunakan BiLSTM-CRF. Korpus Tashkeela digunakan untuk "
             "pretraining, kemudian model disesuaikan dengan data Kitab Fathul Qorib melalui fine-tuning. "
             "Inferensi aplikasi menggunakan model fine-tuned.")
    st.write("Embedding membentuk representasi karakter, BiLSTM mempelajari konteks dari dua arah, "
             "lapisan linear menghasilkan skor label, dan CRF menentukan urutan label harakat. "
             "Sistem kemudian merekonstruksi teks berharakat dari label hasil prediksi.")
    with st.expander("Konfigurasi model aktif", expanded=False):
        if not model_info:
            st.info("Konfigurasi belum tersedia karena model belum berhasil dimuat.")
        else:
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
            ]), hide_index=True, width="stretch")
    st.divider()
    st.subheader("Hasil evaluasi pada data uji", anchor=False)
    st.caption("Kitab Fathul Qorib · Metrik evaluasi tersimpan, bukan tingkat keyakinan untuk setiap prediksi.")
    fine = metrics_data.get("fine_tuned") if isinstance(metrics_data, dict) else None
    if not isinstance(fine, dict):
        st.info("Metrik evaluasi belum tersedia.")
    else:
        columns = st.columns(3)
        for col, label, key in zip(columns, ["Accuracy", "DER", "WER"],
                                   ["accuracy_percent", "der_percent", "wer_percent"]):
            col.metric(label, format_percent(fine.get(key)))
        st.caption("Accuracy: persentase karakter yang benar, termasuk spasi dan tanda baca. "
                   "DER: kesalahan diakritik pada huruf Arab. "
                   "WER: kata Arab dengan sedikitnya satu kesalahan.")
        baseline = metrics_data.get("baseline")
        if isinstance(baseline, dict):
            with st.expander("Perbandingan baseline dan fine-tuned"):
                st.dataframe(pd.DataFrame([
                    {"Model": name, "Accuracy": format_percent(data.get("accuracy_percent")),
                     "DER": format_percent(data.get("der_percent")), "WER": format_percent(data.get("wer_percent"))}
                    for name, data in [("Baseline", baseline), ("Fine-tuned", fine)]
                ]), hide_index=True, width="stretch")
    st.divider()
    st.subheader("Keterbatasan sistem", anchor=False)
    st.markdown(
        "- Hasil diakritisasi bersifat prediktif dan masih dapat mengandung kesalahan.\n"
        "- Evaluasi penelitian menggunakan data uji Kitab Fathul Qorib; hasilnya tidak otomatis "
        "mewakili semua jenis teks Arab.\n"
        "- Karakter di luar kosakata dipetakan ke `<UNK>` dan ditampilkan dalam peringatan hasil.\n"
        "- Teks panjang diproses per segmen maksimal 300 karakter.\n"
        "- Sistem tidak menggantikan pemeriksaan pembacaan, nahwu, atau sharaf oleh pengguna."
    )


with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=62)
    st.html('<div class="brand-kicker">Universitas Malikussaleh</div>'
            '<div class="brand-rule"></div>'
            '<div class="brand-title">Sistem Diakritisasi<br>Teks Arab</div>'
            '<div class="brand-subtitle">Kitab Fathul Qorib<br>Model BiLSTM-CRF</div>')
    with st.container(key="nav"):
        st.radio("Navigasi utama", PAGES, key="page", label_visibility="collapsed")
    status_label = "Model siap digunakan" if READY else "Model belum tersedia"
    status_class = "status-dot ready" if READY else "status-dot"
    st.html(f'<div class="sidebar-note"><div class="status-line"><span class="{status_class}"></span>'
            f'{escape(status_label)}</div><p>Alat bantu pembacaan teks Arab.<br>'
            'Hasil prediksi perlu diperiksa kembali.</p></div>')
    if not READY:
        with st.expander("Detail kesiapan model"):
            st.text(health.get("message", "Backend belum tersedia."))
            st.caption("Pastikan backend, model, pemetaan, dan berkas evaluasi tersedia di proyek.")
            if st.button("Periksa ulang", key="reload_backend"):
                load_backend.clear()
                st.rerun()

st.html('<div class="topline"><strong>UNIMAL · PENELITIAN NLP</strong>'
        f'<span>{escape(st.session_state.page)} / Kitab Fathul Qorib</span></div>')

if not READY:
    st.warning("Model belum siap. Antarmuka dapat ditinjau; pemrosesan tersedia setelah model berhasil dimuat.")

page = st.session_state.page
if page == "Beranda":
    render_home()
elif page == "Diakritisasi":
    render_diakritisasi()
elif page == "Contoh Teks":
    render_examples()
elif page == "Tentang Model":
    render_about()

st.html('<footer class="footer-note">Diakritisasi Otomatis Teks Arab Gundul pada Kitab Fathul Qorib'
        '<br>BiLSTM-CRF · Universitas Malikussaleh</footer>')
