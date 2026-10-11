import re
from typing import Optional, Tuple
from urllib.parse import urlparse

# Pattern matching strictly https://github.com/<owner>/<repo>
GITHUB_URL_REGEX = re.compile(r"^https://github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)(?:/)?$")

# Safe characters check for owner and repo names
VALID_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def validate_and_normalize_github_url(url: str) -> Tuple[str, str, str]:
    """
    Validates that a URL is strictly a public GitHub repo URL.
    Returns: (normalized_url, owner, repo)
    Raises ValueError with descriptive reason if invalid or potential SSRF.
    """
    if not url or not isinstance(url, str):
        raise ValueError("GitHub URL must be provided.")

    clean_url = url.strip().rstrip("/")
    if clean_url.endswith(".git"):
        clean_url = clean_url[:-4].rstrip("/")

    parsed = urlparse(clean_url)
    if parsed.netloc.lower() not in ("github.com", "www.github.com"):
        raise ValueError("Only public GitHub repositories (https://github.com/owner/repo) are allowed.")

    if parsed.scheme != "https":
        raise ValueError("Only secure HTTPS URLs are permitted.")

    match = GITHUB_URL_REGEX.match(clean_url)
    if not match:
        raise ValueError("Invalid GitHub repository format. Expected: https://github.com/<owner>/<repo>")

    owner, repo = match.groups()

    if not VALID_NAME_REGEX.match(owner) or not VALID_NAME_REGEX.match(repo):
        raise ValueError("Repository owner or name contains invalid characters.")

    if owner in (".", "..") or repo in (".", ".."):
        raise ValueError("Invalid owner or repository name.")

    normalized_url = f"https://github.com/{owner}/{repo}"
    return normalized_url, owner, repo
