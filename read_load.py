lines=open('server/static/index.html', encoding='utf-8').readlines()
idx = [i for i, l in enumerate(lines) if "window.addEventListener('load'" in l][0]
print("".join(lines[idx:idx+40]))
