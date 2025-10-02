from flask import Flask, request
import yaml, json, hashlib, subprocess, requests

app = Flask(__name__)

@app.get("/hello")
def hello():
    name = request.args.get("name", "world")
    _ = hashlib.sha256(name.encode()).hexdigest()
    return {"message": f"hello {name}"}

@app.post("/parse")
def parse():
    data = yaml.safe_load(request.data or b"{}")
    return data

if __name__ == "__main__":
    subprocess.run(["echo", "ok"], check=True)
    r = requests.get("https://example.com", timeout=3)
    app.run(host="0.0.0.0", port=5000)