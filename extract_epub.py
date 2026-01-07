import os
import shutil
import zipfile
from bs4 import BeautifulSoup

output_folder = "./output"

def is_valid_content(tag):
    if tag.name in ['aside', 'footer', 'sup']:
        return False
    if 'class' in tag.attrs and any(cl in tag['class'] for cl in ['note', 'footnote']):
        return False
    if 'id' in tag.attrs and 'note' in tag['id']:
        return False
    return True

def extract_text_from_epub(epub_path, output_folder):
    epub_filename = os.path.basename(epub_path).replace('.epub', '.txt')
    output_path = os.path.join(output_folder, epub_filename)
    temp_dir = os.path.join(output_folder, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    core_text = []
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith('.xhtml') or file.endswith('.html') or file.endswith('.xml'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f, 'html.parser')
                    for tag in soup.find_all(is_valid_content):
                        text = tag.get_text(separator='\n', strip=True)
                        core_text.append(text)
    full_text = '\n\n'.join(core_text)
    with open(output_path, 'w', encoding='utf-8') as output_file:
        output_file.write(full_text)
    shutil.rmtree(temp_dir)
    print(f"Extracted text from: {epub_filename}")

def main():
    epub_folder = input("Input folder: ").strip()
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

