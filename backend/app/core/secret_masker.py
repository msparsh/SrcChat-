import re

# File patterns and extensions to completely skip
SENSITIVE_FILENAMES = {
    ".env", ".env.local", ".env.development", ".env.production", ".env.test",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"
}

SENSITIVE_EXTENSIONS = {
    ".pem", ".key", ".pkcs12", ".p12", ".pfx", ".cert", ".crt", ".kdb", ".jks"
}

# Regexes matching tokens, API keys, private keys, JWTs
SECRET_PATTERNS = [
    # Generic API Keys / Tokens
    (re.compile(r"""(?i)(?:api_key|apikey|secret|token|password|auth_token|access_token|bearer)\s*[:=]\s*["']?([a-zA-Z0-9_\-\.]{16,})["']?"""), r"\g<0>"),
    # AWS Access Key ID
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "[REDACTED_AWS_KEY]"),
    # GitHub Personal Access Token (classic & fine-grained)
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\b(github_pat_[A-Za-z0-9_]{82})\b"), "[REDACTED_GITHUB_PAT]"),
    # Slack Token
    (re.compile(r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b"), "[REDACTED_SLACK_TOKEN]"),
    # Private Key headers
    (re.compile(r"-----BEGIN [A-Z0-9_-]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z0-9_-]+ PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
    # Generic high-entropy hex/base64 secrets
    (re.compile(r"\b([0-9a-fA-F]{32,64})\b"), None), # Handled selectively if preceded by secret key
]

def is_sensitive_file(filename: str) -> bool:
    """Returns True if the file should never be indexed due to credential danger."""
    fn_lower = filename.lower()
    if fn_lower in SENSITIVE_FILENAMES:
        return True
    if any(fn_lower.startswith(".env") for _ in [1]):
        return True
    for ext in SENSITIVE_EXTENSIONS:
        if fn_lower.endswith(ext):
            return True
    return False

def mask_secrets(text: str) -> str:
    """Masks secret keys, tokens, and private keys in the given code/text."""
    if not text:
        return text

    masked = text

    # Handle Private keys
    masked = re.sub(
        r"-----BEGIN [A-Z0-9_\s]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9_\s]+ PRIVATE KEY-----",
        "/* [REDACTED_PRIVATE_KEY] */",
        masked
    )

    # Handle standard token patterns
    for pattern, replacement in SECRET_PATTERNS:
        if replacement and not replacement.startswith(r"\g"):
            masked = pattern.sub(replacement, masked)

    # Handle generic key assignments like apiKey = "abcd1234efgh5678"
    def mask_kv(match):
        full = match.group(0)
        secret_part = match.group(1)
        return full.replace(secret_part, "[REDACTED_SECRET]")

    kv_pattern = re.compile(r"""(?i)(?:api[_-]?key|secret[_-]?key|auth[_-]?token|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*["']?([a-zA-Z0-9_\-\.]{12,})["']?""")
    masked = kv_pattern.sub(mask_kv, masked)

    return masked
