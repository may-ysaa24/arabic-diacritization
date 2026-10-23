"""Optional reference-only UI; never calls or imports the inference engine."""
import streamlit as st

import translation_reference as reference
from translation_prediction import prediction_pairs
from translation_matching import lookup

PAGE_SIZE = 10


def sync_reference_file(file_key):
    """Reset pagination on file changes, including a round trip through TXT."""
    previous = st.session_state.get('translation_reference_active_file')
    if previous != file_key:
        for identity in (previous, file_key):
            st.session_state.pop(f'translation_reference_page_{identity}', None)
            st.session_state.pop(f'translation_reference_page_context_{identity}', None)
        st.session_state['translation_reference_active_file'] = file_key


def paged_pairs(pairs, file_key, preview):
    """Render navigation only; instantiate cards for at most one page."""
    page_key = f'translation_reference_page_{file_key}'
    context_key = f'translation_reference_page_context_{file_key}'
    context = (preview, tuple(pair['unit']['unit_id'] for pair in pairs))
    pages = (len(pairs) + PAGE_SIZE - 1) // PAGE_SIZE
    if st.session_state.get(context_key) != context:
        st.session_state[context_key] = context
        st.session_state[page_key] = 1
    if not pairs:
        st.session_state.pop(page_key, None)
        return []
    if st.session_state.get(page_key, 1) not in range(1, pages + 1):
        st.session_state[page_key] = 1
    page = st.selectbox('Halaman terjemahan', range(1, pages + 1), key=page_key,
                        format_func=lambda number: f'{number} / {pages}')
    start = (page - 1) * PAGE_SIZE
    end = min(start + PAGE_SIZE, len(pairs))
    st.caption(f'Paragraf {start + 1}–{end} dari {len(pairs)} · Halaman {page} dari {pages}')
    return pairs[start:end]


@st.fragment
def render_reference_panel(upload_data, dataframe, column, file_key, result=None, *, source_text=None):
    # Both input tabs render on a full app rerun. Manual pagination must not
    # reset the active upload's independent pagination state.
    if file_key != 'manual':
        sync_reference_file(file_key)
    panel = st.expander('Lihat Terjemahan Mandiri', expanded=False,
                        key=f'translation_reference_{file_key}', on_change='rerun')
    if not panel.open:
        return
    with panel:
        st.caption('Terjemahan mandiri disimpan terpisah dari hasil BiLSTM–CRF '
                   'dan tidak disertakan dalam unduhan hasil diakritisasi.')
        preview = st.checkbox('Pratinjau draf lokal (belum diverifikasi)', value=False,
                              key=f'translation_reference_draft_{file_key}')
        if preview:
            st.warning(reference.DRAFT_LABEL)
            st.caption(reference.CONTENT_DRAFT_LABEL)
        exact_demo = (dataframe is not None
                      and reference.match_demo_book(upload_data, dataframe, column) is not None)
        if dataframe is not None:
            # Preserve the existing exact CSV path and its final/draft gates.
            units = (reference.display_units(upload_data, dataframe, column, preview_drafts=True)
                     if preview else reference.display_units(upload_data, dataframe, column))
        if exact_demo:
            pairs = prediction_pairs(units, dataframe, result, preview_drafts=preview)
        else:
            report = lookup(result, dataframe=dataframe, column=column, text=source_text,
                            preview_drafts=preview)
            pairs = report['pairs']
            labels = {'tersedia': 'terjemahan ditampilkan', 'ambigu': 'ambigu; identitas belum pasti',
                      'tidak_cocok': 'tidak cocok dengan referensi kanonis',
                      'prediksi_tidak_sesuai': 'prediksi tersimpan tidak sesuai',
                      'paragraf_tidak_lengkap': 'paragraf tidak lengkap atau berulang',
                      'belum_terverifikasi': 'draf tersedia; aktifkan pratinjau lokal',
                      'terjemahan_belum_tersedia': 'teks kanonis ditemukan; terjemahan belum tersedia'}
            if report.get('error'):
                st.warning(report['error'])
            if report['counts']:
                st.caption('Cakupan pencocokan: ' + '; '.join(
                    f'{count} bagian {labels[status]}' for status, count in report['counts'].items()))
            st.caption('Pencocokan hanya untuk paragraf lengkap. Bagian yang ambigu, parsial, '
                       'atau belum memiliki referensi tidak diterjemahkan. Tidak memakai kemiripan kalimat.')
        visible_pairs = paged_pairs(pairs, file_key, preview)
        if not pairs:
            st.info('Terjemahan belum tersedia')
        else:
            covered = sum(pair.get('input_parts', len(pair['segments'])) for pair in pairs)
            drafts = sum(pair['unit']['verification']['status'] == reference.DRAFT_STATUS for pair in pairs)
            st.caption(f'{len(pairs)} paragraf · {drafts} draf · {len(pairs) - drafts} terverifikasi · '
                       f'{covered} dari {len(dataframe) if dataframe is not None else report["total"]} bagian masukan. '
                       'Segmen lainnya: Terjemahan belum tersedia.')
            for pair in visible_pairs:
                unit = pair['unit']
                with st.container(border=True):
                    is_draft = unit['verification']['status'] == reference.DRAFT_STATUS
                    if is_draft:
                        st.warning(reference.DRAFT_LABEL)
                    st.text('Kitab: ' + pair['kitab'])
                    if unit['section']:
                        st.text('Bagian: ' + unit['section'])
                    st.text('Paragraf: ' + unit['paragraph_id'] + '\nSegmen: '
                            + ', '.join(s['segment_id'] for s in pair['segments']))
                    st.caption('Halaman PDF: ' + ', '.join(dict.fromkeys(
                        str(t['pdf_page']) for t in unit['targets'])))
                    arabic, indonesian = st.columns(2)
                    with arabic:
                        st.markdown('**Arab — hasil BiLSTM–CRF**')
                        for segment in pair['segments']:
                            if len(pair['segments']) > 1:
                                st.caption(segment['segment_id'])
                            st.text(segment['prediction'])
                    with indonesian:
                        st.markdown('**Indonesia — draf terjemahan**' if is_draft
                                    else '**Indonesia — terjemahan mandiri terverifikasi**')
                        st.text(unit['translation']['text_indonesian'])
                    if unit.get('source_note'):
                        st.text('Catatan sumber: ' + unit['source_note'])
                    st.text('Penyusun: ' + unit['translation']['translator'])
                    if is_draft:
                        st.text('Status: ' + reference.DRAFT_STATUS + ' · Belum diperiksa manusia')
                    else:
                        st.text('Verifikasi: verified · ' + unit['verification']['reviewer']
                                + ' · ' + unit['verification']['reviewed_at'])
                    st.caption('Satu terjemahan berlaku untuk seluruh segmen paragraf di atas. '
                               'Hasil Arab menggunakan prediksi yang sudah tersimpan; '
                               'batas antarsegmen tetap ditampilkan.')
