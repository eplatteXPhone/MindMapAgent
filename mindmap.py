"""Convert LLM analysis JSON to markdown and render as standalone HTML mindmap."""

import os

from jinja2 import Environment, FileSystemLoader

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
TEMPLATE_DIR = os.path.dirname(__file__)


def analysis_to_markdown(topic: str, analysis: dict) -> str:
    """Convert the structured LLM analysis to hierarchical markdown for markmap."""
    lines = [f"# {topic}", ""]

    for category in analysis.get("categories", []):
        lines.append(f"## {category['name']}")
        if category.get("description"):
            lines.append(f"  - *{category['description']}*")
        for idea in category.get("ideas", []):
            authors = ", ".join(idea.get("authors", []))
            lines.append(f"  - {idea['text']}")
            if authors:
                lines.append(f"    - by: {authors}")
            if idea.get("note"):
                lines.append(f"    - *{idea['note']}*")
        lines.append("")

    uncategorised = analysis.get("uncategorised", [])
    if uncategorised:
        lines.append("## Uncategorised")
        for idea in uncategorised:
            authors = ", ".join(idea.get("authors", []))
            lines.append(f"  - {idea['text']}")
            if authors:
                lines.append(f"    - by: {authors}")
        lines.append("")

    deps = analysis.get("dependencies", [])
    if deps:
        lines.append("## Dependencies")
        for dep in deps:
            lines.append(f"  - {dep['from']} → {dep['to']}")
            if dep.get("relationship"):
                lines.append(f"    - *{dep['relationship']}*")
        lines.append("")

    return "\n".join(lines)


def render_mindmap_html(
    session_id: str, topic: str, analysis: dict
) -> str:
    """Render analysis as standalone HTML mindmap. Returns the file path."""
    markdown = analysis_to_markdown(topic, analysis)

    total_ideas = sum(
        len(cat.get("ideas", []))
        for cat in analysis.get("categories", [])
    ) + len(analysis.get("uncategorised", []))

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template("mindmap_template.html")
    html = template.render(
        title=f"Mindmap: {topic}",
        markdown=markdown,
        summary=analysis.get("summary", ""),
        idea_count=total_ideas,
        category_count=len(analysis.get("categories", [])),
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, f"{session_id}.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath
