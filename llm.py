"""LLM integration for analysing brainstorming ideas (multi-provider via litellm)."""

import json

from litellm import acompletion

# ── Provider presets ─────────────────────────────────────────────────
PROVIDERS = {
    "Gemini Flash": "gemini/gemini-2.0-flash",
    "Gemini Flash Lite": "gemini/gemini-2.0-flash-lite",
    "OpenAI": "openai/gpt-4o-mini",
    "Anthropic": "anthropic/claude-sonnet-4-6",
}

# ── Module-level config (set from UI) ───────────────────────────────
_api_key: str | None = None
_model: str = PROVIDERS["Gemini Flash"]


def configure(provider: str, api_key: str):
    """Set the active provider and API key."""
    global _api_key, _model
    _api_key = api_key
    _model = PROVIDERS[provider]


def is_configured() -> bool:
    return bool(_api_key)


async def validate_key(provider: str, api_key: str) -> str | None:
    """Test the key with a tiny request. Returns None on success, error string on failure.

    Quota/rate-limit errors are treated as 'key valid' (the key works, just throttled).
    """
    model = PROVIDERS[provider]
    try:
        await acompletion(
            model=model,
            messages=[{"role": "user", "content": "Say OK"}],
            api_key=api_key,
            max_tokens=5,
        )
        return None
    except Exception as ex:
        err = str(ex).lower()
        print(f"[validate_key] {provider}: {ex}", flush=True)
        # Quota/rate-limit errors mean the key itself is valid
        if any(k in err for k in ("quota", "rate limit", "rate_limit", "429", "resource exhausted")):
            return None
        return str(ex)


async def analyse_ideas(topic: str, ideas: list[dict]) -> dict:
    """Send all ideas to the configured LLM for deduplication, categorisation, and structuring.

    Args:
        topic: The brainstorming session topic.
        ideas: List of dicts with 'text' and 'author' keys.

    Returns:
        Structured dict with categories, ideas, dependencies, and summary.
    """
    if not _api_key:
        raise RuntimeError("No API key configured. Set one in the UI first.")

    ideas_text = "\n".join(
        f"- \"{idea['text']}\" (by {idea['author']})" for idea in ideas
    )

    prompt = f"""You are analysing ideas from a brainstorming session.

Topic: "{topic}"

Ideas submitted by participants:
{ideas_text}

Analyse these ideas and return a JSON object with this exact structure:
{{
  "summary": "A brief 1-2 sentence summary of the brainstorming session",
  "categories": [
    {{
      "name": "Category Name",
      "description": "Brief description of this category",
      "ideas": [
        {{
          "text": "The deduplicated/merged idea text",
          "authors": ["author1", "author2"],
          "original_count": 2,
          "note": "Optional note about merging or context"
        }}
      ]
    }}
  ],
  "dependencies": [
    {{
      "from": "Idea or category that depends on another",
      "to": "Idea or category it depends on",
      "relationship": "Brief description of the dependency"
    }}
  ],
  "uncategorised": [
    {{
      "text": "Ideas that don't fit any category",
      "authors": ["author"],
      "note": "Why it doesn't fit"
    }}
  ]
}}

Rules:
- Merge duplicate or very similar ideas, crediting all authors
- Create meaningful categories that group related ideas
- Identify dependencies between ideas or categories
- Keep the original meaning of ideas intact
- If ideas conflict, note the conflict rather than dropping either idea
- Return ONLY valid JSON, no markdown fences or extra text"""

    response = await acompletion(
        model=_model,
        messages=[{"role": "user", "content": prompt}],
        api_key=_api_key,
        max_tokens=4096,
    )

    text = response.choices[0].message.content
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[: text.rfind("```")]
    return json.loads(text)
