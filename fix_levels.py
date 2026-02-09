
import os

file_path = r"f:\New folder (7)\Mechatronics-Data\Mechatronics-Data\templates\levels.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The target split string to search for
target_split = """                                    {% for s in level.preview_subjects %}{{ s.name }} <span class="text-gray-400">({{
                                        s.file_count }})</span>{% if not forloop.last %}, {% endif %}{% endfor %}"""

# The replacement joined string
replacement = """                                    {% for s in level.preview_subjects %}{{ s.name }} <span class="text-gray-400">({{ s.file_count }})</span>{% if not forloop.last %}, {% endif %}{% endfor %}"""

if target_split in content:
    new_content = content.replace(target_split, replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully patched levels.html")
else:
    # Try relaxed matching (normalizing spaces/newlines)
    import re
    # Construct a regex that matches the split pattern with flexible whitespace
    pattern = r"(\{\% for s in level\.preview_subjects \%\d{ s\.name \}\} <span class=\"text-gray-400\">\((\{\{|\s+)\s*s\.file_count\s*\}\)\<\/span\>\{\% if not forloop\.last \%\}, \{\% endif \%\}\{\% endfor \%\})"
    # Actually, simplistic approach: find the specific lines by index or content parts
    lines = content.splitlines()
    found = False
    for i in range(len(lines) - 1):
        if 'level.preview_subjects' in lines[i] and '{{' in lines[i] and 's.name' in lines[i] and 'text-gray-400' in lines[i] and '({{' in lines[i]:
             if 's.file_count' in lines[i+1]:
                 # Join them
                 print(f"Found match at line {i+1}")
                 lines[i] = lines[i].rstrip() + " " + lines[i+1].lstrip()
                 del lines[i+1] # Remove the next line
                 found = True
                 break
    
    if found:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print("Successfully patched levels.html with line logic")
    else:
        print("Target string not found directly or via line logic.")
