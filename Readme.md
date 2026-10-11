<div align="center">

# 💬 SrcChat

### Talk to any public GitHub repository - 100% locally.

Index a codebase, ask questions in plain English, and get answers grounded in the actual source.<br>
No API keys. No cloud. Your questions never leave your machine.

<br>

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLMs-000000?style=for-the-badge&logo=ollama&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-RAG-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![ChromaDB](https://img.shields.io/badge/Chroma-Vector_Store-FF6F61?style=for-the-badge)
![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge)

[Features](#features) •
[Quick Start](#quick-start) •
[Usage](#usage) •
[How It Works](#how-it-works) •
[Roadmap](#roadmap) •
[Contributing](#contributing)

</div>

---

## ✨ Why SrcChat?

Reading an unfamiliar codebase is slow. You skim the README, grep for keywords, jump between files, and still wonder *"where does this actually happen?"*

**SrcChat** turns any public GitHub repo into something you can simply *ask*:

```console
$ python main.py add https://github.com/owner/repo
$ python main.py ask "Where is authentication handled?"
```

It uses retrieval-augmented generation (RAG) to find the most relevant pieces of code and feeds them to a local LLM, so answers come from the real source instead of guesswork.

## 🚀 Features

| | Feature | Description |
|---|---|---|
| 🔒 | **Fully local** | Runs on [Ollama](https://ollama.com). Nothing is sent to third-party APIs. |
| 🛡️ | **Secret masking & safety** | Redacts keys, passwords, and tokens before embedding. Ignores symlinks; code is never executed. |
| 📦 | **Index any public repo** | Point it at a GitHub URL and it clones and indexes the code for you. Re-indexing replaces old data cleanly. |
| 📎 | **Source citations & checks** | Answers include inline `[repo path:Lx-Ly]` citations, GitHub links, and automatic hallucination checks. |
| 🌿 | **Branch & subdirectory control** | Index a specific branch, or just the folder you care about. |
| 🗂️ | **Multi-repo search** | Index several repos and query them together, or narrow to specific ones. |
| 💬 | **Interactive chat mode** | Hold a back-and-forth conversation with query rewriting and memory reset. |
| 🎯 | **Tunable retrieval** | Choose how many chunks of context are retrieved per question. |
| ⚡ | **Simple CLI** | Six commands. No config files, no setup maze. |

## 🏁 Quick Start

### Prerequisites

- **Python 3.10+**
- **[Git](https://git-scm.com/)**, used to clone repositories
- **[Ollama](https://ollama.com/download)** installed on your machine

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/msparsh/SrcChat-.git
cd SrcChat-

# 2. (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Make sure Ollama is running and pull models (gemma3:4b & nomic-embed-text)
python main.py setup
```

That's it. You're ready to chat with code. 🎉

## 🎮 Usage

### Index a repository

```bash
python main.py add https://github.com/owner/repo
```

Want more control?

```bash
# Index a specific branch
python main.py add https://github.com/owner/repo --branch develop

# Index only one subdirectory
python main.py add https://github.com/owner/repo --subdir src/core
```

### Ask a one-off question

```bash
python main.py ask "How does the request routing work?"
```

Limit the search to specific repos, or retrieve more context:

```bash
python main.py ask "Where are errors logged?" --repo owner/repo
python main.py ask "Explain the data model" -r owner/repo-a -r owner/repo-b -k 12
```

### Start an interactive chat

```bash
python main.py chat
```

```text
You: What does this project do?
...
You: Which file would I edit to add a new command?
...
You: reset        # clears chat history
You: exit         # leaves the session
```

### Manage your index

```bash
python main.py list                  # see everything you've indexed
python main.py remove owner/repo     # remove a repo from the index
```

## 📖 Command Reference

| Command | Description | Options |
|---|---|---|
| `setup` | Ensure Ollama is running and the models are pulled | — |
| `add <url>` | Index a GitHub repository | `--branch`, `--subdir` |
| `list` | List indexed repositories | — |
| `remove <name>` | Remove an indexed repository | — |
| `ask "<question>"` | Ask a question across indexed repos | `--repo / -r` (repeatable), `-k` (default `8`) |
| `chat` | Start an interactive session | `--repo / -r` (repeatable), `-k` (default `8`) |

## 🧠 How It Works

SrcChat is a classic local RAG pipeline:

1. **Ingest:** the repo is cloned and its files are split into overlapping chunks.
2. **Embed & store:** each chunk is embedded using an Ollama model and saved in a local Chroma vector database.
3. **Retrieve:** your question is embedded and the `k` most similar chunks are pulled from the index.
4. **Generate:** the retrieved code is passed to a local LLM as context, which answers your question.

## 🧰 Tech Stack

| Layer | Tool |
|---|---|
| LLM & embeddings | [Ollama](https://ollama.com) via `langchain-ollama` |
| Vector database | [Chroma](https://www.trychroma.com/) via `langchain-chroma` |
| Chunking | `langchain-text-splitters` |
| Progress bars | `tqdm` |
| Interface | Python CLI (`argparse`) |

## 📁 Project Structure

```text
SrcChat-/
├── srcchat/           # Core package: indexing, retrieval, chat logic
├── main.py            # CLI entry point
├── SrcChat.ipynb      # Notebook version
├── requirements.txt   # Python dependencies
└── LICENSE            # Apache 2.0
```

## 💡 Tips

- **Start small.** Use `--subdir` on big monorepos to index only the part you need. It's faster and gives sharper answers.
- **Tune `-k`.** Higher values give the model more context for broad questions; lower values keep answers focused.
- **Be specific.** *"Where is the retry logic for failed uploads?"* beats *"How does it work?"*
- **Use `reset`** in chat mode when you switch topics, so old context doesn't muddy new answers.

## 🛣️ Roadmap

- [ ] Web UI (FastAPI backend + frontend interface)
- [ ] Configurable models via command-line flags
- [ ] Support for private repositories (SSH / tokens)
- [ ] Hybrid search (BM25 + vector similarity) and re-ranking
- [ ] Incremental re-sync using git commit hashes

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the project
2. Create your feature branch: `git checkout -b feature/amazing-idea`
3. Commit your changes: `git commit -m "Add amazing idea"`
4. Push to the branch: `git push origin feature/amazing-idea`
5. Open a Pull Request

## 📄 License

Distributed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) for details.

---

<div align="center">

**If SrcChat saved you some code-reading time, consider giving it a ⭐**

Made with ❤️ by [@msparsh](https://github.com/msparsh)

</div>