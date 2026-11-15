"""Test inputs reconstructed from the canonical deployment data bundle."""
import re
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope='session')
def canonical_txt():
    """Reproduce demo TXT without requiring untracked duplicate export files."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'streamlit_app'))
    import translation_reference as reference

    def read(kitab_id):
        book = next(b for b in reference.load_catalog()['books'] if b['kitab_id'] == kitab_id)
        context = reference.load_context(book)
        pages = {row['page'] for row in context['demo'].values()}
        text = '\n\n'.join(row['text_diacritized'] for row in context['raw_rows'] if row['page'] in pages)
        return re.sub('[\u064b-\u0652\u0670]', '', text)

    return read
