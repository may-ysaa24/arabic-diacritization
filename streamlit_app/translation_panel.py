"""Optional reference-only UI; never calls or imports the inference engine."""
import streamlit as st

import translation_reference as reference


@st.fragment
def render_reference_panel(upload_data, dataframe, column, file_key):
    panel = st.expander('Lihat Terjemahan Referensi', expanded=False,
                        key=f'translation_reference_{file_key}', on_change='rerun')
    if not panel.open:
        return
    with panel:
        st.caption('Referensi terpisah dari hasil BiLSTM–CRF. Terjemahan bukan keluaran model '
                   'dan tidak disertakan dalam unduhan hasil diakritisasi.')
        units = reference.display_units(upload_data, dataframe, column)
        if not units:
            st.info('Terjemahan belum tersedia')
            return
        st.caption('Hanya paragraf dengan pasangan, verifikasi, dan izin tampilan yang memenuhi syarat '
                   'ditampilkan. Segmen lainnya: Terjemahan belum tersedia.')
        for unit in units:
            with st.container(border=True):
                st.text('Paragraf: ' + unit['paragraph_id'] + '\nSegmen: '
                        + ', '.join(t['segment_id'] for t in unit['targets']))
                st.text(unit['arabic_gundul'])
                st.text(unit['translation']['text_indonesian'])
                st.text('Sumber: ' + unit['source_parts'][0]['source_url']
                        + '\nPenerjemah: ' + unit['translation']['translator']
                        + '\nPemeriksa: ' + unit['verification']['reviewer'])
                st.caption('Satu terjemahan berlaku untuk seluruh segmen paragraf di atas.')
