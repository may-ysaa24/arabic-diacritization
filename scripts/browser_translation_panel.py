"""Native Edge regression plus real, unverified Thaharah fallback panel.

Reuses the existing multi-file acceptance flow without overwriting its artifacts.
No references, permission evidence, datasets, or model files are written.
"""
from datetime import datetime
from pathlib import Path
import re
import sys

from playwright.sync_api import expect
import browser_multifile as base

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/translation-panel' / ('browser_' + datetime.now().strftime('%Y%m%d_%H%M%S'))


def run(page, url):
    result = original_run(page, url)
    picker = page.locator('input[type="file"]')
    source = ROOT / 'data/demo_fathul_qorib_per_bab/CSV/01_Thaharah.csv'
    picker.set_input_files([str(source)])
    base.select(page, 'Berkas untuk pratinjau, proses ulang, atau unduh', '2. 01_Thaharah.csv')
    card = page.locator('.st-key-file_result_card')
    expect(card.get_by_text('Lihat Terjemahan Referensi', exact=True)).to_have_count(0)
    page.get_by_role('button', name='Proses Diakritisasi', exact=True).click()
    button = card.get_by_role('button', name=re.compile(r'Unduh CSV$'))
    expect(button).to_be_visible(timeout=180_000)
    csv_before = base.download(page, button, 'thaharah_before.csv')
    page.get_by_role('button', name='Siapkan ZIP', exact=True).click()
    zip_before = base.download(page, page.get_by_role('button', name='Unduh Semua (ZIP)', exact=True), 'before_panel.zip')
    panel = card.locator('[data-testid="stExpander"]').filter(
        has=page.get_by_text('Lihat Terjemahan Referensi', exact=True))
    expect(panel).to_be_visible()
    expect(panel.get_by_text('Terjemahan belum tersedia', exact=True)).to_have_count(0)
    for _ in range(2):
        panel.get_by_text('Lihat Terjemahan Referensi', exact=True).click()
        notice = panel.get_by_text('Terjemahan belum tersedia', exact=True)
        expect(notice).to_be_visible()
        notice.scroll_into_view_if_needed()
        expect(notice).to_be_in_viewport(ratio=0.9)
        expect(panel.get_by_text(re.compile('bukan keluaran model'))).to_be_visible()
        page.screenshot(path=str(OUT / 'panel_unavailable.png'), full_page=True, animations='disabled')
        panel.get_by_text('Lihat Terjemahan Referensi', exact=True).click()
        expect(panel.get_by_text('Terjemahan belum tersedia', exact=True)).to_have_count(0)
    assert base.download(page, button, 'thaharah_after.csv') == csv_before
    assert base.download(page, page.get_by_role('button', name='Unduh Semua (ZIP)', exact=True), 'after_panel.zip') == zip_before
    page.set_viewport_size({'width': 390, 'height': 844})
    panel.get_by_text('Lihat Terjemahan Referensi', exact=True).click()
    notice = panel.get_by_text('Terjemahan belum tersedia', exact=True)
    expect(notice).to_be_visible()
    notice.scroll_into_view_if_needed()
    expect(notice).to_be_in_viewport(ratio=0.9)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(OUT / 'panel_mobile.png'), full_page=True, animations='disabled')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    base.select(page, 'Berkas untuk pratinjau, proses ulang, atau unduh', '1. one.txt')
    expect(card.get_by_text('Lihat Terjemahan Referensi', exact=True)).to_have_count(0)
    page.get_by_role('button', name='Proses Diakritisasi', exact=True).click()
    expect(card.get_by_role('button', name=re.compile(r'Unduh TXT$'))).to_be_visible()
    base.select(page, 'Berkas untuk pratinjau, proses ulang, atau unduh', '2. 01_Thaharah.csv')
    expect(button).to_be_visible()
    assert base.download(page, button, 'thaharah_after_switch.csv') == csv_before
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
    result.update(real_thaharah_csv_processed=True, optional_panel_unavailable=True,
                  native_open_close=True, downloads_byte_identical=True,
                  txt_has_no_panel=True, panel_mobile_no_overflow=True,
                  verified_translation_browser_test=False)
    return result


original_run = base.run
if __name__ == '__main__':
    if not (ROOT / 'data/demo_fathul_qorib_per_bab/CSV/01_Thaharah.csv').is_file():
        sys.exit('Private Thaharah CSV required for browser acceptance')
    base.OUT, base.run = OUT, run
    base.main()
