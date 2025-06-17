import glob

html_files = glob.glob('discogs/templates/**/*.html', recursive=True) + glob.glob('theme/templates/**/*.html', recursive=True)

for file in html_files:
    with open(file, 'r') as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        leading_spaces = len(line) - len(stripped)
        indent_level = leading_spaces // 4
        new_leading = ' ' * (indent_level * 2)
        new_line = new_leading + stripped
        new_lines.append(new_line)
    with open(file, 'w') as f:
        f.writelines(new_lines)
