"""Native multi-upload/download acceptance. Creates only test-results artifacts."""
from __future__ import annotations

import csv
from io import BytesIO, StringIO
import json
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from zipfile import ZipFile

from playwright.sync_api import sync_playwright, expect, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-results/multifile/browser"
TEXT = "الحمد لله\n\nabc\n".encode()
CSV = "judul_arab,teks_gundul,info\nرب العالمين,الحمد لله,=1+1\n".encode()


def payload(name, data):
    return {"name": name, "mimeType": "text/plain" if name.endswith(".txt") else "text/csv", "buffer": data}


def select(page, label, value):
    field = page.locator('[data-testid="stSelectbox"]').filter(has=page.get_by_text(label, exact=True))
    expect(page.locator('[data-testid="stStatusWidget"]')).not_to_be_visible(timeout=60_000)
    # A preceding selection can still be finishing a streamed rerender. Reopen
    # only if that rerender closed the native popup before an option was chosen.
    option = page.get_by_role("option", name=value, exact=True)
    for attempt in range(3):
        field.get_by_role("combobox").press("Escape")
        field.get_by_role("combobox").click()
        if label == "Pilih Kolom Teks Arab":
            (OUT / f"column_popup_{attempt}.txt").write_text(page.locator('body').aria_snapshot(), encoding="utf-8")
        try:
            expect(option).to_be_visible(timeout=3000)
            option.click(timeout=3000)
            expect(field.get_by_role("combobox")).to_have_value(value, timeout=3000)
            break
        except (AssertionError, PlaywrightTimeoutError):
            if attempt == 2:
                raise
    print(f"Selected {label}: {value}", flush=True)


def download(page, locator, target):
    with page.expect_download(timeout=60_000) as event:
        locator.click()
    item = event.value
    assert not item.failure()
    data = item.path().read_bytes()
    (OUT / target).write_bytes(data)
    assert item.suggested_filename == Path(item.suggested_filename).name
    assert "/" not in item.suggested_filename and "\\" not in item.suggested_filename
    return data


def zip_rows(data):
    with ZipFile(BytesIO(data)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(n.casefold() for n in names))
        assert all("/" not in n and "\\" not in n for n in names)
        rows = list(csv.DictReader(StringIO(archive.read("ringkasan_status.csv").decode("utf-8-sig"))))
        return rows, {n: archive.read(n) for n in names}


def run(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    page.locator(".st-key-nav label").filter(has_text="Diakritisasi").click()
    page.get_by_role("tab", name="Unggah TXT / CSV", exact=False).click()
    picker = page.locator('input[type="file"]')
    picker.set_input_files([payload("one.txt", TEXT), payload("two.csv", CSV), payload("invalid.txt", b"\x00")])
    label = "Berkas untuk pratinjau, proses ulang, atau unduh"
    expect(page.get_by_text(label, exact=True)).to_be_visible(timeout=60_000)
    select(page, label, "2. two.csv")
    column = page.locator('[data-testid="stSelectbox"]').filter(has=page.get_by_text("Pilih Kolom Teks Arab", exact=True))
    expect(column.get_by_role("combobox")).to_have_value("teks_gundul")
    select(page, "Pilih Kolom Teks Arab", "judul_arab")
    select(page, "Pilih Kolom Teks Arab", "teks_gundul")
    page.get_by_role("button", name="Proses Semua", exact=True).click()
    card = page.locator(".st-key-file_result_card")
    expect(card.get_by_role("button", name=re.compile(r"Unduh CSV$"))).to_be_visible(timeout=90_000)
    csv_before = download(page, card.get_by_role("button", name=re.compile(r"Unduh CSV$")), "two.csv")
    print("Initial processing/download passed", flush=True)
    assert b"\t=1+1" in csv_before
    # Native widget was rotated after the first batch; adding doesn't replace it.
    picker.set_input_files([payload("later.txt", "رب العالمين".encode())])
    # Wait for the upload callback, rather than observing the old CSV result
    # while a newly selected file is still arriving at the server.
    select(page, label, "4. later.txt")
    select(page, label, "2. two.csv")
    expect(page.get_by_role("button", name="Proses Ulang Berkas", exact=True)).to_be_visible(timeout=60_000)
    assert download(page, card.get_by_role("button", name=re.compile(r"Unduh CSV$")), "two_after_add.csv") == csv_before
    page.get_by_role("button", name="Proses Semua", exact=True).click()
    page.get_by_role("button", name="Siapkan ZIP", exact=True).click()
    zip_data = download(page, page.get_by_role("button", name="Unduh Semua (ZIP)", exact=True), "all.zip")
    rows, members = zip_rows(zip_data)
    print("Additive upload and ZIP downloaded", flush=True)
    assert len(rows) == 4 and [r["status"] for r in rows].count("Selesai") == 3
    assert next(r for r in rows if r["berkas"] == "invalid.txt")["status"] == "Tidak valid"
    assert members[next(r["hasil"] for r in rows if r["berkas"] == "two.csv")] == csv_before
    assert members[next(r["hasil"] for r in rows if r["berkas"] == "one.txt")]
    select(page, label, "1. one.txt")
    txt_data = download(page, card.get_by_role("button", name=re.compile(r"Unduh TXT$")), "one.txt")
    assert txt_data == members[next(r["hasil"] for r in rows if r["berkas"] == "one.txt")]
    page.locator(".st-key-nav label").filter(has_text="Tentang Model").click()
    page.locator(".st-key-nav label").filter(has_text="Diakritisasi").click()
    page.get_by_role("tab", name="Unggah TXT / CSV", exact=False).click()
    assert download(page, card.get_by_role("button", name=re.compile(r"Unduh TXT$")), "one_after_navigation.txt") == txt_data
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
    expect(page.locator('[data-testid="stDataFrame"] button[aria-label="Download as CSV"]')).to_have_count(0)
    page.screenshot(path=str(OUT / "multi_results.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path=str(OUT / "multi_mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})
    select(page, label, "2. two.csv")
    page.get_by_role("button", name=re.compile(r"Hapus Berkas$")).click()
    expect(page.get_by_role("button", name="Unduh Semua (ZIP)", exact=True)).to_have_count(0)
    page.get_by_role("button", name="Siapkan ZIP", exact=True).click()
    remaining = download(page, page.get_by_role("button", name="Unduh Semua (ZIP)", exact=True), "after_delete.zip")
    remaining_rows, _ = zip_rows(remaining)
    assert len(remaining_rows) == 3 and "two.csv" not in {r["berkas"] for r in remaining_rows}
    page.get_by_role("button", name=re.compile(r"Hapus Semua$")).click()
    expect(page.get_by_text(label, exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name="Proses Diakritisasi", exact=True)).to_be_disabled()
    expect(page.get_by_role("button", name="Unduh Semua (ZIP)", exact=True)).to_have_count(0)
    picker.set_input_files([payload("one.txt", TEXT)])
    expect(page.get_by_text(label, exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Proses Diakritisasi", exact=True)).to_be_enabled()
    expect(card.get_by_role("button", name=re.compile(r"Unduh TXT$"))).to_have_count(0)
    return {"status": "PASS", "native_mixed_upload": True, "addition_retains_results": True,
            "per_file_column_and_downloads": True, "zip_unique_safe_names_and_statuses": True,
            "csv_export_sanitized": True, "invalid_file_does_not_block_others": True,
            "navigation_persists_results": True, "remove_one_and_clear_all": True,
            "reupload_after_clear_has_no_stale_result": True, "mobile_no_page_overflow": True}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    result = {"status": "FAIL"}
    with (OUT / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([sys.executable, "-B", "-m", "streamlit", "run", str(ROOT / "streamlit_app/app.py"),
                                   "--server.address=127.0.0.1", f"--server.port={port}", "--server.headless=true",
                                   "--server.fileWatcherType=none", "--browser.gatherUsageStats=false"],
                                  cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            url = f"http://127.0.0.1:{port}"
            for _ in range(120):
                if server.poll() is not None:
                    raise RuntimeError("Temporary server exited; see server.log")
                try:
                    with urlopen(url + "/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.25)
            else:
                raise TimeoutError("Temporary Streamlit server not ready")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel=os.environ.get("PLAYWRIGHT_CHANNEL", "msedge"), headless=True)
                try:
                    context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
                    page = context.new_page()
                    page.set_default_timeout(45_000)
                    try:
                        result = run(page, url)
                        result["browser_version"] = browser.version
                    except Exception:
                        page.screenshot(path=str(OUT / "failure.png"), full_page=True)
                        (OUT / "failure_aria.txt").write_text(page.locator('body').aria_snapshot(), encoding="utf-8")
                        raise
                finally:
                    browser.close()
        except Exception as error:
            result["error"] = str(error)
            raise
        finally:
            server.terminate()
            server.wait(timeout=30)
            result["temporary_server_stopped"] = server.poll() is not None
            (OUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
