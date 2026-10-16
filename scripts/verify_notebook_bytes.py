"""Ensure checkout preserves exact research notebook bytes."""
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    notebooks = sorted((ROOT / "notebooks").glob("*.ipynb"))
    assert len(notebooks) == 10, len(notebooks)
    for path in notebooks:
        rel = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        actual = hashlib.sha1(f"blob {len(raw)}".encode() + bytes([0]) + raw).hexdigest()
        expected = subprocess.check_output(["git", "rev-parse", f"HEAD:{rel}"], cwd=ROOT, text=True).strip()
        assert actual == expected, f"{rel}: checkout bytes differ from Git object"
        print("PASS", rel)

if __name__ == "__main__":
    main()
