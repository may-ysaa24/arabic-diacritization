"""Optional reference-only UI; never calls or imports the inference engine."""
import streamlit as st
from html import escape

import translation_reference as reference
from translation_prediction import prediction_pairs
from translation_matching import lookup
from translation_exports import cached_report
from result_presentation import arabic_markup, indonesian_markup, pane_heading, translation_heading

PAGE_SIZE = 10
ARABIC_VIEW = 'Arab Berharakat'
TRANSLATION_VIEW = 'Arab + Terjemahan'


def reset_reference_pages(file_key):
    """Start a different result at page 1, before its widgets are rendered.

    Called on file changes and successful processing, never on presentation
    reruns. Clearing the context also distinguishes new processing generations
    whose canonical paragraph IDs happen to be identical.
    """
    st.session_state[f'translation_reference_page_{file_key}'] = 1
    st.session_state[f'translation_reference_arabic_page_{file_key}'] = 1
    st.session_state.pop(f'translation_reference_page_context_{file_key}', None)


def sync_reference_file(file_key):
    """Reset pagination on file changes, including a round trip through TXT."""
    previous = st.session_state.get('translation_reference_active_file')
    if previous != file_key:
        for identity in (previous, file_key):
            st.session_state.pop(f'translation_reference_page_{identity}', None)
            st.session_state.pop(f'translation_reference_page_context_{identity}', None)
            st.session_state.pop(f'translation_reference_arabic_page_{identity}', None)
        if file_key is not None:
            reset_reference_pages(file_key)
        st.session_state['translation_reference_active_file'] = file_key


def paged_pairs(pairs, file_key, page_size=PAGE_SIZE):
    """Render navigation only; instantiate cards for at most one page."""
    page_key = f'translation_reference_page_{file_key}'
    context_key = f'translation_reference_page_context_{file_key}'
    context = (page_size, tuple(pair['unit']['unit_id'] for pair in pairs))
    pages = (len(pairs) + page_size - 1) // page_size
    if st.session_state.get(context_key) != context:
        st.session_state[context_key] = context
        st.session_state[page_key] = 1
    if not pairs:
        st.session_state.pop(page_key, None)
        return []
    if st.session_state.get(page_key, 1) not in range(1, pages + 1):
        st.session_state[page_key] = 1
    with st.container(horizontal=True, vertical_alignment='center',
                      key=f'translation_page_header_{file_key}'):
        st.html(translation_heading())
        page = st.selectbox('Halaman terjemahan', range(1, pages + 1), key=page_key,
                            format_func=lambda number: f'{number} / {pages}',
                            label_visibility='collapsed', width=150, persist_state='session')
    start = (page - 1) * page_size
    end = min(start + page_size, len(pairs))
    st.caption(f'Paragraf {start + 1}–{end} dari {len(pairs)} · Halaman {page} dari {pages}')
    return pairs[start:end]


def turn_page(page_key, step, pages):
    current = st.session_state.get(page_key, 1)
    if not isinstance(current, int):
        current = 1
    st.session_state[page_key] = min(pages, max(1, current + step))


def visible_page_numbers(page, pages):
    """A bounded window; the native selector still reaches every page."""
    return sorted({1, pages, *range(max(1, page - 1), min(pages, page + 1) + 1)})


def select_page(page_key, page, pages):
    st.session_state[page_key] = min(pages, max(1, page))


def page_actions(pairs, file_key, page_size=PAGE_SIZE):
    """Bottom navigation reaches the same page state without scrolling to the top."""
    pages = (len(pairs) + page_size - 1) // page_size
    key = f'translation_reference_page_{file_key}'
    page = st.session_state.get(key, 1)
    if file_key != 'manual':
        with st.container(horizontal=True, vertical_alignment='center', key='upload_pagination'):
            st.button('Sebelumnya', key=f'translation_reference_prev_{file_key}', disabled=page <= 1,
                      on_click=turn_page, args=(key, -1, pages), icon=':material/chevron_left:')
            previous = None
            for number in visible_page_numbers(page, pages):
                if previous is not None and number - previous > 1:
                    with st.container(width='content', key=f'upload_page_gap_{file_key}_{number}'):
                        st.markdown('…')
                edge = abs(number - page) > 1
                with st.container(width='content', key=f'upload_page_{"edge" if edge else "near"}_{file_key}_{number}'):
                    st.button(str(number), key=f'translation_reference_number_{file_key}_{number}',
                              type='primary' if number == page else 'secondary',
                              on_click=select_page, args=(key, number, pages))
                previous = number
            st.button('Berikutnya', key=f'translation_reference_next_{file_key}', disabled=page >= pages,
                      on_click=turn_page, args=(key, 1, pages), icon=':material/chevron_right:')
        st.caption(f'Halaman {page} dari {pages} · Maksimal {page_size} paragraf per halaman.')
        return
    with st.container(horizontal=True):
        st.button('Sebelumnya', key=f'translation_reference_prev_{file_key}', disabled=page <= 1,
                  on_click=turn_page, args=(key, -1, pages), icon=':material/chevron_left:')
        st.button('Berikutnya', key=f'translation_reference_next_{file_key}', disabled=page >= pages,
                  on_click=turn_page, args=(key, 1, pages), icon=':material/chevron_right:')
    st.caption(f'Halaman {page} dari {pages} · Maksimal {page_size} paragraf per halaman.')


def render_saved_arabic(result, file_key, display_text=None):
    """Only visible rows become readable HTML; the complete CSV remains downloadable."""
    if result.get('input_type') != 'csv':
        st.html(arabic_markup(result['prediction'] if display_text is None else display_text, result=True))
        return
    frame = result['dataframe']
    prediction, status = result['output_columns']['prediction'], result['output_columns']['status']
    pages = max(1, (len(frame) + PAGE_SIZE - 1) // PAGE_SIZE)
    key = f'translation_reference_arabic_page_{file_key}'
    if st.session_state.get(key, 1) not in range(1, pages + 1):
        st.session_state[key] = 1
    page = st.selectbox('Halaman hasil Arab', range(1, pages + 1), key=key,
                        format_func=lambda number: f'{number} / {pages}', persist_state='session')
    start, end = (page - 1) * PAGE_SIZE, min(page * PAGE_SIZE, len(frame))
    st.caption(f'Baris {start + 1 if len(frame) else 0}–{end} dari {len(frame)} · Hasil lengkap tersedia di Unduh CSV.')
    rows = []
    for i in range(start, end):
        row = frame.iloc[i]
        rows.append('<section class="arabic-csv-row"><div class="csv-row-label">'
                    + f'Baris {i + 1} · {escape(str(row[status]))}</div>'
                    + arabic_markup(row[prediction]) + '</section>')
    st.html('<div class="arabic-csv-reader">' + ''.join(rows) + '</div>')


@st.fragment
def render_reference_panel(upload_data, dataframe, column, file_key, result=None, *, source_text=None,
                           display_text=None, summary_html=None, selected_view=None):
    # Both input tabs render on a full app rerun. Manual pagination must not
    # reset the active upload's independent pagination state.
    if file_key != 'manual':
        sync_reference_file(file_key)
    # Retire the removed display checkbox, including state from a live session.
    st.session_state.pop(f'translation_reference_draft_{file_key}', None)
    view = selected_view
    if view is None:
        view = st.segmented_control('Tampilan hasil', [ARABIC_VIEW, TRANSLATION_VIEW],
                                    default=ARABIC_VIEW, selection_mode='single',
                                    key=f'translation_reference_view_{file_key}', width='stretch')
    if summary_html:
        st.html(summary_html)
    if view != TRANSLATION_VIEW:
        render_saved_arabic(result, file_key, display_text)
        return
    with st.container(key=f'translation_workspace_{file_key}'):
        if display_text is not None and display_text != result.get('prediction'):
            st.info('Arab pada tampilan terjemahan memakai hasil asli model. '
                    'Koreksi pengguna tetap digunakan oleh tindakan salin dan unduh.')
        exact_demo = (dataframe is not None
                      and reference.match_demo_book(upload_data, dataframe, column) is not None)
        if dataframe is not None:
            # Include saved drafts for display only; validation and data status
            # remain inside the existing reference/matching modules.
            units = reference.display_units(upload_data, dataframe, column, preview_drafts=True)
        if exact_demo:
            pairs = prediction_pairs(units, dataframe, result, preview_drafts=True)
        else:
            report = cached_report(st.session_state, result, dataframe=dataframe, column=column,
                                   text=source_text, lookup=lookup)
            pairs = report['pairs']
            labels = {'tersedia': 'terjemahan ditampilkan', 'ambigu': 'ambigu; identitas belum pasti',
                      'tidak_cocok': 'tidak cocok dengan referensi kanonis',
                      'prediksi_tidak_sesuai': 'prediksi tersimpan tidak sesuai',
                      'paragraf_tidak_lengkap': 'paragraf tidak lengkap atau berulang',
                      'belum_terverifikasi': 'referensi belum memenuhi syarat tampilan',
                      'terjemahan_belum_tersedia': 'teks kanonis ditemukan; terjemahan belum tersedia'}
            if report.get('error'):
                st.warning(report['error'])
            if report['counts'] and set(report['counts']) != {'tersedia'}:
                st.caption('Cakupan pencocokan: ' + '; '.join(
                    f'{count} bagian {labels[status]}' for status, count in report['counts'].items()))
        page_size = 1 if file_key == 'manual' else PAGE_SIZE
        visible_pairs = paged_pairs(pairs, file_key, page_size)
        if not pairs:
            st.info('Terjemahan belum tersedia')
            st.caption('Belum ada pasangan terjemahan tersimpan yang cocok untuk teks ini. '
                       'Hasil diakritisasi tetap tersedia di bawah.')
            render_saved_arabic(result, file_key)
        else:
            covered = sum(pair.get('input_parts', len(pair['segments'])) for pair in pairs)
            if file_key != 'manual':
                total = len(dataframe) if dataframe is not None else report['total']
                st.caption(f'{len(pairs)} paragraf · '
                           f'{covered} dari {total} bagian masukan.')
            for pair in visible_pairs:
                unit = pair['unit']
                with st.container(border=True, key=f'translation_card_{file_key}_{unit["paragraph_id"]}'):
                    with st.container(key=f'translation_columns_{file_key}_{unit["paragraph_id"]}'):
                        indonesian, arabic = st.columns([1, 1], gap='medium')
                        with indonesian:
                            st.html(pane_heading('id'))
                            st.html(indonesian_markup(unit['translation']['text_indonesian']))
                        with arabic:
                            st.html(pane_heading('ar'))
                            for segment in pair['segments']:
                                st.html(arabic_markup(segment['prediction']))
            if file_key != 'manual' and covered < total:
                st.info('Sebagian teks belum dapat dipasangkan dengan terjemahan. '
                        'Hasil Arab lengkap tetap tersedia.')
                with st.expander('Hasil Arab lengkap'):
                    render_saved_arabic(result, file_key)
            page_actions(pairs, file_key, page_size)
