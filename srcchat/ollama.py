import os
import platform
import shutil
import subprocess
import time
import urllib.request

from langchain_ollama import ChatOllama, OllamaEmbeddings
from .config import CHAT_MODEL, EMBED_MODEL


def ollama_up() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:11434", timeout=2).read()
        return True
    except Exception:
        return False


def ensure_ollama_installed():
    """Install Ollama (Linux / Colab only). On Windows or macOS, install the app from https://ollama.com/download first."""
    if not shutil.which("ollama"):
        if platform.system() != "Linux":
            raise SystemExit("Ollama not found. Install it from https://ollama.com/download, then re-run.")
        sudo = "" if os.geteuid() == 0 else "sudo "
        print("Installing Ollama ...")
        subprocess.run(f"{sudo}apt-get update -qq && {sudo}apt-get install -y -qq zstd curl", shell=True, check=True)
        subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=True)


def start_ollama_server():
    """Start the server in the background and wait until it answers."""
    if not ollama_up():
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            if ollama_up():
                break
            time.sleep(1)
    assert ollama_up(), "Ollama server did not start"
    print("Ollama server is running")


def have_model(name: str) -> bool:
    lines = subprocess.run(["ollama", "list"], capture_output=True, text=True).stdout.splitlines()[1:]
    names = {l.split()[0] for l in lines if l.strip()}
    return name in names or f"{name}:latest" in names


def pull_models():
    """Pull models (skipped if already present)."""
    for m in (CHAT_MODEL, EMBED_MODEL):
        if have_model(m):
            print("already have", m)
        else:
            print(f"pulling {m} (first time only, can take a few minutes) ...")
            r = subprocess.run(["ollama", "pull", m], capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(r.stderr[-500:])
            print("done:", m)


def setup_ollama():
    ensure_ollama_installed()
    start_ollama_server()
    pull_models()


class NomicEmbeddings(OllamaEmbeddings):
    """nomic-embed-text works best with task prefixes on documents and queries."""
    def embed_documents(self, texts):
        return super().embed_documents([f"search_document: {t}" for t in texts])

    def embed_query(self, text):
        return super().embed_query(f"search_query: {text}")


def get_llm():
    # num_ctx matters: Ollama's default context is small and would silently cut off the retrieved code.
    return ChatOllama(model=CHAT_MODEL, temperature=0.1, num_ctx=8192)


def get_embeddings():
    return NomicEmbeddings(model=EMBED_MODEL)
