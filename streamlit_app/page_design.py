"""Shared sidebar and card presentation, following the Diakritisasi workspace.

The Diakritisasi cards and controls remain unchanged. Beranda keeps its
original hero, content, and navigation; only its card surfaces are aligned.
"""

from input_design import BOOK

CSS = '''<style>
:root {
 --page-background:#F8F9F4;
 --page-heading:#063F30;
 --page-muted:#526579;
 --page-primary:#00583F;
 --page-border:#E7ECE5;
 --page-radius:17px;
 --page-shadow:0 5px 20px #103B2410;
}
.stApp:has(.st-key-examples_page),.stApp:has(.st-key-about_page) {background:var(--page-background)}
:is(.st-key-examples_page,.st-key-about_page) {width:100%;max-width:var(--ui-workspace-width);margin-inline:auto;min-width:0;gap:.9rem}
.stApp:has(:is(.st-key-examples_page,.st-key-about_page)) .topline {display:none}
.stApp:has(:is(.st-key-examples_page,.st-key-about_page)) .footer-note {max-width:var(--ui-workspace-width);margin-inline:auto}
/* Use the existing UI-01 sidebar spacing on the other pages too. */
.stApp:has(:is(.st-key-home_hero,.st-key-examples_page,.st-key-about_page)) [data-testid="stSidebar"] :is(.brand-kicker,.brand-title,.brand-rule) {display:none}
.stApp:has(:is(.st-key-home_hero,.st-key-examples_page,.st-key-about_page)) .st-key-nav [role="radiogroup"] > label {min-height:48px;border-radius:8px}
.stApp:has(:is(.st-key-home_hero,.st-key-examples_page,.st-key-about_page)) .sidebar-note {padding:.8rem .85rem;border:1px solid #D8E9DF;background:#E7F2EB;border-radius:13px}
.stApp:has(:is(.st-key-home_hero,.st-key-examples_page,.st-key-about_page)) .sidebar-note p {font-size:.78rem;line-height:1.65;margin:.45rem 0 0}
[data-testid="stSidebar"] .input-sidebar-art {height:235px;max-height:28vh;margin:.6rem -.5rem 0;background:url("data:image/svg+xml;base64,__SIDEBAR_BOOK__") center bottom/contain no-repeat;pointer-events:none}
/* Headers share the reference typography and left edge, not its illustration. */
:is(.st-key-examples_page,.st-key-about_page) .page-heading h1,.st-key-diak_page .st-key-file_workspace .upload-page-hero h1 {font:700 clamp(1.8rem,3.1vw,2.7rem)/1.15 var(--serif);letter-spacing:-.025em;color:var(--page-heading);margin:0 0 .45rem}
:is(.st-key-examples_page,.st-key-about_page) .page-heading p,.st-key-diak_page .st-key-file_workspace .upload-page-hero p {font:400 1rem/1.5 var(--serif);color:var(--page-muted);margin:0}
:is(.st-key-examples_page,.st-key-about_page) .page-heading {padding:1.25rem 0 1.3rem}
.st-key-diak_page .st-key-file_workspace .upload-page-hero {padding:1.25rem 0 1.3rem;min-height:138px}
/* White surfaces and one spacing scale across the existing content groups. */
.stApp:has(.st-key-home_hero) .usage-panel,.st-key-examples_page [class*="st-key-example_panel_"],.st-key-about_page :is(.st-key-about_translation_card,.st-key-about_scope_card,.st-key-about_evaluation_card,.st-key-about_limitations_card),.st-key-diak_page .st-key-file_workspace :is(.st-key-file_upload_card,.st-key-file_management_card,.st-key-file_result_card) {padding:1.15rem 1.2rem 1rem;border:1px solid var(--page-border);border-radius:var(--page-radius);box-shadow:var(--page-shadow);background:#fff;min-width:0}
.stApp:has(.st-key-home_hero) .usage-panel h2 {font:700 1.35rem/1.3 var(--serif);color:var(--page-heading)}
.stApp:has(.st-key-home_hero) .guide-item {border-color:var(--page-border);border-radius:12px;background:#fff;padding:1rem;box-shadow:none}
.st-key-about_page [data-testid="stHeading"] :is(h2,h3),.st-key-diak_page .st-key-file_workspace .workspace-card-heading h2 {font:700 1.35rem/1.3 var(--serif);letter-spacing:0;color:var(--page-heading)}
.st-key-examples_page button {min-height:46px;border-radius:10px}
.st-key-examples_page [data-testid="stBaseButton-secondary"] {background:#fff;border-color:#D6DFE3;color:var(--page-heading)}
.st-key-examples_page [class*="st-key-example_panel_"] {gap:.75rem}
.st-key-examples_page [data-testid="stCaptionContainer"] {color:var(--page-muted)}
.st-key-about_page [data-testid="stMarkdownContainer"] :is(p,li) {line-height:1.75}
.st-key-about_page [data-testid="stMetric"] {background:var(--page-background);border-color:var(--page-border);border-radius:12px}
.st-key-about_page [data-testid="stExpander"] {background:#fff;border-color:#D6DFE3;border-radius:10px}
.st-key-diak_page .st-key-file_workspace .workspace-card-heading p {font:.83rem/1.5 var(--sans);color:#66778B}
.st-key-diak_page .st-key-file_workspace .st-key-process_file button {font:700 1.05rem/1.4 var(--serif)}
@media(max-width:780px){
 .stApp:has(:is(.st-key-examples_page,.st-key-about_page)) .stMainBlockContainer {padding-top:3.1rem}
:is(.st-key-examples_page,.st-key-about_page) .page-heading,.st-key-diak_page .st-key-file_workspace .upload-page-hero {padding:.5rem 0 1rem;min-height:0}
:is(.st-key-examples_page,.st-key-about_page) .page-heading h1,.st-key-diak_page .st-key-file_workspace .upload-page-hero h1 {font-size:1.5rem;line-height:1.25;margin:0}
:is(.st-key-examples_page,.st-key-about_page) .page-heading p,.st-key-diak_page .st-key-file_workspace .upload-page-hero p {font-size:.82rem;line-height:1.5;margin-top:.35rem}
 .st-key-diak_page .st-key-file_workspace .upload-page-hero::after {display:none}
 .st-key-diak_page .st-key-file_workspace .upload-page-hero p {max-width:100%}
.stApp:has(.st-key-home_hero) .usage-panel,.st-key-examples_page [class*="st-key-example_panel_"],.st-key-about_page :is(.st-key-about_translation_card,.st-key-about_scope_card,.st-key-about_evaluation_card,.st-key-about_limitations_card),.st-key-diak_page .st-key-file_workspace :is(.st-key-file_upload_card,.st-key-file_management_card,.st-key-file_result_card) {padding:.9rem;border-radius:13px}
.stApp:has(.st-key-home_hero) .usage-panel h2 {font-size:1.08rem}
.st-key-about_page [data-testid="stHeading"] :is(h2,h3),.st-key-diak_page .st-key-file_workspace .workspace-card-heading h2 {font-size:1.08rem}
 .st-key-diak_page .st-key-file_workspace .workspace-card-heading p {font-size:.74rem}
}
</style>'''.replace('__SIDEBAR_BOOK__', BOOK)
