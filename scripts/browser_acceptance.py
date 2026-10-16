"""Browser-level acceptance tests for the original Streamlit user journey.

Runs against a real Streamlit server and headless Chromium. No model retraining.
"""
from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from arabic_diacritization.inference import predict_long_text
from arabic_diacritization.preprocessing import remove_arabic_diacritics

BASE_URL = os.environ.get("STREAMLIT_URL", "http://127.0.0.1:8501")
SCREENSHOTS = Path(os.environ.get("BROWSER_SCREENSHOTS", "results/browser-acceptance"))
SCREENSHOTS.mkdir(parents=True, exist_ok=True)
ARABIC = "الحمد لله رب العالمين"


def assert_download(download, wanted_name, expected_text=None):
    assert download.suggested_filename == wanted_name, (
        download.suggested_filename, wanted_name
    )
    data = download.path().read_bytes()
    assert data, f"Empty download: {wanted_name}"
    if expected_text is not None:
        assert expected_text in data.decode("utf-8-sig"), wanted_name
    print(f"PASS: downloaded {wanted_name} ({len(data)} bytes)")


def open_workspace(context, label):
    page = context.new_page()
    page.set_default_timeout(45_000)
    page.goto(BASE_URL, wait_until="domcontentloaded")
    expect(page.get_by_text("Model siap digunakan")).to_be_visible(timeout=90_000)
    expect(page.get_by_role("button", name="Mulai Diakritisasi")).to_be_visible()
    page.screenshot(path=str(SCREENSHOTS / f"{label}_home.png"), full_page=True)
    page.get_by_role("button", name="Mulai Diakritisasi").click()
    expect(page.get_by_role("tab", name="Unggah TXT / CSV")).to_be_visible()
    return page


def test_manual(context):
    page = open_workspace(context, "manual")
    page.get_by_role("textbox", name="Teks Arab").fill(ARABIC)
    page.get_by_role("button", name="Proses Diakritisasi").click()
    download_button = page.get_by_role("button", name="Unduh hasil TXT")
    expect(download_button).to_be_visible(timeout=90_000)
    expect(download_button).to_be_enabled()
    page.screenshot(path=str(SCREENSHOTS / "manual_result.png"), full_page=True)
    with page.expect_download(timeout=45_000) as download_info:
        download_button.click()
    download = download_info.value
    expected = predict_long_text(ARABIC)
    assert expected["success"], expected
    assert_download(download, "hasil_diakritisasi.txt", expected["prediction"])
    assert remove_arabic_diacritics(expected["prediction"]) == ARABIC
    page.close()


def upload_file(page, filename, mime_type, contents):
    page.get_by_role("tab", name="Unggah TXT / CSV").click()
    selector = page.locator('input[type="file"]')
    expect(selector).to_have_count(1)
    selector.set_input_files({
        "name": filename,
        "mimeType": mime_type,
        "buffer": contents,
    })
    expect(page.get_by_text(f"Berkas aktif: {filename}", exact=False)).to_be_visible(timeout=45_000)


def test_txt(context):
    page = open_workspace(context, "txt")
    upload_file(page, "contoh.txt", "text/plain", (ARABIC + "\nabc\n").encode("utf-8"))
    expect(page.get_by_role("button", name="Proses Berkas")).to_be_enabled()
    page.get_by_role("button", name="Proses Berkas").click()
    expect(page.get_by_text("File TXT berhasil diproses.")).to_be_visible(timeout=90_000)
    button = page.get_by_role("button", name="Unduh hasil TXT")
    expect(button).to_be_visible()
    page.screenshot(path=str(SCREENSHOTS / "txt_result.png"), full_page=True)
    with page.expect_download(timeout=45_000) as info:
        button.click()
    result = info.value
    assert_download(result, "contoh_hasil_diakritisasi.txt", "abc")
    raw = result.path().read_bytes().decode("utf-8")
    assert remove_arabic_diacritics(raw.splitlines()[0]) == ARABIC
    page.close()


def test_csv(context):
    page = open_workspace(context, "csv")
    raw = ("teks,id\n" + ARABIC + ",1\nabc,2\n").encode("utf-8")
    upload_file(page, "contoh.csv", "text/csv", raw)
    expect(page.get_by_text("Pratinjau CSV")).to_be_visible(timeout=45_000)
    expect(page.get_by_role("button", name="Proses Berkas")).to_be_enabled()
    page.get_by_role("button", name="Proses Berkas").click()
    expect(page.get_by_text("File CSV berhasil diproses.")).to_be_visible(timeout=90_000)
    button = page.get_by_role("button", name="Unduh hasil CSV")
    expect(button).to_be_visible()
    page.screenshot(path=str(SCREENSHOTS / "csv_result.png"), full_page=True)
    with page.expect_download(timeout=45_000) as info:
        button.click()
    result = info.value
    assert_download(result, "contoh_hasil_diakritisasi.csv", "hasil_diacritization")
    text = result.path().read_bytes().decode("utf-8-sig")
    assert "teks,id," in text and "abc" in text
    page.close()


def test_navigation(context):
    page = open_workspace(context, "navigation")
    nav = page.get_by_role("radiogroup", name="Navigasi utama")
    for label in ("Contoh Teks", "Tentang Model", "Beranda", "Diakritisasi"):
        nav.get_by_text(label, exact=True).click()
        expect(page.get_by_text("Model siap digunakan")).to_be_visible()
    page.screenshot(path=str(SCREENSHOTS / "navigation.png"), full_page=True)
    page.close()


def test_mobile(browser):
    """Check the redesigned user flow at a narrow phone viewport."""
    mobile = browser.new_context(
        accept_downloads=True,
        viewport={"width": 390, "height": 844},
        device_scale_factor=1,
        is_mobile=True,
        has_touch=True,
        reduced_motion="reduce",
    )
    try:
        page = mobile.new_page()
        page.set_default_timeout(45_000)
        page.goto(BASE_URL, wait_until="domcontentloaded")
        expect(page.get_by_role("button", name="Mulai Diakritisasi")).to_be_visible(timeout=90_000)
        page.screenshot(path=str(SCREENSHOTS / "mobile_home.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 4"), (
            "Home page overflows narrow viewport"
        )
        page.get_by_role("button", name="Mulai Diakritisasi").click()
        expect(page.get_by_role("textbox", name="Teks Arab")).to_be_visible()
        page.get_by_role("textbox", name="Teks Arab").fill(ARABIC)
        page.get_by_role("button", name="Proses Diakritisasi").click()
        expect(page.get_by_role("button", name="Unduh hasil TXT")).to_be_visible(timeout=90_000)
        page.screenshot(path=str(SCREENSHOTS / "mobile_result.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 4"), (
            "Result page overflows narrow viewport"
        )
        with page.expect_download(timeout=45_000) as download_info:
            page.get_by_role("button", name="Unduh hasil TXT").click()
        assert_download(download_info.value, "hasil_diakritisasi.txt")
    finally:
        mobile.close()


def main():
    failures = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1440, "height": 960},
            reduced_motion="reduce",
        )
        for name, fn in (
            ("manual", test_manual),
            ("txt", test_txt),
            ("csv", test_csv),
            ("navigation", test_navigation),
        ):
            try:
                print(f"START browser test: {name}", flush=True)
                fn(context)
                print(f"PASS browser test: {name}", flush=True)
            except Exception as exc:
                failures.append((name, str(exc)))
                for index, page in enumerate(context.pages):
                    try:
                        page.screenshot(
                            path=str(SCREENSHOTS / f"failure_{name}_{index}.png"),
                            full_page=True,
                        )
                    except Exception:
                        pass
                print(f"FAIL browser test: {name}: {exc}", flush=True)
                for page in context.pages:
                    page.close()
        try:
            print("START browser test: mobile", flush=True)
            test_mobile(browser)
            print("PASS browser test: mobile", flush=True)
        except Exception as exc:
            failures.append(("mobile", str(exc)))
            print(f"FAIL browser test: mobile: {exc}", flush=True)
        context.close()
        browser.close()
    if failures:
        raise AssertionError(f"Browser acceptance failures: {failures}")
    print("All 5 browser acceptance journeys passed.")


if __name__ == "__main__":
    main()
