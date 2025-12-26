from langchain.chat_models import init_chat_model
from src.models.schemas import MessageClassifier, State
from src.config.settings import settings
import re

llm = init_chat_model(settings.LLM_MODEL)


def _extract_username(text: str) -> str | None:
    """Extract GitHub username from text or URL using regex fallbacks."""
    url_pattern = r"https?://github\.com/([\w-]+)(?:/|$)"
    m = re.search(url_pattern, text)
    if m:
        return m.group(1)

    # @username
    at_pattern = r"@([\w-]+)"
    m = re.search(at_pattern, text)
    if m:
        return m.group(1)

    # phrases like: user/username/profile ... <name>
    user_pattern = r"(?:user|username|profile)(?:\s+(?:name|account|id|of|for))*\s+(@?[\w-]+)"
    m = re.search(user_pattern, text, re.IGNORECASE)
    if m:
        return m.group(1).lstrip("@")

    return None


def _extract_owner_repo(text: str) -> tuple[str | None, str | None]:
    """Extract owner and repo name from text or URL using regex fallbacks."""
    # URL owner/repo
    url_pattern = r"https?://github\.com/([\w-]+)/([\w-]+)"
    m = re.search(url_pattern, text)
    if m:
        return m.group(1), m.group(2)

    # "repo <name> by <owner>"
    by_pattern = r"repo\s+(@?[\w-]+)\s+by\s+(@?[\w-]+)"
    m = re.search(by_pattern, text, re.IGNORECASE)
    if m:
        return m.group(2).lstrip("@"), m.group(1).lstrip("@")

    # "owner is/of <owner> ... repo is/name <repo>"
    owner_repo_pattern = (
        r"(?:owner|user|author)(?:\s+\w+)*?\s+(?:is|of|=)\s+(@?[\w-]+)(?:.*?)(?:repo|repository)"
        r"(?:\s+\w+)*?\s+(?:is|name|=|called|by\s+the\s+name\s+of)\s+(@?[\w-]+)"
    )
    m = re.search(owner_repo_pattern, text, re.IGNORECASE)
    if m:
        return m.group(1).lstrip("@"), m.group(2).lstrip("@")

    # "repo of <owner>/<repo>" or "repo of <owner> repo <repo>"
    slash_pattern = r"repo\s+(?:of\s+)?(@?[\w-]+)[/\s]+(@?[\w-]+)"
    m = re.search(slash_pattern, text, re.IGNORECASE)
    if m:
        return m.group(1).lstrip("@"), m.group(2).lstrip("@")

    return None, None


def classify_message(state: State):
    """Classify the user message and extract username/repo when applicable."""
    last_message = state["messages"][-1]
    user_text = last_message.content if hasattr(last_message, "content") else last_message.get("content")

    classifier_llm = llm.with_structured_output(MessageClassifier)

    result = classifier_llm.invoke([
        {
            "role": "system",
            "content": """
Classify the user message into ONE of these categories AND extract identifiers:

1. 'Github_user':
   - Use when the message asks about a GitHub USER (profile/person)
   - URL like "https://github.com/<username>" (NO repo after username)
   - Extract: username (owner). Set repo_name = null.

2. 'Github':
   - Use when the message asks about a specific GitHub REPOSITORY
   - URL like "https://github.com/<owner>/<repo>" (HAS repo name)
   - Extract: username = owner, repo_name = repo.

3. 'logical':
   - Use when it's a general question without GitHub identifiers
   - Extract: both username and repo_name = null.

RULES:
- Prefer explicit IDs from URLs; otherwise, infer from natural language (e.g., "repo react by facebook").
- Do not fabricate values. If uncertain, leave the field null.
""",
        },
        {"role": "user", "content": user_text},
    ])

    message_type = result.message_type
    username = result.username
    repo_name = result.repo_name

    # Fallbacks via regex if LLM didn't populate
    if message_type == "Github_user" and not username:
        username = _extract_username(user_text)

    if message_type == "Github":
        if not (username and repo_name):
            owner, repo = _extract_owner_repo(user_text)
            username = username or owner
            repo_name = repo_name or repo

    return {"message_type": message_type, "username": username, "repo_name": repo_name}