# sort_dump.py
import os
import re

DUMP_FILE = 'code_dump.txt'
# This pattern finds the markdown headers like '### symbolic_agi/config.py'
HEADER_PATTERN = re.compile(r'###\s+(symbolic_agi1/[a-zA-Z_]+\.py)')

def sort_the_dump(dump_file_path):
    """Reads the dump file and creates the individual source code files."""
    print(f"Reading from {dump_file_path}...")
    try:
        with open(dump_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"\nERROR: The file '{dump_file_path}' was not found.")
        print("Please copy the AI's code dump and save it as 'code_dump.txt'.")
        return

    # Split the content by the file headers
    # This gives us a list where every odd element is a file path
    # and every even element (after the first) is a code block.
    parts = HEADER_PATTERN.split(content)
    
    if len(parts) < 3:
        print("\nERROR: Could not find any valid file sections to parse.")
        return

    # Iterate over the found sections
    for i in range(1, len(parts), 2):
        file_path = parts[i].strip()
        code_block = parts[i+1]
        
        # Clean up the code block, removing the markdown fences
        # and any leading/trailing whitespace.
        if '```python' in code_block:
            code_content = code_block.split('```python\n', 1)[1].rsplit('\n```', 1)[0]
        else:
            code_content = code_block.strip()
        
        # Ensure the target directory exists
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        
        # Write the extracted code to the file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code_content)
            print(f"✅ Created file: {file_path}")
        except IOError as e:
            print(f"❌ Failed to write file {file_path}: {e}")

if __name__ == '__main__':
    sort_the_dump(DUMP_FILE)
    print("\nProcess finished. All files should be created.")