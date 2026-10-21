"""Session-only upload collection and bounded exports; no inference or text changes."""

from hashlib import sha256
from io import BytesIO, StringIO
import csv
from pathlib import Path
import re
import sys
import unicodedata
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

import pandas as pd

from file_safety import spreadsheet_safe_csv

MAX_FILES = 20
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_RETAINED_BYTES = 128 * 1024 * 1024
MAX_EXPORT_BYTES = 32 * 1024 * 1024
MAX_TEXT_CHARS = 250_000
MAX_ROWS = 10_000
MAX_COLUMNS = 100
MAX_CELLS = 100_000

# The existing single-file panel is a view of one collection entry. Keeping its
# keys also preserves the manual-input/UI integrations and existing test seam.
ACTIVE_FIELDS = ("upload_snapshot", "upload_validation_cache", "csv_column",
                 "file_result", "file_result_signature", "file_processing")


def retained_bytes(value, seen=None):
    """Conservative retained payload estimate, with shared references counted once."""
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    if isinstance(value, pd.DataFrame):
        return int(value.memory_usage(index=True, deep=True).sum()) + sys.getsizeof(value.columns)
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(retained_bytes(k, seen) + retained_bytes(v, seen) for k, v in value.items())
    elif isinstance(value, (list, tuple, set)):
        size += sum(retained_bytes(v, seen) for v in value)
    return size


def persist_active(state):
    entry = state["upload_files"].get(state["active_upload_id"])
    if entry and state["upload_snapshot"] is entry["upload_snapshot"]:
        for key in ACTIVE_FIELDS:
            entry[key] = state[key]


def load_active(state, file_id):
    state["active_upload_id"] = file_id
    entry = state["upload_files"].get(file_id, {})
    for key in ACTIVE_FIELDS:
        state[key] = entry.get(key)


def add_uploads(state, uploads):
    """Add rather than replace; exact name+content duplicates are idempotent."""
    persist_active(state)
    entries = state["upload_files"]
    messages = []
    first_new = None
    for upload in uploads:
        if len(entries) >= MAX_FILES:
            messages.append(f"Batas {MAX_FILES} berkas tercapai; berkas tambahan tidak disimpan.")
            break
        name = str(upload.name)
        size = getattr(upload, "size", None)
        # Do not copy an oversized native uploader buffer into persistent state.
        data = None if size is not None and size > MAX_FILE_BYTES else upload.getvalue()
        size = len(data) if data is not None else size
        digest = sha256(data).hexdigest() if data is not None else f"oversize:{size}"
        if size > MAX_FILE_BYTES:
            data = None
        if any((e["upload_snapshot"]["name"], e["upload_snapshot"]["digest"]) == (name, digest)
               for e in entries.values()):
            continue
        if sum(len(e["upload_snapshot"]["data"] or b"") for e in entries.values()) + len(data or b"") > MAX_INPUT_BYTES:
            messages.append(f"{name}: tidak ditambahkan; batas total masukan 20 MiB.")
            continue
        entry = dict.fromkeys(ACTIVE_FIELDS)
        entry["upload_snapshot"] = {"name": name, "size": size, "data": data, "digest": digest}
        entry["export_bytes"] = None
        if retained_bytes(entries) + retained_bytes(entry) > MAX_RETAINED_BYTES:
            messages.append(f"{name}: tidak ditambahkan; batas memori sesi tercapai.")
            continue
        file_id = uuid4().hex
        entries[file_id] = entry
        first_new = first_new or file_id
    if state["active_upload_id"] not in entries:
        load_active(state, first_new or next(iter(entries), None))
    state["upload_messages"] = messages


def remove_upload(state, file_id):
    persist_active(state)
    state["upload_files"].pop(file_id, None)
    if state["active_upload_id"] == file_id:
        load_active(state, next(iter(state["upload_files"]), None))
    state["uploader_generation"] += 1


def clear_uploads(state):
    state["upload_files"] = {}
    load_active(state, None)
    state["upload_messages"] = []
    state["uploader_generation"] += 1


def text_capacity_error(text, csv_input=False):
    """Preflight UI limits before pandas/inference; never truncate a payload."""
    if len(text) > (1_000_000 if csv_input else MAX_TEXT_CHARS):
        return "Berkas melampaui batas karakter pemrosesan sesi; pisahkan berkas tanpa memotong kata."
    if not csv_input:
        if len(text.splitlines()) > MAX_ROWS:
            return f"TXT melampaui batas {MAX_ROWS:,} baris per berkas."
        return None
    try:
        sample = text[:8192]
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            try:
                dialect = csv.Sniffer().sniff(next(line for line in text.splitlines() if line.strip()))
            except (csv.Error, StopIteration):
                dialect = csv.excel
        cells = 0
        for row_number, row in enumerate(csv.reader(StringIO(text), dialect), 1):
            cells += len(row)
            if row_number > MAX_ROWS + 1 or len(row) > MAX_COLUMNS or cells > MAX_CELLS:
                return "CSV melampaui batas 10.000 baris, 100 kolom, atau 100.000 sel per berkas."
    except csv.Error as error:
        return f"CSV tidak dapat diperiksa dengan aman: {error}"
    return None


def safe_output_name(name, suffix, token=""):
    """Portable basename only, including Windows reserved names and bidi controls."""
    name = str(name).replace("\\", "/").rsplit("/", 1)[-1]
    stem = Path(name).stem
    stem = "".join(c for c in stem if unicodedata.category(c)[0] not in {"C", "M"})
    stem = re.sub(r"[^\w\- .]", "_", stem, flags=re.UNICODE).strip(" ._")[:64] or "berkas"
    if stem.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10))}:
        stem = "berkas_" + stem
    # Prefix keeps names safe even when user input begins with a spreadsheet sigil.
    return f"hasil_{token + '_' if token else ''}{stem}.{suffix}"


def result_export(result):
    if not result or not result.get("success"):
        return None
    return (spreadsheet_safe_csv(result["dataframe"]) if result["input_type"] == "csv"
            else result["download_bytes"])


def entry_status(entry):
    validation = (entry.get("upload_validation_cache") or {}).get("validation")
    result = entry.get("file_result")
    if validation and not validation.get("success"):
        return "Tidak valid", validation.get("message", "")
    if result:
        return ("Selesai" if result.get("success") else "Gagal"), result.get("message", "")
    return "Menunggu", "Belum diproses"


def build_zip(entries):
    """Bounded, sanitized results plus a status row for every queued file."""
    output = BytesIO()
    rows = []
    total = 0
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for index, entry in enumerate(entries.values(), 1):
            snapshot = entry["upload_snapshot"]
            result = entry.get("file_result") or {}
            status, message = entry_status(entry)
            export = entry.get("export_bytes")
            filename = ""
            if result.get("success"):
                export = export if export is not None else result_export(result)
                total += len(export)
                if total > MAX_EXPORT_BYTES:
                    raise ValueError("Total hasil melampaui batas ZIP 32 MiB; unduh hasil per berkas.")
                filename = safe_output_name(snapshot["name"], result["input_type"], f"{index:03d}")
                archive.writestr(filename, export)
            counts = result.get("status_summary") or {}
            rows.append({"berkas": snapshot["name"], "format": Path(snapshot["name"]).suffix,
                         "ukuran_byte": snapshot["size"], "kolom": entry.get("csv_column") or "",
                         "status": status, "pesan": message, "hasil": filename,
                         "ringkasan_baris": str(counts) if counts else ""})
        summary = spreadsheet_safe_csv(pd.DataFrame(rows))
        if total + len(summary) > MAX_EXPORT_BYTES:
            raise ValueError("Ringkasan dan hasil melampaui batas ZIP 32 MiB.")
        archive.writestr("ringkasan_status.csv", summary)
    return output.getvalue()
