"""UI-1 presentation, scoped to manual input and the shared Diakritisasi header.

Artwork is local SVG, never a screenshot or user-supplied HTML. Logo stays original.
"""
from base64 import b64encode
from pathlib import Path
from urllib.parse import quote

ASSETS = Path(__file__).resolve().parent / 'assets'
LEARNING_ART = b64encode((ASSETS.parent / '.streamlit' / 'sidebar_book.svg').read_bytes()).decode('ascii')
BOOK = b64encode((ASSETS / 'sidebar_book.svg').read_bytes()).decode('ascii')


def page_header():
    return ('<header class="input-page-hero">'
            '<div class="input-hero-title">'
            '<div><h1>Diakritisasi Teks Arab</h1>'
            '<p class="manual-hero-copy">Otomatisasi pemberian harakat pada teks Arab kitab Fathul Qorib '
            'dengan model BiLSTM–CRF.</p>'
            '<p class="upload-hero-copy">Diakritisasi otomatis teks Arab menggunakan model BiLSTM–CRF.</p>'
            '</div></div>'
            '<div class="input-hero-illustration">'
            f'<img src="data:image/svg+xml;base64,{LEARNING_ART}" '
            'alt="Satu guru dan satu murid laki-laki belajar kitab terbuka"></div></header>')


CSS = '''<style>
/* Shared header/sidebar only; upload cards and their controls keep existing styles. */
.stApp {background:#F8F9F4}
.topline {display:none}
.stMainBlockContainer {padding-top:.65rem}
.st-key-diak_page {max-width:100%;gap:1rem}
.st-key-diak_page .input-page-hero {position:relative;isolation:isolate;background:#F2F8F3;border:1px solid #D5E6DC;border-radius:17px;padding:.75rem 1.25rem;min-height:0;display:flex;align-items:center;justify-content:space-between;gap:1.2rem}
.st-key-diak_page .input-hero-title {flex:1;min-width:0}
.st-key-diak_page .input-hero-title::after {content:"";display:block;width:84px;height:2px;margin-top:.7rem;background:#CCA74D}
.st-key-diak_page .input-hero-illustration {flex:none;width:180px;max-width:33%;line-height:0}
.st-key-diak_page .input-hero-illustration img {display:block;width:100%;height:auto;mix-blend-mode:multiply}
.st-key-diak_page .input-page-hero h1 {font:700 clamp(2.25rem,2.5vw,2.375rem)/1.15 var(--serif);letter-spacing:-.025em;color:#063F30;margin:0 0 .45rem}
.input-page-hero p {font:400 1rem/1.45 var(--serif);color:#526579;margin:0;max-width:36rem}
[data-testid="stSidebar"] .brand-kicker,[data-testid="stSidebar"] .brand-title,[data-testid="stSidebar"] .brand-rule {display:none}
[data-testid="stSidebar"] .input-sidebar-art {height:235px;max-height:28vh;margin:.6rem -.5rem 0;background:url("data:image/svg+xml;base64,__BOOK__") center bottom/contain no-repeat;pointer-events:none}
[data-testid="stSidebar"] .sidebar-note {padding:.8rem .85rem;border:1px solid #D8E9DF;background:#E7F2EB;border-radius:13px}
[data-testid="stSidebar"] .sidebar-note p {font-size:.78rem;line-height:1.65;margin:.45rem 0 0}
.st-key-nav [role="radiogroup"] > label {min-height:48px;border-radius:8px}
.st-key-diak_page [data-testid="stTabs"] {gap:.65rem}
.st-key-diak_page [role="tablist"] {background:transparent;border:0;padding:0;gap:.7rem;margin:0;border-radius:0}
.st-key-diak_page [role="tab"] {border:1px solid #DEE6E2;background:#FFFFFF;color:#3F5D57;min-width:200px;min-height:46px;justify-content:center;box-shadow:0 2px 8px #0C342308}
.st-key-diak_page [role="tab"] p {font-size:.95rem}
.st-key-diak_page [role="tab"][aria-selected="true"] {background:#00583F;color:#fff;border-color:#00583F}
.st-key-workspace {gap:.9rem}
.st-key-workspace .st-key-manual_card,.st-key-workspace .st-key-manual_result_card {padding:1.15rem 1.2rem 1rem;border:1px solid #E7ECE5;border-radius:17px;box-shadow:0 5px 20px #103B2410;position:relative}
.st-key-workspace .st-key-manual_card {gap:.5rem}
.st-key-workspace .workspace-card-heading {position:relative;margin:0 0 .65rem;align-items:center;gap:.85rem;min-height:44px}
.st-key-workspace .workspace-card-heading .step-number {width:42px;height:42px;flex-basis:42px;font:700 1.3rem/1 var(--serif);background:#E2F0E6}
.st-key-workspace .workspace-card-heading h2 {font:700 1.35rem/1.3 var(--serif);letter-spacing:0;color:#063F30}
.st-key-workspace .workspace-card-heading p {font:.83rem/1.5 var(--sans);color:#66778B;margin:.1rem 0 0}
.st-key-manual_card .workspace-card-heading {padding-right:135px}
.st-key-workspace .manual-char-count {position:absolute;right:0;top:.4rem;color:#62778B;font-size:.8rem}
.st-key-workspace .st-key-arabic_input textarea {min-height:116px;font-size:25px;line-height:2.05;padding:.7rem 1rem;background:#fff;border:1px solid #D6DFE3;border-radius:10px;box-shadow:inset 0 1px 3px #18392A03}
.st-key-workspace .st-key-arabic_input textarea::placeholder {color:#8A98A9}
.st-key-workspace .input-example {color:#85909F;font-size:.74rem;margin:-.25rem 0 .1rem;line-height:1.6}
.st-key-workspace .input-notes {font-size:.73rem;line-height:1.65;color:#647587;max-width:100%;gap:.4rem}
.st-key-workspace .st-key-manual_actions {flex-direction:row-reverse;justify-content:flex-start;gap:.6rem;margin-top:.2rem}
.st-key-workspace .st-key-process_manual button {background:#00583F;border-color:#00583F;width:248px;max-width:100%;min-width:0;min-height:46px;padding:.55rem 1rem;font-family:var(--serif);font-size:1.05rem;box-shadow:0 2px 5px #004A2B16}
.st-key-workspace .st-key-process_manual button::after {content:"→";font:400 1.35rem/1 var(--sans);margin-left:.35rem}
.st-key-workspace .st-key-manual_result_card > [data-testid="stElementContainer"] .workspace-card-heading {min-height:66px;padding-right:48%}
.st-key-manual_result_card .st-key-translation_reference_view_manual {position:absolute;right:1.2rem;top:1.1rem;width:45%;max-width:430px;z-index:1}
.st-key-manual_result_card .st-key-translation_reference_view_manual button {font-size:.8rem;min-height:40px}
.st-key-workspace .processing-summary {background:#EAF4EC;border:1px solid #DBEADF;border-radius:12px;padding:.8rem 1rem;margin:.2rem 0 .4rem}
.st-key-workspace .processing-summary h3 {font:700 1.12rem/1.3 var(--serif);margin:0 0 .45rem;gap:.7rem}
.st-key-workspace .processing-summary h3 .ui-icon {display:none}
.st-key-workspace .processing-summary h3::before {content:"✓";display:grid;place-items:center;width:30px;height:30px;flex:0 0 30px;border-radius:50%;background:#007044;color:white;font:700 1.1rem/1 var(--sans)}
.st-key-workspace .processing-summary dl {display:flex;flex-wrap:wrap;gap:.45rem 1rem}
.st-key-workspace .processing-stat {display:flex;align-items:baseline;gap:.35rem;padding:0;border:0;background:none}
.st-key-workspace .processing-stat dt,.st-key-workspace .processing-stat dd {font-size:.75rem;margin:0;line-height:1.5}
.st-key-workspace .processing-summary > p {font-size:.68rem;margin-top:.45rem}
.st-key-workspace .st-key-manual_result_payload {gap:.7rem}
.st-key-workspace .st-key-manual_result_actions {gap:.55rem;margin:.35rem 0}
.st-key-workspace .st-key-manual_result_actions button {min-height:44px}
.st-key-workspace .st-key-manual_result_actions .copy-button {font-size:.85rem}
.st-key-workspace [class*="st-key-translation_card_manual_"] {padding:0;border:0;box-shadow:none;background:transparent}
.st-key-workspace [class*="st-key-translation_columns_manual_"] [data-testid="stColumn"] {border:1px solid #D9E9DF;border-radius:12px;overflow:hidden;padding:.8rem;background:#FBFEFC}
.st-key-workspace [class*="st-key-translation_columns_manual_"] [data-testid="stColumn"]:first-child {background:#FFFCF4;border-color:#EFE1BE}
.st-key-workspace [class*="st-key-translation_columns_manual_"] [data-testid="stColumn"]:first-child [data-testid="stMarkdownContainer"] {color:#8A510E}
.st-key-workspace [class*="st-key-translation_columns_manual_"] [data-testid="stMarkdownContainer"] p {font:600 1rem/1.5 var(--serif)}
.st-key-workspace [class*="st-key-translation_columns_manual_"] .translation-indonesian {font:400 1.05rem/1.7 var(--serif);color:#19273B;padding:.3rem .1rem}
.st-key-workspace [class*="st-key-translation_columns_manual_"] .arabic-text {font-size:27px;line-height:2.05;color:#172235;padding:.3rem .1rem}
.st-key-workspace .st-key-arabic_correction {margin-top:.2rem}
@media(max-width:1100px){
 .st-key-manual_result_card .st-key-translation_reference_view_manual {position:static;width:100%;max-width:none}
 .st-key-workspace .st-key-manual_result_card > [data-testid="stElementContainer"] .workspace-card-heading {padding-right:0;min-height:44px}
}
@media(max-width:780px){
 .stMainBlockContainer {padding-top:3.1rem}
 .st-key-diak_page .input-page-hero {padding:1rem;gap:1rem;border-radius:13px}
 .st-key-diak_page .input-hero-illustration {width:150px}
 .st-key-diak_page .input-page-hero h1 {font-size:1.65rem;line-height:1.25;margin:0}
 .input-page-hero p {font-size:.94rem;line-height:1.5;margin-top:.35rem}
 .st-key-diak_page [role="tablist"] {gap:.45rem;width:100%}
 .st-key-diak_page [role="tab"] {min-width:0;min-height:44px;flex:1;padding:.65rem .55rem}
 .st-key-diak_page [role="tab"] p {font-size:.82rem}
 .st-key-workspace .st-key-manual_card,.st-key-workspace .st-key-manual_result_card {padding:.9rem;border-radius:13px}
 .st-key-workspace .workspace-card-heading {gap:.6rem}
 .st-key-workspace .workspace-card-heading .step-number {width:34px;height:34px;flex-basis:34px;font-size:1.1rem}
 .st-key-workspace .workspace-card-heading h2 {font-size:1.08rem}
 .st-key-workspace .workspace-card-heading p {font-size:.74rem}
 .st-key-manual_card .workspace-card-heading {padding-right:82px}
 .st-key-workspace .manual-char-count {top:.3rem;right:0;font-size:.68rem}
 .st-key-workspace .st-key-manual_actions {flex-direction:column;align-items:stretch}
 .st-key-workspace .st-key-manual_actions > div {width:100%}
 .st-key-workspace .st-key-process_manual button,.st-key-workspace .st-key-reset_manual button {width:100%;min-width:0}
 .st-key-workspace .input-example {font-size:.68rem}
 .st-key-workspace .st-key-manual_result_actions {flex-wrap:wrap}
 .st-key-workspace .processing-summary {padding:.7rem .8rem}
 .st-key-workspace .processing-summary dl {gap:.4rem .7rem}
 .st-key-workspace .processing-stat dt,.st-key-workspace .processing-stat dd {font-size:.7rem}
 .st-key-workspace [class*="st-key-translation_columns_manual_"] .arabic-text {font-size:25px;line-height:2}
}
@media(max-width:540px){
 .st-key-diak_page .input-page-hero {flex-direction:column;align-items:stretch;gap:.6rem}
 .st-key-diak_page .input-hero-illustration {width:104px;max-width:60%;align-self:flex-end}
}
@media(prefers-reduced-motion:reduce){.st-key-workspace * {scroll-behavior:auto!important}}
</style>'''.replace('__BOOK__', BOOK)

# Result-only refinements: inputs, upload controls, and inference stay unchanged.
_ICON_PATHS = {
    'book': '<path d="M12 5v15M12 5C8 2 3 3 2 4v15c3-2 7-1 10 1 3-2 7-3 10-1V4c-3-2-7-2-10 1Z"/>',
    'translate': '<path d="M3 5h12M9 2v3M5 5c1 5 4 8 8 10M13 5c-1 5-5 9-10 11M14 21l4-10 4 10M16 17h4"/>',
    'file': '<path d="M14 2H5v20h14V7Zm0 0v5h5M8 12h8M8 16h8"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
    'check': '<path d="m4 12 5 5L20 6"/>',
    'model': '<rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 9h6v6H9ZM9 2v3m6-3v3M9 19v3m6-3v3M2 9h3m-3 6h3m14-6h3m-3 6h3"/>',
    'pencil': '<path d="m4 16-1 5 5-1L21 7l-4-4Zm10-10 4 4M4 16l4 4"/>',
}
_ICONS = {name: 'url("data:image/svg+xml,' + quote(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="black" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    + path + '</svg>', safe='') + '")' for name, path in _ICON_PATHS.items()}

CSS += '''<style>
.st-key-diak_page .result-icon {display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;flex:0 0 24px;color:inherit}
.st-key-diak_page .result-icon::before {content:"";display:block;width:100%;height:100%;background:currentColor;mask:var(--result-symbol) center/contain no-repeat}
.st-key-diak_page .result-success {position:relative;isolation:isolate;background:#F2F9F5;border:1px solid #D8E9DF;border-radius:15px;padding:1.35rem 1.5rem;overflow:hidden;margin:.25rem 0 1.05rem}
.st-key-diak_page .result-success::after {content:"";position:absolute;z-index:-1;right:-30px;bottom:-65px;width:210px;height:170px;border:1px solid #C9DCC9;border-top:3px solid #D7BF80;border-radius:65% 25% 0 0;background:#E4F0E6;transform:rotate(-14deg);opacity:.65;pointer-events:none}
.st-key-diak_page .result-success-heading {display:flex;align-items:center;gap:1.05rem;margin-bottom:1.3rem}
.st-key-diak_page .result-success-heading > .result-icon {padding:14px;box-sizing:content-box;width:28px;height:28px;flex-basis:28px;border-radius:50%;background:#08794C;color:white}
.st-key-diak_page .result-success-heading h3 {display:block;font:700 1.65rem/1.25 var(--serif);color:#142839;margin:0 0 .35rem}
.st-key-diak_page .result-success-heading h3::before {display:none}
.st-key-diak_page .result-success-heading p {font-size:.92rem;line-height:1.55;color:#53677A;margin:0}
.st-key-diak_page .result-success dl {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7rem;margin:0}
.st-key-diak_page .result-success .processing-stat {display:flex;align-items:center;gap:.65rem;min-width:0;border:0;border-right:1px solid #D8E9DF;padding:0 .5rem 0 0;background:transparent}
.st-key-diak_page .result-success .processing-stat:last-child {border-right:0}
.st-key-diak_page .result-success .processing-stat > .result-icon {padding:10px;box-sizing:content-box;width:22px;height:22px;flex-basis:22px;border-radius:50%;background:#E0EFE6;color:#176047}
.st-key-diak_page .result-success .processing-stat dt {font:.77rem/1.5 var(--sans);color:#5D7283;margin:0}
.st-key-diak_page .result-success .processing-stat dd {font:700 1rem/1.5 var(--serif);color:#174B38;margin:.15rem 0 0;overflow-wrap:anywhere}
.st-key-diak_page .result-success .result-summary-note {font-size:.68rem;color:#5D7283;line-height:1.5;margin:.8rem 0 0}
.st-key-diak_page .st-key-manual_result_card .workspace-card-heading h2 {font-size:1.75rem;color:#142839}
.st-key-diak_page [class*="st-key-translation_reference_view_"] button {min-height:44px;gap:.5rem}
.st-key-diak_page [class*="st-key-translation_reference_view_"] button::before {content:"";display:block;width:21px;height:21px;flex:0 0 21px;background:currentColor;mask:__BOOK_ICON__ center/contain no-repeat}
.st-key-diak_page [class*="st-key-translation_reference_view_"] button:last-child::before {mask-image:__TRANSLATE_ICON__}
.st-key-diak_page [class*="st-key-translation_reference_view_"] button[aria-checked="true"] {border-color:#168055;background:#E7F3EB;color:#075838}
.st-key-diak_page [class*="st-key-translation_page_header_"] {gap:1rem;justify-content:space-between;flex-wrap:wrap;margin:.45rem 0 .1rem}
.st-key-diak_page [class*="st-key-translation_page_header_"] > [data-testid="stElementContainer"]:has(.translation-section-heading) {flex:1 1 280px;min-width:0}
.st-key-diak_page .translation-section-heading {display:flex;align-items:center;gap:.85rem;color:#176047;min-width:0}
.st-key-diak_page .translation-section-heading > .result-icon {width:32px;height:32px;flex-basis:32px}
.st-key-diak_page .translation-section-heading h3 {font:700 1.3rem/1.4 var(--serif);color:#142839;margin:0 0 .2rem}
.st-key-diak_page .translation-section-heading p {font:.84rem/1.55 var(--sans);color:#5D7283;margin:0}
.st-key-diak_page [class*="st-key-translation_card_"] {border:0;padding:0;background:transparent;box-shadow:none}
.st-key-diak_page [class*="st-key-translation_columns_"] [data-testid="stColumn"] {background:#F2F9F5;border:1px solid #D8E9DF;border-radius:14px;padding:1.1rem 1.2rem;min-width:0;overflow:visible}
.st-key-diak_page [class*="st-key-translation_columns_"] [data-testid="stColumn"]:first-child {background:#FAF5E9;border-color:#E9D7AE}
.st-key-diak_page .result-pane-heading {display:flex;align-items:center;gap:.65rem;font:700 1.25rem/1.45 var(--serif);color:#176047;margin:0 0 .7rem;direction:ltr}
.st-key-diak_page .result-pane-heading .result-icon {background:#E0EFE6;border-radius:50%;padding:9px;box-sizing:content-box}
.st-key-diak_page [class*="st-key-translation_columns_"] [data-testid="stColumn"]:first-child .result-pane-heading {color:#80550D}
.st-key-diak_page [class*="st-key-translation_columns_"] [data-testid="stColumn"]:first-child .result-icon {background:#F4E7C6}
.st-key-diak_page [class*="st-key-translation_columns_"] .translation-indonesian {font:400 1.07rem/1.8 var(--serif);color:#302B24;padding:.25rem 0 .5rem}
.st-key-diak_page [class*="st-key-translation_columns_"] .arabic-text {font-size:29px;line-height:2.25;color:#183E31;padding:.25rem 0 .65rem;overflow:visible;max-height:none}
.st-key-diak_page [class*="st-key-translation_page_header_"] input {font-weight:600;text-align:center}
.st-key-diak_page [class*="st-key-translation_reference_prev_"],.st-key-diak_page [class*="st-key-translation_reference_next_"] {min-height:44px}
.st-key-diak_page .st-key-manual_result_card .arabic-result {max-height:none;overflow:visible;background:#F2F9F5;color:#183E31;border-color:#D8E9DF}
.st-key-diak_page [role="tab"]:first-child p::before {mask-image:__PENCIL_ICON__}
@media(max-width:1100px){
 .st-key-diak_page .result-success dl {grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}
 .st-key-diak_page .result-success .processing-stat:nth-child(2) {border-right:0}
}
@media(max-width:780px){
 .st-key-diak_page .result-success {padding:1rem}
 .st-key-diak_page .result-success-heading {gap:.7rem;margin-bottom:1rem}
 .st-key-diak_page .result-success-heading > .result-icon {width:22px;height:22px;flex-basis:22px;padding:10px}
 .st-key-diak_page .result-success-heading h3 {font-size:1.4rem}
 .st-key-diak_page .result-success-heading p {font-size:.8rem}
 .st-key-diak_page .result-success .processing-stat {gap:.45rem}
 .st-key-diak_page .result-success .processing-stat > .result-icon {width:18px;height:18px;flex-basis:18px;padding:7px}
 .st-key-diak_page .result-success .processing-stat dt {font-size:.7rem}
 .st-key-diak_page .result-success .processing-stat dd {font-size:.9rem}
 .st-key-diak_page .st-key-manual_result_card .workspace-card-heading h2 {font-size:1.3rem}
 .st-key-diak_page [class*="st-key-translation_columns_"] [data-testid="stColumn"] {padding:1rem}
 .st-key-diak_page .result-pane-heading {font-size:1.12rem;flex-wrap:wrap;gap:.6rem}
 .st-key-diak_page .result-pane-heading .result-icon {width:21px;height:21px;flex-basis:21px;padding:7px}
 .st-key-diak_page [class*="st-key-translation_columns_"] .arabic-text {font-size:27px;line-height:2.2}
}
@media(max-width:370px){.st-key-diak_page .result-success dl {grid-template-columns:1fr}.st-key-diak_page .result-success .processing-stat {border-right:0}}
/* Small-screen refinements; desktop geometry and typography stay unchanged. */
@media(max-width:430px){
 .st-key-diak_page .input-page-hero {display:grid;grid-template-columns:minmax(0,1fr) 56px;align-items:center;padding:.7rem .8rem;gap:.4rem .5rem}
 .st-key-diak_page .input-hero-title,.st-key-diak_page .input-hero-title > div {display:contents}
 .st-key-diak_page .input-page-hero h1 {grid-column:1 / -1;font-size:1.375rem;line-height:1.25}
 .st-key-diak_page .input-page-hero p {grid-column:1;font-size:.85rem;line-height:1.5;margin:0}
 .st-key-diak_page .input-hero-title::after {grid-column:1 / -1;margin-top:.2rem}
 .st-key-diak_page .input-hero-illustration {grid-column:2;grid-row:2;width:56px;max-width:none;align-self:center}
 .st-key-workspace .st-key-arabic_input textarea {font-size:24px;line-height:2;padding:.65rem .75rem}
 .st-key-diak_page .result-success {padding:.8rem}
 .st-key-diak_page .result-success-heading {gap:.5rem;margin-bottom:.65rem}
 .st-key-diak_page .result-success-heading > .result-icon {width:20px;height:20px;flex-basis:20px;padding:6px}
 .st-key-diak_page .result-success-heading h3 {font-size:1.2rem;line-height:1.35}
 .st-key-diak_page .result-success dl {grid-template-columns:repeat(2,minmax(0,1fr));gap:.65rem}
 .st-key-diak_page .result-success .processing-stat {gap:.35rem;border-right:0}
 .st-key-diak_page .result-success .processing-stat > .result-icon {width:16px;height:16px;flex-basis:16px;padding:5px}
 .st-key-diak_page .result-success .processing-stat dd {font-size:.85rem;line-height:1.5;overflow-wrap:anywhere}
 .st-key-diak_page [class*="st-key-translation_columns_"] [data-testid="stColumn"] {padding:.7rem}
 .st-key-diak_page .result-pane-heading {font-size:1rem;line-height:1.5;flex-wrap:nowrap;gap:.4rem}
 .st-key-diak_page .result-pane-heading .result-icon {width:18px;height:18px;flex-basis:18px;padding:5px;flex-shrink:0}
 .st-key-diak_page [class*="st-key-translation_columns_"] .arabic-text {font-size:25px;line-height:2;overflow:visible}
 .st-key-diak_page [class*="st-key-translation_columns_"] .translation-indonesian {font-size:1rem;line-height:1.75}
 .st-key-diak_page .st-key-file_workspace .processing-summary-file {padding:.8rem}
 .st-key-diak_page .st-key-file_workspace .processing-summary-file h3 {font-size:1.2rem;margin-bottom:.6rem}
 .st-key-diak_page .st-key-file_workspace .processing-summary-file dl {gap:.6rem}
 .st-key-diak_page .st-key-file_workspace .processing-summary-file > p {margin-top:.6rem}
}
</style>'''.replace('__BOOK_ICON__', _ICONS['book']).replace('__TRANSLATE_ICON__', _ICONS['translate']).replace('__PENCIL_ICON__', _ICONS['pencil'])
CSS += '<style>' + ''.join('.result-icon-' + name + '{--result-symbol:' + uri + '}'
                          for name, uri in _ICONS.items()) + '</style>'
