"""Small runtime check for the installed app and its bundled OpenCC data."""

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from docx import Document

from doc_converter import convert_docx_file
from mac_opencc import OpenCC


def run_self_test():
    cases = {
        't2gov': ('啟淨垔', '啓净垔'),
        't2s': ('繁體中文', '繁体中文'),
        's2t': ('简体中文', '簡體中文'),
        't2gov_jieba': ('啟淨', '啓净'),
        't2gov_jieba_traditional': ('啟淨', '啓净'),
    }
    for mode, (source, expected) in cases.items():
        actual = OpenCC(mode).convert(source)
        if actual != expected:
            raise AssertionError(f'{mode}: {source!r} -> {actual!r}; expected {expected!r}')
        print(f'{mode}: {actual}')
    print('OpenCC resources: OK')

    with TemporaryDirectory() as directory:
        source = Path(directory) / 'sample.docx'
        document = Document()
        document.add_paragraph('啟淨')
        document.save(source)
        result = convert_docx_file(str(source), directory, 't2gov', log_callback=print)
        assert result, 'DOCX conversion failed'
        converted = Document(result)
        assert converted.paragraphs[0].text == '啓净'
        with ZipFile(result) as package:
            regions = [name for name in package.namelist()
                       if name.startswith(('word/header', 'word/footer'))]
            assert not regions, regions
    print('DOCX header/footer resources: OK')


if __name__ == '__main__':
    run_self_test()
