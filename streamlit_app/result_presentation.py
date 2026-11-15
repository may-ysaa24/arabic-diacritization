"""Escaped, readable result markup. No inference, matching, or text normalization."""
from html import escape


def arabic_markup(text, *, result=False):
    classes = 'arabic-text arabic-result' if result else 'arabic-text'
    return f'<div class="{classes}" lang="ar" dir="rtl">{escape(str(text))}</div>'


def indonesian_markup(text):
    return f'<div class="translation-indonesian" lang="id" dir="ltr">{escape(str(text))}</div>'


def result_icon(name):
    """Decorative local CSS-mask icons; labels remain ordinary accessible text."""
    return f'<span class="result-icon result-icon-{escape(name)}" aria-hidden="true"></span>'


def pane_heading(language):
    if language == 'id':
        content = result_icon('translate') + '<span>Terjemahan Indonesia</span>'
    else:
        content = '<span>Teks Arab Berharakat</span>' + result_icon('book')
    return '<h3 class="result-pane-heading">' + content + '</h3>'


def translation_heading():
    return ('<div class="translation-section-heading">' + result_icon('book')
            + '<div><h3>Hasil Terjemahan</h3><p>Hasil diakritisasi dan terjemahan referensi bahasa Indonesia.</p>'
            '</div></div>')


def success_summary_markup(items, note):
    icons = ('file', 'clock', 'check', 'model')
    metrics = ''.join(
        '<div class="processing-stat">' + result_icon(icon)
        + '<div><dt>' + escape(label) + '</dt><dd>' + escape(str(value)) + '</dd></div></div>'
        for (label, value), icon in zip(items, icons)
    )
    return ('<section class="processing-summary result-success" aria-label="Ringkasan Hasil Pemrosesan">'
            '<div class="result-success-heading">' + result_icon('check')
            + '<div><h3>Berhasil diproses</h3>'
            '<p>Teks berhasil diakritisasi menggunakan model BiLSTM–CRF.</p></div></div>'
            '<dl>' + metrics + '</dl><p class="result-summary-note">' + escape(note) + '</p></section>')
