"""Edge acceptance for input/results: real model, local drafts, and responsive screenshots."""
import csv
from hashlib import sha256
from io import StringIO
from pathlib import Path
import re
import sys

from playwright.sync_api import expect
import browser_multifile as base
import browser_acceptance as acceptance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/result-simplified'
DESIGN_SAMPLE = (
    'وَإِنَّمَا يُكْرَهُ شَرْعًا بِقَطْرٍ حَارٍ فِي إِنَاءٍ مُنْطَبِعٍ إِلَّا إِنَاءَ النَّقْدَيْنِ لِصِفَاءِ جَوْهِرِهِمَا، '
    'وَإِذَا بَرَدَ زَالَتُ الْكَرَاهَةُ. وَاخْتَارَ النَّوَوِيُّ عَدَمَ الْكَرَاهَةِ مُطْلَقًا، '
    'وَيُكْرَهُ أَيْضًا شَدِيدُ السُّخُونَةِ وَالْبُرُودَةِ.'
)


def calls():
    path = OUT / 'model_calls.txt'
    return path.read_text(encoding='utf-8').splitlines() if path.exists() else []


def run(page, url):
    acceptance.BASE_URL, acceptance.SCREENSHOTS = url, OUT
    page.goto(url, wait_until='domcontentloaded')
    page.locator('.st-key-home_cta button').click()
    area = page.get_by_role('textbox', name='Teks Arab', exact=True)
    expect(area).to_be_visible(timeout=90_000)
    assert area.get_attribute('maxlength') is None  # No invented 10,000-character limit.
    before_calls = calls()
    raw = '\n\n'.join([rows[91]['teks_gundul'], rows[92]['teks_gundul'], DESIGN_SAMPLE])
    area.fill(raw)
    expect(page.locator('#manual_char_count')).to_have_text(str(len(raw)))
    assert calls() == before_calls  # Typing never predicts.
    page.locator('.st-key-process_manual button').click()
    card = page.locator('.st-key-manual_result_card')
    arabic = card.locator('.arabic-result').first
    expect(arabic).to_be_visible(timeout=90_000)
    prediction = arabic.text_content()
    assert len(calls()) == len(before_calls) + 1
    after_process = calls()
    download = card.locator('.st-key-manual_result_actions').get_by_role('button', name=re.compile('Unduh TXT$'))
    before = base.download(page, download, 'manual_before.txt')
    assert before.decode('utf-8') == prediction
    card.get_by_role('radio', name='Arab + Terjemahan', exact=True).click()
    preview = card.get_by_role('checkbox', name='Pratinjau draf lokal (belum diverifikasi)', exact=True)
    expect(preview).to_have_count(0)
    field = card.get_by_role('combobox', name='Halaman terjemahan', exact=True)
    expect(field).to_have_value('1 / 3')
    base.select(page, 'Halaman terjemahan', '3 / 3')
    expect(card.locator('[class*="st-key-translation_card_manual_"]')).to_have_count(1)
    expect(card.get_by_text('Draf terjemahan, belum diverifikasi', exact=True)).to_have_count(0)
    expect(card.get_by_text('Detail Referensi', exact=True)).to_have_count(0)
    expect(page.locator('.input-book-label')).to_have_count(0)
    for width, height in [(1440, 1100), (1024, 1050), (768, 1024), (390, 844)]:
        page.set_viewport_size({'width': width, 'height': height})
        sidebar = page.locator('[data-testid="stSidebar"]')
        if width <= 780:
            # Streamlit collapses the drawer asynchronously on a narrow resize.
            # Wait for that state before trying to operate its controls.
            expect(sidebar).to_have_attribute('aria-expanded', 'false')
        acceptance.wait_sidebar_transition(sidebar)
        acceptance.set_sidebar(page, width > 780)
        # Top-of-page view captures the actual header, input and result hierarchy.
        page.locator('.input-page-hero').scroll_into_view_if_needed()
        acceptance.assert_layout(page)
        assert area.evaluate('(el) => getComputedStyle(el).direction') == 'rtl'
        process = page.locator('.st-key-process_manual button')
        assert process.bounding_box()['height'] >= 44
        if width > 780:
            assert 220 <= process.bounding_box()['width'] <= 270
        else:
            assert process.bounding_box()['width'] <= width
        left = card.locator('[data-testid="stColumn"]').filter(has=page.get_by_text('Terjemahan Indonesia', exact=True))
        right = card.locator('[data-testid="stColumn"]').filter(has=page.get_by_text('Teks Arab Berharakat', exact=True))
        a, b = left.bounding_box(), right.bounding_box()
        if width == 1440:
            assert a['x'] < b['x']
        elif width <= 768:
            assert b['y'] + b['height'] <= a['y'] + 1
        assert right.locator('.arabic-text').evaluate_all('(els) => els.every(e => getComputedStyle(e).direction === "rtl" && e.scrollWidth <= e.clientWidth + 1)')
        assert right.locator('.result-pane-heading').evaluate(
            'el => el.lastElementChild.classList.contains("result-icon-book")')
        assert left.locator('.result-pane-heading').evaluate(
            'el => el.firstElementChild.classList.contains("result-icon-translate")')
        assert right.locator('.arabic-text').evaluate_all(
            '(els) => els.every(e => e.scrollHeight <= e.clientHeight + 1 && getComputedStyle(e).overflowY === "visible")')
        expect(card.get_by_text('Draf terjemahan, belum diverifikasi', exact=True)).to_have_count(0)
        expect(card.get_by_text('Teks berhasil diakritisasi menggunakan model BiLSTM–CRF.', exact=True)).to_be_visible()
        university = page.locator('.brand-university')
        assert university.evaluate('el => getComputedStyle(el).textAlign') == 'center'
        expect(page.get_by_text('Unggul, Mandiri, dan Islami', exact=True)).to_have_count(0)
        area.focus(); page.keyboard.press('Tab')
        assert page.evaluate('''() => {const e=document.activeElement,s=getComputedStyle(e);
            return e.matches(':focus-visible') && (s.outlineStyle!=='none'||s.boxShadow!=='none');}''')
        area.evaluate('(el) => {el.scrollTop=0;}')
        page.mouse.move(width - 6, 6)  # Keep screenshots independent of hover leftovers.
        page.screenshot(path=str(OUT / f'input_{width}.png'), full_page=True, animations='disabled')
        # Streamlit scrolls its main container rather than the document. Capture
        # the complete result card separately so both languages are visible.
        card.locator('[class*="st-key-translation_card_manual_"]').first.screenshot(
            path=str(OUT / f'result_{width}.png'), animations='disabled')
        # A long mobile pair exceeds the scroll viewport. Separate native card
        # captures preserve the complete paragraphs without altering page CSS.
        right.screenshot(path=str(OUT / f'arabic_card_{width}.png'), animations='disabled')
        left.screenshot(path=str(OUT / f'indonesian_card_{width}.png'), animations='disabled')
        # Capture the result hierarchy, not just the top-of-page input form.
        card.evaluate('''el => {el.scrollIntoView({block:'start'});
            const main=el.closest('[data-testid="stMain"]'); if(main) main.scrollTop-=24;}''')
        page.screenshot(path=str(OUT / f'translation_{width}.png'), animations='disabled')
        card.get_by_role('radio', name='Arab Berharakat', exact=True).click()
        expect(card.locator('.arabic-result').first).to_have_text(prediction)
        card.evaluate('''el => {el.scrollIntoView({block:'start'});
            const main=el.closest('[data-testid="stMain"]'); if(main) main.scrollTop-=24;}''')
        page.screenshot(path=str(OUT / f'arabic_{width}.png'), animations='disabled')
        card.get_by_role('radio', name='Arab + Terjemahan', exact=True).click()
        expect(preview).to_have_count(0)
        base.select(page, 'Halaman terjemahan', '3 / 3')
        assert calls() == after_process
        print(f'Result refinement {width}px PASS', flush=True)
    page.set_viewport_size({'width':1440,'height':1100})
    card.get_by_role('button', name=re.compile('Sebelumnya')).click()
    expect(field).to_have_value('2 / 3')
    card.get_by_role('button', name=re.compile('Berikutnya')).click()
    expect(field).to_have_value('3 / 3')
    assert calls() == after_process
    assert base.download(page, download, 'manual_after.txt') == before
    card.get_by_role('radio', name='Arab Berharakat', exact=True).click()
    expect(arabic).to_have_text(prediction)
    page.get_by_role('button', name=re.compile('Koreksi Manual$')).click()
    expect(page.get_by_role('textbox', name='Koreksi Manual Harakat', exact=True)).to_be_visible()
    assert calls() == after_process
    page.context.grant_permissions(['clipboard-read','clipboard-write'])
    acceptance.test_manual(page.context)
    acceptance.test_mobile(page.context.browser)
    assert sha256((ROOT/'references/fathul_qorib/original/translations.jsonl').read_bytes()).hexdigest() == reference_hash
    return {'status':'PASS','manual_viewports':[1440,1024,768,390],
            'real_canonical_drafts':3,'manual_paragraphs_per_page':1,
            'automatic_saved_translation_display':True,'typing_and_navigation_do_not_infer':True,
            'rtl_and_responsive_columns':True,'keyboard_focus':True,'copy_download_correction_restore':True,
            'exports_unchanged':True,'translation_data_unchanged':True,'mobile_touch_navigation':True,
            'requested_long_arabic_sample':True,'arabic_and_translation_view_screenshots':True,
            'requested_icon_order':True,'removed_preview_draft_badge_and_reference_details':True,
            'process_button_desktop_220_to_270_px':True,'no_inner_paragraph_scroll':True}


if __name__ == '__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    reference_hash=sha256((ROOT/'references/fathul_qorib/original/translations.jsonl').read_bytes()).hexdigest()
    rows=list(csv.DictReader(StringIO((ROOT/'data/demo_fathul_qorib_per_bab/CSV/01_Thaharah.csv').read_text(encoding='utf-8-sig'))))
    harness=f'''
import sys,runpy
from pathlib import Path
sys.path.insert(0,{str(ROOT/'streamlit_app')!r})
import inference_engine as backend
if not getattr(backend,'_UI1_counted',False):
    original=backend.predict_long_text
    def counted(*args,**kwargs):
        with Path({str(OUT/'model_calls.txt')!r}).open('a',encoding='utf-8') as f:f.write('TEST_ONLY manual inference\\n')
        return original(*args,**kwargs)
    backend.predict_long_text=counted
    backend._UI1_counted=True
runpy.run_path({str(ROOT/'streamlit_app/app.py')!r},run_name='__main__')
'''
    path=OUT/'harness_TEST_ONLY.py'
    path.write_text(harness,encoding='utf-8')
    base.OUT,base.run=OUT,run
    base.main(app_path=path)
