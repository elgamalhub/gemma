# Run in a GitHub Codespace:  python server.py
import os, re, json, time, subprocess, urllib.request
def sh(c): subprocess.run(c, shell=True, check=True, stdout=subprocess.DEVNULL)
if not os.path.exists("llama.cpp/build/bin/llama-server"):
    sh("sudo apt-get -qq update && sudo apt-get -qq install -y cmake libssl-dev")
    sh("rm -rf llama.cpp && git clone -q --depth 1 https://github.com/ggml-org/llama.cpp")
    sh("cmake -S llama.cpp -B llama.cpp/build -DGGML_NATIVE=OFF -DCMAKE_BUILD_TYPE=Release -DCMAKE_UNITY_BUILD=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF")
    sh("cmake --build llama.cpp/build -j2 --target llama-server")
if not os.path.exists("cf"):
    sh("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cf && chmod +x cf")
    sh("pip -q install huggingface_hub")
NAME, MODEL = "codespace", "unsloth/gemma-4-E4B-it-GGUF:UD-Q4_K_XL"
API_KEY, HF_TOKEN, REGISTRY = (os.environ[k] for k in ("API_KEY", "HF_TOKEN", "REGISTRY"))
subprocess.Popen(["llama.cpp/build/bin/llama-server", "-hf", MODEL, "--host", "127.0.0.1", "--port", "8080",
                  "--api-key", API_KEY, "--jinja", "-c", "4096"], stdout=open("llama.log", "w"), stderr=subprocess.STDOUT)
for _ in range(180):  # wait up to 15 min (model download)
    try:
        urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=3); break
    except Exception: time.sleep(5)
else: raise RuntimeError(open("llama.log").read()[-2000:])
tun = subprocess.Popen(["./cf", "tunnel", "--url", "http://127.0.0.1:8080"], stderr=subprocess.PIPE, text=True)
url = None
for line in tun.stderr:
    m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
    if m: url = m.group(0); break
from huggingface_hub import HfApi
api = HfApi(token=HF_TOKEN)
api.create_repo(REGISTRY, repo_type="dataset", private=True, exist_ok=True)
json.dump({"url": url, "t": time.time()}, open(f"{NAME}.json", "w"))
api.upload_file(path_or_fileobj=f"{NAME}.json", path_in_repo=f"{NAME}.json", repo_id=REGISTRY, repo_type="dataset")
print("LIVE:", url, "- registered as", NAME, "- keep this cell running")
tun.wait()