"""
Question Generation Tool for Retrieval Benchmarking.
Extracts candidate questions from repository files using the configured LLM adapter
for subsequent human verification.
"""

import os
import sys
import json
import asyncio
from typing import List, Dict, Any

# Ensure backend app is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.llm.llm_adapter import get_llm_adapter


PROMPT_TEMPLATE = """You are creating gold-standard retrieval evaluation benchmark questions for a codebase.
Given the file path '{file_path}' and code snippet:
```
{snippet}
```

Generate 2 precise questions about the behavior, symbols, or architecture in this file.
Return ONLY valid JSON matching this schema:
[
  {{"question": "...", "expected_files": ["{file_path}"]}}
]
"""


async def generate_questions_for_files(files: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    adapter = get_llm_adapter()
    generated = []

    for item in files:
        file_path = item["path"]
        content = item["content"]
        snippet = "\n".join(content.splitlines()[:50])

        prompt = PROMPT_TEMPLATE.format(file_path=file_path, snippet=snippet)
        try:
            resp = await adapter.generate(prompt)
            clean = resp.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1].rsplit("\n", 1)[0].strip()
            items = json.loads(clean)
            if isinstance(items, list):
                generated.extend(items)
        except Exception:
            # Fallback deterministic template if model is dummy or fails parsing
            generated.append({
                "question": f"Where is the functionality in {file_path} implemented?",
                "expected_files": [file_path]
            })

    return generated


async def main():
    sample_files = [
        {
            "path": "backend/app/core/validator.py",
            "content": "def validate_and_normalize_github_url(url: str): ..."
        },
        {
            "path": "backend/app/core/secret_masker.py",
            "content": "def mask_secrets(content: str): ..."
        }
    ]

    out_file = os.path.join(os.path.dirname(__file__), "candidate_questions.jsonl")
    candidates = await generate_questions_for_files(sample_files)
    with open(out_file, "w", encoding="utf-8") as fp:
        for c in candidates:
            fp.write(json.dumps(c) + "\n")

    print(f"Generated {len(candidates)} candidate questions written to {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
