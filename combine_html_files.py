import os
from bs4 import BeautifulSoup
from urllib.parse import unquote

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

def collect_opf_files(folder_path):
    opf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.opf')]
    return opf_files

def parse_opf_for_order(opf_path, folder_path):
    manifest_dict = {}
    try:
        with open(opf_path, 'r', encoding='utf-8') as f:
            opf_content = f.read()
        opf_soup = BeautifulSoup(opf_content, 'html.parser')
        manifest = opf_soup.find('manifest')
        if manifest:
            for item in manifest.find_all('item'):
                item_id = item.get('id')
                href_raw = item.get('href')
                media_type = (item.get('media-type') or '').lower()
                if item_id and href_raw and ('xhtml' in media_type or 'html' in media_type):
                    href = unquote(href_raw)
                    filename = os.path.basename(href)
                    manifest_dict[item_id] = filename
        spine = opf_soup.find('spine')
        if not spine or not manifest_dict:
            return []
        ordered_idrefs = [itemref.get('idref') for itemref in spine.find_all('itemref') if itemref.get('idref')]
        ordered_files = []
        seen = set()
        for idref in ordered_idrefs:
            filename = manifest_dict.get(idref)
            if filename and filename not in seen:
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path) and filename.lower().endswith(('.html', '.xhtml')):
                    ordered_files.append(filename)
                    seen.add(filename)
        return ordered_files
    except Exception as e:
        print(f"Failed to parse OPF: {e}")
        return []

def get_all_html_files(folder_path):
    html_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.html', '.xhtml'))]
    html_files.sort(key=natural_key)
    return html_files

def enforce_spine_match_or_fallback(ordered_from_spine, all_html_files, opf_files):
    if not opf_files:
        return all_html_files, False
    if not ordered_from_spine:
        print("OPF exists but no valid spine order could be built, falling back to filename sorting")
        return all_html_files, False
    referenced_set = set(ordered_from_spine)
    all_set = set(all_html_files)
    extra_files = all_set - referenced_set
    if extra_files:
        print("Mismatch detected: OPF spine order is present and valid, but extra HTML/XHTML files exist that are not referenced.")
        print(f"Extra files found ({len(extra_files)}):")
        for f in sorted(extra_files, key=natural_key):
            print(f"  - {f}")
        print("To prevent wrong reading order the script will stop here.")
        print("Either remove the extra files, update the OPF manifest/spine, or delete the .opf file to use filename sorting instead.")
        return [], True
    return ordered_from_spine, False

def print_opf_status(opf_files, ordered_files):
    if not opf_files:
        print("No .opf file found, will use filename sorting.")
        return
    opf_filename = opf_files[0]
    print(f"Found OPF file: {opf_filename}")
    if len(opf_files) > 1:
        print(f"  (multiple .opf files exist, using the first one)")
    if ordered_files:
        print(f"Using EPUB spine order with {len(ordered_files)} files")
    else:
        print("Could not get valid order from OPF, falling back to filename sorting")

def main():
    folder_path = input('Enter the folder path (default "input"): ').strip().strip('"\'') or 'input'
    if not os.path.isdir(folder_path):
        print("The path is not a valid folder.")
        return
    output_file = folder_path + "_output.html"
    opf_files = collect_opf_files(folder_path)
    opf_files.sort(key=natural_key) if opf_files else None
    ordered_files_from_opf = []
    if opf_files:
        opf_path = os.path.join(folder_path, opf_files[0])
        ordered_files_from_opf = parse_opf_for_order(opf_path, folder_path)
    print_opf_status(opf_files, ordered_files_from_opf)
    all_html_files = get_all_html_files(folder_path)
    html_files, stopped_due_to_mismatch = enforce_spine_match_or_fallback(ordered_files_from_opf, all_html_files, opf_files)
    if stopped_due_to_mismatch:
        return
    if not html_files:
        print("No HTML or XHTML files found in the folder.")
        return
    print(f"Processing {len(html_files)} file{'s' if len(html_files) > 1 else ''} in the chosen order")
    first_filename, base_soup = get_first_valid_html_file(folder_path, html_files)
    if base_soup is None:
        print("Could not read any HTML files.")
        return
    if not base_soup.body:
        body_tag = base_soup.new_tag('body')
        if base_soup.html:
            base_soup.html.append(body_tag)
        else:
            base_soup.append(body_tag)
    base_soup.body.clear()
    body = base_soup.body
    for filename in html_files:
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            file_soup = BeautifulSoup(content, 'html.parser')
            if not file_soup.body:
                body_tag = file_soup.new_tag('body')
                if file_soup.html:
                    file_soup.html.append(body_tag)
                else:
                    file_soup.append(body_tag)
            for img in file_soup.body.find_all('img'):
                parent = img.parent
                img.decompose()
                clean_empty_parents(parent)
            inner_content = file_soup.body.decode_contents()
            if inner_content.strip():
                fragment = BeautifulSoup(inner_content, 'html.parser')
                body.extend(list(fragment.children))
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(base_soup.prettify())
    print(f"Combined HTML saved to {output_file}")

if __name__ == "__main__":
    main()
