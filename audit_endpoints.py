import re
import os

print("--- Frontend API Calls (index.html) ---")
try:
    with open("server/static/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    calls = re.findall(r'fetch\([\'"`]([^\'"`]+)[\'"`]', html)
    for c in sorted(set(calls)):
        print(c)
except Exception as e:
    print(f"Error: {e}")

print("\n--- Backend Endpoints (main.py) ---")
try:
    with open("server/main.py", "r", encoding="utf-8") as f:
        main = f.read()
    routes = re.findall(r'@app\.(get|post|delete|put|patch)\([\'"`]([^\'"`]+)[\'"`]', main)
    for m, p in routes:
        print(f"{m.upper()} {p}")
except Exception as e:
    print(f"Error: {e}")
