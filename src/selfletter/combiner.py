"""
Newsletter combiner - Combines daily summaries into a single newsletter file.
"""

import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List
from collections import defaultdict

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
        
        # Save combined newsletter
        newsletter_path = date_dir / "daily-newsletter.md"
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
        
        # Extract frontmatter
        frontmatter = {}
        summary_content = []
        in_frontmatter = False
        frontmatter_ended = False
        
        for line in lines:
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    in_frontmatter = False
                    frontmatter_ended = True
                    continue
            
            if in_frontmatter:
                # Parse YAML-like frontmatter
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"')
            elif frontmatter_ended:
                summary_content.append(line)
        
        return {
            'title': frontmatter.get('title', 'Untitled'),
            'source_url': frontmatter.get('source_url', ''),
            'type': frontmatter.get('type', 'unknown'),
            'date': frontmatter.get('date', ''),
            'summary': '\n'.join(summary_content).strip(),
        }
    
    def _generate_newsletter(self, date: str, summaries_by_type: Dict[str, List[Dict]]) -> str:
        """Generate the combined newsletter content."""
        lines = []
        
        # Header
        lines.append(f"# Daily Newsletter - {date}")
        lines.append("")
        lines.append(f"*Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*")
        lines.append("")
        
        # Table of contents
        lines.append("## Table of Contents")
        lines.append("")
        total_count = sum(len(summaries) for summaries in summaries_by_type.values())
        lines.append(f"**Total items: {total_count}**")
        lines.append("")
        
        for content_type, summaries in sorted(summaries_by_type.items()):
            lines.append(f"- [{content_type.title()}](#{content_type}) ({len(summaries)} items)")
        lines.append("")
        lines.append("---")
        lines.append("")
        
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
        
        for content_type in sorted_types:
            summaries = summaries_by_type[content_type]
            
            lines.append(f"## {content_type.title()}")
            lines.append("")
            lines.append(f"*{len(summaries)} item(s)*")
            lines.append("")
            
            for i, summary in enumerate(summaries, 1):
                lines.append(f"### {i}. {summary['title']}")
                lines.append("")
                lines.append(f"**Source:** [{summary['source_url']}]({summary['source_url']})")
                lines.append("")
                lines.append(summary['summary'])
                lines.append("")
                lines.append("---")
                lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append(f"*End of newsletter for {date}*")
        
        return '\n'.join(lines)

