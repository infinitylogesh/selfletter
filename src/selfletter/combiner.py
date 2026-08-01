"""
Newsletter combiner - Combines daily summaries into a single newsletter file.
"""

import logging
import html
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

import markdown

logger = logging.getLogger(__name__)


class NewsletterCombiner:
    """Combines individual summaries into a daily newsletter."""
    
    def __init__(self, output_dir: str = "newsletter"):
        self.output_dir = Path(output_dir)
    
    def combine_daily_summaries(self, date: str = None) -> str:
        """
        Combine all summaries for a given date into a single newsletter.
        
        Args:
            date: Date string in YYYY-MM-DD format. If None, uses today.
        
        Returns:
            Path to the combined newsletter file.
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        date_dir = self.output_dir / date

        # check if newsletter .md file exists
        newsletter_path = date_dir / "daily-newsletter.md"
        if newsletter_path.exists():
            logger.info(f"Newsletter already exists for {date}")
            return str(newsletter_path)
        
        if not date_dir.exists():
            logger.warning(f"No summaries found for date: {date}")
            return None
        
        # Collect all markdown files grouped by type
        summaries_by_type = self._collect_summaries(date_dir)
        
        if not summaries_by_type:
            logger.warning(f"No summaries to combine for date: {date}")
            return None
        
        # Generate combined newsletter
        newsletter_content = self._generate_newsletter(date, summaries_by_type)

        newsletter_path.write_text(newsletter_content)
        
        logger.info(f"Combined newsletter saved to: {newsletter_path}")
        return str(newsletter_path)
    
    def _collect_summaries(self, date_dir: Path) -> Dict[str, List[Dict]]:
        """Collect all summaries grouped by content type."""
        summaries_by_type = defaultdict(list)
        
        # Iterate through all subdirectories (types)
        for type_dir in date_dir.iterdir():
            if not type_dir.is_dir():
                continue
            
            content_type = type_dir.name
            
            # Read all markdown files in this type directory
            for md_file in type_dir.glob("*.md"):
                try:
                    content = md_file.read_text()
                    
                    # Parse frontmatter and content
                    summary_data = self._parse_summary_file(content)
                    summary_data['filename'] = md_file.name
                    
                    summaries_by_type[content_type].append(summary_data)
                    
                except Exception as e:
                    logger.error(f"Error reading summary file {md_file}: {e}")
        
        return summaries_by_type
    
    def _parse_summary_file(self, content: str) -> Dict:
        """Parse a summary markdown file with frontmatter."""
        lines = content.split('\n')

        # Extract only the leading frontmatter block. Horizontal rules inside
        # a generated summary must remain part of the summary.
        frontmatter = {}
        summary_start = 0
        if lines and lines[0].strip() == '---':
            for index, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    summary_start = index + 1
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"')

        summary_content = lines[summary_start:]
        
        return {
            'title': frontmatter.get('title', 'Untitled'),
            'source_url': frontmatter.get('source_url', ''),
            'type': frontmatter.get('type', 'unknown'),
            'date': frontmatter.get('date', ''),
            'summary': '\n'.join(summary_content).strip(),
        }

    @staticmethod
    def _clean_summary(summary: str) -> str:
        """Normalize common model formatting mistakes before rendering."""
        summary = summary.strip()
        lines = summary.splitlines()

        # Models occasionally wrap the entire response in a markdown fence,
        # which otherwise makes the newsletter display as one large code block.
        opening_index = next(
            (
                index
                for index, line in enumerate(lines)
                if re.fullmatch(r"```(?:markdown|md)\s*", line, re.IGNORECASE)
            ),
            None,
        )
        if opening_index is not None:
            closing_indexes = [
                index
                for index, line in enumerate(lines[opening_index + 1:], opening_index + 1)
                if line.strip() == "```"
            ]
            if closing_indexes and not any(
                line.strip() for line in lines[closing_indexes[-1] + 1:]
            ):
                summary = "\n".join(
                    lines[opening_index + 1:closing_indexes[-1]]
                ).strip()
            else:
                # An unmatched outer marker should not leak into the issue.
                summary = "\n".join(
                    lines[:opening_index] + lines[opening_index + 1:]
                ).strip()

        # Paper cards already provide the main title. Keep headings inside each
        # card visually subordinate to it.
        summary = re.sub(
            r"^(#{1,6})(\s+)",
            lambda match: f"{'#' * min(len(match.group(1)) + 2, 6)}{match.group(2)}",
            summary,
            flags=re.MULTILINE,
        )
        return summary

    @classmethod
    def _render_summary_html(cls, summary: str) -> str:
        """Render a paper summary as an embeddable HTML fragment."""
        return markdown.markdown(
            cls._clean_summary(summary),
            extensions=[
                'tables',
                'fenced_code',
                'codehilite',
                'nl2br',
                'sane_lists',
            ],
        )

    @classmethod
    def _render_paper_card(cls, index: int, summary: Dict) -> str:
        """Build a collapsed, email-friendly paper card."""
        title = html.escape(summary['title'])
        source_url = html.escape(summary['source_url'], quote=True)
        content_type = html.escape(summary['type'].replace('-', ' ').title())
        body = cls._render_summary_html(summary['summary'])

        return f'''<details class="paper-card" style="border: 1px solid #e5e7eb; border-radius: 12px; margin: 0 0 16px; overflow: hidden; background: #ffffff;">
<summary style="cursor: pointer; padding: 18px 20px; font-size: 17px; line-height: 1.45; color: #111827;">
<span style="display: inline-block; min-width: 32px; margin-right: 8px; color: #6366f1; font-weight: 700;">{index:02d}</span><strong>{title}</strong><br>
<span style="display: inline-block; margin: 6px 0 0 40px; color: #6b7280; font-size: 13px;">Expand for the full analysis</span>
</summary>
<div class="paper-card-content" style="padding: 4px 20px 22px; border-top: 1px solid #e5e7eb; color: #1f2937;">
<p style="margin: 16px 0 20px;"><span style="display: inline-block; margin-right: 8px; padding: 3px 8px; border-radius: 999px; background: #eef2ff; color: #4338ca; font-size: 11px; font-weight: 700; letter-spacing: .04em;">{content_type}</span><a href="{source_url}" style="color: #4f46e5; font-weight: 600;">Read the original paper &#8599;</a></p>
{body}
</div>
</details>'''
    
    def _generate_newsletter(self, date: str, summaries_by_type: Dict[str, List[Dict]]) -> str:
        """Generate the combined newsletter content."""
        total_count = sum(len(summaries) for summaries in summaries_by_type.values())
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            display_date = f"{parsed_date.strftime('%B')} {parsed_date.day}, {parsed_date.year}"
        except ValueError:
            display_date = date

        # Keep Buttondown in Markdown mode so custom HTML such as <details>
        # remains intact instead of being converted by the rich-text editor.
        lines = [
            "<!-- buttondown-editor-mode: plaintext -->",
            "",
            '<div class="issue-intro" style="margin: 0 0 28px; padding: 24px; border-radius: 16px; background: #f5f3ff; border: 1px solid #ddd6fe;">',
            '<p style="margin: 0 0 8px; color: #6d28d9; font-size: 12px; font-weight: 700; letter-spacing: .1em;">DAILY AI PAPERS</p>',
            f'<h1 style="margin: 0 0 10px; color: #111827; font-size: 28px; line-height: 1.2;">{html.escape(display_date)}</h1>',
            f'<p style="margin: 0; color: #4b5563;">{total_count} research papers, distilled into practical takeaways. Select any paper to expand its full analysis.</p>',
            "</div>",
            "",
            '<h2 style="margin: 0 0 16px; color: #111827; font-size: 21px;">Today\'s papers</h2>',
            "",
        ]
        
        # Content sections by type
        type_order = ['arxiv', 'huggingface', 'youtube', 'article']
        
        # Sort types: known types first in order, then alphabetically
        sorted_types = []
        for t in type_order:
            if t in summaries_by_type:
                sorted_types.append(t)
        
        for t in sorted(summaries_by_type.keys()):
            if t not in sorted_types:
                sorted_types.append(t)
        
        paper_number = 1
        for content_type in sorted_types:
            for summary in summaries_by_type[content_type]:
                lines.append(self._render_paper_card(paper_number, summary))
                lines.append("")
                paper_number += 1
        
        # Footer
        lines.extend([
            '<p style="margin: 28px 0 0; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 13px; text-align: center;">That\'s today\'s research briefing. Reply with the paper you found most useful.</p>',
            "",
        ])
        
        return '\n'.join(lines)
