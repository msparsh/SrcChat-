import re
import time
from langchain_core.messages import HumanMessage, SystemMessage

from .config import CITE_RE, SYSTEM_PROMPT
from .ollama import get_llm
from .storage import get_vectorstore, resolve_repos

HISTORY = []   # list of (role, text); used to resolve follow-up questions
_llm = None


def get_chat_llm():
    global _llm
    if _llm is None:
        _llm = get_llm()
    return _llm


def reset_chat():
    HISTORY.clear()


def check_citations(answer, used):
    by_label = {d.page_content.split("\n", 1)[0].strip()[1:-1]: d.page_content for d in used}
    warnings = []
    for c in sorted(set(CITE_RE.findall(answer))):
        if c not in by_label:
            warnings.append(f"cited chunk was never retrieved: [{c}]")
    for sent in re.split(r"(?<=[.!?])\s+|\n", answer):
        labels = [c for c in CITE_RE.findall(sent) if c in by_label]
        for ident in set(re.findall(r"`([A-Za-z_][A-Za-z0-9_.]*)`", sent)) if labels else []:
            core = ident.split(".")[-1]
            if not any(core in by_label[l] for l in labels):
                warnings.append(f"`{ident}` does not appear in the chunk cited next to it {labels}")
    return warnings


def standalone_question(q):
    if not HISTORY:
        return q
    convo = "\n".join(f"{role}: {text[:500]}" for role, text in HISTORY[-6:])
    msgs = [
        SystemMessage(content="Rewrite the user's last question as one standalone search query about a codebase. "
                              "Use the conversation to resolve words like 'it' or 'that'. Output only the query."),
        HumanMessage(content=f"Conversation:\n{convo}\n\nLast question: {q}"),
    ]
    llm = get_chat_llm()
    return llm.invoke(msgs).content.strip() or q


def ask(question, repos=None, verbose=True, k=8):
    """k = total chunks to retrieve (split across the selected repos). Use k=10-12 for broad, open-ended questions."""
    scope = resolve_repos(repos)
    q = standalone_question(question)
    if verbose and q != question:
        print(f"(searching for: {q})")

    per_repo = max(3, k // len(scope))
    hits = []
    vs = get_vectorstore()
    for r in scope:
        hits += vs.similarity_search(q, k=per_repo, filter={"repo": r})

    context, used = "", []
    for d in hits:
        block = f"<chunk>\n{d.page_content}\n</chunk>\n"
        if len(context) + len(block) > 12000:
            break
        context += block
        used.append(d)

    msgs = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"<context>\n{context}</context>\n\nQuestion: {q}"),
    ]
    llm = get_chat_llm()
    t0, ttft, answer = time.time(), None, ""
    for chunk in llm.stream(msgs):
        if ttft is None and chunk.content:
            ttft = time.time() - t0
        answer += chunk.content
        if verbose:
            print(chunk.content, end="", flush=True)
    total = time.time() - t0

    refused = answer.strip().startswith("I couldn't find") and len(answer.strip()) < 250
    warnings = [] if refused else check_citations(answer, used)

    sources, seen = [], set()
    for d in used:
        m = d.metadata
        if m["url"] not in seen:
            seen.add(m["url"])
            sources.append(f"{m['repo']}  {m['path']}:L{m['start_line']}-L{m['end_line']}  {m['url']}")
    if verbose:
        if refused:
            print("\n\n(no relevant code was found, so the retrieved chunks were not used)")
        else:
            print("\n\nSources retrieved:")
            for sline in sources:
                print(" -", sline)
            for w in warnings:
                print(" ! check:", w)
        print(f"\n[time to first token {ttft or 0:.1f}s, total {total:.1f}s]")

    HISTORY.append(("user", question))
    HISTORY.append(("assistant", answer))
    return {"answer": answer, "sources": sources, "query": q, "refused": refused,
            "warnings": warnings, "ttft": ttft, "total": total}
