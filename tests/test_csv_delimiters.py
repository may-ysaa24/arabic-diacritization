"""Delimiter detection must preserve CSV fields before any model processing."""
import csv
from io import StringIO

import pandas as pd
import pytest

from arabic_diacritization.file_processing import read_csv_bytes, process_csv_bytes


ENCODINGS = ('utf-8', 'utf-8-sig', 'utf-16', 'cp1256')


def csv_bytes(rows, *, delimiter=',', encoding='utf-8', quoting=csv.QUOTE_MINIMAL,
              lineterminator='\r\n'):
    stream = StringIO(newline='')
    csv.writer(stream, delimiter=delimiter, quoting=quoting,
               lineterminator=lineterminator).writerows(rows)
    return stream.getvalue().encode(encoding)


@pytest.mark.parametrize('encoding', ENCODINGS)
@pytest.mark.parametrize('quoting', (csv.QUOTE_MINIMAL, csv.QUOTE_ALL))
@pytest.mark.parametrize('lineterminator', ('\n', '\r\n'))
def test_single_column_header_is_not_split(encoding, quoting, lineterminator):
    values = ['الحمد لله', 'قال: "نعم", ثم سكت; وكذلك|هنا', 'سطر أول\nسطر ثان']
    result = read_csv_bytes(csv_bytes([['arabic'], *[[v] for v in values]],
        encoding=encoding, quoting=quoting, lineterminator=lineterminator))
    assert result['success'], result.get('message')
    pd.testing.assert_frame_equal(result['dataframe'], pd.DataFrame({'arabic': values}))


@pytest.mark.parametrize('encoding', ENCODINGS)
@pytest.mark.parametrize('delimiter', (',', ';', '\t', '|', ':', '^', ' '))
def test_multicolumn_delimiters_quoted_values_and_empty_cells(encoding, delimiter):
    rows = [['id', 'arabic', 'note'], ['01', 'الحمد لله', ''],
            ['02', 'قال "نعم"' + delimiter + 'ثم سكت\nسطر ثان', 'NA']]
    result = read_csv_bytes(csv_bytes(rows, delimiter=delimiter, encoding=encoding))
    assert result['success'], result.get('message')
    expected = pd.DataFrame(rows[1:], columns=rows[0])
    pd.testing.assert_frame_equal(result['dataframe'], expected)


def test_single_column_blank_lines_and_header_only():
    result = read_csv_bytes('\n\narabic\nالحمد لله\n'.encode('utf-8'))
    assert result['success']
    assert result['dataframe'].to_dict('list') == {'arabic': ['الحمد لله']}
    header_only = read_csv_bytes(b'arabic\n')
    assert header_only['success']
    assert list(header_only['dataframe'].columns) == ['arabic']
    assert header_only['dataframe'].empty


def test_single_column_actual_inference_and_download():
    result = process_csv_bytes(csv_bytes([['arabic'], ['الحمد لله']]), text_column='arabic')
    assert result['success'], result.get('message')
    assert result['status_summary'] == {'berhasil': 1}
    output = pd.read_csv(StringIO(result['download_bytes'].decode('utf-8-sig')),
                         dtype=str, keep_default_na=False)
    assert output['arabic'].tolist() == ['الحمد لله']
    assert output[result['output_columns']['prediction']].str.len().gt(0).all()
