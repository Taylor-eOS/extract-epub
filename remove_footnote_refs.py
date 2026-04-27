import sys
import re

def remove_footnote_refs(text):
    return re.sub(r'\(\s*[^()]{1,50}?\d[^()]{0,50}?\)', '', text)

def process_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    cleaned = remove_footnote_refs(text)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(cleaned)

if __name__ == '__main__':
    process_file(sys.argv[1])
