import os
from bs4 import BeautifulSoup
from combine_html_files import natural_key

def get_folder_path():
    prompt = 'Enter the folder path (default "input"): '
    user_input = input(prompt).strip().strip('"\'')
    return user_input if user_input else 'input'

def find_and_sort_html_files(folder_path):
    html_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.html', '.xhtml'))]
    html_files.sort(key=natural_key)
    return html_files

def extract_head_and_content(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        raw = f.read()
    soup = BeautifulSoup(raw, 'html.parser')
    head_content = ""
    head_tag = soup.find('head')
    if head_tag:
        head_content = head_tag.decode_contents()
    body_tag = soup.find('body')
    if body_tag:
        content = body_tag.decode_contents()
    else:
        html_tag = soup.find('html')
        if html_tag:
            content = html_tag.decode_contents()
        else:
            content = raw
    return head_content, content

def build_section(filename, content):
    section_title = (
        os.path.splitext(filename)[0]
        .replace('_', ' ')
        .replace('-', ' ')
        .title())
    wrapped = (
        "<section>\n"
        f"<h2>{section_title}</h2>\n"
        "<hr>\n"
        f"{content}\n"
        "</section>\n")
    return wrapped

def combine_files(folder_path):
    html_files = find_and_sort_html_files(folder_path)
    if not html_files:
        print("No HTML or XHTML files found in the folder.")
        return None
    combined_head = None
    combined_body_parts = []
    for index, filename in enumerate(html_files):
        file_path = os.path.join(folder_path, filename)
        try:
            head_content, content = extract_head_and_content(file_path)
            if index == 0 and head_content:
                combined_head = head_content
            section_html = build_section(filename, content)
            combined_body_parts.append(section_html)
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    if combined_head is None:
        combined_head = ""
    final_html = (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        f"{combined_head}\n"
        "</head>\n"
        "<body>\n"
        f"{' '.join(combined_body_parts)}\n"
        "</body>\n"
        "</html>\n")
    output_file = folder_path + "_output.html"
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(final_html)
    return output_file

def main():
    folder_path = get_folder_path()
    output_file = combine_files(folder_path)
    if output_file:
        print(f"Combined HTML saved to {output_file}")

if __name__ == "__main__":
    main()

