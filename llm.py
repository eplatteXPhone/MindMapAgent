"""Claude API integration for analysing brainstorming ideas."""

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"


async def analyse_ideas(topic: str, ideas: list[dict]) -> dict:
    """Send all ideas to Claude for deduplication, categorisation, and structuring.

    Args:
        topic: The brainstorming session topic.
        ideas: List of dicts with 'text' and 'author' keys.

    Returns:
        Structured dict with categories, ideas, dependencies, and summary.
    """
    client = anthropic.AsyncAnthropic()

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

    response = await client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[: text.rfind("```")]
    return json.loads(text)
