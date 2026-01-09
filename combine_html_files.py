import os
import sys
from bs4 import BeautifulSoup

folder_path = input("Enter the folder path: ").strip().strip('"\'')
output_file = folder_path + "_output.html"
combined_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Combined Document</title>
</head>
<body>
</body>
</html>"""
soup = BeautifulSoup(combined_html, 'html.parser')
body = soup.body
html_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.html') or f.lower().endswith('.htm')]
html_files.sort()
header_used = False

for filename in html_files:
    file_path = os.path.join(folder_path, filename)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        file_soup = BeautifulSoup(content, 'html.parser')
        file_body = file_soup.find('body')
        if file_body:
            content_elements = file_body.contents
        else:
            content_elements = file_soup.contents
        if not header_used:
            file_head = file_soup.find('head')
            if file_head:
                title = file_head.find('title')
                if title:
                    soup.title.string = title.get_text()
                styles = file_head.find_all('style')
                for style in styles:
                    soup.head.append(style)
                links = file_head.find_all('link', rel='stylesheet')
                for link in links:
                    soup.head.append(link)
            header_used = True
        section = soup.new_tag('section')
        h2 = soup.new_tag('h2')
        h2.string = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
        section.append(h2)
        hr = soup.new_tag('hr')
        section.append(hr)
        for element in content_elements:
            if element.name not in [None, 'html', 'head', 'body']:
                section.append(element)
        body.append(section)
        body.append(soup.new_tag('br'))
    except Exception as e:
        print(f"Error processing {filename}: {e}")

with open(output_file, 'w', encoding='utf-8') as out:
    out.write(str(soup.prettify()))

print(f"Combined HTML saved to {output_file}")
