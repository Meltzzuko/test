from flask import Flask, request
import os, yaml, pickle, hashlib, subprocess, requests

app = Flask(__name__)

# ตัวอย่าง Secret ปลอม → ให้ Trivy จับ
AWS_ACCESS_KEY_ID = "AKIA1234567890FAKEKEY"
AWS_SECRET_ACCESS_KEY = "abcdabcdabcdabcdabcdabcdabcdabcdabcdabcd"

@app.get("/hello")
def hello():
    name = request.args.get("name", "world")
    # ใช้แฮชแบบแข็งแรง (ตัวอย่างเฉยๆ ไม่เกี่ยวกับการล้ม)
    _ = hashlib.sha256(name.encode()).hexdigest()
    return {"message": f"hello {name}"}

# Code Injection: eval บน input → Semgrep ERROR
@app.get("/calc")
def calc():
    expr = request.args.get("expr", "")
    return {"result": eval(expr)}

# Insecure Deserialization: yaml.load ที่ไม่ปลอดภัย → Semgrep ERROR
@app.post("/parse")
def parse():
    data = request.data or b"{}"
    return yaml.load(data, Loader=yaml.Loader)  # ไม่ใช้ safe_loader

# Command Injection: shell=True + User input → Semgrep ERROR
@app.get("/run")
def run_cmd():
    cmd = request.args.get("cmd", "echo hi")
    out = subprocess.check_output(cmd, shell=True, text=True)
    return {"out": out}

# SSRF: ดึง URL ตาม input โดยไม่กรอง → อาจถูกจับด้วยบาง rule
@app.get("/fetch")
def fetch():
    url = request.args.get("url", "http://example.com")
    r = requests.get(url, timeout=2)
    return {"status": r.status_code, "len": len(r.content)}

# Path Traversal: เปิดไฟล์ตาม path ผู้ใช้ → บางกฎอาจเตือน
@app.get("/read")
def read_file():
    path = request.args.get("path", "/etc/hosts")
    with open(path, "r", encoding="utf-8") as f:
        return {"content": f.read()[:200]}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
