import os
from bs4 import BeautifulSoup

folder_path = input('Enter the folder path (default "input"): ').strip().strip('"\'') or 'input'
output_file = folder_path + "_output.html"

html_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.html', '.xhtml'))]
html_files.sort()

combined_head = None
combined_body_parts = []

for index, filename in enumerate(html_files):
    file_path = os.path.join(folder_path, filename)
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw = f.read()
        soup = BeautifulSoup(raw, 'html.parser')
        if index == 0:
            head = soup.find('head')
            if head:
                combined_head = head.decode_contents()
            else:
                combined_head = ""
        body = soup.find('body')
        if body:
            content = body.decode_contents()
        else:
            html = soup.find('html')
            if html:
                content = html.decode_contents()
            else:
                content = raw
        section_title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
        wrapped = (
            "<section>\n"
            "<h2>" + section_title + "</h2>\n"
            "<hr>\n"
            + content +
            "\n</section>\n"
        )
        combined_body_parts.append(wrapped)
    except Exception as e:
        print(f"Error processing {filename}: {e}")

if combined_head is None:
    combined_head = ""

final_html = (
    "<!DOCTYPE html>\n"
    "<html lang=\"en\">\n"
    "<head>\n"
    + combined_head +
    "\n</head>\n"
    "<body>\n"
    + "\n".join(combined_body_parts) +
    "\n</body>\n"
    "</html>\n"
)

with open(output_file, 'w', encoding='utf-8') as out:
    out.write(final_html)

print(f"Combined HTML saved to {output_file}")

