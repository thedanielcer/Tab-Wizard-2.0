from urllib.parse import urlparse

# === CLEANING RULES ===
# Define how to clean titles per domain
CLEANING_RULES = {
    "youtube.com": {
        "remove_suffix": " - YouTube",
    },
    "chatgpt.com": {
        "remove_prefix": "ChatGPT - ",
        "replace_exact": {"ChatGPT": "New Chat"},
    },
    "github.com": {
        "split_by": "/",  # Take only the second part: repo name
    },
}

def clean_tab_title(title: str, url: str) -> str:
    """Clean a browser tab title based on domain-specific rules.

    Args:
        title: The original tab title.
        url: The tab URL.

    Returns:
        A cleaned title suitable for displaying on limited space (like Stream Deck keys).
    """
    title = title.strip()
    if not title:
        return title

    domain = urlparse(url).netloc.lower()

    # Apply cleaning rules if domain matches
    for match_domain, rules in CLEANING_RULES.items():
        if domain == match_domain or domain.endswith("." + match_domain):
            # Apply specific cleaning steps

            if "replace_exact" in rules:
                if title in rules["replace_exact"]:
                    return rules["replace_exact"][title]

            if "remove_prefix" in rules:
                prefix = rules["remove_prefix"]
                if title.startswith(prefix):
                    title = title[len(prefix):].strip()

            if "remove_suffix" in rules:
                suffix = rules["remove_suffix"]
                if title.endswith(suffix):
                    title = title[:-len(suffix)].strip()

            if "split_by" in rules:
                splitter = rules["split_by"]
                parts = title.split(splitter, 1)
                if len(parts) > 1:
                    return parts[1].strip()

            break  # Stop after first matching domain

    return title  # Return possibly cleaned title
