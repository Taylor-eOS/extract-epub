import os
import shutil
import zipfile
from bs4 import BeautifulSoup
import tempfile
import re

output_folder = "./output"
input_folder = "./input"

def get_opf_path(temp_dir):
    container_path = os.path.join(temp_dir, 'META-INF', 'container.xml')
    if not os.path.exists(container_path):
        return None
    with open(container_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        rootfiles = soup.find_all('rootfile')
        for rootfile in rootfiles:
            if rootfile.get('media-type') == 'application/oebps-package+xml':
                full_path = rootfile.get('full-path')
                if full_path:
                    return os.path.join(temp_dir, full_path)
    return None

def get_content_paths(opf_path, temp_dir):
    if opf_path is None or not os.path.exists(opf_path):
        return []
    with open(opf_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    manifest = {}
    for item in soup.find_all('item'):
        item_id = item.get('id')
        href = item.get('href')
        properties = item.get('properties')
        if item_id and href and properties != 'nav':
            manifest[item_id] = href
    spine = soup.find('spine')
    if spine is None:
        return []
    ordered_hrefs = []
    for itemref in spine.find_all('itemref'):
        linear = itemref.get('linear', 'yes')
        if linear == 'no':
            continue
        idref = itemref.get('idref')
        if idref and idref in manifest:
            ordered_hrefs.append(manifest[idref])
    opf_dir = os.path.dirname(opf_path)
    content_paths = []
    for href in ordered_hrefs:
        if href:
            full_path = os.path.normpath(os.path.join(opf_dir, href))
            content_paths.append(full_path)
    return content_paths

def natural_sort_key(path, temp_dir):
    rel = os.path.relpath(path, temp_dir).lower()
    return [int(s) if s.isdigit() else s for s in re.split(r'([0-9]+)', rel)]

def extract_text_from_epub(epub_path, output_folder):
    epub_filename = os.path.basename(epub_path).replace('.epub', '.txt')
    output_path = os.path.join(output_folder, epub_filename)
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        opf_path = get_opf_path(temp_dir)
        content_paths = get_content_paths(opf_path, temp_dir)
        fallback_used = False
        if not content_paths:
            fallback_used = True
            print("Warning: Could not determine reading order from OPF file, using fallback scanning")
            content_paths = []
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith(('.xhtml', '.html', '.htm')):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, temp_dir).lower()
                        if not any(exclude in rel_path for exclude in ['nav', 'toc', 'cover', 'stylesheet', 'image', '/css/', '/styles/']):
                            content_paths.append(full_path)
            if content_paths:
                content_paths.sort(key=lambda p: natural_sort_key(p, temp_dir))
        core_parts = []
        bad_classes = ['note', 'footnote', 'sidenote', 'marginnote', 'endnote', 'reference']
        bad_tags = ['script', 'style', 'aside', 'footer', 'nav', 'sup', 'header']
        for file_path in content_paths:
            if not os.path.isfile(file_path):
                continue
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            for tag in soup.find_all(bad_tags):
                tag.decompose()
            for tag in soup.find_all(class_=lambda c: c and any(bad in ' '.join(c) for bad in bad_classes)):
                tag.decompose()
            for tag in soup.find_all(id=lambda i: i and 'note' in i.lower()):
                tag.decompose()
            possible_titles = soup.find_all(['h1', 'h2', 'title'])
            title_text = None
            for t in possible_titles:
                txt = t.get_text(strip=True)
                if txt:
                    title_text = txt.upper()
                    t.decompose()
                    break
            body = soup.find('body')
            if body:
                text = body.get_text(separator=' ', strip=True)
            else:
                text = soup.get_text(separator=' ', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            cleaned_text = ' '.join(lines)
            cleaned_text = re.sub(r'\s{2,}', ' ', cleaned_text)
            part = []
            if title_text:
                part.append(title_text)
            if cleaned_text:
                part.append(cleaned_text)
            if part:
                core_parts.append('\n\n'.join(part))
        if not core_parts:
            print("Warning: No text content found in the EPUB")
            return
        full_text = '\n\n\n\n'.join(core_parts)
        with open(output_path, 'w', encoding='utf-8') as output_file:
            output_file.write(full_text)
        method = "fallback method" if fallback_used else "OPF spine order"
        print(f"Extracted text from: {epub_filename} (using {method})")
    except zipfile.BadZipFile:
        print("Error: The file is not a valid EPUB")
    except Exception as e:
        print(f"Error processing {epub_filename}: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    #epub_folder = input("Input folder: ").strip()
    epub_folder = input_folder
    if not os.path.isdir(epub_folder):
        print("The provided path is not a valid folder")
        return
    os.makedirs(output_folder, exist_ok=True)
    epub_files = [f for f in os.listdir(epub_folder) if f.lower().endswith(".epub")]
    if not epub_files:
        print("No EPUB files found in the folder")
        return
    epub_files.sort(key=str.lower)
    full_paths = [os.path.join(epub_folder, f) for f in epub_files]
    print("\nFound EPUB files:")
    for index, filename in enumerate(epub_files, start=1):
        print(f"{index}. {filename}")
    while True:
        choice = input(
            "\nEnter the number of the file to convert (or press Enter to quit): "
        ).strip()
        if choice == "":
            print("No file selected, exiting")
            return
        if choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(epub_files):
                selected_path = full_paths[num - 1]
                selected_name = epub_files[num - 1]
                print(f"Converting: {selected_name}")
                extract_text_from_epub(selected_path, output_folder)
                return
            else:
                print("Number out of range, please try again")
        else:
            print("Please enter a valid number")

if __name__ == "__main__":
    main()
