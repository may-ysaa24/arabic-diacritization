"""Edge: all 328 real Thaharah segments and their stored model Arabic/original drafts."""
from collections import Counter
from hashlib import sha256
import csv
from io import StringIO, BytesIO
from pathlib import Path
import re
import sys

import pandas as pd
from playwright.sync_api import expect, TimeoutError as PlaywrightTimeoutError
import browser_multifile as base

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'streamlit_app'))
import translation_reference as reference

OUT = ROOT / 'test-results/translation-panel'
PREVIEW = 'Pratinjau draf lokal (belum diverifikasi)'


def calls():
    return (OUT / 'model_calls.txt').read_text(encoding='utf-8').splitlines()


def run(page, url):
    page.on('pageerror', lambda error: print('Browser page error:', error, flush=True))
    result = original_run(page, url)
    paragraph_count = len(DRAFTS)
    segment_count = sum(len(u['targets']) for u in DRAFTS)
    label = 'Berkas untuk pratinjau, proses ulang, atau unduh'
    page.locator('input[type="file"]').set_input_files([base.payload('01_Thaharah.csv', DATA)])
    base.select(page, label, '2. 01_Thaharah.csv')
    page.get_by_role('button', name='Proses Diakritisasi', exact=True).click()
    card = page.locator('.st-key-file_result_card')
    button = card.get_by_role('button', name=re.compile(r'Unduh CSV$'))
    expect(button).to_be_visible(timeout=90_000)
    before = base.download(page, button, 'thaharah_before_preview.csv')
    rows = {row['id']: row for row in csv.DictReader(StringIO(before.decode('utf-8-sig')))}
    page.get_by_role('button', name='Siapkan ZIP', exact=True).click()
    zip_button = page.get_by_role('button', name='Unduh Semua (ZIP)', exact=True)
    zip_before = base.download(page, zip_button, 'thaharah_before_preview.zip')
    before_calls = calls()
    panel = card.get_by_text('Lihat Terjemahan Mandiri', exact=True)
    panel.click()
    preview = card.get_by_role('checkbox', name=PREVIEW, exact=True)
    def set_preview(enabled):
        # Streamlit's React Aria checkbox has an overlaid visible label.
        # Click that user-facing label instead of the clipped input element.
        if preview.is_checked() != enabled:
            card.get_by_text(PREVIEW, exact=True).click()
        if enabled:
            expect(preview).to_be_checked()
        else:
            expect(preview).not_to_be_checked()
    expect(preview).not_to_be_checked()
    expect(card.get_by_text('Terjemahan belum tersedia', exact=True)).to_be_visible()
    expect(card.get_by_text(re.compile(r'^Paragraf:'))).to_have_count(0)
    set_preview(True)
    page_field = card.locator('[data-testid="stSelectbox"]').filter(
        has=page.get_by_text('Halaman terjemahan', exact=True)).get_by_role('combobox')
    pages = (paragraph_count + 9) // 10
    left = card.locator('[data-testid="stColumn"]').filter(has=page.get_by_text('Arab \u2014 hasil BiLSTM\u2013CRF', exact=True))
    right = card.locator('[data-testid="stColumn"]').filter(has=page.get_by_text('Indonesia \u2014 draf terjemahan', exact=True))
    def visit(number):
        value = f'{number} / {pages}'
        if page_field.input_value() != value:
            for attempt in range(3):
                page_field.press('Escape')
                page_field.click()
                page_field.fill(value)
                option = page.get_by_role('option', name=value, exact=True)
                try:
                    try:
                        expect(option).to_be_visible(timeout=1500)
                    except AssertionError:
                        # Virtualized lists can retain the old scroll position.
                        # Scroll only if needed; avoid racing a filtered list.
                        page.get_by_role('listbox').hover()
                        page.mouse.wheel(0, -5000)
                        expect(option).to_be_visible(timeout=3000)
                    option.click(timeout=3000)
                    break
                except (AssertionError, PlaywrightTimeoutError):
                    if attempt == 2:
                        raise
        expect(page_field).to_have_value(value)
        start, end = (number - 1) * 10, min(number * 10, paragraph_count)
        expected = DRAFTS[start:end]
        expect(card.get_by_text(f'Paragraf {start + 1}–{end} dari {paragraph_count} · Halaman {number} dari {pages}', exact=True)).to_be_visible()
        expect(card.get_by_text(re.compile(r'^Paragraf:'))).to_have_count(len(expected))
        expect(card.get_by_text(reference.DRAFT_LABEL, exact=True)).to_have_count(len(expected) + 1)
        expect(left).to_have_count(len(expected))
        expect(right).to_have_count(len(expected))
        for i, unit in enumerate(expected):
            text = unit['translation']['text_indonesian']
            for target in unit['targets']:
                segment = target['segment_id']
                expect(left.nth(i).get_by_text(rows[segment]['hasil_diacritization'], exact=True)).to_be_visible()
                expect(card.get_by_text(re.compile('Paragraf: ' + unit['paragraph_id']))).to_contain_text(segment)
            expect(right.nth(i).get_by_text(text, exact=True)).to_be_visible()
            assert text.encode('utf-8') not in before
        for text, count in Counter(u['translation']['text_indonesian'] for u in expected).items():
            expect(right.get_by_text(text, exact=True)).to_have_count(count)
        expect(card.get_by_text(re.compile('Verifikasi: verified'))).to_have_count(0)
        expect(page.locator('[data-testid="stStatusWidget"]')).not_to_be_visible(timeout=60_000)
        assert calls() == before_calls
        return expected
    expect(page_field).to_have_value('1 / 32')
    visited = []
    for number in range(1, pages + 1):
        visited.extend(unit['unit_id'] for unit in visit(number))
        if number in (1, 16, 32):
            print(f'Thaharah page {number}/{pages} passed', flush=True)
    assert visited == [unit['unit_id'] for unit in DRAFTS]
    assert left.nth(6).bounding_box()['x'] < right.nth(6).bounding_box()['x']
    multi = [i for i, u in enumerate(DRAFTS) if len(u['targets']) > 1]
    assert len(multi) == 10
    right.nth(6).scroll_into_view_if_needed()  # Last complete paragraph spans 00327–00328.
    page.screenshot(path=str(OUT / 'draft_desktop.png'), full_page=False, animations='disabled')
    page.set_viewport_size({'width': 390, 'height': 844})
    right.nth(6).scroll_into_view_if_needed()
    expect(right.nth(6)).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(OUT / 'draft_mobile.png'), full_page=False, animations='disabled')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    visit(16)
    visit(1)  # Backward navigation also reuses the stored predictions.
    for _ in range(2):
        set_preview(False)
        expect(card.get_by_text('Terjemahan belum tersedia', exact=True)).to_be_visible()
        expect(card.get_by_text(re.compile(r'^Paragraf:'))).to_have_count(0)
        set_preview(True)
        expect(page_field).to_have_value('1 / 32')
        visit(1)
    assert calls() == before_calls
    assert base.download(page, button, 'thaharah_after_preview.csv') == before
    assert base.download(page, zip_button, 'thaharah_after_preview.zip') == zip_before
    _, members = base.zip_rows(zip_before)
    assert before in members.values()
    assert all(unit['translation']['text_indonesian'].encode() not in content
               for unit in DRAFTS for content in members.values())
    # Even optional draft preview must refuse another CSV with forged IDs.
    page.locator('input[type="file"]').set_input_files([
        base.payload('WRONG_ID.csv', DATA.replace(b'FQDEMO_01_00001', b'FQDEMO_01_99999'))])
    base.select(page, label, '3. WRONG_ID.csv')
    page.get_by_role('button', name='Proses Diakritisasi', exact=True).click()
    expect(button).to_be_visible(timeout=90_000)
    panel.click()
    expect(preview).not_to_be_checked()
    set_preview(True)
    expect(card.get_by_text('Terjemahan belum tersedia', exact=True)).to_be_visible()
    expect(card.get_by_text(re.compile(r'^Paragraf:'))).to_have_count(0)
    base.select(page, label, '2. 01_Thaharah.csv')
    # Wait for the NEW file's closed expander, rather than observing the old
    # forged file's checkbox during the streamed result-card replacement.
    expect(preview).to_have_count(0)
    panel.click()
    expect(preview).not_to_be_checked()
    set_preview(True)
    expect(page_field).to_have_value('1 / 32')
    before_calls = calls()
    visit(1)
    after_other_calls = calls()
    set_preview(False)
    expect(card.get_by_text('Terjemahan belum tersedia', exact=True)).to_be_visible()
    assert calls() == after_other_calls
    assert base.download(page, button, 'thaharah_after_switch.csv') == before
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
    assert sha256(reference.TRANSLATIONS_PATH.read_bytes()).hexdigest() == TRANSLATION_SHA256
    result.update(synthetic_only=False, real_thaharah_csv=True, real_drafts_prepared=paragraph_count,
        real_drafts_displayed=paragraph_count, real_segments_displayed=segment_count,
        pagination_pages_visited=pages, paragraphs_per_page=10, max_cards_rendered=10,
        first_middle_last_pages_pass=True, page_resets_on_file_change=True,
        translation_data_unchanged=True,
        multi_segment_paragraphs_displayed=len(multi), verified_translations_displayed=0,
        explicit_opt_in_default_off=True, draft_warnings_visible=True,
        model_arabic_matches_download=True, side_by_side_desktop=True,
        preview_does_not_infer=True, wrong_id_unavailable_even_in_preview=True,
        final_mode_hides_all_drafts=True, csv_and_zip_byte_identical=True,
        translation_not_in_exports=True)
    return result


original_run = base.run
if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    TRANSLATION_SHA256 = sha256(reference.TRANSLATIONS_PATH.read_bytes()).hexdigest()
    DATA = (reference.DEMO / 'CSV/01_Thaharah.csv').read_bytes()
    frame = pd.read_csv(BytesIO(DATA), dtype=str, keep_default_na=False)
    DRAFTS = reference.display_units(DATA, frame, 'teks_gundul', preview_drafts=True)
    assert len(DRAFTS) == 317 and all(u['verification']['status'] == reference.DRAFT_STATUS for u in DRAFTS)
    assert [t['segment_id'] for u in DRAFTS for t in u['targets']] == frame['id'].tolist() == [f'FQDEMO_01_{i:05d}' for i in range(1, 329)]
    assert reference.display_units(DATA, frame, 'teks_gundul') == []
    # Instrument backend calls only; real production data/reader paths are unchanged.
    harness = f'''
import runpy, sys
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'streamlit_app')!r})
import inference_engine as backend
if not getattr(backend, '_TEST_ONLY_counted', False):
    original = backend.process_uploaded_file
    def counted(*args, **kwargs):
        with Path({str(OUT / 'model_calls.txt')!r}).open('a', encoding='utf-8') as stream:
            stream.write('TEST_ONLY backend call\\n')
        return original(*args, **kwargs)
    backend.process_uploaded_file = counted
    backend._TEST_ONLY_counted = True
runpy.run_path({str(ROOT / 'streamlit_app/app.py')!r}, run_name='__main__')
'''
    path = OUT / 'harness_TEST_ONLY.py'
    path.write_text(harness, encoding='utf-8')
    base.OUT, base.run = OUT, run
    base.main(app_path=path)
