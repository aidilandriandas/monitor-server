import re
html = open('server/static/index.html', encoding='utf-8').read()
match = re.search(r'document\.addEventListener\([\'"]DOMContentLoaded[\'"](.*?)\}\);', html, flags=re.DOTALL)
if match:
    lines = match.group(1).split('\n')
    for line in lines[:20]:
        print(line)
    print("...")
else:
    print("Not found")
