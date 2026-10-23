
"""UI akademik BiLSTM-CRF. Backend asli diimpor tanpa modifikasi.

Sumber notebook: 07_build_streamlit_ui_akademik.ipynb, Cell 4.
Perubahan tampilan tidak mengganti hasil atau aturan inferensi backend.
"""

from base64 import b64encode
from copy import deepcopy
from html import escape
from importlib import import_module
from io import BytesIO
from json import dumps
from math import isfinite
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import pandas as pd
import streamlit as st

from file_safety import spreadsheet_safe_csv, txt_control_error
import upload_queue as queue
import translation_reference as reference
from translation_panel import render_reference_panel, sync_reference_file


# Streamlit sends frontend configuration before executing this script. Bootstrap
# each session once so even an external working directory or a false CLI/env
# override cannot expose the native dataframe export on the first rendered page.
# This uses the supported Streamlit 1.63 client option, not CSS hiding.
export_policy_changed = not st.get_option("client.disableDataExport")
if export_policy_changed:
    st.set_option("client.disableDataExport", True)
if export_policy_changed or not st.session_state.get("_ui_export_policy_ready", False):
    st.session_state["_ui_export_policy_ready"] = True
    st.rerun()


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
  color-scheme:light;
  --ink:#064937;
  --muted:#526A61;
  --green:#009344;
  --green-dark:#006F34;
  --green-soft:#E3F2E9;
  --sidebar:#F0F6F1;
  --gold:#E2A313;
  --canvas:#FCFDFC;
  --border:#DCE8DF;
  --border-strong:#9CBBA8;
  --ui-sidebar-width:284px;
  --ui-content-width:1240px;
  --ui-workspace-width:1040px;
  --ui-page-title:clamp(1.65rem,2.3vw,2rem);
  --ui-control-height:40px;
  --arabic:"Noto Naskh Arabic","Amiri","Scheherazade New","Traditional Arabic","DejaVu Sans",serif;
  --sans:"Segoe UI",system-ui,Arial,sans-serif;
  --serif:"Georgia","Cambria","Times New Roman",serif;
}
html,body {font-family:var(--sans)}
.stApp {background:var(--canvas);color:var(--ink)}
[data-testid="stHeader"] {background:transparent}
.stMainBlockContainer {max-width:var(--ui-content-width);padding:1rem 1.4rem 1.5rem}
.stApp [data-testid="stSidebar"] {background:var(--sidebar);border-right:1px solid var(--border)}
.stApp [data-testid="stSidebar"][aria-expanded="true"] {width:var(--ui-sidebar-width);min-width:var(--ui-sidebar-width);max-width:var(--ui-sidebar-width)}
[data-testid="stSidebarHeader"] {height:20px;min-height:20px}
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stImage"]) {align-self:center}
[data-testid="stAppDeployButton"] {display:none}
[data-testid="stSidebarUserContent"] {padding:1rem 1.15rem 1.1rem}
[data-testid="stSidebar"] [data-testid="stImage"] {margin:0 auto .1rem}
.brand-university {font:700 1.03rem/1.4 var(--serif);text-align:center;color:var(--ink);margin:.35rem -.4rem .9rem}
.brand-rule {width:38px;height:3px;border-radius:3px;background:var(--gold);margin:0 0 1.1rem}
.brand-kicker,.eyebrow {font-size:.72rem;line-height:1.5;font-weight:650;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:0 0 .6rem}
.brand-title {font:700 1.23rem/1.35 var(--serif);color:var(--ink);letter-spacing:-.02em;margin-bottom:1.25rem}
.st-key-nav [role="radiogroup"] {gap:.35rem;width:100%}
.st-key-nav [role="radiogroup"] > label {
  position:relative;display:flex;align-items:center;width:100%;min-height:44px;
  margin:0;padding:.6rem .75rem;border:1px solid transparent;border-radius:11px;
  transition:background-color .16s,border-color .16s;
}
/* Keep the native radio input keyboard accessible while using local SVG icons. */
.st-key-nav [data-testid="stRadioOption"] > div > div > div:not([data-testid]) {display:none}
.st-key-nav [role="radiogroup"] > label::before {
  content:"";flex:0 0 20px;width:20px;height:20px;margin-right:.7rem;
  background:var(--muted);mask:var(--nav-icon) center/contain no-repeat;
}
.st-key-nav [role="radiogroup"] > label:nth-child(1) {--nav-icon:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22m3%2010%209-7%209%207M5%209v12h5v-7h4v7h5V9%22%2F%3E%3C%2Fsvg%3E")}
.st-key-nav [role="radiogroup"] > label:nth-child(2) {--nav-icon:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M14%202H5v20h14V7Z%22%2F%3E%3Cpath%20d%3D%22M14%202v6h5M8%2012h8M8%2016h8%22%2F%3E%3C%2Fsvg%3E")}
.st-key-nav [role="radiogroup"] > label:nth-child(3) {--nav-icon:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M12%205C8%202%204%203%202%204v16c3-2%207-2%2010%200%203-2%207-2%2010%200V4c-3-1-7-2-10%201Zm0%200v15%22%2F%3E%3C%2Fsvg%3E")}
.st-key-nav [role="radiogroup"] > label:nth-child(4) {--nav-icon:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Ccircle%20cx%3D%2212%22%20cy%3D%2212%22%20r%3D%2210%22%2F%3E%3Cpath%20d%3D%22M12%2011v6M12%207v.1%22%2F%3E%3C%2Fsvg%3E")}
.st-key-nav [role="radiogroup"] > label p {color:var(--ink);font-size:.9rem;font-weight:550;margin:0}
.st-key-nav [role="radiogroup"] > label:has(input:checked) {background:var(--green-soft)}
.st-key-nav [role="radiogroup"] > label:has(input:checked)::before {background:var(--green-dark)}
.st-key-nav [role="radiogroup"] > label:has(input:checked)::after {content:"";position:absolute;left:-1.15rem;top:5px;bottom:5px;width:5px;border-radius:0 5px 5px 0;background:var(--green)}
.st-key-nav [role="radiogroup"] > label:has(input:checked) p {color:var(--green-dark);font-weight:700}
.st-key-nav [role="radiogroup"] > label:hover:not(:has(input:checked)) {background:#E8F1EA}
.st-key-nav [role="radiogroup"] > label:has(input:focus-visible) {outline:3px solid var(--green-dark);outline-offset:3px}
.sidebar-note {margin-top:clamp(1.5rem,7vh,4rem);padding:.85rem;border-radius:12px;background:#E1EEE5;color:var(--ink)}
.status-line {display:flex;align-items:center;gap:.55rem;font-size:.8rem;font-weight:650}
.status-dot {flex:0 0 9px;width:9px;height:9px;border-radius:50%;background:#986A08;box-shadow:0 0 0 4px #E2A31322}
.status-dot.ready {background:var(--green);box-shadow:0 0 0 4px #00934422}
.sidebar-note p {font-size:.75rem;line-height:1.65;color:var(--muted);margin:.4rem 0 0 1.2rem}
.topline {display:flex;align-items:center;justify-content:space-between;gap:1rem;min-height:44px;margin:0 -1.4rem;padding:0 2.4rem .65rem 1.4rem;border-bottom:1px solid var(--border);font-size:.87rem;color:var(--muted)}
.breadcrumb,.topline-book {display:flex;align-items:center;gap:.8rem}
.breadcrumb .separator {color:#81968A}
.ui-icon {display:inline-block;width:24px;height:24px;flex-shrink:0;vertical-align:middle;background:currentColor;mask:var(--icon) center/contain no-repeat}
.icon-home {--icon:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22m3%2010%209-7%209%207M5%209v12h5v-7h4v7h5V9%22%2F%3E%3C%2Fsvg%3E")}
.icon-file {--icon:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M14%202H5v20h14V7Z%22%2F%3E%3Cpath%20d%3D%22M14%202v6h5M8%2012h8M8%2016h8%22%2F%3E%3C%2Fsvg%3E")}
.icon-book {--icon:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M12%205C8%202%204%203%202%204v16c3-2%207-2%2010%200%203-2%207-2%2010%200V4c-3-1-7-2-10%201Zm0%200v15%22%2F%3E%3C%2Fsvg%3E")}
.icon-info {--icon:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Ccircle%20cx%3D%2212%22%20cy%3D%2212%22%20r%3D%2210%22%2F%3E%3Cpath%20d%3D%22M12%2011v6M12%207v.1%22%2F%3E%3C%2Fsvg%3E")}
.icon-arrow {--icon:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M3%2012h18m-7-7%207%207-7%207%22%2F%3E%3C%2Fsvg%3E")}
.icon-gear {--icon:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22m9%203%201-2h4l1%202%202%201%202-1%203%203-1%202%201%203%202%201v3l-2%201-1%202%201%202-3%203-2-1-2%201-1%202h-4l-1-2-2-1-2%201-3-3%201-2-1-2-2-1v-3l2-1%201-3-1-2%203-3%202%201Z%22%20transform%3D%22translate%281%201%29%20scale%28.85%29%22%2F%3E%3Ccircle%20cx%3D%2212%22%20cy%3D%2212%22%20r%3D%223.5%22%2F%3E%3C%2Fsvg%3E")}
.page-heading {padding:1.35rem .1rem .9rem}
.page-heading .eyebrow {color:var(--green-dark)}
.page-heading h1 {font:700 var(--ui-page-title)/1.25 var(--serif);letter-spacing:-.025em;margin:.2rem 0 .6rem;color:var(--ink)}
.page-heading p {color:var(--muted);font-size:.9rem;line-height:1.7;max-width:850px;margin:0}
.st-key-home_hero {position:relative;isolation:isolate;overflow:visible;width:100%;padding:2rem 1.2rem 3.8rem;min-height:390px;text-align:center}
.st-key-home_hero::before {content:"";position:absolute;inset:0 -1.4rem;z-index:-1;pointer-events:none;background:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%201440%20570%22%20fill%3D%22none%22%3E%3Cg%20opacity%3D%22.17%22%20transform%3D%22translate%280%20170%29%20scale%281.25%29%22%3E%3Cg%20fill%3D%22none%22%20stroke%3D%22%23699982%22%20stroke-width%3D%221.6%22%3E%3Cpath%20d%3D%22M0%2C-98%20Q42%2C-70%2042%2C-42%20Q70%2C-42%2098%2C0%20Q70%2C42%2042%2C42%20Q42%2C70%200%2C98%20Q-42%2C70%20-42%2C42%20Q-70%2C42%20-98%2C0%20Q-70%2C-42%20-42%2C-42%20Q-42%2C-70%200%2C-98Z%22%20transform%3D%22rotate%280%29%22%2F%3E%3Cpath%20d%3D%22M0%2C-98%20Q42%2C-70%2042%2C-42%20Q70%2C-42%2098%2C0%20Q70%2C42%2042%2C42%20Q42%2C70%200%2C98%20Q-42%2C70%20-42%2C42%20Q-70%2C42%20-98%2C0%20Q-70%2C-42%20-42%2C-42%20Q-42%2C-70%200%2C-98Z%22%20transform%3D%22rotate%2822.5%29%22%2F%3E%3Cpath%20d%3D%22M0%2C-98%20Q42%2C-70%2042%2C-42%20Q70%2C-42%2098%2C0%20Q70%2C42%2042%2C42%20Q42%2C70%200%2C98%20Q-42%2C70%20-42%2C42%20Q-70%2C42%20-98%2C0%20Q-70%2C-42%20-42%2C-42%20Q-42%2C-70%200%2C-98Z%22%20transform%3D%22rotate%2845%29%22%2F%3E%3Ccircle%20r%3D%2272%22%2F%3E%3Ccircle%20r%3D%22116%22%2F%3E%3Cpath%20d%3D%22M0%2C-116%20L28%2C-68%20L82%2C-82%20L68%2C-28%20L116%2C0%22%20transform%3D%22rotate%280%29%22%2F%3E%3Cpath%20d%3D%22M0%2C-116%20L28%2C-68%20L82%2C-82%20L68%2C-28%20L116%2C0%22%20transform%3D%22rotate%2890%29%22%2F%3E%3Cpath%20d%3D%22M0%2C-116%20L28%2C-68%20L82%2C-82%20L68%2C-28%20L116%2C0%22%20transform%3D%22rotate%28180%29%22%2F%3E%3Cpath%20d%3D%22M0%2C-116%20L28%2C-68%20L82%2C-82%20L68%2C-28%20L116%2C0%22%20transform%3D%22rotate%28270%29%22%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20opacity%3D%22.17%22%20transform%3D%22translate%281440%20170%29%20scale%281.25%29%22%3E%3Cg%20fill%3D%22none%22%20stroke%3D%22%23699982%22%20stroke-width%3D%221.6%22%3E%3Cpath%20d%3D%22M0%2C-98%20Q42%2C-70%2042%2C-42%20Q70%2C-42%2098%2C0%20Q70%2C42%2042%2C42%20Q42%2C70%200%2C98%20Q-42%2C70%20-42%2C42%20Q-70%2C42%20-98%2C0%20Q-70%2C-42%20-42%2C-42%20Q-42%2C-70%200%2C-98Z%22%20transform%3D%22rotate%280%29%22%2F%3E%3Cpath%20d%3D%22M0%2C-98%20Q42%2C-70%2042%2C-42%20Q70%2C-42%2098%2C0%20Q70%2C42%2042%2C42%20Q42%2C70%200%2C98%20Q-42%2C70%20-42%2C42%20Q-70%2C42%20-98%2C0%20Q-70%2C-42%20-42%2C-42%20Q-42%2C-70%200%2C-98Z%22%20transform%3D%22rotate%2822.5%29%22%2F%3E%3Cpath%20d%3D%22M0%2C-98%20Q42%2C-70%2042%2C-42%20Q70%2C-42%2098%2C0%20Q70%2C42%2042%2C42%20Q42%2C70%200%2C98%20Q-42%2C70%20-42%2C42%20Q-70%2C42%20-98%2C0%20Q-70%2C-42%20-42%2C-42%20Q-42%2C-70%200%2C-98Z%22%20transform%3D%22rotate%2845%29%22%2F%3E%3Ccircle%20r%3D%2272%22%2F%3E%3Ccircle%20r%3D%22116%22%2F%3E%3Cpath%20d%3D%22M0%2C-116%20L28%2C-68%20L82%2C-82%20L68%2C-28%20L116%2C0%22%20transform%3D%22rotate%280%29%22%2F%3E%3Cpath%20d%3D%22M0%2C-116%20L28%2C-68%20L82%2C-82%20L68%2C-28%20L116%2C0%22%20transform%3D%22rotate%2890%29%22%2F%3E%3Cpath%20d%3D%22M0%2C-116%20L28%2C-68%20L82%2C-82%20L68%2C-28%20L116%2C0%22%20transform%3D%22rotate%28180%29%22%2F%3E%3Cpath%20d%3D%22M0%2C-116%20L28%2C-68%20L82%2C-82%20L68%2C-28%20L116%2C0%22%20transform%3D%22rotate%28270%29%22%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20fill%3D%22%238DB6A0%22%20opacity%3D%22.12%22%3E%3Cpath%20d%3D%22M15%20475V390%20Q-15%20357%2045%20320%20Q105%20357%2075%20390V475Z%22%2F%3E%3Cpath%20d%3D%22M43%20323V301L47%20293L51%20301V323Z%22%2F%3E%3Cpath%20d%3D%22M120%20490V418Q98%20397%20134%20368Q170%20397%20148%20418V490Z%22%2F%3E%3Cpath%20d%3D%22M132%20370V350L136%20343L140%20350V370Z%22%2F%3E%3Cpath%20d%3D%22M1240%20480V405Q1193%20365%201275%20308Q1357%20365%201310%20405V480Z%22%2F%3E%3Cpath%20d%3D%22M1272%20310V284L1276%20277L1280%20284V310Z%22%2F%3E%3C%2Fg%3E%3Cg%20opacity%3D%22.19%22%20stroke%3D%22%237AA58B%22%20stroke-width%3D%223%22%20fill%3D%22%23E3F2E9%22%3E%3Cpath%20d%3D%22M1122%20415Q1204%20400%201270%20472Q1340%20418%201435%20420L1386%20551Q1313%20532%201256%20562Q1199%20526%201093%20537Z%22%2F%3E%3Cpath%20d%3D%22M1138%20400Q1210%20391%201270%20465L1256%20552Q1197%20511%201104%20526Z%22%2F%3E%3Cpath%20d%3D%22M1280%20464Q1341%20400%201427%20405L1381%20539Q1318%20523%201266%20552Z%22%2F%3E%3Cpath%20d%3D%22M1154%20429L1211%20449M1146%20443L1220%20469M1139%20458L1213%20485M1300%20473L1386%20440M1297%20489L1378%20459M1291%20505L1368%20480%22%20stroke-width%3D%222%22%2F%3E%3Cpath%20d%3D%22M1093%20537Q1199%20526%201256%20562Q1313%20532%201386%20551%22%20stroke%3D%22%23C99A36%22%2F%3E%3C%2Fg%3E%3Cpath%20d%3D%22M0%20440C170%20417%20210%20541%20460%20530S785%20482%201030%20531S1284%20496%201440%20472V570H0Z%22%20fill%3D%22%238DB6A0%22%20opacity%3D%22.17%22%2F%3E%3Cpath%20d%3D%22M0%20490C177%20448%20286%20565%20580%20549S866%20514%201114%20550S1312%20508%201440%20511V570H0Z%22%20fill%3D%22%237EA88E%22%20opacity%3D%22.13%22%2F%3E%3Cpath%20d%3D%22M0%20492C177%20449%20286%20562%20580%20548M1114%20551C1236%20542%201320%20505%201440%20512%22%20stroke%3D%22%23E2A313%22%20stroke-width%3D%222%22%20opacity%3D%22.42%22%2F%3E%3C%2Fsvg%3E") center bottom/cover no-repeat}
.hero {max-width:1230px;margin:0 auto}
.hero .eyebrow {color:#946800;font-size:.74rem;font-weight:700;letter-spacing:.12em;margin:0 0 .75rem}
.hero-rule {width:42px;height:3px;border-radius:3px;background:var(--gold);margin:0 auto 1.1rem}
.hero h1 {font:700 clamp(1.85rem,2.75vw,2.65rem)/1.22 var(--serif);letter-spacing:-.035em;color:var(--ink);margin:0 auto .9rem}
.hero h1 span {display:block;font-size:.79em;line-height:1.35;margin-top:.15rem;letter-spacing:-.025em}
.hero p {font-size:clamp(.92rem,1.05vw,1rem);line-height:1.75;color:var(--muted);max-width:850px;margin:0 auto 1.1rem}
.st-key-home_actions {justify-content:center;gap:.85rem;margin-top:.6rem}
.st-key-home_actions button p {font-size:.93rem}
.st-key-home_actions button {min-height:46px;padding:.65rem 1.25rem;font-size:.93rem;border-radius:10px}
.st-key-home_actions [data-testid="stBaseButton-primary"] {background:linear-gradient(115deg,#008647,#007D40);border-color:#008343;box-shadow:0 7px 18px #006F3418}
.st-key-home_actions [data-testid="stBaseButton-primary"]:hover {background:var(--green-dark)}
.usage-panel {position:relative;margin-top:-.8rem;padding:1.15rem 1.1rem 1rem;border:1px solid #E4ECE6;border-radius:18px;background:#FFFFFFF2;box-shadow:0 5px 22px #06493708}
.usage-panel h2 {font:700 clamp(1.3rem,1.8vw,1.55rem)/1.3 var(--serif);color:var(--ink);letter-spacing:-.025em;margin:0 0 .65rem .35rem}
.section-rule {width:39px;height:3px;background:var(--gold);border-radius:3px;margin:0 0 1.15rem .35rem}
.guide-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1.8rem}
.guide-item {position:relative;display:grid;grid-template-columns:38px minmax(0,1fr);column-gap:.8rem;align-items:start;border:1px solid #E2EAE5;border-radius:14px;background:#FCFDFC;padding:1rem .9rem;min-height:150px;box-shadow:0 3px 10px #06493704}
.guide-item:not(:last-child)::after {content:"";position:absolute;right:-1.5rem;top:50%;width:20px;height:20px;background:var(--muted);mask:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M3%2012h18m-7-7%207%207-7%207%22%2F%3E%3C%2Fsvg%3E") center/contain no-repeat}
.guide-item .number {width:38px;height:38px;border-radius:50%;background:var(--green-soft);color:var(--green-dark);display:grid;place-items:center;font-size:1.05rem;font-weight:750}
.guide-item .ui-icon {width:26px;height:26px;color:var(--ink);margin:.05rem 0 .45rem}
.guide-item h3 {font:700 1.05rem/1.4 var(--serif);color:var(--ink);margin:0 0 .2rem}
.guide-item p {font-size:.86rem;line-height:1.65;color:var(--muted);margin:0}
.arabic-text {direction:rtl;unicode-bidi:plaintext;text-align:right;font-family:var(--arabic);font-size:28px;line-height:2.1;white-space:pre-wrap;overflow-wrap:anywhere;word-break:normal;letter-spacing:normal;color:var(--ink)}
.arabic-result {padding:1.25rem 1.45rem;border:1px solid #CCE0D2;border-radius:13px;min-height:230px;max-height:510px;overflow-y:auto;background:#F1F7F3}
.empty-output {border:1.5px dashed var(--border-strong);background:var(--canvas);min-height:230px;border-radius:13px;display:flex;flex-direction:column;justify-content:center;align-items:flex-start;padding:2rem;color:var(--muted)}
.empty-output strong {color:var(--ink);font-size:1.08rem;margin-bottom:.55rem}
.empty-output p {max-width:360px;font-size:.85rem;line-height:1.8;margin:0}
.st-key-workspace {margin-top:.45rem}
.st-key-arabic_input textarea,.st-key-arabic_correction textarea {direction:rtl;text-align:right;unicode-bidi:plaintext;font-family:var(--arabic);font-size:25px;line-height:2.1;letter-spacing:normal;border:1px solid var(--border-strong);border-radius:12px;padding:.75rem 1rem;min-height:140px;background:var(--canvas);color:var(--ink)}
.st-key-workspace [data-testid="stTextArea"] textarea:focus {border-color:var(--green-dark)}
[data-testid="stTabs"] [role="tablist"] {border-bottom:1px solid var(--border);gap:.55rem}
[data-testid="stTabs"] button[role="tab"] {font-weight:650;padding:.75rem 1.15rem}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {color:var(--green-dark);border-color:var(--green-dark)}
[data-testid="stExpander"],[data-testid="stVerticalBlockBorderWrapper"] {border-color:var(--border);border-radius:12px}
[data-testid="stFileUploader"] section {border-color:var(--border-strong);border-radius:12px;background:var(--canvas)}
[data-testid="stMetric"] {background:var(--canvas);border:1px solid var(--border);border-radius:13px;padding:.85rem 1rem}
[data-testid="stMetricLabel"] p {color:var(--muted);font-size:.84rem}
[data-testid="stMetricValue"] {color:var(--ink);font-weight:750}
[data-testid="stBaseButton-primary"],.st-key-arabic_correction [data-testid="stFormSubmitButton"] button {background:var(--green-dark);border-color:var(--green-dark);color:#fff;border-radius:10px}
[data-testid="stBaseButton-primary"]:hover:not(:disabled),.st-key-arabic_correction [data-testid="stFormSubmitButton"] button:hover:not(:disabled) {background:var(--ink);border-color:var(--ink);color:#fff}
[data-testid="stBaseButton-secondary"] {color:var(--ink);background:var(--canvas);border:1px solid var(--border-strong);border-radius:10px}
[data-testid="stBaseButton-secondary"]:hover:not(:disabled) {color:var(--green-dark);background:#F1F7F3;border-color:var(--green-dark)}
[data-testid="stBaseButton-primary"]:disabled,[data-testid="stBaseButton-secondary"]:disabled,.st-key-arabic_correction [data-testid="stFormSubmitButton"] button:disabled {color:var(--muted);background:#F1F7F3;border-color:var(--border);opacity:1}
.st-key-arabic_correction [data-testid="stFormSubmitButton"] button:focus-visible {outline:3px solid var(--green-dark);outline-offset:3px}
[data-testid="stCaptionContainer"],[data-testid="InputInstructions"] {color:var(--muted);opacity:1}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button {min-height:var(--ui-control-height);font-weight:650;transition:border-color .16s,background .16s}
[data-testid="stAlert"] {border-radius:11px}
.footer-note {border-top:1px solid var(--border);margin:1.5rem .1rem .2rem;padding:.85rem 0;color:var(--muted);font-size:.75rem;line-height:1.8}
button:focus-visible,a:focus-visible,textarea:focus-visible {outline:3px solid var(--green-dark);outline-offset:3px}
@media(min-width:1500px){
  .st-key-home_hero {padding-top:2.2rem;min-height:400px}
  .guide-item {min-height:150px;padding:1rem}
}
@media(max-width:1100px){
  [data-testid="stSidebarUserContent"] {padding-left:1.15rem;padding-right:1.15rem}
  .st-key-nav [role="radiogroup"] > label:has(input:checked)::after {left:-1.15rem}
  .hero h1 {font-size:2.2rem}
  .guide-grid {gap:1rem}
  .guide-item {grid-template-columns:1fr;gap:.7rem;padding:1rem}
  .guide-item:not(:last-child)::after {display:none}
}
@media(max-width:780px){
  .stApp [data-testid="stSidebar"][aria-expanded="true"] {min-width:0;width:min(var(--ui-sidebar-width),calc(100vw - 45px))}
  .stMainBlockContainer {padding:3.2rem .9rem 1.2rem}
   .topline {margin:0 -.9rem;padding:0 .9rem .65rem;font-size:.77rem;gap:.65rem}
  .topline .ui-icon {width:20px;height:20px}
  .st-key-home_hero {padding:1.8rem 0 3.4rem;min-height:0}
  .st-key-home_hero::before {inset:0 -.9rem;background-size:auto 100%;opacity:.75}
  .hero .eyebrow {font-size:.65rem;letter-spacing:.1em}
  .hero h1 {font-size:clamp(1.8rem,5.8vw,2.2rem);line-height:1.2}
  .hero h1 span {font-size:.76em;line-height:1.45;margin-top:.6rem}
  .hero p {font-size:.92rem;line-height:1.75}
  .st-key-home_actions {gap:.7rem;margin-top:.6rem}
  .st-key-home_actions button p {font-size:.9rem}
  .st-key-home_actions button {min-height:44px;padding:.6rem 1rem;font-size:.9rem}
   .usage-panel {padding:1rem .9rem;border-radius:15px;margin-top:-.7rem}
  .guide-grid {grid-template-columns:1fr;gap:.8rem}
  .guide-item {grid-template-columns:42px minmax(0,1fr);column-gap:1rem;min-height:0;padding:1rem}
  .guide-item .number {width:42px;height:42px}
  .guide-item .ui-icon {width:27px;height:27px;margin-bottom:.35rem}
  .page-heading {padding-top:1.2rem}
}
@media(max-width:430px){
  .topline {font-size:.7rem}
  .breadcrumb,.topline-book {gap:.45rem}
  .hero h1 {font-size:1.85rem}
  .arabic-text {font-size:24px}
  .st-key-arabic_input textarea,.st-key-arabic_correction textarea {font-size:23px}
  .sidebar-note {margin-top:1.75rem}
}

/* Diacritization workspace: scoped to keep the existing home design intact. */
.st-key-diak_page {width:100%;max-width:var(--ui-workspace-width);margin-inline:auto;min-width:0}
.st-key-diak_page .page-heading {padding:1.35rem 0 .9rem}
.st-key-diak_page .page-heading h1 {font-size:var(--ui-page-title)}
.st-key-diak_page [role="tablist"] {gap:.45rem;padding:.35rem;background:#EFF5F1;border:1px solid var(--border);border-radius:12px;margin-bottom:.25rem;width:fit-content;max-width:100%}
.st-key-diak_page [role="tab"] {padding:.55rem .95rem;border-radius:9px;border:0;color:var(--muted);font-weight:650;min-height:44px}
.st-key-diak_page [role="tab"][aria-selected="true"] {background:var(--green-dark);color:#fff;box-shadow:0 2px 6px #006F3414}
.st-key-diak_page [role="tab"] p {color:inherit}
.st-key-diak_page .react-aria-SelectionIndicator {display:none}
.st-key-workspace,.st-key-file_workspace {gap:1.25rem;min-width:0}
.st-key-manual_card,.st-key-manual_result_card,.st-key-file_upload_card,.st-key-file_result_card {
  padding:1rem 1.15rem;border:1px solid var(--border);border-radius:16px;
  background:#fff;box-shadow:0 4px 18px #06493706;min-width:0;
}
.workspace-card-heading {display:flex;align-items:center;gap:.7rem;margin:0 0 .2rem}
.workspace-card-heading .step-number {display:grid;place-items:center;flex:0 0 32px;width:32px;height:32px;border-radius:50%;background:var(--green-soft);color:var(--green-dark);font-size:.9rem;font-weight:750}
.workspace-card-heading h2 {font:700 .8rem/1.4 var(--sans);letter-spacing:.08em;color:var(--ink);margin:0}
.st-key-diak_page [data-testid="stWidgetLabel"] p {font-size:.87rem;font-weight:600}
.st-key-arabic_input textarea::placeholder {color:var(--muted);opacity:1}
.input-notes {display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;color:var(--muted);font-size:.78rem;line-height:1.7}
.manual-char-count {white-space:nowrap;font-variant-numeric:tabular-nums}
.st-key-manual_actions,.st-key-file_actions,.st-key-manual_result_actions,.st-key-file_result_actions {gap:.7rem;align-items:center;justify-content:flex-start}
.st-key-process_manual button::before,.st-key-process_file button::before {content:"";width:19px;height:19px;flex:0 0 19px;background:currentColor;mask:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22black%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22m14%205%205%205L8%2021l-5-5ZM11%208l5%205M5%202v5M2.5%204.5h5M20%2014v5M17.5%2016.5h5M17%201v4M15%203h4%22%2F%3E%3C%2Fsvg%3E") center/contain no-repeat}
.st-key-diak_page .empty-output {min-height:125px;padding:1.15rem;align-items:center;text-align:center;background:#FAFCFA;border-color:#BCD0C3;gap:.25rem}
.st-key-diak_page .empty-output .ui-icon {width:32px;height:32px;color:#6B927D;margin-bottom:.35rem}
.st-key-diak_page .empty-output strong {font-size:.96rem;margin-bottom:0}
.st-key-diak_page .empty-output p {font-size:.8rem;max-width:540px}
.st-key-diak_page .arabic-result {min-height:135px;max-height:400px;background:#F7FAF8;border-color:#D3E3D9;font-size:27px;line-height:2.15}
.prediction-comparison {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;min-width:0}
.comparison-panel {min-width:0;padding:.85rem 1rem;border:1px solid var(--border);border-radius:12px;background:var(--canvas)}
.comparison-panel h3 {font:650 .87rem/1.5 var(--sans);color:var(--green-dark);margin:0 0 .6rem}
.comparison-panel .arabic-text {font-size:25px;line-height:2.15}
@media(max-width:1024px){
  .prediction-comparison {grid-template-columns:minmax(0,1fr)}
}
.copy-control {display:inline-flex;align-items:center;gap:.5rem;position:relative}
.copy-button {display:inline-flex;align-items:center;justify-content:center;gap:.45rem;min-height:var(--ui-control-height);padding:.4rem .8rem;border:1px solid var(--border-strong);border-radius:10px;background:var(--canvas);color:var(--ink);font:650 .88rem/1.5 var(--sans);cursor:pointer;white-space:nowrap}
.copy-button .ui-icon {width:18px;height:18px}
.copy-button:hover:enabled {background:#F1F7F3;border-color:var(--green-dark)}
.copy-button:disabled {background:#F1F7F3;color:var(--muted);border-color:var(--border);cursor:default}
.copy-status {font-size:.75rem;color:var(--green-dark);max-width:230px}
.st-key-diak_page [data-testid="stFileUploader"] section {border:1.5px dashed #A7C8B4;background:#F4F9F6;border-radius:12px;padding:.85rem}
.st-key-diak_page [data-testid="stFileUploader"] {min-width:0}
.upload-help {color:var(--muted);font-size:.8rem;line-height:1.7;margin:0}
.file-facts {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;padding:.8rem;border:1px solid var(--border);border-radius:12px;background:#F9FBF9}
.file-fact span {display:block;color:var(--muted);font-size:.72rem;margin-bottom:.25rem}
.file-fact strong {font-size:.83rem;font-weight:650;color:var(--ink);overflow-wrap:anywhere}
.file-meta {font-size:.78rem;color:var(--muted);line-height:1.7;margin:.55rem 0 0}
.txt-preview {padding:.7rem 1rem;border:1px solid var(--border);border-radius:10px;background:#F8FBF9;max-height:200px;overflow-y:auto}
.txt-preview .arabic-text {font-size:25px;line-height:2.1}
.st-key-diak_page [data-testid="stDataFrame"] {min-width:0;max-width:100%}
.st-key-manual_result_card,.st-key-file_result_card {scroll-margin-block-start:5rem}
.st-key-manual_result_card h2:focus-visible,.st-key-file_result_card h2:focus-visible {outline:2px solid var(--green-dark);outline-offset:5px}
.st-key-scroll_manual,.st-key-scroll_file,.st-key-mobile_navigation,.st-key-manual_guard,.st-key-manual_stale_notice {display:none}
.manual-stale-notice {padding:.75rem 1rem;border:1px solid var(--border-strong);border-radius:12px;background:var(--green-soft);color:var(--ink);font-size:.87rem;line-height:1.7}
.st-key-manual_result_card[data-input-stale="true"] .st-key-manual_stale_notice {display:flex}
.st-key-manual_result_card[data-input-stale="true"] .st-key-manual_result_payload {display:none}
.processing-summary {min-width:0}
.processing-summary h3 {display:flex;align-items:center;gap:.4rem;font:650 .79rem/1.5 var(--sans);color:var(--ink);margin:0 0 .5rem}
.processing-summary .ui-icon {width:16px;height:16px;color:var(--green-dark)}
.processing-summary dl {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.5rem;margin:0;padding:0}
.processing-summary-file dl {grid-template-columns:repeat(3,minmax(0,1fr))}
.processing-stat {min-width:0;padding:.5rem .65rem;border:1px solid var(--border);border-radius:10px;background:#F7FAF8}
.processing-stat dt {font-size:.72rem;line-height:1.4;color:var(--muted)}
.processing-stat dd {font-size:.87rem;font-weight:650;line-height:1.5;color:var(--ink);margin:.2rem 0 0;overflow-wrap:anywhere}
.processing-summary p {font-size:.71rem;line-height:1.6;color:var(--muted);margin:.45rem 0 0}
@media(max-width:1024px){
  .processing-summary dl {grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media(max-width:780px){
  .st-key-diak_page .page-heading {padding-top:1.1rem}
  .st-key-manual_card,.st-key-manual_result_card,.st-key-file_upload_card,.st-key-file_result_card {padding:1rem;border-radius:14px}
  .st-key-workspace,.st-key-file_workspace {gap:1.25rem}
  .st-key-diak_page [role="tab"] {padding:.6rem .85rem}
  .file-facts {grid-template-columns:repeat(2,minmax(0,1fr));gap:.8rem}
  .input-notes {gap:.35rem}
}
@media(max-width:430px){
  .workspace-card-heading {gap:.6rem}
  .workspace-card-heading h2 {font-size:.77rem;letter-spacing:.06em}
  .st-key-arabic_input textarea {font-size:24px}
  .st-key-diak_page .arabic-result {font-size:25px;padding:1rem}
  .st-key-diak_page [role="tab"] {padding:.6rem .65rem;font-size:.8rem}
  .st-key-manual_actions,.st-key-file_actions {flex-direction:column;align-items:stretch}
  .st-key-manual_actions > div,.st-key-file_actions > div {width:100%}
  .st-key-manual_actions button,.st-key-file_actions button {width:100%}
  .st-key-diak_page .empty-output {padding:1rem}
}

.icon-copy {--icon:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22black%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Crect%20x%3D%228%22%20y%3D%228%22%20width%3D%2212%22%20height%3D%2213%22%20rx%3D%222%22%2F%3E%3Cpath%20d%3D%22M15%208V3H3v13h5%22%2F%3E%3C%2Fsvg%3E")}

.st-key-diak_page [role="tab"]:first-child p {display:flex;align-items:center;gap:.5rem}
.st-key-diak_page [role="tab"]:first-child p::before {content:"";width:19px;height:19px;flex:0 0 19px;background:currentColor;mask:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22black%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M8%207H4a1%201%200%200%200-1%201v8a1%201%200%200%200%201%201h4M16%207h4a1%201%200%200%201%201%201v8a1%201%200%200%201-1%201h-4M12%203v18M9%203h6M9%2021h6%22%2F%3E%3C%2Fsvg%3E") center/contain no-repeat}
[data-testid="stHeading"] h2 {font-size:1.4rem;line-height:1.4}
[data-testid="stHeading"] h3 {font-size:1.2rem;line-height:1.4}
[data-testid="stMetricValue"] {font-size:1.75rem}
[class*="st-key-example_panel_"] {padding:1rem 1.1rem}
.st-key-process_manual button,.st-key-process_file button {gap:.45rem;justify-content:center}
.st-key-process_manual button > div,.st-key-process_file button > div {flex:0 1 auto;width:auto}
@media(max-width:780px){
  :root {--ui-control-height:44px}
}

@media(prefers-reduced-motion:reduce){
  *,*::before,*::after {scroll-behavior:auto!important;animation:none!important;transition:none!important}
}
@media print{
  [data-testid="stSidebar"],[data-testid="stHeader"],[data-testid="stToolbar"] {display:none!important}
  .stMainBlockContainer {max-width:none;padding:0}
  .arabic-result {max-height:none;overflow:visible}
  .st-key-home_hero::before {display:none}
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
    "manual_result_input": None, "manual_processing": None,
    "manual_correction": None, "manual_correction_generation": 0,
    "upload_snapshot": None, "upload_validation_cache": None,
    "file_result": None, "file_result_signature": None, "file_processing": None,
    "csv_column": None, "example_results": {}, "uploader_generation": 0,
    "upload_files": {}, "active_upload_id": None, "upload_messages": [],
    "queue_zip": None,
}.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default


def clear_manual_correction():
    widget_key = f"_manual_correction_{st.session_state.manual_correction_generation}"
    st.session_state.pop(widget_key, None)
    st.session_state.manual_correction = None
    # New form/widget identities also discard Streamlit's unsubmitted browser draft.
    st.session_state.manual_correction_generation += 1


def restore_model_result():
    clear_manual_correction()


def apply_manual_correction(widget_key, generation):
    # Form callbacks run before rendering, keeping the result and exports in sync.
    if generation == st.session_state.manual_correction_generation and widget_key in st.session_state:
        st.session_state.manual_correction = st.session_state[widget_key]


def sidebar_page_changed():
    st.session_state.mobile_navigation_request = uuid4().hex


def close_mobile_sidebar(request_id):
    """Use the native close control once, only after sidebar navigation on mobile.

    Streamlit 1.63 has no public viewport-aware sidebar toggle API. These scoped
    test IDs identify its own close button; no styles or component state are forced.
    """
    script = """<script>(() => {
      const request = __REQUEST__;
      if (window._unimalSidebarNavigation === request) return;
      window._unimalSidebarNavigation = request;
      if (!matchMedia('(max-width:780px)').matches) return;
      requestAnimationFrame(() => requestAnimationFrame(() => {
        const sidebar = document.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return;
        if (sidebar.getAttribute('aria-expanded') === 'true') {
          sidebar.querySelector('[data-testid="stSidebarCollapseButton"] button')?.click();
        }
        requestAnimationFrame(() => {
          const animations = sidebar.getAnimations?.() ?? [];
          Promise.allSettled(animations.map(animation => animation.finished)).then(() => {
            requestAnimationFrame(() => {
              const currentSidebar = document.querySelector('[data-testid="stSidebar"]');
              if (window._unimalSidebarNavigation !== request || currentSidebar?.getAttribute('aria-expanded') !== 'false') return;
              const heading = document.querySelector('[data-testid="stMain"] h1');
              const active = document.activeElement;
              if (active !== document.body && active !== heading && !currentSidebar.contains(active)) return;
              if (heading) { heading.tabIndex = -1; heading.focus({preventScroll:true}); }
            });
          });
        });
      }));
    })();</script>""".replace("__REQUEST__", dumps(request_id))
    with st.container(key="mobile_navigation"):
        st.html(script, unsafe_allow_javascript=True)


def navigate(page, example=None):
    st.session_state.page = page
    if example is not None:
        st.session_state.manual_input = example
        st.session_state["_manual_input"] = example
        st.session_state.manual_result = None
        st.session_state.manual_result_input = None
        st.session_state.manual_processing = None
        clear_manual_correction()


def manual_changed():
    st.session_state.manual_input = st.session_state["_manual_input"]
    st.session_state.manual_result = None
    st.session_state.manual_result_input = None
    st.session_state.manual_processing = None
    clear_manual_correction()


def reset_manual():
    st.session_state.manual_input = ""
    st.session_state["_manual_input"] = ""
    st.session_state.manual_result = None
    st.session_state.manual_result_input = None
    st.session_state.manual_processing = None
    clear_manual_correction()


def reset_file():
    if st.session_state.active_upload_id in st.session_state.upload_files:
        queue.remove_upload(st.session_state, st.session_state.active_upload_id)
        st.session_state.queue_zip = None
        return
    st.session_state.upload_snapshot = None
    st.session_state.upload_validation_cache = None
    st.session_state.file_result = None
    st.session_state.file_result_signature = None
    st.session_state.file_processing = None
    st.session_state.csv_column = None
    st.session_state.uploader_generation += 1


def upload_changed(widget_key):
    if widget_key != f"_upload_{st.session_state.uploader_generation}":
        return
    uploaded = st.session_state.get(widget_key) or []
    queue.add_uploads(st.session_state, uploaded if isinstance(uploaded, list) else [uploaded])
    st.session_state.queue_zip = None
    # A fresh native widget releases the submitted batch's buffers. Removing a
    # native upload never implicitly deletes a stored result; use explicit delete.
    st.session_state.uploader_generation += 1


def active_file_changed():
    file_id = st.session_state.get("_active_file")
    if file_id in st.session_state.upload_files:
        queue.persist_active(st.session_state)
        queue.load_active(st.session_state, file_id)


def reset_all_files():
    queue.clear_uploads(st.session_state)
    st.session_state.queue_zip = None


def column_changed(upload_identity, file_id=None):
    snapshot = st.session_state.upload_snapshot
    # An upload/remove and an old selectbox event can share one rerun. Ignore
    # callbacks from the previous file; let Streamlit clean up absent widgets.
    if (snapshot is None or (snapshot["name"], snapshot["digest"]) != upload_identity
            or file_id != st.session_state.active_upload_id):
        return
    column = st.session_state.get("_csv_column")
    if column is None:
        return
    st.session_state.csv_column = column
    st.session_state.file_result = None
    st.session_state.file_result_signature = None
    st.session_state.file_processing = None
    entry = st.session_state.upload_files.get(file_id)
    if entry:
        entry["export_bytes"] = None
    st.session_state.queue_zip = None
    queue.persist_active(st.session_state)


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


def card_heading(number, title):
    st.html(f'<header class="workspace-card-heading"><span class="step-number">{escape(number)}</span>'
            f'<h2>{escape(title)}</h2></header>')


def empty_output(message="Masukkan teks Arab, kemudian pilih Proses Diakritisasi."):
    st.html(f'<div class="empty-output">{ui_icon("file")}<strong>Hasil akan tampil di sini</strong>'
            f'<p>{escape(message)}</p></div>')


def copy_button(text, key, disabled=False):
    """Only JSON-encoded text enters the script; user content cannot become HTML/JS."""
    element_id = f"copy_{key}"
    payload = dumps(str(text), ensure_ascii=True).replace("<", "\\u003c")
    html = (f'<div class="copy-control"><button type="button" class="copy-button" id="{element_id}" '
            f'{"disabled" if disabled else ""}>{ui_icon("copy")}<span>Salin</span></button>'
            f'<span class="copy-status" id="{element_id}_status" role="status" aria-live="polite"></span></div>')
    if not disabled:
        html += """<script>(() => {
          const button = document.getElementById(__ID__);
          const status = document.getElementById(__STATUS__);
          const text = __TEXT__;
          if (!button) return;
          function fallback() {
            const area = document.createElement('textarea');
            area.value = text; area.readOnly = true;
            area.style.cssText = 'position:fixed;left:-10000px;top:0';
            document.body.appendChild(area); area.select();
            let copied = false;
            try { copied = document.execCommand('copy'); }
            finally { area.remove(); button.focus(); }
            if (!copied) throw new Error('copy blocked');
          }
          button.onclick = async () => {
            try {
              if (window.isSecureContext && navigator.clipboard?.writeText) {
                try { await navigator.clipboard.writeText(text); } catch (_) { fallback(); }
              } else { fallback(); }
              status.textContent = 'Teks disalin.';
            } catch (_) { status.textContent = 'Akses salin ditolak browser. Pilih dan salin teks hasil.'; }
          };
        })();</script>""".replace("__ID__", dumps(element_id)).replace("__STATUS__", dumps(element_id + "_status")).replace("__TEXT__", payload)
    st.html(html, width="content", unsafe_allow_javascript=not disabled)


def result_actions(text, key, filename="hasil_diakritisasi.txt", data=None, disabled=False):
    with st.container(horizontal=True, key=f"{key}_result_actions"):
        copy_button(text, key, disabled=disabled)
        st.download_button("Unduh TXT", data if data is not None else text.encode("utf-8"),
                           file_name=filename, mime="text/plain; charset=utf-8",
                           key=f"download_{key}", icon=":material/download:", disabled=disabled,
                           on_click="ignore")


def input_notes(text):
    st.html('<div class="input-notes"><span>Teks dibaca dari kanan ke kiri. Harakat masukan '
            'akan dihapus sebelum prediksi ulang.</span>'
            f'<span class="manual-char-count"><span id="manual_char_count">{len(text):,}</span> karakter</span></div>'
            """<script>(() => {
              function bindCounter() {
                const area = document.querySelector('.st-key-arabic_input textarea');
                const counter = document.getElementById('manual_char_count');
                if (!area || !counter) return false;
                if (area._unimalCounter) area.removeEventListener('input', area._unimalCounter);
                area._unimalCounter = () => { counter.textContent = Array.from(area.value).length.toLocaleString('id-ID'); };
                area.addEventListener('input', area._unimalCounter); area._unimalCounter();
                return true;
              }
              if (!bindCounter()) {
                const observer = new MutationObserver(() => { if (bindCounter()) observer.disconnect(); });
                observer.observe(document.body, {childList:true, subtree:true});
                window.setTimeout(() => observer.disconnect(), 10000);
              }
              // Close the native mobile drawer after choosing a destination.
              if (window._unimalMobileNav) {
                document.removeEventListener('change', window._unimalMobileNav, true);
                document.removeEventListener('click', window._unimalMobileNav, true);
              }
              window._unimalMobileNav = event => {
                if (innerWidth > 780 || !event.target.closest('.st-key-nav')) return;
                window.setTimeout(() => {
                  const sidebar = document.querySelector('[data-testid="stSidebar"]');
                  if (sidebar?.getAttribute('aria-expanded') === 'true') {
                    sidebar.querySelector('[data-testid="stSidebarCollapseButton"] button')?.click();
                  }
                }, 80);
              };
              document.addEventListener('change', window._unimalMobileNav, true);
              document.addEventListener('click', window._unimalMobileNav, true);
            })();</script>""", unsafe_allow_javascript=True)


def manual_result_guard(snapshot):
    """Client-side stale notice only; manual_changed and the server equality check remain authoritative."""
    marker = (f'<span id="manual_result_snapshot" hidden data-valid="{str(snapshot is not None).lower()}">'
              f'{escape(snapshot if snapshot is not None else "")}</span>')
    script = """<script>(() => {
      const renderId = __RENDER_ID__;
      window._unimalManualGuard?.dispose();
      let observer, timeout;
      function sync() {
        const area = document.querySelector('.st-key-arabic_input textarea');
        const marker = document.getElementById('manual_result_snapshot');
        const card = document.querySelector('.st-key-manual_result_card');
        const payload = document.querySelector('.st-key-manual_result_payload');
        if (!area || !marker || !card || !payload) return null;
        const stale = marker.dataset.valid === 'true' && area.value !== marker.textContent;
        card.dataset.inputStale = String(stale);
        payload.inert = stale;
        if (stale) window._unimalPendingResultScroll?.();
        return stale;
      }
      function onInput(event) {
        if (event.target instanceof Element && event.target.matches('.st-key-arabic_input textarea')) sync();
      }
      function blockStaleAction(event) {
        if (event.target instanceof Element && event.target.closest('.st-key-manual_result_payload') && sync()) {
          event.preventDefault();
          event.stopImmediatePropagation();
        }
      }
      function dispose() {
        observer?.disconnect();
        window.clearTimeout(timeout);
        document.removeEventListener('input', onInput, true);
        document.removeEventListener('click', blockStaleAction, true);
        document.removeEventListener('submit', blockStaleAction, true);
      }
      window._unimalManualGuard = {dispose, sync, renderId};
      document.addEventListener('input', onInput, true);
      document.addEventListener('click', blockStaleAction, true);
      document.addEventListener('submit', blockStaleAction, true);
      // Only wait for Streamlit to mount this render's UI-owned anchors; no polling.
      if (sync() === null) {
        observer = new MutationObserver(() => {
          if (sync() !== null) { observer.disconnect(); window.clearTimeout(timeout); }
        });
        observer.observe(document.body, {childList:true, subtree:true});
        timeout = window.setTimeout(() => observer.disconnect(), 10000);
      }
    })();</script>""".replace("__RENDER_ID__", dumps(uuid4().hex))
    with st.container(key="manual_guard"):
        st.html(marker + script, unsafe_allow_javascript=True)


def processing_call(function, *args, summary_key=None, **kwargs):
    with st.status("Model sedang memproses teks…", expanded=True) as status:
        bar = st.empty()
        progress_text = st.empty()

        def callback(current, total):
            if total > 0:
                bar.progress(min(1.0, max(0.0, current / total)))
                progress_text.caption(f"Memproses bagian {current} dari {total}…")

        # Time only the backend call, including its real progress callbacks.
        started = perf_counter()
        try:
            result = function(*args, progress_callback=callback, **kwargs)
        except Exception as error:
            result = {"success": False, "message": f"Pemrosesan gagal: {error}"}
        finally:
            elapsed = perf_counter() - started
        if summary_key is not None:
            st.session_state[summary_key] = {"elapsed_seconds": elapsed} if result.get("success") else None
        bar.empty()
        progress_text.empty()
        if result.get("success"):
            status.update(label="Pemrosesan selesai. Hasil tersedia di bawah.", state="complete", expanded=False)
        else:
            status.update(label=result.get("message", "Pemrosesan belum berhasil."), state="error", expanded=False)
    return result


def scroll_to_result(mode, request_id):
    """Emit once for a successful process action, never for a saved result rerender."""
    targets = {"manual": ".st-key-manual_result_card", "file": ".st-key-file_result_card"}
    selector = targets[mode]
    # Both values are UI-owned constants/UUIDs, never user text or file contents.
    script = """<script>(() => {
      const request = __REQUEST__;
      const selector = __SELECTOR__;
      const seen = window._unimalScrolledResults ??= new Set();
      if (seen.has(request)) return;
      seen.add(request);
      window._unimalPendingResultScroll?.();
      let frame, observer, timeout, scheduled = false;
      function cancel() {
        observer?.disconnect();
        window.clearTimeout(timeout);
        window.cancelAnimationFrame(frame);
        document.removeEventListener('pointerdown', cancel, true);
        document.removeEventListener('keydown', cancel, true);
        if (window._unimalPendingResultScroll === cancel) delete window._unimalPendingResultScroll;
      }
      function ready() {
        if (scheduled) return;
        const card = document.querySelector(selector);
        const download = card?.querySelector('[data-testid="stDownloadButton"] button:not(:disabled)');
        if (!card || !download || !card.getBoundingClientRect().height || !download.getClientRects().length) return;
        scheduled = true;
        observer?.disconnect();
        frame = requestAnimationFrame(() => {
          frame = requestAnimationFrame(() => {
            if (!card.isConnected || !download.getClientRects().length) { cancel(); return; }
            cancel();
            const heading = card.querySelector('h2');
            if (heading) { heading.tabIndex = -1; heading.focus({preventScroll:true}); }
            const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
            card.scrollIntoView({behavior:reduced ? 'instant' : 'smooth', block:'start', inline:'nearest'});
          });
        });
      }
      window._unimalPendingResultScroll = cancel;
      // A later interaction cancels a pending jump instead of interrupting the user.
      document.addEventListener('pointerdown', cancel, true);
      document.addEventListener('keydown', cancel, true);
      observer = new MutationObserver(ready);
      observer.observe(document.body, {childList:true, subtree:true});
      timeout = window.setTimeout(cancel, 5000);
      ready();
    })();</script>""".replace("__REQUEST__", dumps(request_id)).replace("__SELECTOR__", dumps(selector))
    with st.container(key=f"scroll_{mode}"):
        st.html(script, unsafe_allow_javascript=True)


def unknown_warning(result):
    unknown = result.get("unknown_characters") or []
    if unknown:
        st.warning("Karakter di luar kosakata ditemukan dan dipetakan ke <UNK>.")
        st.text("Karakter: " + ", ".join(repr(char) for char in unknown))


def compare_prediction(original_text, prediction):
    """Display the exact input snapshot and output; never normalize either text."""
    with st.expander("Bandingkan dengan Teks Asli", key="manual_comparison"):
        st.html(
            '<div class="prediction-comparison">'
            '<section class="comparison-panel" aria-labelledby="comparison-original-title">'
            '<h3 id="comparison-original-title">Teks Asli</h3>'
            '<div class="arabic-text" lang="ar" dir="rtl">'
            f'{escape(original_text)}</div></section>'
            '<section class="comparison-panel" aria-labelledby="comparison-prediction-title">'
            '<h3 id="comparison-prediction-title">Hasil Prediksi</h3>'
            '<div class="arabic-text" lang="ar" dir="rtl">'
            f'{escape(prediction)}</div></section></div>'
        )


def processing_summary(items, note, *, file=False):
    """Build a compact, escaped UI summary without modifying backend results."""
    class_name = "processing-summary processing-summary-file" if file else "processing-summary"
    cards = ''.join(
        f'<div class="processing-stat"><dt>{escape(label)}</dt><dd>{escape(str(value))}</dd></div>'
        for label, value in items
    )
    return (f'<section class="{class_name}" aria-label="Ringkasan Hasil Pemrosesan">'
            f'<h3>{ui_icon("info")}Ringkasan Hasil Pemrosesan</h3>'
            f'<dl>{cards}</dl><p>{escape(note)}</p></section>')


def processing_duration(metadata):
    seconds = metadata["elapsed_seconds"]
    return "< 0,001 dtk" if seconds < .001 else f"{seconds:.3f} dtk".replace(".", ",")


def manual_processing_summary(original_text):
    metadata = st.session_state.manual_processing
    if metadata is None:
        return ""
    source = "Koreksi Pengguna" if st.session_state.manual_correction is not None else "Prediksi Model"
    return processing_summary([
        ("Karakter input", f"{len(original_text):,}".replace(",", ".")),
        ("Waktu pemrosesan", processing_duration(metadata)),
        ("Status", "Selesai"), ("Sumber teks aktif", source),
    ], "Durasi panggilan prediksi, termasuk praproses dan penggabungan hasil; tanpa waktu interaksi pengguna.")


def file_processing_summary(result, filename):
    metadata = st.session_state.file_processing
    if metadata is None:
        return
    statuses = result.get("status_summary")
    counts = statuses if statuses is not None else {}
    available = statuses is not None
    count = lambda value: f"{value:,}".replace(",", ".") if available else "Tidak tersedia"
    st.html(processing_summary([
        (f'Berkas {result["input_type"].upper()}', filename),
        ("Baris diperiksa", count(sum(counts.values()))),
        ("Berhasil diprediksi", count(counts.get("berhasil", 0))),
        ("Tidak diprediksi", count(sum(counts.get(name, 0) for name in ("kosong", "non_arab", "campuran")))),
        ("Baris gagal", count(counts.get("gagal", 0))),
        ("Waktu pemrosesan", processing_duration(metadata)),
    ], "Baris kosong, non-Arab, dan campuran tidak diprediksi model; teks dapat dinormalisasi sesuai aturan sistem. "
       "Durasi mencakup pembacaan berkas, pemrosesan, dan penyiapan unduhan; tanpa waktu interaksi pengguna.", file=True))


def correction_editor(prediction):
    """Keep the editor draft and applied correction separate from model output."""
    generation = st.session_state.manual_correction_generation
    widget_key = f"_manual_correction_{generation}"
    if widget_key not in st.session_state:
        correction = st.session_state.manual_correction
        st.session_state[widget_key] = prediction if correction is None else correction
    with st.expander("Koreksi Hasil", key="manual_correction_editor"):
        with st.container(key="arabic_correction"):
            with st.form(f"manual_correction_form_{generation}", enter_to_submit=False, border=False):
                st.text_area("Koreksi Manual Harakat", key=widget_key, height=180)
                st.caption("Sunting teks, lalu pilih Terapkan Koreksi. Perubahan editor belum digunakan "
                           "oleh Salin dan Unduh TXT sebelum diterapkan.")
                st.form_submit_button("Terapkan Koreksi", type="primary", on_click=apply_manual_correction,
                                      args=(widget_key, generation))
        st.button("Kembalikan Hasil Model", key="restore_manual_model", on_click=restore_model_result,
                  icon=":material/undo:")
        st.caption("Hasil asli model tetap tersedia melalui Kembalikan Hasil Model "
                   "atau Akses Hasil Asli Model setelah koreksi diterapkan.")


def show_prediction(result, key, original_text=None):
    if not result.get("success"):
        st.error(result.get("message", "Pemrosesan belum berhasil."))
        empty_output("Perbaiki masukan, lalu jalankan prediksi kembali.")
        result_actions("", key, disabled=True)
        return
    corrected = original_text is not None and st.session_state.manual_correction is not None
    export_text = st.session_state.manual_correction if corrected else result["prediction"]
    if original_text is not None:
        st.html(manual_processing_summary(original_text))
        source = "Koreksi Pengguna" if corrected else "Prediksi Model"
        st.caption(f"{source} · Salin dan Unduh TXT menggunakan teks yang ditampilkan di bawah.")
    arabic(export_text, result=True)
    result_actions(export_text, key, filename="hasil_koreksi_manual.txt" if corrected else "hasil_diakritisasi.txt")
    if original_text is not None:
        if export_text == "":
            st.warning("Koreksi manual kosong. Salin dan Unduh TXT akan menghasilkan teks kosong.")
        compare_prediction(original_text, result["prediction"])
        correction_editor(result["prediction"])
        if corrected:
            with st.expander("Akses Hasil Asli Model", key="manual_original_result"):
                st.caption("Salin dan Unduh TXT di bagian ini menggunakan hasil asli model, tanpa koreksi manual.")
                arabic(result["prediction"])
                result_actions(result["prediction"], "manual_model", filename="hasil_asli_model.txt")
    st.caption("Prediksi otomatis; periksa kembali ketepatan harakat sebelum digunakan.")
    unknown_warning(result)
    if result.get("had_diacritics"):
        st.info("Harakat pada masukan dihapus sebelum prediksi ulang.")
    with st.expander("Detail pemrosesan"):
        st.write({
            "Karakter masukan bersih": result.get("total_characters"),
            "Huruf Arab": result.get("arabic_letters"),
            "Jumlah segmen": result.get("total_chunks"),
            "Panjang tiap segmen": result.get("chunk_lengths"),
        })


def ui_icon(name):
    """Local CSS-mask icon, with its visible text label kept accessible."""
    return f'<span class="ui-icon icon-{escape(name)}" aria-hidden="true"></span>'


def render_home():
    with st.container(key="home_hero"):
        st.html(
            '<section class="hero">'
            '<div class="eyebrow">Penelitian Natural Language Processing</div>'
            '<div class="hero-rule" aria-hidden="true"></div>'
            '<h1>Diakritisasi Otomatis Teks Arab Gundul'
            '<span>pada Kitab Fathul Qorib menggunakan BiLSTM-CRF</span></h1>'
            '<p>Sistem ini memprediksi harakat pada teks Arab tanpa harakat secara otomatis '
            'menggunakan model BiLSTM-CRF yang dilatih pada korpus Tashkeela dan '
            'disesuaikan dengan data Kitab Fathul Qorib.</p></section>'
        )
        with st.container(key="home_actions", horizontal=True):
            st.button("Mulai Diakritisasi", type="primary", icon=":material/arrow_forward:",
                      key="home_cta", on_click=navigate, args=("Diakritisasi",))
            st.button("Lihat Contoh", icon=":material/description:", key="home_examples",
                      on_click=navigate, args=("Contoh Teks",))
    steps = (
        ("01", "file", "Masukkan Teks Arab",
         "Unggah berkas TXT/CSV atau ketik teks Arab tanpa harakat."),
        ("02", "gear", "Proses Diakritisasi",
         "Sistem memprediksi harakat menggunakan model BiLSTM-CRF."),
        ("03", "file", "Lihat Hasil",
         "Periksa hasil diakritisasi, lalu salin atau unduh dalam format TXT atau CSV."),
    )
    cards = ''.join(
        f'<article class="guide-item"><div class="number">{number}</div><div>'
        f'{ui_icon(icon)}<h3>{title}</h3><p>{description}</p></div></article>'
        for number, icon, title, description in steps
    )
    st.html('<section class="usage-panel" aria-labelledby="usage-title">'
            '<h2 id="usage-title">Cara Menggunakan Sistem</h2>'
            '<div class="section-rule" aria-hidden="true"></div>'
            f'<div class="guide-grid">{cards}</div></section>')


def render_manual():
    scroll_request = None
    if "_manual_input" not in st.session_state:
        st.session_state["_manual_input"] = st.session_state.manual_input
    with st.container(key="workspace"):
        with st.container(key="manual_card", border=True):
            card_heading("01", "MASUKKAN TEKS ARAB")
            with st.container(key="arabic_input"):
                text = st.text_area("Teks Arab", key="_manual_input", height=160,
                                    placeholder=EXAMPLES[0], on_change=manual_changed)
            input_notes(text)
            with st.container(horizontal=True, key="manual_actions"):
                process = st.button("Proses Diakritisasi", key="process_manual", type="primary", disabled=not READY)
                st.button("Bersihkan", key="reset_manual", on_click=reset_manual, icon=":material/delete_sweep:")
            if process:
                clear_manual_correction()
                st.session_state.manual_processing = None
                st.session_state.manual_input = text
                if not text.strip():
                    st.session_state.manual_result = {"success": False,
                        "message": "Masukkan teks Arab terlebih dahulu sebelum memproses."}
                    st.error(st.session_state.manual_result["message"])
                else:
                    st.session_state.manual_result = processing_call(
                        engine.predict_long_text, text, summary_key="manual_processing")
                st.session_state.manual_result_input = text
                if st.session_state.manual_result.get("success"):
                    scroll_request = uuid4().hex
            with st.expander("Panduan masukan"):
                st.write("Gunakan teks Arab tanpa campuran huruf Latin. Teks panjang dibagi otomatis "
                         "menjadi segmen maksimal 300 karakter, lalu digabungkan sesuai urutan.")
        with st.container(key="manual_result_card", border=True):
            card_heading("02", "HASIL PREDIKSI")
            with st.container(key="manual_stale_notice"):
                st.html('<div class="manual-stale-notice" role="status" aria-live="polite">'
                        '<strong>Input berubah, jalankan prediksi kembali.</strong><br>'
                        'Hasil sebelumnya tidak berlaku untuk input yang sedang disunting.</div>')
            result = st.session_state.manual_result
            current = bool(result) and st.session_state.manual_result_input == text
            with st.container(key="manual_result_payload"):
                if current:
                    show_prediction(result, "manual", original_text=st.session_state.manual_result_input)
                    if result.get("success"):
                        render_reference_panel(None, None, None, "manual", result,
                                               source_text=st.session_state.manual_result_input)
                else:
                    empty_output()
                    result_actions("", "manual", disabled=True)
            manual_result_guard(text if current and result.get("success") else None)
        if scroll_request:
            scroll_to_result("manual", scroll_request)


def read_upload_validation(snapshot):
    """Validate using the original backend readers without changing uploaded bytes."""
    if snapshot is None:
        return {"success": False, "message": "Belum ada berkas yang dipilih."}
    suffix = Path(snapshot["name"]).suffix.lower()
    if snapshot["data"] is None or snapshot["size"] > 5 * 1024 * 1024:
        return {"success": False, "message": "Ukuran berkas melebihi batas 5 MB."}
    if not snapshot["data"]:
        return {"success": False, "message": "Berkas kosong. Pilih berkas yang berisi data."}
    if suffix not in (".txt", ".csv"):
        return {"success": False, "message": "Format berkas tidak didukung. Gunakan TXT atau CSV."}
    if engine is None:
        return {"success": False, "message": "Backend belum tersedia untuk memeriksa berkas."}
    try:
        if suffix == ".csv":
            decoded = engine.decode_text_bytes(snapshot["data"])
            if not decoded.get("success"):
                return decoded
            error = queue.text_capacity_error(decoded["text"], csv_input=True)
            if error:
                return {"success": False, "message": error}
        preview = (engine.read_csv_file(uploaded_copy(snapshot)) if suffix == ".csv"
                   else engine.decode_text_bytes(snapshot["data"]))
        if preview.get("success") and suffix == ".csv" and not len(preview["dataframe"].columns):
            return {"success": False, "message": "CSV tidak memiliki kolom yang dapat dipilih."}
        if preview.get("success") and suffix == ".csv":
            frame = preview["dataframe"]
            if len(frame) > queue.MAX_ROWS or len(frame.columns) > queue.MAX_COLUMNS or frame.size > queue.MAX_CELLS:
                return {"success": False, "message": "CSV melampaui batas 10.000 baris, 100 kolom, atau 100.000 sel per berkas."}
            preview["arabic_columns"] = engine.detect_arabic_columns(preview["dataframe"])
        if preview.get("success") and suffix == ".txt":
            error = txt_control_error(preview["text"]) or queue.text_capacity_error(preview["text"])
            if error:
                return {"success": False, "message": error, "encoding": preview.get("encoding")}
        return preview
    except Exception as error:
        return {"success": False, "message": f"Berkas tidak dapat dibaca: {error}"}


def inspect_upload(snapshot):
    """Keep one private parse/validation for the active file, independent of widgets.

    Readers have fixed parsing options. Include their policy version and suffix
    alongside the content digest, so a rename can reuse parsing but a different
    format or payload cannot. Cache failures too; replace the entry, never append.
    Return an isolated copy so render/processing code cannot mutate cached data.
    """
    if snapshot is None:
        st.session_state.upload_validation_cache = None
        return {"success": False, "message": "Belum ada berkas yang dipilih."}
    key = (snapshot["digest"], snapshot["size"], Path(snapshot["name"]).suffix.lower(),
           "backend-readers-v1/txt-controls-v1/5MiB", engine is not None)
    cached = st.session_state.upload_validation_cache
    if cached is None or cached["key"] != key:
        cached = {"key": key, "validation": read_upload_validation(snapshot)}
        st.session_state.upload_validation_cache = cached
    return deepcopy(cached["validation"])


def inspect_queue():
    """Validate each new entry once, keeping all parses private to this session."""
    queue.persist_active(st.session_state)
    for entry in st.session_state.upload_files.values():
        cache = entry["upload_validation_cache"]
        if cache is not None and cache.get("backend_available") == (engine is not None):
            continue
        snapshot = entry["upload_snapshot"]
        validation = read_upload_validation(snapshot)
        cache = {"key": (snapshot["digest"], snapshot["size"], Path(snapshot["name"]).suffix.lower(),
                         "backend-readers-v1/txt-controls-v1/5MiB", engine is not None),
                 "validation": validation, "backend_available": engine is not None}
        if queue.retained_bytes(st.session_state.upload_files) + queue.retained_bytes(cache) > queue.MAX_RETAINED_BYTES:
            cache["validation"] = {"success": False, "message": "Batas memori sesi tercapai. Hapus berkas lain lalu unggah kembali."}
        entry["upload_validation_cache"] = cache
        if cache["validation"].get("success") and Path(snapshot["name"]).suffix.lower() == ".csv":
            frame = cache["validation"]["dataframe"]
            names = [item["column"] for item in cache["validation"]["arabic_columns"]]
            options = names + [col for col in frame.columns if col not in names]
            if entry["csv_column"] not in options:
                entry["csv_column"] = "teks_gundul" if "teks_gundul" in options else options[0]
    if st.session_state.active_upload_id in st.session_state.upload_files:
        queue.load_active(st.session_state, st.session_state.active_upload_id)


def process_active_file(validation):
    # Recheck on the server as well as disabling the button in the UI.
    if not READY or not validation.get("success"):
        return
    snapshot = st.session_state.upload_snapshot
    column = st.session_state.csv_column if Path(snapshot["name"]).suffix.lower() == ".csv" else None
    entry = st.session_state.upload_files.get(st.session_state.active_upload_id)
    st.session_state.queue_zip = None
    if entry:
        entry["export_bytes"] = None
        entry["file_result"] = None
    st.session_state.file_result = None
    result = processing_call(engine.process_uploaded_file, uploaded_copy(snapshot),
                             text_column=column, summary_key="file_processing")
    try:
        export = queue.result_export(result)
    except Exception as error:
        result = {"success": False, "message": f"Hasil tidak dapat diekspor: {error}"}
        export = None
        st.session_state.file_processing = None
    if entry and result.get("success"):
        candidate = {"file_result": result, "export_bytes": export}
        other_exports = sum(len(e.get("export_bytes") or b"") for e in st.session_state.upload_files.values())
        if (queue.retained_bytes(st.session_state.upload_files) + queue.retained_bytes(candidate) > queue.MAX_RETAINED_BYTES
                or other_exports + len(export) > queue.MAX_EXPORT_BYTES - 1024 * 1024):
            result = {"success": False, "message": "Hasil melampaui batas memori sesi/ekspor. Hapus hasil lain atau gunakan berkas lebih kecil; tidak ada teks yang dipotong."}
            export = None
            st.session_state.file_processing = None
    st.session_state.file_result = result
    st.session_state.file_result_signature = (snapshot["name"], snapshot["digest"], column)
    queue.persist_active(st.session_state)
    if entry:
        entry["export_bytes"] = export


def process_all_files():
    """Sequential work, no shared active result, and no inference on rerenders."""
    selected = st.session_state.active_upload_id
    queue.persist_active(st.session_state)
    for file_id, entry in list(st.session_state.upload_files.items()):
        validation = (entry["upload_validation_cache"] or {}).get("validation", {})
        if not validation.get("success") or (entry.get("file_result") or {}).get("success"):
            continue
        queue.load_active(st.session_state, file_id)
        st.text(f"Memproses: {entry['upload_snapshot']['name']}")
        try:
            process_active_file(validation)
        except Exception as error:
            # Includes export failures after a successful backend call.
            st.session_state.file_result = {"success": False, "message": f"Pemrosesan berkas gagal: {error}"}
            st.session_state.file_processing = None
            entry["export_bytes"] = None
            queue.persist_active(st.session_state)
    queue.load_active(st.session_state, selected)


def render_queue_controls():
    entries = st.session_state.upload_files
    if not entries:
        return
    inspect_queue()
    with st.container(horizontal=True):
        process_all = st.button("Proses Semua", key="process_all_files", type="primary", disabled=not READY)
        st.button("Hapus Semua", key="reset_all_files", on_click=reset_all_files, icon=":material/delete_sweep:")
    if process_all and READY:
        process_all_files()
    rows = []
    for entry in entries.values():
        snapshot = entry["upload_snapshot"]
        status, message = queue.entry_status(entry)
        cache = (entry.get("upload_validation_cache") or {}).get("validation", {})
        rows.append({"Nama": snapshot["name"], "Format": Path(snapshot["name"]).suffix.lstrip(".").upper(),
                     "Ukuran (byte)": snapshot["size"], "Validitas": "Valid" if cache.get("success") else "Tidak valid",
                     "Status": status, "Ringkasan": str((entry.get("file_result") or {}).get("status_summary") or message)})
    # A native table cannot expose raw CSV downloads (export policy above).
    with st.expander("Daftar berkas sesi", expanded=True):
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.session_state["_active_file"] = st.session_state.active_upload_id
    ids = list(entries)
    st.selectbox("Berkas untuk pratinjau, proses ulang, atau unduh", ids, key="_active_file",
                 format_func=lambda file_id: f"{ids.index(file_id) + 1}. {entries[file_id]['upload_snapshot']['name']}",
                 on_change=active_file_changed)


def render_queue_zip():
    entries = st.session_state.upload_files
    if not entries:
        return
    if st.button("Siapkan ZIP", key="prepare_queue_zip"):
        queue.persist_active(st.session_state)
        try:
            st.session_state.queue_zip = queue.build_zip(entries)
        except Exception as error:
            st.session_state.queue_zip = None
            st.error(f"ZIP belum dapat disiapkan: {error}")
    if st.session_state.queue_zip is not None:
        st.download_button("Unduh Semua (ZIP)", st.session_state.queue_zip, file_name="hasil_diakritisasi_semua.zip",
                           mime="application/zip", key="download_all_files", on_click="ignore")
    else:
        st.caption("Siapkan ZIP untuk mengunduh semua hasil tersimpan beserta ringkasan setiap berkas, termasuk berkas gagal atau belum diproses.")


def file_information(snapshot, validation):
    kind = Path(snapshot["name"]).suffix.lstrip(".").upper() or "Tanpa ekstensi"
    size = len(snapshot["data"]) if snapshot["data"] is not None else snapshot["size"]
    facts = (("Jenis", kind),
             ("Ukuran", f"{size:,} byte ({size / 1024:.1f} KB)"),
             ("Pemeriksaan", "Valid" if validation.get("success") else "Belum valid"))
    st.html('<div class="file-facts">' + ''.join(
        f'<div class="file-fact"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in facts) + '</div>')
    details = []
    if validation.get("encoding"):
        details.append("Encoding terbaca: " + str(validation["encoding"]))
    if kind == "CSV" and validation.get("success"):
        details.append(f"Jumlah baris data: {len(validation['dataframe']):,}")
    if details:
        st.html('<p class="file-meta">' + escape(" | ".join(details)) + '</p>')


def render_file_result(result, filename):
    if not result.get("success"):
        st.error(result.get("message", "Berkas belum berhasil diproses."))
        empty_output("Periksa berkas dan coba proses kembali.")
        return
    file_processing_summary(result, filename)
    st.success(result["message"])
    output_filename = (queue.safe_output_name(filename, result["input_type"], st.session_state.active_upload_id)
                       if st.session_state.active_upload_id else result["output_filename"])
    if result["input_type"] == "txt":
        arabic(result["prediction"], result=True)
        result_actions(result["prediction"], "file", filename=output_filename, data=result["download_bytes"])
    else:
        # Fit short results without growing beyond the existing scrollable area.
        table_height = min(320, 35 * (len(result["dataframe"]) + 1) + 3)
        st.dataframe(result["dataframe"], hide_index=True, width="stretch", height=table_height, row_height=35)
        with st.container(horizontal=True, key="file_result_actions"):
            st.download_button("Unduh CSV", spreadsheet_safe_csv(result["dataframe"]), file_name=output_filename,
                               mime="text/csv; charset=utf-8", key="download_file", icon=":material/download:",
                               on_click="ignore")
    if result["input_type"] == "csv":
        st.caption("CSV unduhan diamankan untuk spreadsheet: nilai berisiko formula diberi awalan tab, termasuk header. "
                   "Angka negatif ASCII murni (-12, -3.5, -1e3) tetap; bentuk ambigu diekspor sebagai teks. "
                   "Pratinjau dan hasil model tidak diubah; periksa kembali harakat.")
    else:
        st.caption("Unduhan mengikuti keluaran backend, termasuk normalisasi sistem. Periksa kembali ketepatan harakat.")
    unknown_warning(result)
    for warning in result.get("warnings") or []:
        st.warning(f"Baris {warning['line']}: {warning['note']}")
    summary = result.get("status_summary") or {}
    if summary:
        with st.expander("Ringkasan status pemrosesan"):
            labels = {"berhasil": "Berhasil diprediksi", "kosong": "Kosong; tidak diprediksi",
                      "non_arab": "Non-Arab; tidak diprediksi", "campuran": "Campuran; tidak diprediksi",
                      "gagal": "Gagal diproses"}
            st.dataframe(pd.DataFrame([{"Status": labels.get(name, name), "Jumlah": count}
                                      for name, count in summary.items()]), hide_index=True, width="stretch")
            st.caption("Istilah ‘dipertahankan’ pada catatan backend berarti tidak diprediksi model; "
                       "teks dapat dinormalisasi dan tidak dijamin identik dengan masukan.")


def render_file():
    sync_reference_file(st.session_state.active_upload_id)
    scroll_request = st.session_state.pop("queue_scroll_request", None)
    with st.container(key="file_workspace"):
        with st.container(key="file_upload_card", border=True):
            card_heading("01", "UNGGAH TEKS ARAB")
            st.html('<p class="upload-help">Pilih berkas, periksa pratinjau, lalu proses diakritisasi. '
                    'Format TXT atau CSV, maksimal 5 MiB per berkas, 20 berkas dan total masukan 20 MiB per sesi. '
                    'Tambahkan berkas tanpa menghapus hasil sebelumnya. Baris kosong, non-Arab, dan campuran tidak diprediksi; '
                    'teks dapat dinormalisasi sesuai aturan sistem.</p>')
            widget_key = f"_upload_{st.session_state.uploader_generation}"
            st.file_uploader("Pilih berkas TXT atau CSV", type=["txt", "csv"], key=widget_key,
                             accept_multiple_files=True,
                             max_upload_size=5, on_change=upload_changed, args=(widget_key,),
                             help="Batch unggahan dipindahkan ke daftar sesi dan pemilih unggahan dikosongkan kembali. "
                                  "Berkas dan hasil tetap tersimpan saat menambah unggahan atau berpindah halaman.")
            st.caption("Batas pemrosesan per berkas: TXT 250.000 karakter/10.000 baris; CSV 1.000.000 karakter, "
                       "10.000 baris, 100 kolom, 100.000 sel. Anggaran data sesi 128 MiB dan ekspor 32 MiB. "
                       "Berkas yang melampaui batas ditolak tanpa pemotongan teks.")
            for message in st.session_state.upload_messages:
                st.warning(message)
            render_queue_controls()
            snapshot = st.session_state.upload_snapshot
            validation = inspect_upload(snapshot)
            selected_column = None
            if snapshot is not None:
                st.caption(f"Berkas aktif: {snapshot['name']} — tersimpan dalam sesi ini. "
                           "Tambahkan unggahan untuk menyimpan berkas lain, atau pilih Hapus Berkas untuk menghapus yang aktif.")
                file_information(snapshot, validation)
                if not validation.get("success"):
                    st.error(validation["message"])
                elif Path(snapshot["name"]).suffix.lower() == ".csv":
                    dataframe = validation["dataframe"]
                    candidates = validation["arabic_columns"]
                    names = [item["column"] for item in candidates]
                    options = names + [col for col in dataframe.columns if col not in names]
                    if st.session_state.csv_column not in options:
                        st.session_state.csv_column = "teks_gundul" if "teks_gundul" in options else options[0]
                    st.session_state["_csv_column"] = st.session_state.csv_column
                    selected_column = st.selectbox("Pilih Kolom Teks Arab", options, key="_csv_column", on_change=column_changed,
                                                   args=((snapshot["name"], snapshot["digest"]), st.session_state.active_upload_id))
                    if names:
                        st.caption("Kandidat kolom teks Arab: " + ", ".join(map(str, names)))
                    with st.expander("Pratinjau CSV", expanded=True):
                        st.dataframe(dataframe.head(5), hide_index=True, width="stretch")
                        st.caption("Pratinjau maksimal 5 baris. Pemrosesan menggunakan seluruh berkas.")
                    with st.expander("Pratinjau teks kolom terpilih (RTL)"):
                        arabic("\n".join(dataframe[selected_column].head(5).astype(str)))
                else:
                    with st.expander("Pratinjau TXT", expanded=True):
                        excerpt = "".join(validation["text"].splitlines(keepends=True)[:8])[:4000]
                        st.html('<div class="txt-preview"><div class="arabic-text" lang="ar" dir="rtl">'
                                + escape(excerpt) + '</div></div>')
                        st.caption("Pratinjau maksimal 8 baris atau 4.000 karakter. Seluruh berkas tetap diproses.")
            else:
                st.caption(validation["message"])
            signature = ((snapshot["name"], snapshot["digest"], selected_column) if snapshot else None)
            with st.container(horizontal=True, key="file_actions"):
                process = st.button("Proses Ulang Berkas" if st.session_state.file_result else "Proses Diakritisasi", type="primary", key="process_file",
                                    disabled=not (READY and validation.get("success")))
                st.button("Hapus Berkas", key="reset_file", on_click=reset_file,
                          disabled=snapshot is None, icon=":material/delete_sweep:")
            if process and READY and validation.get("success"):
                process_active_file(validation)
                if st.session_state.file_result.get("success"):
                    scroll_request = uuid4().hex
                if st.session_state.active_upload_id:
                    st.session_state.queue_scroll_request = scroll_request
                    st.rerun()
            if not READY:
                st.info("Model belum siap; pemrosesan berkas dinonaktifkan.")
        with st.container(key="file_result_card", border=True):
            card_heading("02", "HASIL DIAKRITISASI")
            result = st.session_state.file_result
            if result and validation.get("success") and st.session_state.file_result_signature == signature:
                render_file_result(result, snapshot["name"])
                if result.get("success"):
                    render_reference_panel(snapshot["data"], validation.get("dataframe"), selected_column,
                                           st.session_state.active_upload_id or snapshot["digest"], result,
                                           source_text=validation.get("text"))
            else:
                empty_output("Pilih berkas TXT atau CSV yang valid, lalu jalankan Proses Diakritisasi.")
        if scroll_request:
            scroll_to_result("file", scroll_request)
        queue.persist_active(st.session_state)
        render_queue_zip()


def render_diakritisasi():
    with st.container(key="diak_page"):
        heading("Area kerja", "Diakritisasi Teks Arab",
                "Tambahkan harakat pada teks Arab secara otomatis menggunakan model BiLSTM-CRF.")
        manual_tab, file_tab = st.tabs(["Input Teks", ":material/upload_file: Unggah TXT / CSV"])
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


def sidebar_logo():
    """Render the original emblem with its baked-in light background filtered out."""
    data = b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 423">'
           '<title>Logo Universitas Malikussaleh</title><defs>'
           '<filter id="logo-background" color-interpolation-filters="sRGB">'
           '<feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  -2 -2 -2 0 5"/>'
           '</filter></defs><image width="360" height="423" '
           f'href="data:image/png;base64,{data}" filter="url(#logo-background)"/></svg>')
    st.image(svg, width=76)


with st.sidebar:
    if LOGO_PATH.exists():
        sidebar_logo()
    st.html('<div class="brand-university">Universitas Malikussaleh</div>'
            '<div class="brand-rule" aria-hidden="true"></div>'
            '<div class="brand-kicker">Penelitian NLP</div>'
            '<div class="brand-title">Sistem Diakritisasi<br>Teks Arab Gundul</div>')
    with st.container(key="nav"):
        st.radio("Navigasi utama", PAGES, key="page", label_visibility="collapsed", width="stretch",
                 on_change=sidebar_page_changed)
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

st.html('<header class="topline">'
        f'<div class="breadcrumb">{ui_icon("home")}<span class="separator">/</span>'
        f'<span aria-current="page">{escape(st.session_state.page)}</span></div>'
        f'<div class="topline-book">{ui_icon("book")}<span>Kitab Fathul Qorib</span></div>'
        '</header>')

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

navigation_request = st.session_state.pop("mobile_navigation_request", None)
if navigation_request:
    close_mobile_sidebar(navigation_request)
