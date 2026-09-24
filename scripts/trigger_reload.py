"""Touch the questions module to trigger uvicorn --reload."""
import pathlib, time, urllib.request, json

# Touch the file to trigger reload
f = pathlib.Path(r"D:\cursor_project\agent-knowledge-hub_optimized\backend\app\interview\questions.py")
orig = f.read_text(encoding="utf-8")
f.write_text(orig + "\n", encoding="utf-8")
print("Touched questions.py, waiting for reload...")
time.sleep(5)

# Check
r = urllib.request.urlopen("http://127.0.0.1:8001/api/health", timeout=10)
d = json.loads(r.read())
print(f"questions: {d['questions']}")
