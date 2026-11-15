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
import browser_acceptance as acceptance

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'streamlit_app'))
import translation_reference as reference

OUT = ROOT / 'test-results/upload-final'
PREVIEW = 'Pratinjau draf lokal (belum diverifikasi)'


def calls():
    path = OUT / 'model_calls.txt'
    return path.read_text(encoding='utf-8').splitlines() if path.exists() else []


def capture_upload_start(page, url):
    page.goto(url, wait_until='domcontentloaded')
    page.locator('.st-key-nav label').filter(has_text='Diakritisasi').click()
    page.get_by_role('tab', name='Unggah TXT / CSV', exact=False).click()
    expect(page.locator('[data-testid="stStatusWidget"]')).not_to_be_visible(timeout=60_000)
    expect(page.locator('.st-key-process_file button')).to_have_count(1)
    before = calls()
    for width, height in [(1440, 1100), (1024, 1050), (768, 1024), (390, 844)]:
        page.set_viewport_size({'width': width, 'height': height})
        sidebar = page.locator('[data-testid="stSidebar"]')
        if width <= 780:
            expect(sidebar).to_have_attribute('aria-expanded', 'false')
        acceptance.wait_sidebar_transition(sidebar)
        acceptance.set_sidebar(page, width > 780)
        page.locator('.upload-page-hero').scroll_into_view_if_needed()
        expect(page.locator('.input-page-hero')).not_to_be_visible()
        expect(page.get_by_role('heading', name='Unggah TXT/CSV', exact=True)).to_be_visible()
        expect(page.get_by_text('Unggah berkas teks Arab untuk diproses menggunakan model BiLSTM–CRF.', exact=True)).to_be_visible()
        expect(page.locator('.input-book-label')).to_have_count(0)
        expect(page.get_by_role('button', name='Proses Diakritisasi', exact=True)).to_be_disabled()
        button = page.locator('.st-key-process_file button')
        if width > 780:
            assert 220 <= button.bounding_box()['width'] <= 270
        assert button.bounding_box()['height'] >= 44
        uploader = page.locator('[data-testid="stFileUploader"]')
        settings = page.locator('.st-key-file_output_settings')
        listing = page.locator('.st-key-file_management_columns [data-testid="stColumn"]').first
        active = page.locator('.st-key-file_settings_card')
        if width == 1440:
            assert uploader.bounding_box()['x'] + uploader.bounding_box()['width'] < settings.bounding_box()['x']
            assert listing.bounding_box()['x'] + listing.bounding_box()['width'] < active.bounding_box()['x']
        else:
            assert uploader.bounding_box()['y'] + uploader.bounding_box()['height'] <= settings.bounding_box()['y']
            assert listing.bounding_box()['y'] + listing.bounding_box()['height'] <= active.bounding_box()['y']
        acceptance.assert_layout(page)
        page.mouse.move(width-6, 6)
        page.screenshot(path=str(OUT / f'upload_final_{width}.png'), animations='disabled')
    assert calls() == before
    page.set_viewport_size({'width': 1440, 'height': 1100})
    expect(page.locator('[data-testid="stSidebar"]')).to_have_attribute('aria-expanded', 'true')
    acceptance.wait_sidebar_transition(page.locator('[data-testid="stSidebar"]'))


def capture_matched_upload(page, frame):
    """Plain CSV, long filename, a real stored translation plus an unmatched row."""
    source = frame.iloc[25]['teks_gundul']
    data = pd.DataFrame({'arabic': [source, 'السلام عليكم'], 'info': ['=1+1', 'outside']}).to_csv(index=False).encode()
    name = 'thaharah_' + 'teks_arab_' * 9 + '.csv'
    page.locator('input[type="file"]').set_input_files([base.payload(name, data)])
    base.select(page, 'Berkas untuk pratinjau, proses ulang, atau unduh', '4. ' + name)
    settings = page.locator('.st-key-file_output_settings')
    card = page.locator('.st-key-file_result_card')
    before_calls = calls()
    settings.get_by_role('radio', name='Arab + Terjemahan', exact=True).click()
    assert calls() == before_calls
    settings.get_by_role('button', name='Proses Diakritisasi', exact=True).click()
    indo = card.locator('.translation-indonesian')
    expected = next(u for u in DRAFTS if any(t['segment_id'] == frame.iloc[25]['id'] for t in u['targets']))
    expect(indo).to_have_text(expected['translation']['text_indonesian'], timeout=90_000)
    assert len(calls()) == len(before_calls) + 1
    saved_calls = calls()
    expect(card.get_by_text('Sebagian teks belum dapat dipasangkan dengan terjemahan. Hasil Arab lengkap tetap tersedia.', exact=True)).to_be_visible()
    card.get_by_text('Hasil Arab lengkap', exact=True).click()
    expect(card.locator('.arabic-csv-row')).to_have_count(2)
    card.get_by_text('Hasil Arab lengkap', exact=True).click()
    download = card.get_by_role('button', name=re.compile(r'Unduh CSV$'))
    before = base.download(page, download, 'ordinary_before_mode.csv')
    arabic = card.locator('[data-testid="stColumn"]').filter(has=page.get_by_text('Teks Arab Berharakat', exact=True))
    indonesia = card.locator('[data-testid="stColumn"]').filter(has=page.get_by_text('Terjemahan Indonesia', exact=True))
    for width, height in [(1440,1100),(1024,1050),(768,1024),(390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        sidebar = page.locator('[data-testid="stSidebar"]')
        if width <= 780:
            expect(sidebar).to_have_attribute('aria-expanded', 'false')
        acceptance.wait_sidebar_transition(sidebar)
        acceptance.set_sidebar(page, width > 780)
        acceptance.assert_layout(page)
        assert arabic.locator('.arabic-text').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).direction==="rtl" && e.scrollWidth<=e.clientWidth+1)')
        # Check the accepted panes directly, independently of outer layout.
        for pane, background, border, heading, text, body in (
            (indonesia, 'rgb(250, 245, 233)', 'rgb(233, 215, 174)', 'rgb(128, 85, 13)', 'rgb(48, 43, 36)', '.translation-indonesian'),
            (arabic, 'rgb(242, 249, 245)', 'rgb(216, 233, 223)', 'rgb(23, 96, 71)', 'rgb(24, 62, 49)', '.arabic-text')):
            assert pane.evaluate('(e)=>getComputedStyle(e).backgroundColor') == background
            assert pane.evaluate('(e)=>getComputedStyle(e).borderColor') == border
            assert pane.evaluate('(e)=>getComputedStyle(e).borderRadius') == '14px'
            assert pane.locator('.result-pane-heading').evaluate('(e)=>getComputedStyle(e).color') == heading
            assert pane.locator(body).evaluate_all('(els)=>els.every(e=>getComputedStyle(e).color==="'+text+'")')
        a,b = arabic.bounding_box(),indonesia.bounding_box()
        if width == 1440: assert b['x'] < a['x']
        if width <= 768: assert a['y'] + a['height'] <= b['y'] + 1
        card.evaluate('el=>el.scrollIntoView({block:"start"})')
        page.screenshot(path=str(OUT / f'upload_translation_{width}.png'), animations='disabled')
        if width == 1440:
            page.screenshot(path=str(OUT / 'upload_result_translation.png'), animations='disabled')
            page.screenshot(path=str(OUT / 'upload_final_translation.png'), animations='disabled')
        if width == 390:
            arabic.screenshot(path=str(OUT/'upload_result_mobile.png'), animations='disabled')
            indonesia.screenshot(path=str(OUT/'upload_indonesian_mobile.png'), animations='disabled')
    page.set_viewport_size({'width':1440,'height':1100})
    settings.get_by_role('radio', name='Arab Berharakat', exact=True).click()
    expect(card.locator('.arabic-csv-row')).to_have_count(2)
    assert base.download(page, download, 'ordinary_after_mode.csv') == before
    assert expected['translation']['text_indonesian'].encode() not in before
    assert calls() == saved_calls


def run(page, url):
    page.on('pageerror', lambda error: print('Browser page error:', error, flush=True))
    capture_upload_start(page, url)
    result = original_run(page, url)
    paragraph_count = len(DRAFTS)
    segment_count = sum(len(u['targets']) for u in DRAFTS)
    label = 'Berkas untuk pratinjau, proses ulang, atau unduh'
    page.locator('input[type="file"]').set_input_files([base.payload('01_Thaharah.csv', DATA)])
    base.select(page, label, '2. 01_Thaharah.csv')
    page.locator('.st-key-file_management_card').screenshot(path=str(OUT / 'upload_final_files.png'), animations='disabled')
    page.get_by_role('button', name='Proses Diakritisasi', exact=True).click()
    card = page.locator('.st-key-file_result_card')
    button = card.get_by_role('button', name=re.compile(r'Unduh CSV$'))
    expect(button).to_be_visible(timeout=90_000)
    before = base.download(page, button, 'thaharah_before_preview.csv')
    card.evaluate('el => el.scrollIntoView({block:"start"})')
    page.screenshot(path=str(OUT / 'upload_result_arabic.png'), animations='disabled')
    page.screenshot(path=str(OUT / 'upload_final_results.png'), animations='disabled')
    rows = {row['id']: row for row in csv.DictReader(StringIO(before.decode('utf-8-sig')))}
    page.get_by_role('button', name=re.compile(r'Siapkan ZIP$')).click()
    zip_button = page.get_by_role('button', name=re.compile(r'Unduh Semua \(ZIP\)$'))
    zip_before = base.download(page, zip_button, 'thaharah_before_preview.zip')
    before_calls = calls()
    settings = page.locator('.st-key-file_output_settings')
    panel = settings.get_by_role('radio', name='Arab + Terjemahan', exact=True)
    panel.click()
    preview = card.get_by_role('checkbox', name=PREVIEW, exact=True)
    expect(preview).to_have_count(0)
    cards = card.locator('[class*="st-key-translation_card_"]')
    page_field = card.locator('[data-testid="stSelectbox"]').filter(
        has=page.get_by_text('Halaman terjemahan', exact=True)).get_by_role('combobox')
    pages = (paragraph_count + 9) // 10
    left = card.locator('[data-testid="stColumn"]').filter(has=page.get_by_text('Teks Arab Berharakat', exact=True))
    right = card.locator('[data-testid="stColumn"]').filter(has=page.get_by_text('Terjemahan Indonesia', exact=True))
    def visit(number):
        value = f'{number} / {pages}'
        expect(page.locator('[data-testid="stStatusWidget"]')).not_to_be_visible(timeout=60_000)
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
                    expect(page.locator('[data-testid="stStatusWidget"]')).not_to_be_visible(timeout=60_000)
                    expect(page_field).to_have_value(value)
                    break
                except (AssertionError, PlaywrightTimeoutError):
                    if attempt == 2:
                        raise
        expect(page_field).to_have_value(value)
        start, end = (number - 1) * 10, min(number * 10, paragraph_count)
        expected = DRAFTS[start:end]
        expect(card.get_by_text(f'Paragraf {start + 1}–{end} dari {paragraph_count} · Halaman {number} dari {pages}', exact=True)).to_be_visible()
        expect(cards).to_have_count(len(expected))
        expect(card.get_by_text(reference.DRAFT_LABEL, exact=True)).to_have_count(0)
        expect(card.get_by_text(reference.CONTENT_DRAFT_LABEL, exact=True)).to_have_count(0)
        expect(card.get_by_text('Detail Referensi', exact=True)).to_have_count(0)
        expect(left).to_have_count(len(expected))
        expect(right).to_have_count(len(expected))
        for i, unit in enumerate(expected):
            text = unit['translation']['text_indonesian']
            # Streamed deltas can update the page selector before replacing
            # all ten cards. Wait for the exact expected identity, not just
            # the unchanged card count from the preceding page.
            expect(cards.nth(i)).to_have_attribute('class', re.compile(re.escape(unit['paragraph_id'])))
            for target in unit['targets']:
                segment = target['segment_id']
                expect(left.nth(i).get_by_text(rows[segment]['hasil_diacritization'], exact=True)).to_be_visible()
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
    assert left.nth(6).bounding_box()['x'] > right.nth(6).bounding_box()['x']
    multi = [i for i, u in enumerate(DRAFTS) if len(u['targets']) > 1]
    assert len(multi) == 10
    right.nth(6).scroll_into_view_if_needed()  # Last complete paragraph spans 00327–00328.
    page.screenshot(path=str(OUT / 'draft_desktop.png'), full_page=False, animations='disabled')
    checked_viewports = []
    for width, height in [(1440, 1000), (1024, 900), (768, 1024), (390, 844)]:
        page.set_viewport_size({'width': width, 'height': height})
        if width <= 780:
            expect(page.locator('[data-testid="stSidebar"]')).to_have_attribute('aria-expanded', 'false')
        acceptance.wait_sidebar_transition(page.locator('[data-testid="stSidebar"]'))
        acceptance.set_sidebar(page, width > 780)
        left.nth(6).scroll_into_view_if_needed()
        expect(left.nth(6)).to_be_visible()
        arabic_box, indo_box = left.nth(6).bounding_box(), right.nth(6).bounding_box()
        if width == 1440:
            assert arabic_box['x'] > indo_box['x']
        elif width <= 768:
            assert arabic_box['y'] + arabic_box['height'] <= indo_box['y'] + 1
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        for readable in [left.nth(6).locator('.arabic-text'), right.nth(6).locator('.translation-indonesian')]:
            assert readable.evaluate_all('(els) => els.length > 0 && els.every(el => el.scrollWidth <= el.clientWidth + 1)')
        assert left.nth(6).locator('.arabic-text').evaluate_all('(els) => els.every(el => getComputedStyle(el).direction === "rtl")')
        page.screenshot(path=str(OUT / f'draft_{width}.png'), full_page=False, animations='disabled')
        page.get_by_role('tab', name='Input Teks', exact=True).click()
        area = page.get_by_role('textbox', name='Teks Arab', exact=True)
        expect(area).to_be_visible()
        assert area.evaluate('(el) => getComputedStyle(el).direction') == 'rtl'
        assert area.evaluate('(el) => parseFloat(getComputedStyle(el).fontSize)') >= 24
        primary = page.locator('.st-key-process_manual button')
        assert primary.bounding_box()['height'] >= 44
        area.focus(); page.keyboard.press('Tab')
        assert page.evaluate('''() => {
            const el = document.activeElement, style = getComputedStyle(el);
            return el.matches(':focus-visible') &&
                (style.outlineStyle !== 'none' || style.boxShadow !== 'none');
        }''')
        acceptance.assert_layout(page)
        page.locator('.st-key-manual_card').scroll_into_view_if_needed()
        page.screenshot(path=str(OUT / f'input_{width}.png'), full_page=False, animations='disabled')
        page.get_by_role('tab', name='Unggah TXT / CSV', exact=False).click()
        uploader = page.locator('[data-testid="stFileUploader"]')
        expect(uploader).to_be_visible()
        assert uploader.bounding_box()['width'] <= width
        table_details = card.get_by_text('Tabel hasil CSV dan metadata', exact=True)
        table_details.click()
        table = card.locator('[data-testid="stDataFrame"]').first
        table.scroll_into_view_if_needed()
        expect(table).to_be_visible()
        acceptance.assert_layout(page)
        page.screenshot(path=str(OUT / f'csv_{width}.png'), full_page=False, animations='disabled')
        table_details.click()
        checked_viewports.append(width)
        print(f'Responsive translation layout {width}px passed', flush=True)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    visit(16)
    pagination = card.locator('.st-key-upload_pagination')
    expect(pagination.get_by_role('button', name='16', exact=True)).to_have_attribute('kind', 'primary')
    assert pagination.get_by_role('button').count() <= 7
    pagination.screenshot(path=str(OUT / 'upload_final_pagination.png'), animations='disabled')
    pagination.get_by_role('button', name='17', exact=True).click()
    expect(page_field).to_have_value('17 / 32')
    visit(17)
    visit(1)  # Backward navigation also reuses the stored predictions.
    card.get_by_role('button', name=re.compile('Berikutnya')).click()
    expect(page_field).to_have_value('2 / 32')
    card.get_by_role('button', name=re.compile('Sebelumnya')).click()
    expect(page_field).to_have_value('1 / 32')
    assert calls() == before_calls
    for _ in range(2):
        settings.get_by_role('radio', name='Arab Berharakat', exact=True).click()
        expect(cards).to_have_count(0)
        panel.click()
        expect(page_field).to_have_value('1 / 32')
        visit(1)
    assert calls() == before_calls
    assert base.download(page, button, 'thaharah_after_preview.csv') == before
    assert base.download(page, zip_button, 'thaharah_after_preview.zip') == zip_before
    _, members = base.zip_rows(zip_before)
    assert before in members.values()
    assert all(unit['translation']['text_indonesian'].encode() not in content
               for unit in DRAFTS for content in members.values())
    # Reject a forged paragraph identity; valid other paragraphs remain available.
    page.locator('input[type="file"]').set_input_files([
        base.payload('WRONG_ID.csv', DATA.replace(b'FQDEMO_01_00001', b'FQDEMO_01_99999'))])
    base.select(page, label, '3. WRONG_ID.csv')
    page.get_by_role('button', name='Proses Diakritisasi', exact=True).click()
    expect(button).to_be_visible(timeout=90_000)
    panel.click()
    expect(preview).to_have_count(0)
    expect(cards).to_have_count(10)
    expect(card.locator('[class*="st-key-translation_card_"][class*="_' + DRAFTS[0]['paragraph_id'] + '"]')).to_have_count(0)
    expect(card.get_by_text(re.compile('1 bagian tidak cocok dengan referensi kanonis'))).to_be_visible()
    base.select(page, label, '2. 01_Thaharah.csv')
    expect(settings.get_by_role('radio', name='Arab Berharakat', exact=True)).to_be_checked()
    panel.click()
    expect(preview).to_have_count(0)
    expect(page_field).to_have_value('1 / 32')
    before_calls = calls()
    visit(1)
    after_other_calls = calls()
    settings.get_by_role('radio', name='Arab Berharakat', exact=True).click()
    expect(cards).to_have_count(0)
    assert calls() == after_other_calls
    assert base.download(page, button, 'thaharah_after_switch.csv') == before
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
    assert sha256(reference.TRANSLATIONS_PATH.read_bytes()).hexdigest() == TRANSLATION_SHA256
    capture_matched_upload(page, frame)
    # Reuse actual-browser correction/copy/stale-input checks on a separate session.
    page.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    acceptance.BASE_URL, acceptance.SCREENSHOTS = url, OUT
    acceptance.test_manual(page.context)
    acceptance.test_mobile(page.context.browser)
    result.update(synthetic_only=False, real_thaharah_csv=True, real_drafts_prepared=paragraph_count,
        real_drafts_displayed=paragraph_count, real_segments_displayed=segment_count,
        pagination_pages_visited=pages, paragraphs_per_page=10, max_cards_rendered=10,
        first_middle_last_pages_pass=True, page_resets_on_file_change=True,
        translation_data_unchanged=True,
        multi_segment_paragraphs_displayed=len(multi), verified_translations_displayed=0,
        automatic_saved_translation_display=True, technical_reference_ui_hidden=True,
        model_arabic_matches_download=True, side_by_side_desktop=True,
        preview_does_not_infer=True, wrong_id_paragraph_rejected_valid_others_retained=True,
        arabic_mode_hides_translations=True, csv_and_zip_byte_identical=True,
        translation_not_in_exports=True, responsive_viewports=checked_viewports,
        desktop_indonesian_left_arabic_right=True, mobile_arabic_above_indonesian=True,
        manual_correction_copy_and_original_result_preserved=True,
        keyboard_focus_and_touch_targets=True, bottom_pagination_preserves_inference=True,
        mobile_touch_context_navigation_manual_and_download=True)
    result.update(upload_settings_before_inference=True, partial_translation_keeps_complete_arabic=True,
                  upload_long_filename_responsive=True, single_click_single_processing_call=True,
                  upload_screenshots_saved=True, numbered_pagination_pass=True,
                  accepted_result_pane_colors_and_radius_preserved=True)
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
