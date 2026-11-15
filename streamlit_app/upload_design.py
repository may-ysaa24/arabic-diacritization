"""Upload-only presentation. Readers, limits, prediction, and exports stay in their existing modules."""
from html import escape
from pathlib import Path
from input_design import BOOK

from upload_queue import entry_status


def page_header():
    return ('<header class="upload-page-hero"><div><h1>Unggah TXT/CSV</h1>'
            '<p>Unggah berkas teks Arab untuk diproses menggunakan model BiLSTM–CRF.</p>'
            '</div></header>')


def dropzone_copy():
    """Presentation only; pointer events pass through to the native dropzone."""
    return ('<div class="upload-drop-copy"><span class="upload-drop-symbol" aria-hidden="true"></span>'
            '<strong>Seret dan lepas file di sini</strong>'
            '<p>atau klik tombol untuk memilih berkas</p></div>')


def empty_file_list():
    """Static guidance only; the native uploader remains the single input."""
    return ('<div class="upload-empty-state">'
            '<div class="upload-empty-intro" role="status">'
            '<span class="upload-empty-icon" aria-hidden="true">'
            '<span class="upload-empty-symbol"></span></span>'
            '<h3>Belum ada berkas dalam sesi ini.</h3>'
            '<p>Berkas yang diunggah akan muncul di sini.</p></div>'
            '<section class="upload-empty-tips" aria-label="Petunjuk singkat">'
            '<h4>Petunjuk singkat</h4><ol>'
            '<li>Unggah berkas TXT atau CSV di sebelah kiri.</li>'
            '<li>Berkas yang diunggah akan muncul di sini.</li>'
            '<li>Pilih berkas aktif untuk diproses.</li>'
            '<li>Gunakan <strong>Proses Diakritisasi</strong> atau <strong>Proses Semua</strong> sesuai kebutuhan.</li>'
            '</ol></section></div>')


def uploader_copy_script():
    """Localize native text nodes without replacing inputs or event handlers."""
    return '''<script>(() => {
      window._unimalUploadCopy?.dispose();
      let mounted = false;
      const observer = new MutationObserver(records => {
        const root = document.querySelector('.st-key-upload_drop_area');
        if (!root) { if (mounted) observer.disconnect(); return; }
        if (!mounted || records.some(r => root.contains(r.target))) sync(root);
      });
      function replaceText(element, value) {
        const nodes = element ? [...element.childNodes].filter(n => n.nodeType === Node.TEXT_NODE) : [];
        nodes.forEach((node, index) => {
          const next = index === 0 ? value : '';
          if (node.nodeValue !== next) node.nodeValue = next;
        });
      }
      function sync(root) {
        mounted = true;
        const zone = root.querySelector('[data-testid="stFileUploaderDropzone"]');
        if (!zone) return;
        const button = zone.querySelector('button');
        replaceText(button?.querySelector('[data-testid="stMarkdownContainer"] p'), 'Pilih File');
        if (button && button.getAttribute('aria-label') !== 'Pilih File')
          button.setAttribute('aria-label', 'Pilih File');
        replaceText(zone.querySelector('[data-testid="stFileUploaderDropzoneInstructions"] span'),
                    'Maksimal 5 MiB per berkas • Format: TXT, CSV');
      }
      observer.observe(document.body, {childList:true, subtree:true, characterData:true});
      const root = document.querySelector('.st-key-upload_drop_area');
      if (root) sync(root);
      window._unimalUploadCopy = {dispose:() => observer.disconnect()};
    })();</script>'''


def file_row(entry, *, active=False):
    snapshot = entry['upload_snapshot']
    kind = Path(snapshot['name']).suffix.lstrip('.').upper()
    size = snapshot['size']
    size_label = f'{size:,} byte' if size < 1024 else f'{size / 1024:,.1f} KiB'
    status, message = entry_status(entry)
    valid = (entry.get('upload_validation_cache') or {}).get('validation', {}).get('success')
    label = 'Valid · Siap diproses' if valid and status == 'Menunggu' else status
    validation = (entry.get('upload_validation_cache') or {}).get('validation', {})
    count = ''
    if valid and kind == 'CSV' and validation.get('dataframe') is not None:
        count = f" · {len(validation['dataframe']):,} baris data"
    elif valid and kind == 'TXT' and isinstance(validation.get('text'), str):
        count = f" · {len(validation['text'].splitlines()):,} baris teks"
    status_class = (' done' if status == 'Selesai' else
                    ' failed' if status in ('Gagal', 'Tidak valid') else '')
    detail = ('<p class="upload-row-error">' + escape(message) + '</p>') if status in ('Gagal', 'Tidak valid') else ''
    return ('<div class="upload-file-row' + (' is-active' if active else '') + '">'
            '<span class="ui-icon icon-file" aria-hidden="true"></span>'
            '<div class="upload-file-description"><strong dir="auto">' + escape(snapshot['name'])
            + '</strong><p>' + escape(kind + ' · ' + size_label + count) + '</p></div>'
            '<span class="upload-file-status' + status_class + '">' + escape(label) + '</span></div>' + detail)


CSS = '''<style>
/* The manual header and all result-pane styling remain unchanged. */
.input-page-hero .upload-hero-copy {display:none}
.st-key-file_workspace .upload-page-hero {position:relative;isolation:isolate;padding:1rem 0 .6rem;min-height:108px;display:flex;align-items:center}
.st-key-file_workspace .upload-page-hero::after {content:"";position:absolute;z-index:-1;inset:0 0 0 auto;width:22%;opacity:.2;background:url("data:image/svg+xml;base64,__BOOK__") right center/contain no-repeat;pointer-events:none}
.st-key-file_workspace .upload-page-hero > div {width:100%}
.st-key-file_workspace .upload-page-hero h1 {font:700 clamp(1.7rem,3vw,2.4rem)/1.25 var(--serif);color:#063F30;letter-spacing:-.02em;margin:0 0 .4rem}
.st-key-file_workspace .upload-page-hero p {font:.9rem/1.6 var(--sans);color:#526579;margin:0;max-width:77%}
.st-key-file_workspace {gap:1rem;min-width:0}
.st-key-file_workspace .st-key-file_upload_card,.st-key-file_workspace .st-key-file_management_card,.st-key-file_workspace .st-key-file_result_card {padding:1.2rem;border:1px solid #E1E9E3;border-radius:16px;box-shadow:0 3px 14px #103B2408;background:white;gap:.7rem}
.st-key-file_workspace .st-key-file_settings_card,.st-key-file_workspace .st-key-file_output_settings {gap:.65rem;min-width:0}
.st-key-file_workspace .st-key-file_settings_card {border-left:1px solid #E8EDE9;padding-left:1.2rem}
.st-key-file_workspace .st-key-file_output_settings {padding-left:.4rem}
.st-key-file_workspace .st-key-file_output_settings [data-testid="stButtonGroup"] button {min-height:44px}
.st-key-file_workspace .st-key-file_output_settings [data-testid="stButtonGroup"] {flex-wrap:wrap}
.st-key-file_workspace .st-key-file_output_settings [data-testid="stButtonGroup"] p {white-space:normal;font-size:.82rem}
.st-key-file_workspace .workspace-card-heading {align-items:center;gap:.8rem;margin:0 0 .5rem}
.st-key-file_workspace .workspace-card-heading h2 {font:700 1.4rem/1.35 var(--serif);color:#142839;letter-spacing:0}
.st-key-file_workspace .workspace-card-heading p {font:.84rem/1.6 var(--sans);color:#617487;margin:.15rem 0 0}
.st-key-file_workspace .workspace-card-heading .step-number {width:42px;height:42px;flex-basis:42px;border-radius:50%;background:#E2F0E6;font:700 1.3rem/1 var(--serif)}
.st-key-file_workspace [data-testid="stFileUploaderDropzone"] {background:#F8FBF8;border:1.5px dashed #93B6A3;border-radius:12px;padding:1rem}
.st-key-file_workspace .upload-instruction {font-size:.78rem;color:#617487;margin:0;line-height:1.5}
.st-key-file_workspace [data-testid="stFileUploaderDropzone"] svg {color:#176047}
.st-key-file_workspace [data-testid="stFileUploaderDropzone"] button {min-height:44px;flex-shrink:0}
.st-key-file_workspace [data-testid="stCaptionContainer"] p {overflow-wrap:anywhere}
.st-key-file_workspace h3 {font:700 1.25rem/1.4 var(--serif);color:#163E30;margin:0}
.st-key-file_workspace .st-key-file_list_heading {align-items:center;justify-content:space-between;gap:.75rem}
.st-key-file_workspace .st-key-file_list_heading > [data-testid="stElementContainer"]:has(.workspace-card-heading) {flex:1;min-width:0}
.st-key-file_workspace .st-key-file_list {border-top:1px solid #E1E9E3;border-bottom:1px solid #E1E9E3;padding:0 .2rem;gap:0}
.st-key-file_workspace [class*="st-key-file_row_"] {gap:.7rem;flex-wrap:nowrap;justify-content:space-between;min-width:0;padding:.55rem 0;border-bottom:1px solid #EDF1ED}
.st-key-file_workspace [class*="st-key-file_row_"]:last-child {border-bottom:0}
.st-key-file_workspace [class*="st-key-file_row_"] > [data-testid="stElementContainer"]:has(.upload-file-row) {flex:1 1 0;min-width:0}
.st-key-file_workspace [class*="st-key-file_row_"] button {min-height:44px;font-size:.79rem}
.st-key-file_workspace .upload-file-row {display:flex;align-items:center;gap:.75rem;min-width:0;padding:.3rem .4rem;border-left:3px solid transparent}
.st-key-file_workspace .upload-file-row.is-active {border-left-color:#168055;background:#F3F9F5;border-radius:4px}
.st-key-file_workspace .upload-file-row .ui-icon {color:#176047;width:22px;height:22px;flex:0 0 22px}
.st-key-file_workspace .upload-file-description {flex:1;min-width:0}
.st-key-file_workspace .upload-file-description strong {display:block;font-size:.88rem;font-weight:600;color:#193F31;overflow-wrap:anywhere;unicode-bidi:plaintext}
.st-key-file_workspace .upload-file-description p {font-size:.75rem;line-height:1.5;color:#6A7B89;margin:.2rem 0 0}
.st-key-file_workspace .upload-file-status {font-size:.7rem;color:#3D6150;max-width:130px;text-align:center;line-height:1.5;background:#F0F4F1;padding:.25rem .5rem;border-radius:20px}
.st-key-file_workspace .upload-file-status.done {background:#DDF3E4;color:#165B39}
.st-key-file_workspace .upload-file-status.failed {background:#FFF0E9;color:#963F29}
.st-key-file_workspace .upload-row-error {font-size:.75rem;color:#9A3A2C;margin:.3rem .5rem;overflow-wrap:anywhere}
.st-key-file_workspace .st-key-file_actions {justify-content:flex-end;gap:.65rem;flex-wrap:wrap;margin-top:.5rem}
.st-key-file_workspace .st-key-process_file button {width:248px;max-width:100%;min-width:0;min-height:46px;padding:.55rem 1rem;background:#00583F;border-color:#00583F}
.st-key-file_workspace .st-key-process_file button:disabled {background:#E1EAE4;border-color:#E1EAE4;color:#63766C;box-shadow:none}
.st-key-file_workspace .st-key-process_all_files button {min-height:46px}
.st-key-file_workspace .processing-summary-file {background:#F2F9F5;border:1px solid #D8E9DF;border-radius:13px;padding:1.15rem;margin:.2rem 0 .8rem}
.st-key-file_workspace .processing-summary-file h3 {font:700 1.4rem/1.35 var(--serif);color:#174B38;margin:0 0 .8rem}
.st-key-file_workspace .processing-summary-file dl {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem 1rem}
.st-key-file_workspace .processing-summary-file .processing-stat {background:transparent;border:0;border-radius:0;padding:0;min-width:0}
.st-key-file_workspace .processing-summary-file dt {font-size:.75rem;color:#62788A}
.st-key-file_workspace .processing-summary-file dd {font:700 1rem/1.5 var(--serif);color:#174B38;overflow-wrap:anywhere;margin:.2rem 0 0}
.st-key-file_workspace .processing-summary-file > p {font-size:.7rem;line-height:1.6;color:#64778B;margin:.9rem 0 0}
.st-key-file_workspace .st-key-file_batch_exports {padding:.6rem 0;gap:.5rem}
.st-key-file_workspace .arabic-result {background:#F2F9F5;border-color:#D8E9DF;color:#183E31}
.st-key-file_workspace .file-meta {margin:0;color:#63768A;font-size:.76rem}
.st-key-file_workspace .st-key-file_export_toolbar {justify-content:center;align-items:center;gap:.5rem;padding:.6rem;border:1px solid #E1E9E3;border-radius:12px;background:#F8FAF7;flex-wrap:wrap}
.st-key-file_workspace .st-key-file_export_toolbar button {min-height:44px}
.st-key-file_workspace .st-key-upload_pagination {justify-content:center;gap:.35rem;flex-wrap:wrap}
.st-key-file_workspace .st-key-upload_pagination button {min-width:40px;min-height:44px;padding:.35rem .6rem}
.st-key-file_workspace .st-key-upload_pagination button[kind="primary"] {background:#00583F;border-color:#00583F}
@media(max-width:1100px){
 .st-key-file_workspace .processing-summary-file dl {grid-template-columns:repeat(2,minmax(0,1fr))}
 .st-key-file_workspace .st-key-file_upload_columns [data-testid="stHorizontalBlock"],.st-key-file_workspace .st-key-file_management_columns [data-testid="stHorizontalBlock"] {flex-direction:column}
 .st-key-file_workspace .st-key-file_upload_columns [data-testid="stColumn"],.st-key-file_workspace .st-key-file_management_columns [data-testid="stColumn"] {width:100%;flex:1 1 auto}
 .st-key-file_workspace .st-key-file_settings_card {border-left:0;border-top:1px solid #E8EDE9;padding:1rem 0 0}
 .st-key-file_workspace .st-key-file_output_settings {padding:0}
 .st-key-file_workspace .st-key-file_upload_columns [data-testid="stHorizontalBlock"],.st-key-file_workspace .st-key-file_management_columns [data-testid="stHorizontalBlock"] {gap:1rem}
}
@media(max-width:780px){
 .st-key-file_workspace .st-key-file_upload_card,.st-key-file_workspace .st-key-file_management_card,.st-key-file_workspace .st-key-file_result_card {padding:.9rem;border-radius:13px}
 .st-key-file_workspace .upload-page-hero {min-height:92px;padding:.5rem 0 .3rem}
 .st-key-file_workspace .upload-page-hero p {font-size:.78rem;max-width:90%}
 .st-key-file_workspace .upload-page-hero::after {width:18%;opacity:.12}
 .st-key-file_workspace .workspace-card-heading h2 {font-size:1.15rem}
 .st-key-file_workspace .workspace-card-heading p {font-size:.76rem}
 .st-key-file_workspace .workspace-card-heading .step-number {width:34px;height:34px;flex-basis:34px;font-size:1.1rem}
 .st-key-file_workspace [data-testid="stFileUploaderDropzone"] {padding:.75rem;flex-wrap:wrap;gap:.5rem}
 .st-key-file_workspace .upload-file-row {flex-wrap:wrap;gap:.4rem .6rem}
 .st-key-file_workspace .upload-file-status {max-width:none;text-align:left;margin-left:28px}
 .st-key-file_workspace .upload-file-description strong {font-size:.8rem}
 .st-key-file_workspace [class*="st-key-file_row_"] {gap:.3rem}
 .st-key-file_workspace [class*="st-key-file_row_"] button {font-size:.72rem;padding:.4rem .5rem}
 .st-key-file_workspace .st-key-file_actions {flex-direction:column;align-items:stretch}
 .st-key-file_workspace .st-key-file_actions > div {width:100%}
 .st-key-file_workspace .st-key-process_file button,.st-key-file_workspace .st-key-process_all_files button {width:100%}
 .st-key-file_workspace .st-key-upload_pagination [class*="st-key-translation_reference_prev_"] p,.st-key-file_workspace .st-key-upload_pagination [class*="st-key-translation_reference_next_"] p {font-size:0}
 .st-key-file_workspace .st-key-upload_pagination [class*="st-key-upload_page_edge_"],.st-key-file_workspace .st-key-upload_pagination [class*="st-key-upload_page_gap_"] {display:none}
}
</style>'''.replace('__BOOK__', BOOK)

# Shared header and tabs live in input_design; only upload-card presentation follows.
CSS += '''<style>
.st-key-diak_page .st-key-file_workspace .st-key-file_upload_card {padding:1.1rem}
.st-key-diak_page .st-key-file_workspace .st-key-file_upload_card .workspace-card-heading {margin-bottom:.45rem}
.st-key-diak_page .st-key-file_workspace .st-key-file_upload_card .st-key-upload_drop_area {position:relative;gap:0}
.st-key-upload_drop_area > [data-testid="stElementContainer"]:has(.upload-drop-copy) {position:absolute;top:2rem;left:0;width:100%;height:0;z-index:1;pointer-events:none}
.st-key-upload_drop_area .upload-drop-copy {text-align:center;padding:0 1rem;color:#164D3D;pointer-events:none}
.upload-drop-copy .upload-drop-symbol {display:block;width:34px;height:34px;margin:0 auto .4rem;background:currentColor;mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M7 18H6a4 4 0 0 1-.8-7.9 7 7 0 0 1 13.6 0A4 4 0 0 1 18 18h-1M12 21V9m-4 4 4-4 4 4'/%3E%3C/svg%3E") center/contain no-repeat}
.upload-drop-copy strong {display:block;font:650 1rem/1.5 var(--sans)}
.upload-drop-copy p {font:.85rem/1.5 var(--sans);color:#687E88;margin:.15rem 0 0}
.st-key-diak_page .st-key-file_workspace .st-key-file_upload_card [data-testid="stFileUploaderDropzone"] {min-height:180px;padding:5rem 1rem .75rem;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:.65rem;background:#F7FBF8;border:1px dashed #9FC4B1;border-radius:13px}
.st-key-file_upload_card [data-testid="stFileUploaderDropzone"] > span {flex:none;margin:0}
.st-key-file_upload_card [data-testid="stFileUploaderDropzoneInstructions"] {flex:none;min-width:0;width:100%;align-items:center;text-align:center}
.st-key-file_upload_card [data-testid="stFileUploaderDropzoneInstructions"] > div {width:100%;justify-content:center;text-align:center}
.st-key-file_upload_card [data-testid="stFileUploaderDropzoneInstructions"] span {width:100%;font:.75rem/1.5 var(--sans);color:#718594;text-align:center;white-space:normal;overflow-wrap:anywhere}
.st-key-file_upload_card [data-testid="stFileUploaderDropzone"] button {min-height:44px;padding:.5rem 1.1rem;background:#fff;border-color:#A9C7B8;border-radius:10px;color:#07553C}
.st-key-diak_page .st-key-file_workspace .st-key-file_upload_columns [data-testid="stColumn"]:last-child {border-left:1px solid #E0E9E3;padding-left:1.4rem}
.st-key-diak_page .st-key-file_workspace .st-key-file_upload_card .st-key-file_output_settings {height:100%;min-height:100%;border-left:0;padding-left:0;gap:.9rem}
.st-key-file_upload_card .st-key-file_output_settings [data-testid="stWidgetLabel"] p {font-size:.9rem;font-weight:650;color:#064937}
.st-key-diak_page .st-key-file_workspace .st-key-file_upload_card .st-key-file_actions {flex-direction:column;align-items:stretch;gap:.5rem;margin:.25rem 0 .15rem;padding-bottom:.5rem;border-bottom:1px solid #E4ECE6}
.st-key-file_upload_card .st-key-file_actions > [data-testid="stElementContainer"] {width:100%}
.st-key-diak_page .st-key-file_workspace .st-key-file_upload_card .st-key-process_file button {width:100%;min-height:50px;border-radius:11px;font:650 1.05rem/1.4 var(--sans);gap:.6rem}
.st-key-file_upload_card .st-key-process_file button::after {content:"";width:20px;height:20px;flex:0 0 20px;margin-left:.35rem;background:currentColor;mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M4 12h16m-6-6 6 6-6 6'/%3E%3C/svg%3E") center/contain no-repeat}
.st-key-file_upload_card .st-key-file_output_settings [data-testid="stExpander"] {margin-top:.35rem;border-color:#DCE6DF;border-radius:11px;background:#fff}
@media(max-width:1100px){
 .st-key-diak_page .st-key-file_workspace .st-key-file_upload_columns [data-testid="stColumn"]:last-child {border-left:0;border-top:1px solid #E0E9E3;padding:1rem 0 0}
 .st-key-diak_page .st-key-file_workspace .st-key-file_upload_card .st-key-file_output_settings {height:auto;min-height:0;border:0;padding:0}
}
@media(max-width:780px){
 .st-key-diak_page .st-key-file_workspace .st-key-file_upload_card {padding:.9rem}
 .st-key-diak_page .st-key-file_workspace .st-key-file_upload_card [data-testid="stFileUploaderDropzone"] {min-height:208px;padding-top:6rem}
 .upload-drop-copy strong {font-size:.94rem}
 .upload-drop-copy p {font-size:.8rem}
}
</style>'''

# Upload layout: actions below upload, files/settings at right, view in result card.
CSS += '''<style>
.st-key-file_main_columns [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]) {align-items:stretch}
.st-key-file_main_columns [data-testid="stColumn"] {min-width:0}
.st-key-file_workspace .st-key-file_main_columns .st-key-file_management_card {padding:1.1rem}
.st-key-file_workspace .st-key-file_main_columns .st-key-file_upload_card,
.st-key-file_workspace .st-key-file_main_columns .st-key-file_management_card {gap:.55rem}
.st-key-file_workspace .st-key-file_result_view {margin:.1rem 0 .6rem;max-width:100%}
.st-key-file_workspace .st-key-file_result_view [data-testid="stButtonGroup"] button {min-height:40px}
.st-key-file_workspace .st-key-file_result_view [data-testid="stWidgetLabel"] p {font-size:.85rem;font-weight:650;color:#064937}

.st-key-file_workspace .st-key-file_main_columns .st-key-file_upload_columns,
.st-key-file_workspace .st-key-file_main_columns .st-key-file_management_columns {gap:.55rem}
.st-key-file_workspace .st-key-file_main_columns .st-key-file_output_settings {padding:0;height:auto;min-height:0}
.st-key-file_workspace .st-key-file_main_columns .st-key-file_settings_card {border-left:0;border-top:1px solid #E8EDE9;padding:1rem 0 0;margin-top:.4rem}
.st-key-file_workspace .st-key-file_main_columns .upload-file-row {display:grid;grid-template-columns:22px minmax(0,1fr);gap:.2rem .6rem}
.st-key-file_main_columns .upload-file-row > .ui-icon {grid-column:1;grid-row:1 / 3}
.st-key-file_main_columns .upload-file-status {grid-column:2;justify-self:start;margin-left:0;max-width:100%;text-align:left}
.st-key-file_main_columns .st-key-file_list_heading {flex-wrap:wrap}
.st-key-file_main_columns .st-key-file_list {scrollbar-gutter:stable}
.st-key-file_main_columns .st-key-file_output_settings [data-testid="stExpander"] summary {min-height:44px}
.st-key-file_workspace .upload-empty-state {display:flex;flex-direction:column;gap:.7rem;padding:.65rem;border:1px solid #E1E9E4;border-radius:12px;background:#FAFCFA}
.st-key-file_workspace .upload-empty-intro {display:flex;flex-direction:column;align-items:center;gap:.35rem;text-align:center;padding:.15rem .3rem}
.st-key-file_workspace .upload-empty-icon {display:grid;place-items:center;position:relative;width:32px;height:32px;color:#627873}
.st-key-file_workspace .upload-empty-icon::after {content:"+";position:absolute;right:-4px;bottom:-2px;display:grid;place-items:center;width:18px;height:18px;border-radius:50%;background:#D3A642;color:white;font:600 16px/1 var(--sans);border:2px solid #FAFCFA}
.st-key-file_workspace .upload-empty-symbol {width:34px;height:38px;background:currentColor;mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z'/%3E%3Cpath d='M14 2v6h6M8 12h8M8 16h5'/%3E%3C/svg%3E") center/contain no-repeat}
.st-key-file_workspace .upload-empty-state h3 {font:700 1.1rem/1.4 var(--serif);color:#174B38;margin:0}
.st-key-file_workspace .upload-empty-state p {font:.82rem/1.55 var(--sans);color:#617487;margin:0}
.st-key-file_workspace .upload-empty-tips {padding:.45rem .7rem;border-radius:9px;background:#EDF5EF;text-align:left}
.st-key-file_workspace .upload-empty-tips h4 {font:700 .95rem/1.4 var(--serif);color:#174B38;margin:0 0 .4rem}
.st-key-file_workspace .upload-empty-tips ol {list-style:none;counter-reset:upload-tip;padding:0;margin:0;display:grid;gap:.25rem}
.st-key-file_workspace .upload-empty-tips li {counter-increment:upload-tip;position:relative;padding-left:1.65rem;font:.8rem/1.55 var(--sans);color:#526579;overflow-wrap:anywhere}
.st-key-file_workspace .upload-empty-tips li::before {content:counter(upload-tip);position:absolute;left:0;top:.12rem;display:grid;place-items:center;width:17px;height:17px;border:1px solid #448467;border-radius:50%;font:600 .7rem/1 var(--sans);color:#246246}
.st-key-file_workspace .st-key-file_settings_empty {position:relative;padding:.6rem .7rem .6rem 2.1rem;border:1px solid #F0E3CB;border-radius:10px;background:#FBF5E8;min-height:min-content;flex-shrink:0}
.st-key-file_workspace .st-key-file_settings_empty::before {content:"i";position:absolute;left:.65rem;top:.75rem;display:grid;place-items:center;width:17px;height:17px;border:1px solid #B48E38;border-radius:50%;color:#A77F22;font:700 .75rem/1 var(--serif)}
.st-key-file_workspace .st-key-file_settings_empty p {font-size:.78rem;line-height:1.5;margin:0;color:#63715F}
.st-key-file_workspace .st-key-reset_all_files button {border:1px solid #ECC5BE;border-radius:8px;color:#A44337;background:#FFFDFC;min-height:40px}
.st-key-file_workspace .st-key-reset_all_files button:disabled {border-color:#E1E7E2;color:#89998E;background:#FAFCFA}
.st-key-file_workspace .st-key-file_upload_card {container-type:inline-size}
.st-key-file_workspace .st-key-file_main_columns .st-key-file_upload_card,
.st-key-file_workspace .st-key-file_main_columns .st-key-file_management_card {gap:.4rem}
.st-key-file_workspace .st-key-file_upload_input {gap:.4rem}
.st-key-file_workspace .st-key-file_list_panel {gap:.45rem}
.st-key-file_workspace .st-key-file_main_columns .st-key-file_settings_card {padding-top:.45rem;margin-top:.1rem}
.st-key-diak_page .st-key-file_workspace .st-key-file_upload_card .st-key-file_actions {margin:.1rem 0;padding-bottom:.35rem;gap:.6rem}
.st-key-file_workspace .st-key-file_upload_columns {gap:.35rem}
@container (min-width:440px){
 .st-key-diak_page .st-key-file_workspace .st-key-file_upload_card .st-key-file_actions {flex-direction:row;flex-wrap:nowrap}
 .st-key-file_workspace .st-key-file_upload_card .st-key-file_actions > [data-testid="stElementContainer"] {flex:1 1 0;min-width:0;width:auto}
 .st-key-file_workspace .st-key-file_upload_card .st-key-file_actions > [data-testid="stElementContainer"]:first-child {flex-grow:1.15}
 .st-key-file_workspace .st-key-file_upload_card .st-key-file_actions button {width:100%;min-height:48px;font-size:.9rem}
}
@media(max-width:1100px){
 .st-key-file_main_columns [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]) {flex-direction:column;gap:1rem}
 .st-key-file_main_columns [data-testid="stColumn"] {width:100%;flex:1 1 auto}
 .st-key-file_workspace .st-key-file_main_columns .st-key-file_upload_card,
 .st-key-file_workspace .st-key-file_main_columns .st-key-file_management_card,
 .st-key-file_main_columns .st-key-file_management_columns,
 .st-key-file_main_columns .st-key-file_list_empty {height:auto;flex-grow:0}
}
</style>'''
