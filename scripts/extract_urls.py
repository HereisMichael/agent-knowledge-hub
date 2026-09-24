import json, re

with open(r"C:\Users\2025\.cursor\projects\d-cursor-project\agent-tools\b871603c-6a5e-480f-9689-3e8708fdfa3f.txt", "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    name = item["name"]
    if "综合面经题库" in name:
        print(item["download_url"])
