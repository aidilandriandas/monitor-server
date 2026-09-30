import re

html = open('server/static/index.html', encoding='utf-8').read()

# find all onclicks
onclicks = re.findall(r'onclick=[\'"]([^\'"]+)[\'"]', html)

# find all defined functions
defined_funcs = re.findall(r'(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(', html)
defined_funcs = set(defined_funcs)

# Check if onclick functions are in defined
missing = []
for oc in onclicks:
    # Some onclicks might be JS code like "document.getElementById('x').submit()"
    if '(' in oc:
        func_name = oc.split('(')[0].strip()
        if func_name and re.match(r'^[a-zA-Z0-9_]+$', func_name):
            if func_name not in defined_funcs:
                missing.append(oc)

print("Missing onclick functions:", set(missing))
