import sys

with open('server/static/index.html', encoding='utf-8') as f:
    lines = f.readlines()

with open('out.txt', 'w', encoding='utf-8') as f:
    for i, l in enumerate(lines):
        if 'function secBlockIp(' in l:
            for j in range(i, min(i+30, len(lines))):
                f.write(lines[j])
            sys.exit(0)
