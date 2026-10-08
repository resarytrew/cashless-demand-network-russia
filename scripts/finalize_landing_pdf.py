"""Finalize the browser-built landing edition as A4 landscape with bookmarks."""
import json
import shutil
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import fitz

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / 'tmp/pdfs'
    titles = json.loads((folder / 'page-titles.json').read_text(encoding='utf-8'))
    reader = PdfReader(folder / 'landing-edition.pdf')
    pages = list(reader.pages)
    while len(pages) > len(titles) and not (pages[-1].extract_text() or '').strip():
        pages.pop()
    if len(pages) != len(titles):
        raise RuntimeError(f'Unexpected pagination: {len(pages)} pages, {len(titles)} titles')
    writer = PdfWriter()
    for i, page in enumerate(pages):
        if len(page.extract_text() or '') < 150:
            raise RuntimeError(f'Unexpected sparse page {i + 1}')
        page.scale_to(841.8898, 595.2756)
        writer.add_page(page)
        writer.add_outline_item(titles[i], i)
    writer.add_metadata({'/Title': 'География спроса — полная версия лендинга',
                         '/Subject': 'Профили локального безналичного потребительского спроса. 2023–2024',
                         '/Author': 'География спроса', '/Language': 'ru-RU'})
    intermediate = folder / 'a4-edition.pdf'
    with intermediate.open('wb') as stream:
        writer.write(stream)
    output = ROOT / 'output/pdf/geografiya-sprosa.pdf'
    output.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open(intermediate)
    document.save(output, garbage=4, deflate=True)
    document.close()
    verified = fitz.open(output)
    audit = {'pages': len(verified), 'bytes': output.stat().st_size,
             'page_format': 'A4 landscape', 'bookmarks': len(verified.get_toc()),
             'text_characters': sum(len(p.get_text()) for p in verified),
             'source': 'Live local landing, saved interactive states, no model reruns'}
    (folder / 'verification.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copy2(output, ROOT / "site/assets/research-brief.pdf")
    print(json.dumps(audit, ensure_ascii=True))


if __name__ == '__main__':
    main()
