"""Tests for combining paper summaries into a newsletter."""

from selfletter.combiner import NewsletterCombiner


def _paper(title="A Useful <Paper>", summary="## What changed?\n\nA useful result."):
    return {
        "title": title,
        "source_url": "https://arxiv.org/abs/1234.5678?x=1&y=2",
        "type": "huggingface",
        "date": "2026-07-31",
        "summary": summary,
    }


def test_newsletter_uses_collapsed_paper_cards():
    content = NewsletterCombiner()._generate_newsletter(
        "2026-07-31",
        {"huggingface": [_paper(), _paper("Second paper")]},
    )

    assert content.startswith("<!-- buttondown-editor-mode: plaintext -->")
    assert "July 31, 2026" in content
    assert "2 research papers" in content
    assert content.count('<details class="paper-card"') == 2
    assert content.count("<summary ") == 2
    assert "<details open" not in content
    assert "Expand for the full analysis" in content
    assert "Table of Contents" not in content


def test_paper_card_renders_summary_markdown_and_escapes_metadata():
    card = NewsletterCombiner._render_paper_card(1, _paper())

    assert "A Useful &lt;Paper&gt;" in card
    assert "x=1&amp;y=2" in card
    assert "<h4>What changed?</h4>" in card
    assert "<p>A useful result.</p>" in card


def test_summary_removes_accidental_outer_markdown_fence():
    summary = "```markdown\n## What changed?\n\n- First\n- Second\n```"

    rendered = NewsletterCombiner._render_summary_html(summary)

    assert "<code>" not in rendered
    assert "<h4>What changed?</h4>" in rendered
    assert "<li>First</li>" in rendered


def test_summary_removes_outer_fence_after_model_preamble():
    summary = "Here is the requested summary.\n\n```markdown\n## Result\n\nUseful.\n```"

    rendered = NewsletterCombiner._render_summary_html(summary)

    assert "requested summary" not in rendered
    assert "<code>" not in rendered
    assert "<h4>Result</h4>" in rendered


def test_frontmatter_parser_preserves_horizontal_rules_in_summary():
    content = '''---
title: "Paper"
source_url: "https://example.com"
type: "huggingface"
date: "2026-07-31"
---

Before

---

After
'''

    parsed = NewsletterCombiner()._parse_summary_file(content)

    assert "Before\n\n---\n\nAfter" in parsed["summary"]
