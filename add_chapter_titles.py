from bs4 import BeautifulSoup
import re
from pathlib import Path

def build_ncx_mapping(ncx_path):
    mapping = {}
    with open(ncx_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')
    for navpoint in soup.find_all('navPoint'):
        label = navpoint.find('text')
        content = navpoint.find('content')
        if label and content:
            title = label.get_text(strip=True)
            src = content.get('src', '')
            stem_match = re.match(r'^([^#]+)\.html', src)
            if stem_match:
                stem = stem_match.group(1)
                mapping[stem.lower()] = title
    return mapping

def replace_chapter_stems(input_txt_path, output_txt_path, mapping):
    with open(input_txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            new_lines.append(line)
            continue
        lower_stripped = stripped.lower()
        replaced = False
        for stem, title in mapping.items():
            if lower_stripped.startswith(stem):
                prefix = line[:line.lower().find(stem)]
                rest = line[line.lower().find(stem) + len(stem):].lstrip()
                new_lines.append('\n')
                new_lines.append(f"{prefix}{title}{rest}")
                new_lines.append('\n')
                replaced = True
                break
        if not replaced:
            new_lines.append(line)
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    return len(mapping), sum(1 for line in new_lines if any(s.lower() in line.lower() for s in mapping))

if __name__ == '__main__':
    epub_extract_folder = Path('.')
    ncx_file = 'toc.ncx'
    input_text = input("File basename: ")
    output_text = input_text + '_with_titles.txt'
    input_text = input_text + '.txt'
    stem_to_title = build_ncx_mapping(ncx_file)
    print(f'Found {len(stem_to_title)} chapter mappings')
    count_replaced = replace_chapter_stems(input_text, output_text, stem_to_title)
    print(f'Replaced occurrences in {count_replaced} lines')
    print('Result saved to', output_text)

