import os
from bs4 import BeautifulSoup

def natural_key(s):
    parts = []
    buf = ""
    is_digit = False
    for c in s:
        if c.isdigit():
            if not is_digit:
                if buf:
                    parts.append(buf.lower())
                buf = c
                is_digit = True
            else:
                buf += c
        else:
            if is_digit:
                parts.append(int(buf))
                buf = c
                is_digit = False
            else:
                buf += c
    if buf:
        parts.append(int(buf) if is_digit else buf.lower())
    return parts

def get_first_valid_html_file(folder_path, html_files):
    for filename in html_files:
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            if soup.body:
                return filename, soup
        except Exception:
            pass
    return None, None

def clean_empty_parents(tag):
    while tag and tag.name != 'body':
        parent = tag.parent
        if parent and len(parent.contents) == 1 and parent.contents[0] == tag:
            next_tag = parent
            parent.decompose()
            tag = next_tag
        else:
            break

def main():
    folder_path = input('Enter the folder path (default "input"): ').strip().strip('"\'') or 'input'
    if not os.path.isdir(folder_path):
        print("The path is not a valid folder.")
        return
    output_file = folder_path + "_output.html"
    html_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.html', '.xhtml'))]
    if not html_files:
        print("No HTML or XHTML files found in the folder.")
        return
    html_files.sort(key=natural_key)
    first_filename, base_soup = get_first_valid_html_file(folder_path, html_files)
    if base_soup is None:
        print("None of the files contain a <body> tag.")
        return
    if base_soup.body:
        base_soup.body.clear()
    else:
        body_tag = base_soup.new_tag('body')
        if base_soup.html:
            base_soup.html.append(body_tag)
        else:
            base_soup.append(body_tag)
    body = base_soup.body
    for filename in html_files:
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            file_soup = BeautifulSoup(content, 'html.parser')
            if not file_soup.body:
                continue
            for img in file_soup.body.find_all('img'):
                parent = img.parent
                img.decompose()
                clean_empty_parents(parent)
            inner_content = file_soup.body.decode_contents()
            if inner_content.strip():
                fragment = BeautifulSoup(inner_content, 'html.parser')
                body.extend(fragment.children)
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(base_soup.prettify())
    print(f"Combined HTML saved to {output_file}")

if __name__ == "__main__":
    main()
