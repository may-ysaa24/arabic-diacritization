
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
    --ui-ink: #19372C;
    --ui-muted: #607269;
    --ui-green: #009344;
    --ui-green-dark: #006F34;
    --ui-gold: #E2A313;
    --ui-soft: #F1F7F3;
    --ui-line: #D9E6DE;
    --ui-serif: "Liberation Serif", "Times New Roman", serif;
    --ui-sans: "Cabin", "Segoe UI", Arial, sans-serif;
    --ui-arabic: "Noto Naskh Arabic", "Amiri", "Traditional Arabic", "DejaVu Sans", serif;
}
.stApp { background: #FCFDFC; color: var(--ui-ink); font-family: var(--ui-sans); }
.stMainBlockContainer { max-width: 1200px; padding: 4.6rem 2.8rem 2rem; }
[data-testid="stSidebar"] { background: #F3F8F5; border-right: 1px solid var(--ui-line); }
[data-testid="stSidebar"] > div:first-child { padding-top: 2.5rem; }
.brand-kicker, .eyebrow {
    color: var(--ui-green); font-size: .73rem; font-weight: 700;
    letter-spacing: .12em; text-transform: uppercase; margin-bottom: .65rem;
}
.brand-rule { width: 34px; height: 3px; background: var(--ui-gold); border-radius: 10px; margin: .8rem 0 .9rem; }
.brand-title { font-family: var(--ui-serif); font-size: 1.52rem; font-weight: 700; line-height: 1.25; color: #0D422B; }
.brand-subtitle { color: var(--ui-muted); font-size: .84rem; line-height: 1.65; margin: .6rem 0 1.8rem; }
.st-key-nav [role="radiogroup"] { gap: .35rem; }
.st-key-nav [role="radiogroup"] > label {
    padding: .68rem .85rem; width: 100%; border-radius: 8px;
    margin: 0; border: 1px solid transparent; min-height: 44px;
    transition: background-color .18s ease, border-color .18s ease, transform .18s ease;
}
.st-key-nav [role="radiogroup"] > label:has(input:checked) {
    background: #E3F2E9; border-color: #C9E2D2; color: #075B2D;
}
.st-key-nav [role="radiogroup"] > label:hover { background: #EAF4ED; transform: translateX(2px); }
.st-key-nav [role="radiogroup"] > label p { font-size: .94rem; font-weight: 560; }
.sidebar-note { border-top: 1px solid #D4DFD7; margin-top: 2rem; padding-top: 1.2rem; }
.sidebar-note p { color: var(--ui-muted); font-size: .8rem; line-height: 1.6; }
.status-line { font-size: .84rem; color: var(--ui-muted); display: flex; align-items: center; gap: .5rem; }
.status-dot { background: #78867C; width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.status-dot.ready { background: var(--ui-green); box-shadow: 0 0 0 4px rgba(0,147,68,.12); }
.topline {
    display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
    border-bottom: 1px solid var(--ui-line); padding-bottom: 1rem; margin-bottom: 1.7rem;
    color: var(--ui-muted); font-size: .78rem;
}
.topline strong { color: #1E543A; font-weight: 650; }
.st-key-home_hero { padding: .35rem 0 .5rem; }
.hero { padding: .35rem 0 .7rem; }
.hero h1 {
    font-family: var(--ui-serif); font-size: clamp(2.45rem, 4.4vw, 3.65rem);
    font-weight: 700; line-height: 1.08; letter-spacing: -.035em;
    max-width: 730px; color: #0A462B; margin: .7rem 0 .55rem;
}
.hero .research-subtitle { color: #267047; font-size: 1.08rem; font-weight: 650; line-height: 1.55; margin: 0 0 .9rem; }
.hero p { max-width: 670px; color: var(--ui-muted); line-height: 1.75; font-size: 1rem; margin: 0; }
.hero-note { color: var(--ui-muted); font-size: .79rem; line-height: 1.6; margin-top: .35rem; }
.research-card {
    position: relative; overflow: hidden; background: #F3F8F5;
    border: 1px solid #D7E8DE; border-radius: 14px; padding: 1.3rem 1.4rem 1.25rem;
    min-height: 245px; display: flex; flex-direction: column; justify-content: space-between;
    transition: transform .2s ease, box-shadow .2s ease;
}
.research-card::before { content: ""; position: absolute; inset: 0 auto 0 0; width: 4px; background: var(--ui-green); }
.research-card:hover { transform: translateY(-2px); box-shadow: 0 12px 30px rgba(16,74,43,.08); }
.research-card .card-kicker { color: var(--ui-green-dark); font-size: .72rem; font-weight: 750; letter-spacing: .1em; }
.research-card .arabic-text { font-size: 29px; line-height: 2.15; margin: .65rem 0; }
.research-card .card-caption { color: var(--ui-muted); font-size: .8rem; line-height: 1.6; }
.research-card .gold-line { width: 46px; height: 3px; background: var(--ui-gold); border-radius: 4px; }
.page-heading { padding: .1rem 0 1rem; }
.page-heading h1 { font-family: var(--ui-serif); font-size: 2.15rem; font-weight: 700; letter-spacing: -.025em; margin: 0 0 .55rem; color: #113E2A; }
.page-heading p { color: var(--ui-muted); line-height: 1.7; max-width: 800px; margin: 0; }
.st-key-home_actions { padding: 0 0 .7rem; }
.arabic-text {
    direction: rtl; unicode-bidi: plaintext; text-align: right;
    font-family: var(--ui-arabic); font-size: 27px; line-height: 2.1;
    white-space: pre-wrap; overflow-wrap: anywhere; word-break: normal;
    letter-spacing: normal; font-weight: 400; padding: .25rem 0;
}
.arabic-result {
    background: #F5F8F5; border: 1px solid #DBE7DD; border-radius: 9px;
    padding: 1.15rem 1.35rem; min-height: 205px; max-height: 520px; overflow-y: auto;
}
.empty-output {
    border: 1px dashed #CAD8CE; border-radius: 9px; min-height: 205px;
    display: flex; flex-direction: column; justify-content: center; padding: 1.5rem;
    color: var(--ui-muted); background: #F9FBF9;
}
.empty-output strong { color: #456655; font-size: 1rem; margin-bottom: .5rem; }
.empty-output p { font-size: .88rem; line-height: 1.7; margin: 0; max-width: 320px; }
.work-label { font-size: .74rem; font-weight: 700; color: var(--ui-green); letter-spacing: .07em; margin-bottom: .45rem; }
.section-title { font-size: 1.2rem; font-weight: 640; color: var(--ui-ink); margin: .2rem 0 .25rem; }
.muted { color: var(--ui-muted); font-size: .88rem; line-height: 1.75; }
.home-section { display:flex; justify-content:space-between; align-items:end; gap:1rem; margin:1.7rem 0 .25rem; }
.home-section h2 { font-family:var(--ui-serif); font-size:1.55rem; color:#173D2B; margin:0; }
.home-section p { color:var(--ui-muted); font-size:.84rem; margin:0; }
.guide-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: .8rem 0; }
.guide-item { background:#FFFFFF; border:1px solid var(--ui-line); border-radius:11px; padding:1.15rem 1.2rem; transition:transform .18s ease, border-color .18s ease, box-shadow .18s ease; }
.guide-item:hover { transform:translateY(-2px); border-color:#BFDCCB; box-shadow:0 8px 22px rgba(14,73,42,.06); }
.guide-item .number { color: var(--ui-green-dark); font-size: .74rem; font-weight: 700; margin-bottom: .65rem; letter-spacing:.08em; }
.guide-item h3 { font-size: 1rem; margin: 0 0 .5rem; font-weight: 640; }
.guide-item p { font-size: .88rem; line-height: 1.7; color: var(--ui-muted); margin: 0; }
.footer-note { border-top: 1px solid var(--ui-line); margin-top: 2rem; padding-top: 1rem;
    color: var(--ui-muted); font-size: .76rem; line-height: 1.7; }
.st-key-arabic_input textarea, .st-key-file_arabic textarea {
    direction: rtl; text-align: right; unicode-bidi: plaintext;
    font-family: var(--ui-arabic); font-size: 26px; line-height: 2;
    letter-spacing: normal; padding: 1rem; background: #FFFFFF;
}
.st-key-arabic_copy pre, .st-key-arabic_copy code {
    direction: rtl; text-align: right; unicode-bidi: plaintext;
    font-family: var(--ui-arabic); font-size: 23px; line-height: 2; letter-spacing: normal;
}
.st-key-workspace [data-testid="stVerticalBlockBorderWrapper"],
.st-key-about_architecture [data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--ui-line); }
button { min-height: 42px; }
[data-testid="stBaseButton-primary"] { background: #007B3A; border-color: #007B3A; box-shadow:0 5px 14px rgba(0,123,58,.14); }
[data-testid="stBaseButton-primary"]:hover { background: #00652F; border-color: #00652F; transform:translateY(-1px); }
[data-testid="stButton"] button { transition:transform .18s ease, box-shadow .18s ease, background-color .18s ease; }
[data-testid="stMetricLabel"] p { font-size: .86rem; color: var(--ui-muted); }
[data-testid="stMetricValue"] { font-size: 1.65rem; color: #194B36; }
button:focus-visible, a:focus-visible { outline: 3px solid #427F65 !important; outline-offset: 3px; }
@media (max-width: 900px) {
    .stMainBlockContainer { padding: 4.5rem 1.3rem 1.8rem; }
    .hero h1 { font-size: 2.65rem; }
    .st-key-home_hero [data-testid="stHorizontalBlock"] { flex-wrap:wrap; }
    .st-key-home_hero [data-testid="stColumn"] { min-width:min(100%, 340px); }
    .st-key-workspace [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
    .st-key-workspace [data-testid="stColumn"] { min-width: min(100%, 310px); }
}
@media (max-width: 600px) {
    .stMainBlockContainer { padding: 4.5rem 1rem 1.3rem; }
    .hero h1 { font-size: 2.35rem; }
    .page-heading h1 { font-size: 1.7rem; }
    .guide-grid { grid-template-columns: 1fr; gap: .4rem; }
    .home-section { align-items:start; flex-direction:column; }
    .arabic-text { font-size: 25px; }
    .arabic-result { padding: .85rem; }
}
@media (prefers-reduced-motion: no-preference) {
    [data-testid="stMainBlockContainer"] > div { animation: ui-enter .28s ease-out both; }
    @keyframes ui-enter { from { opacity:.72; transform:translateY(4px); } to { opacity:1; transform:none; } }
}
@media print {
    [data-testid="stSidebar"], [data-testid="stHeader"] { display: none; }
    .stApp { background: #FFFFFF; }
    .stMainBlockContainer { max-width: none; padding: 0; }
    .arabic-result { max-height: none; overflow: visible; }
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
            st.caption("Teks berharakat juga dapat dimasukkan; harakat lama akan diprediksi ulang.")
            with st.container(horizontal=True):
                process = st.button("Proses Diakritisasi", key="process_manual", type="primary",
                                    disabled=not READY, icon=":material/auto_stories:")
                st.button("Bersihkan", key="reset_manual", on_click=reset_manual)
            if process:
                st.session_state.manual_input = text
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
    st.write("Unggah teks untuk diproses sebagai berkas.")
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
                st.caption("Kolom terdeteksi: " + ", ".join(map(str, names)))
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
    st.caption("Kitab Fathul Qorib · Hasil evaluasi penelitian, bukan tingkat keyakinan setiap prediksi.")
    fine = metrics_data.get("fine_tuned") if isinstance(metrics_data, dict) else None
    if not isinstance(fine, dict):
        st.info("Metrik evaluasi belum tersedia.")
    else:
        columns = st.columns(3)
        for col, label, key in zip(columns, ["Accuracy", "DER", "WER"],
                                   ["accuracy_percent", "der_percent", "wer_percent"]):
            col.metric(label, format_percent(fine.get(key)))
        st.caption("Accuracy: ketepatan label pada karakter valid. DER: kesalahan label pada huruf Arab. "
                   "WER: persentase kata yang berbeda dari referensi.")
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
