import argparse
import sys
from srcchat import add_repo, ask, list_repos, remove_repo, reset_chat, setup_ollama


def main():
    parser = argparse.ArgumentParser(description="RepoChat: talk to public GitHub repos with Ollama")
    subparsers = parser.add_subparsers(dest="command")

    # setup
    subparsers.add_parser("setup", help="Ensure Ollama is running and models are pulled")

    # add
    add_parser = subparsers.add_parser("add", help="Index a GitHub repository")
    add_parser.add_argument("url", help="GitHub repo URL (https://github.com/owner/repo)")
    add_parser.add_argument("--branch", help="Specific branch to clone", default=None)
    add_parser.add_argument("--subdir", help="Index only a specific subdirectory", default=None)

    # list
    subparsers.add_parser("list", help="List indexed repositories")

    # remove
    rm_parser = subparsers.add_parser("remove", help="Remove an indexed repository")
    rm_parser.add_argument("name", help="Repository name (owner/repo or repo)")

    # ask
    ask_parser = subparsers.add_parser("ask", help="Ask a question across indexed repositories")
    ask_parser.add_argument("question", help="Question to ask")
    ask_parser.add_argument("--repo", "-r", action="append", dest="repos", help="Limit search to specific repos")
    ask_parser.add_argument("-k", type=int, default=8, help="Number of chunks to retrieve (default: 8)")

    # chat / interactive mode
    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session")
    chat_parser.add_argument("--repo", "-r", action="append", dest="repos", help="Limit search to specific repos")
    chat_parser.add_argument("-k", type=int, default=8, help="Number of chunks to retrieve (default: 8)")

    args = parser.parse_args()

    if args.command == "setup":
        setup_ollama()
    elif args.command == "add":
        add_repo(args.url, branch=args.branch, subdir=args.subdir)
    elif args.command == "list":
        list_repos()
    elif args.command == "remove":
        remove_repo(args.name)
    elif args.command == "ask":
        ask(args.question, repos=args.repos, k=args.k)
    elif args.command == "chat":
        print("Starting interactive RepoChat. Type 'exit', 'quit', or 'reset' (to clear history).\n")
        while True:
            try:
                q = input("\nYou: ").strip()
                if not q:
                    continue
                if q.lower() in {"exit", "quit"}:
                    break
                if q.lower() == "reset":
                    reset_chat()
                    print("Chat history cleared.")
                    continue
                print()
                ask(q, repos=args.repos, k=args.k)
            except (KeyboardInterrupt, EOFError):
                break
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
