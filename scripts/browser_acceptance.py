"""Real-browser acceptance for the supported app; no training or research writes.

Run against an existing server. See README for requirements-browser.txt,
PLAYWRIGHT_CHANNEL, STREAMLIT_URL and BROWSER_SCREENSHOTS.
"""
from __future__ import annotations

import csv
import io
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from arabic_diacritization.inference import predict_long_text
from arabic_diacritization.file_processing import process_txt_bytes

BASE_URL = os.environ.get("STREAMLIT_URL", "http://127.0.0.1:8501")
SCREENSHOTS = Path(os.environ.get("BROWSER_SCREENSHOTS", "results/browser-acceptance"))
ARABIC = "الحمد لله رب العالمين"
ALTERNATIVE = "رب العالمين"
SCROLL_SCRIPT = """(() => {
  window._acceptanceResultScrolls = [];
  const original = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function(options) {
    if (this.matches('.st-key-manual_result_card,.st-key-file_result_card'))
      window._acceptanceResultScrolls.push(options);
    return original.call(this, options);
  };
})();"""


def prediction(text):
    result = predict_long_text(text)
    assert result["success"], result.get("message")
    return result["prediction"]


def screenshot(page, name):
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True)


def assert_layout(page):
    assert page.evaluate("""() => {
      const main = document.querySelector('[data-testid="stMain"]');
      return document.documentElement.scrollWidth <= innerWidth &&
        main.scrollWidth <= main.clientWidth;
    }"""), "Page/main has horizontal overflow"
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)


def assert_native_exports_disabled(page):
    # Assert absence of the real native control, rather than CSS invisibility.
    expect(page.locator('[data-testid="stDataFrame"] button[aria-label="Download as CSV"]')).to_have_count(0)


def assert_native_copy_disabled(page, frame):
    marker = "acceptance: native dataframe copy must stay disabled"
    page.evaluate("text => navigator.clipboard.writeText(text)", marker)
    canvas = frame.locator("canvas").first
    expect(canvas).to_be_visible()
    canvas.scroll_into_view_if_needed()
    box = canvas.bounding_box()
    assert box and box["width"] > 45 and box["height"] > 52
    # Glide deliberately places its event-catching scroller above the canvas.
    # Send a real pointer click to the cell through that overlay, not a forced
    # click on the canvas element (which is not the pointer target).
    page.mouse.click(box["x"] + 45, box["y"] + 52)
    assert frame.evaluate("e => e.contains(document.activeElement)"), "Grid did not receive keyboard focus"
    page.keyboard.press("ControlOrMeta+c")
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    assert page.evaluate("() => navigator.clipboard.readText()") == marker, "Native table copy bypassed serializer"


def assert_download(page, button, filename, expected_text=None):
    expect(button).to_be_enabled()
    with page.expect_download(timeout=45_000) as info:
        button.click()
    download = info.value
    assert download.suggested_filename == filename, (download.suggested_filename, filename)
    data = download.path().read_bytes()
    assert data, f"Empty download: {filename}"
    if expected_text is not None:
        assert data == expected_text.encode("utf-8"), f"Download differs from active result: {filename}"
    print(f"PASS download: {filename} ({len(data)} bytes)", flush=True)
    return data


def summary(card, label, value):
    expect(card.locator(".processing-stat").filter(has_text=label).locator("dd")).to_have_text(str(value))


def wait_sidebar_transition(sidebar):
    # aria-expanded changes before the drawer's CSS transition finishes.
    # Reopening it in that interval tests an animation race, not a settled UI.
    sidebar.evaluate("""async sidebar => {
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      await Promise.allSettled(sidebar.getAnimations().map(animation => animation.finished));
      await new Promise(resolve => requestAnimationFrame(resolve));
    }""")


def set_sidebar(page, opened):
    sidebar = page.locator('[data-testid="stSidebar"]')
    current = sidebar.get_attribute("aria-expanded") == "true"
    if current != opened:
        selector = ('[data-testid="stSidebarCollapseButton"] button' if current
                    else 'button[data-testid="stExpandSidebarButton"]')
        page.locator(selector).click()
    expect(sidebar).to_have_attribute("aria-expanded", str(opened).lower())
    wait_sidebar_transition(sidebar)
    expect(sidebar).to_have_attribute("aria-expanded", str(opened).lower())


def navigate(page, label, *, mobile=False):
    set_sidebar(page, True)
    page.get_by_role("radiogroup", name="Navigasi utama").get_by_text(label, exact=True).click()
    expect(page.locator('.breadcrumb [aria-current="page"]')).to_have_text(label)
    expect(page.locator('[data-testid="stSidebar"]')).to_have_attribute("aria-expanded", str(not mobile).lower())
    wait_sidebar_transition(page.locator('[data-testid="stSidebar"]'))


def open_workspace(context, label):
    page = context.new_page()
    page.set_default_timeout(45_000)
    page.add_init_script(SCROLL_SCRIPT)
    page.goto(BASE_URL, wait_until="domcontentloaded")
    # Material icons can contribute a prefix to accessible names. Use the
    # UI-owned container and verify its text, rather than matching that prefix.
    cta = page.locator(".st-key-home_cta button")
    expect(cta).to_contain_text("Mulai Diakritisasi", timeout=90_000)
    expect(cta).to_be_visible()
    assert_layout(page)
    screenshot(page, f"{label}_home")
    cta.click()
    expect(page.get_by_role("tab", name=re.compile(r"Input Teks$"))).to_be_visible()
    expect(page.locator(".st-key-process_manual button")).to_be_enabled(timeout=90_000)
    return page


def scroll_count(page):
    return page.evaluate("window._acceptanceResultScrolls.length")


def predict_manual(page, text):
    before = scroll_count(page)
    page.get_by_role("textbox", name="Teks Arab", exact=True).fill(text)
    page.locator(".st-key-process_manual button").click()
    expected = prediction(text)
    result = page.locator(".st-key-manual_result_payload .arabic-result")
    expect(result).to_have_text(expected, timeout=90_000)
    assert result.text_content() == expected
    page.wait_for_function("n => window._acceptanceResultScrolls.length === n", arg=before + 1)
    return expected


def test_manual(context):
    page = open_workspace(context, "manual")
    raw = "الحمد لله\nرب العالمين"
    model = predict_manual(page, raw)
    card = page.locator(".st-key-manual_result_card")
    summary(card, "Karakter input", len(raw))
    summary(card, "Sumber teks aktif", "Prediksi Model")
    count = scroll_count(page)
    page.locator(".st-key-manual_comparison summary").click()
    panels = card.locator(".comparison-panel .arabic-text")
    expect(panels).to_have_count(2)
    assert panels.all_text_contents() == [raw, model]
    expect(panels.first).to_have_attribute("dir", "rtl")
    page.locator(".st-key-manual_correction_editor summary").click()
    corrected = "الْحَمْدُ لِلَّهِ\nرَبِّ الْعَالَمِينَ"
    assert corrected != model, "Correction fixture must actually change model output"
    page.get_by_role("textbox", name="Koreksi Manual Harakat", exact=True).fill(corrected)
    page.get_by_role("button", name="Terapkan Koreksi", exact=True).click()
    active = card.locator(".st-key-manual_result_payload .arabic-result")
    expect(active).to_have_text(corrected)
    assert active.text_content() == corrected
    summary(card, "Sumber teks aktif", "Koreksi Pengguna")
    page.locator("#copy_manual").click()
    expect(page.locator("#copy_manual_status")).to_have_text("Teks disalin.")
    assert page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n") == corrected
    actions = card.locator(".st-key-manual_result_actions")
    assert_download(page, actions.get_by_role("button", name=re.compile(r"Unduh TXT$")),
                    "hasil_koreksi_manual.txt", corrected)
    page.locator(".st-key-manual_original_result summary").click()
    assert_download(page, card.locator(".st-key-manual_model_result_actions").get_by_role("button", name=re.compile(r"Unduh TXT$")),
                    "hasil_asli_model.txt", model)
    page.get_by_role("button", name=re.compile(r"Kembalikan Hasil Model$")).click()
    expect(active).to_have_text(model)
    summary(card, "Sumber teks aktif", "Prediksi Model")
    assert scroll_count(page) == count
    assert_download(page, actions.get_by_role("button", name=re.compile(r"Unduh TXT$")),
                    "hasil_diakritisasi.txt", model)
    area = page.get_by_role("textbox", name="Teks Arab", exact=True)
    area.fill(ALTERNATIVE)  # Keep focus: stale protection before server commit.
    expect(card).to_have_attribute("data-input-stale", "true")
    payload = card.locator(".st-key-manual_result_payload")
    expect(payload).to_be_hidden()
    assert payload.evaluate("e => e.inert")
    expect(page.locator("#manual_char_count")).to_have_text(str(len(ALTERNATIVE)))
    area.press("Tab")
    expect(card.locator('[data-testid="stDownloadButton"] button')).to_be_disabled()
    expect(card.locator(".processing-summary")).to_have_count(0)
    assert scroll_count(page) == count
    predict_manual(page, ALTERNATIVE)
    assert_layout(page)
    screenshot(page, "manual_result")
    page.close()


def upload_file(page, filename, mime_type, data):
    page.get_by_role("tab", name=re.compile(r"Unggah TXT \/ CSV$")).click()
    page.locator('input[type="file"]').set_input_files({"name": filename, "mimeType": mime_type, "buffer": data})
    expect(page.get_by_text(f"Berkas aktif: {filename}", exact=False)).to_be_visible()


def process_file(page, kind):
    before = scroll_count(page)
    button = page.locator(".st-key-process_file button")
    expect(button).to_have_text("Proses Diakritisasi")
    expect(button).to_be_enabled()
    button.click()
    expect(page.get_by_text(f"File {kind} berhasil diproses.", exact=True)).to_be_visible(timeout=90_000)
    page.wait_for_function("n => window._acceptanceResultScrolls.length === n", arg=before + 1)
    assert_native_exports_disabled(page)


def test_txt(context):
    page = open_workspace(context, "txt")
    raw = (ARABIC + "\r\n\r\nabc\n").encode("utf-16")
    expected = process_txt_bytes(raw, filename="contoh.txt")
    assert expected["success"]
    upload_file(page, "contoh.txt", "text/plain", raw)
    process_file(page, "TXT")
    card = page.locator(".st-key-file_result_card")
    for label, value in [("Baris diperiksa", 3), ("Berhasil diprediksi", 1), ("Tidak diprediksi", 2), ("Baris gagal", 0)]:
        summary(card, label, value)
    data = assert_download(page, card.get_by_role("button", name=re.compile(r"Unduh TXT$")),
                           "contoh_hasil_diakritisasi.txt")
    assert data == expected["download_bytes"]
    assert_layout(page)
    screenshot(page, "txt_result")
    page.close()


def test_csv(context):
    page = open_workspace(context, "csv")
    values = ["=1+1", "+SUM(1,1)", "@SUM(1,1)", "-1+2", "\u200b=1+1", "＝1+1", "-12", "plain"]
    alternatives = [ALTERNATIVE, "abc", "", "الحمد abc", "abc", "abc", "abc", "abc"]
    source = io.StringIO(newline="")
    writer = csv.writer(source, lineterminator="\n")
    writer.writerow(["teks", "alternatif", "info", "id", "=header"])
    for index, (value, alternative) in enumerate(zip(values, alternatives), 1):
        writer.writerow([ARABIC if index == 1 else "abc", alternative, value, str(index), "literal"])
    upload_file(page, "contoh.csv", "text/csv", source.getvalue().encode("utf-8"))
    expect(page.get_by_text("Pratinjau CSV", exact=True)).to_be_visible()
    preview = page.locator(".st-key-file_upload_card [data-testid=stDataFrame]").first
    expect(preview).to_be_visible()
    assert_native_exports_disabled(page)
    assert_native_copy_disabled(page, preview)
    column = page.locator('[data-testid="stSelectbox"] button[aria-haspopup="listbox"]')
    for name in ("teks", "alternatif"):
        column.click()
        page.get_by_role("option", name=name, exact=True).click()
        expect(page.get_by_role("combobox", name="Pilih Kolom Teks Arab", exact=True)).to_have_value(name)
    process_file(page, "CSV")
    card = page.locator(".st-key-file_result_card")
    for label, value in [("Baris diperiksa", 8), ("Berhasil diprediksi", 1), ("Tidak diprediksi", 7), ("Baris gagal", 0)]:
        summary(card, label, value)
    assert_native_copy_disabled(page, card.locator('[data-testid="stDataFrame"]').first)
    data = assert_download(page, card.get_by_role("button", name=re.compile(r"Unduh CSV$")),
                           "contoh_hasil_diakritisasi.csv")
    assert data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    assert text.startswith('"teks","alternatif","info","id","\t=header"')
    rows = list(csv.DictReader(io.StringIO(text, newline="")))
    assert len(rows) == 8
    assert [r["info"] for r in rows] == ["\t" + v if i < 6 else v for i, v in enumerate(values)]
    assert [r["id"] for r in rows] == [str(i) for i in range(1, 9)]
    assert [r["alternatif"] for r in rows] == alternatives
    assert all(r["\t=header"] == "literal" for r in rows)
    assert rows[0]["hasil_diacritization"] == prediction(ALTERNATIVE)
    assert [r["status_diacritization"] for r in rows] == [
        "berhasil", "non_arab", "kosong", "campuran", "non_arab", "non_arab", "non_arab", "non_arab"]
    screenshot(page, "csv_result")
    before = scroll_count(page)
    navigate(page, "Tentang Model")
    navigate(page, "Diakritisasi")
    page.get_by_role("tab", name=re.compile(r"Unggah TXT \/ CSV$")).click()
    expect(page.get_by_text("Berkas aktif: contoh.csv", exact=False)).to_be_visible()
    expect(page.get_by_role("combobox", name="Pilih Kolom Teks Arab", exact=True)).to_have_value("alternatif")
    retained = assert_download(page, card.get_by_role("button", name=re.compile(r"Unduh CSV$")),
                               "contoh_hasil_diakritisasi.csv")
    assert retained == data
    assert scroll_count(page) == before
    page.locator(".st-key-reset_file button").click()
    expect(page.get_by_text("Berkas aktif: contoh.csv", exact=False)).to_have_count(0)
    expect(page.locator(".st-key-file_result_actions")).to_have_count(0)
    assert_layout(page)
    page.close()


def test_invalid(context):
    page = open_workspace(context, "invalid")
    page.locator(".st-key-process_manual button").click()
    expect(page.locator(".st-key-manual_card").get_by_text("Masukkan teks Arab terlebih dahulu sebelum memproses.")).to_be_visible()
    assert scroll_count(page) == 0
    for name, mime, data in [("invalid.txt", "text/plain", b"\x00\x01"),
                             ("empty.txt", "text/plain", b""),
                             ("broken.csv", "text/csv", b'teks,id\n"unterminated')]:
        upload_file(page, name, mime, data)
        expect(page.locator(".st-key-process_file button")).to_be_disabled()
        expect(page.locator(".st-key-file_result_actions")).to_have_count(0)
        assert scroll_count(page) == 0
    page.locator(".st-key-reset_file button").click()
    page.locator('input[type="file"]').set_input_files({
        "name": "oversize.txt", "mimeType": "text/plain", "buffer": b"a" * (5 * 1024 * 1024 + 1)})
    expect(page.get_by_text("Error: File must be 5.0MB or smaller.", exact=True)).to_be_visible()
    expect(page.locator(".st-key-process_file button")).to_be_disabled()
    screenshot(page, "invalid_files")
    page.close()


def test_navigation(context):
    page = open_workspace(context, "navigation")
    for label in ("Contoh Teks", "Tentang Model", "Beranda", "Diakritisasi"):
        navigate(page, label)
        assert_layout(page)
        set_sidebar(page, False)
        assert_layout(page)
        set_sidebar(page, True)
        assert_native_exports_disabled(page)
    screenshot(page, "navigation")
    page.close()


def test_mobile(browser):
    context = browser.new_context(accept_downloads=True, permissions=["clipboard-read", "clipboard-write"],
                                  viewport={"width": 390, "height": 844}, device_scale_factor=1,
                                  is_mobile=True, has_touch=True, reduced_motion="reduce")
    errors = []
    context.on("weberror", lambda error: errors.append(str(error.error)))
    try:
        page = open_workspace(context, "mobile")
        for label in ("Contoh Teks", "Tentang Model", "Beranda", "Diakritisasi"):
            navigate(page, label, mobile=True)
            assert_layout(page)
            set_sidebar(page, True)
            assert_layout(page)
            set_sidebar(page, False)
        result = predict_manual(page, ARABIC)
        assert page.evaluate("window._acceptanceResultScrolls.at(-1).behavior") == "instant"
        card = page.locator(".st-key-manual_result_card")
        assert_download(page, card.get_by_role("button", name=re.compile(r"Unduh TXT$")),
                        "hasil_diakritisasi.txt", result)
        count = scroll_count(page)
        page.locator(".st-key-manual_comparison summary").click()
        positions = page.locator(".comparison-panel").evaluate_all(
            "es => es.map(e => {const r=e.getBoundingClientRect();return {x:r.x,y:r.y}})")
        assert positions[0]["x"] == positions[1]["x"] and positions[1]["y"] > positions[0]["y"]
        assert scroll_count(page) == count
        assert_layout(page)
        screenshot(page, "mobile_result")
        assert not errors, errors
    except Exception:
        for index, page in enumerate(context.pages):
            screenshot(page, f"failure_mobile_{index}")
        raise
    finally:
        context.close()


def main():
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    failures = []
    with sync_playwright() as playwright:
        channel = os.environ.get("PLAYWRIGHT_CHANNEL")
        options = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if channel:
            options["channel"] = channel
        browser = playwright.chromium.launch(**options)
        print(f"Browser: {browser.version}; channel={channel or 'bundled chromium'}", flush=True)
        context = browser.new_context(accept_downloads=True, permissions=["clipboard-read", "clipboard-write"],
                                      viewport={"width": 1440, "height": 960}, reduced_motion="reduce")
        for name, fn in [("manual", test_manual), ("txt", test_txt), ("csv", test_csv),
                         ("invalid", test_invalid), ("navigation", test_navigation)]:
            errors = []
            def on_error(error):
                errors.append(str(error.error))
            context.on("weberror", on_error)
            try:
                print(f"START browser test: {name}", flush=True)
                fn(context)
                assert not errors, errors
                print(f"PASS browser test: {name}", flush=True)
            except Exception as exc:
                failures.append((name, str(exc)))
                for index, page in enumerate(context.pages):
                    try:
                        screenshot(page, f"failure_{name}_{index}")
                    except Exception:
                        pass
                print(f"FAIL browser test: {name}: {exc}", flush=True)
            finally:
                context.remove_listener("weberror", on_error)
                for page in context.pages:
                    page.close()
        try:
            print("START browser test: mobile", flush=True)
            test_mobile(browser)
            print("PASS browser test: mobile", flush=True)
        except Exception as exc:
            failures.append(("mobile", str(exc)))
            print(f"FAIL browser test: mobile: {exc}", flush=True)
        finally:
            context.close()
            browser.close()
    if failures:
        raise AssertionError(f"Browser acceptance failures: {failures}")
    print("All 6 browser acceptance journeys passed.", flush=True)


if __name__ == "__main__":
    main()
