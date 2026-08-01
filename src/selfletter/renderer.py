"""
HTML Newsletter Renderer.
Converts markdown newsletter to stylish HTML with proper rendering of images, LaTeX, and code.
"""

import re
import logging
from typing import Optional
from datetime import datetime

import markdown
from markdown.extensions import codehilite, fenced_code, tables, toc

logger = logging.getLogger(__name__)


class NewsletterRenderer:
    """Renders markdown newsletter to stylish HTML."""
    
    def __init__(self, newsletter_name: str = "Daily AI Papers"):
        self.newsletter_name = newsletter_name
        self.md = markdown.Markdown(
            extensions=[
                'tables',
                'fenced_code',
                'codehilite',
                'toc',
                'nl2br',
                'sane_lists',
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'linenums': False,
                    'guess_lang': True,
                },
                'toc': {
                    'permalink': False,
                },
            }
        )
    
    def render(self, markdown_content: str, date: str = None) -> str:
        """
        Render markdown content to styled HTML newsletter.
        
        Args:
            markdown_content: The markdown content to render
            date: Date string for the newsletter header
        
        Returns:
            Complete HTML document string
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Pre-process markdown for better rendering
        processed_md = self._preprocess_markdown(markdown_content)
        
        # Convert markdown to HTML
        self.md.reset()
        html_body = self.md.convert(processed_md)
        
        # Post-process HTML for images and LaTeX
        html_body = self._postprocess_html(html_body)
        
        # Wrap in full HTML document with styles
        return self._wrap_html(html_body, date)
    
    def _preprocess_markdown(self, content: str) -> str:
        """Pre-process markdown for better rendering."""
        # Fix image sizing syntax (convert {width=Xpx} to HTML)
        content = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)\{width=(\d+)px\}',
            r'<img src="\2" alt="\1" style="max-width: \3px; width: 100%;">',
            content
        )
        
        # Protect LaTeX from markdown processing by wrapping in HTML spans
        # KaTeX auto-render will find these and render them
        # Display math: $$...$$ -> <span class="math-display">$$...$$</span>
        content = re.sub(
            r'\$\$([^$]+)\$\$',
            r'<span class="math-display">$$\1$$</span>',
            content
        )
        # Inline math: $...$ -> <span class="math-inline">$...$</span>
        content = re.sub(
            r'(?<!\$)\$([^$\n]+)\$(?!\$)',
            r'<span class="math-inline">$\1$</span>',
            content
        )
        
        return content
    
    def _postprocess_html(self, html: str) -> str:
        """Post-process HTML for better rendering."""
        # Make all images responsive
        html = re.sub(
            r'<img([^>]*)>',
            lambda m: self._make_image_responsive(m.group(0)),
            html
        )
        
        # Add target="_blank" to external links
        html = re.sub(
            r'<a href="(https?://[^"]+)"',
            r'<a href="\1" target="_blank" rel="noopener noreferrer"',
            html
        )
        
        return html
    
    def _make_image_responsive(self, img_tag: str) -> str:
        """Make an image tag responsive."""
        # If already has style, append to it
        if 'style="' in img_tag:
            return img_tag
        
        # Add responsive styles
        if 'class="' in img_tag:
            return img_tag.replace('class="', 'class="responsive-img ')
        else:
            return img_tag.replace('<img', '<img class="responsive-img"')
    
    def _wrap_html(self, body: str, date: str) -> str:
        """Wrap HTML body in complete document with styles."""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.newsletter_name} - {date}</title>
    
    <!-- KaTeX for LaTeX rendering -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body, {{
            delimiters: [
                {{left: '$$', right: '$$', display: true}},
                {{left: '$', right: '$', display: false}}
            ],
            throwOnError: false
        }});"></script>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --primary-color: #6366f1;
            --primary-dark: #4f46e5;
            --text-color: #1f2937;
            --text-muted: #6b7280;
            --bg-color: #ffffff;
            --bg-secondary: #f9fafb;
            --border-color: #e5e7eb;
            --code-bg: #1e1e1e;
            --success-color: #10b981;
            --warning-color: #f59e0b;
        }}
        
        @media (prefers-color-scheme: dark) {{
            :root {{
                --primary-color: #818cf8;
                --primary-dark: #6366f1;
                --text-color: #f3f4f6;
                --text-muted: #9ca3af;
                --bg-color: #111827;
                --bg-secondary: #1f2937;
                --border-color: #374151;
                --code-bg: #0d1117;
            }}
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.7;
            color: var(--text-color);
            background-color: var(--bg-color);
            font-size: 16px;
            -webkit-font-smoothing: antialiased;
        }}
        
        .newsletter-container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* Header */
        .newsletter-header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
            border-radius: 16px;
            margin-bottom: 40px;
            color: white;
        }}
        
        .newsletter-header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }}
        
        .newsletter-header .date {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .newsletter-header .tagline {{
            font-size: 0.95rem;
            opacity: 0.8;
            margin-top: 12px;
        }}
        
        /* Content */
        .newsletter-content {{
            background: var(--bg-color);
        }}
        
        h1 {{
            font-size: 2rem;
            font-weight: 700;
            margin: 2rem 0 1rem;
            color: var(--text-color);
            letter-spacing: -0.02em;
        }}
        
        h2 {{
            font-size: 1.5rem;
            font-weight: 600;
            margin: 2.5rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--primary-color);
            color: var(--text-color);
        }}
        
        h3 {{
            font-size: 1.25rem;
            font-weight: 600;
            margin: 2rem 0 0.75rem;
            color: var(--text-color);
        }}
        
        h4 {{
            font-size: 1.1rem;
            font-weight: 600;
            margin: 1.5rem 0 0.5rem;
            color: var(--text-color);
        }}
        
        p {{
            margin: 1rem 0;
            color: var(--text-color);
        }}
        
        a {{
            color: var(--primary-color);
            text-decoration: none;
            transition: color 0.2s;
        }}
        
        a:hover {{
            color: var(--primary-dark);
            text-decoration: underline;
        }}
        
        /* Lists */
        ul, ol {{
            margin: 1rem 0;
            padding-left: 1.5rem;
        }}
        
        li {{
            margin: 0.5rem 0;
        }}
        
        li > ul, li > ol {{
            margin: 0.25rem 0;
        }}
        
        /* Images */
        img, .responsive-img {{
            max-width: 100%;
            height: auto;
            border-radius: 12px;
            margin: 1.5rem 0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}
        
        /* Code */
        code {{
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 0.9em;
            background: var(--bg-secondary);
            padding: 0.2em 0.4em;
            border-radius: 4px;
            color: var(--primary-color);
        }}
        
        pre {{
            background: var(--code-bg);
            border-radius: 12px;
            padding: 1.25rem;
            overflow-x: auto;
            margin: 1.5rem 0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        
        pre code {{
            background: none;
            padding: 0;
            color: #e5e7eb;
            font-size: 0.875rem;
            line-height: 1.6;
        }}
        
        /* Code highlighting */
        .highlight {{
            background: var(--code-bg);
            border-radius: 12px;
            padding: 1.25rem;
            overflow-x: auto;
            margin: 1.5rem 0;
        }}
        
        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            font-size: 0.95rem;
        }}
        
        th, td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        
        th {{
            background: var(--bg-secondary);
            font-weight: 600;
            color: var(--text-color);
        }}
        
        tr:hover {{
            background: var(--bg-secondary);
        }}
        
        /* Blockquotes */
        blockquote {{
            border-left: 4px solid var(--primary-color);
            padding: 1rem 1.5rem;
            margin: 1.5rem 0;
            background: var(--bg-secondary);
            border-radius: 0 8px 8px 0;
            color: var(--text-muted);
            font-style: italic;
        }}
        
        blockquote p {{
            margin: 0;
        }}
        
        /* Horizontal rules */
        hr {{
            border: none;
            height: 1px;
            background: var(--border-color);
            margin: 2.5rem 0;
        }}

        /* Collapsible paper cards */
        details.paper-card {{
            transition: border-color 0.2s, box-shadow 0.2s;
        }}

        details.paper-card:hover,
        details.paper-card[open] {{
            border-color: var(--primary-color) !important;
            box-shadow: 0 8px 20px -12px rgba(79, 70, 229, 0.45);
        }}

        details.paper-card > summary {{
            user-select: none;
        }}

        details.paper-card[open] > summary {{
            background: var(--bg-secondary);
        }}

        .paper-card-content > :first-child {{
            margin-top: 1rem;
        }}

        .paper-card-content h3,
        .paper-card-content h4,
        .paper-card-content h5,
        .paper-card-content h6 {{
            line-height: 1.4;
        }}
        
        /* Math display */
        .math-display {{
            display: block;
            text-align: center;
            margin: 1.5rem 0;
            overflow-x: auto;
        }}
        
        .math-inline {{
            display: inline;
        }}
        
        /* Footer */
        .newsletter-footer {{
            text-align: center;
            padding: 40px 20px;
            margin-top: 40px;
            border-top: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        
        .newsletter-footer p {{
            margin: 0.5rem 0;
        }}
        
        /* LaTeX/KaTeX styling */
        .katex {{
            font-size: 1.1em;
        }}
        
        .katex-display {{
            margin: 1.5rem 0;
            overflow-x: auto;
            overflow-y: hidden;
        }}
        
        /* Responsive */
        @media (max-width: 640px) {{
            .newsletter-container {{
                padding: 12px;
            }}
            
            .newsletter-header {{
                padding: 30px 16px;
                border-radius: 12px;
            }}
            
            .newsletter-header h1 {{
                font-size: 1.75rem;
            }}
            
            h1 {{
                font-size: 1.5rem;
            }}
            
            h2 {{
                font-size: 1.25rem;
            }}
            
            h3 {{
                font-size: 1.1rem;
            }}
            
            pre {{
                padding: 1rem;
                font-size: 0.8rem;
            }}
            
            table {{
                font-size: 0.85rem;
            }}
            
            th, td {{
                padding: 0.5rem;
            }}
        }}
        
        /* Print styles */
        @media print {{
            .newsletter-header {{
                background: var(--primary-color) !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            
            a {{
                color: var(--primary-color);
            }}
            
            pre, code {{
                white-space: pre-wrap;
                word-wrap: break-word;
            }}
        }}
    </style>
</head>
<body>
    <div class="newsletter-container">
        <header class="newsletter-header">
            <h1>📚 {self.newsletter_name}</h1>
            <div class="date">{date}</div>
            <div class="tagline">Your daily digest of top AI research papers</div>
        </header>
        
        <main class="newsletter-content">
            {body}
        </main>
        
        <footer class="newsletter-footer">
            <p>Generated by <strong>SelfLetter</strong></p>
            <p>Powered by HuggingFace Daily Papers</p>
        </footer>
    </div>
</body>
</html>'''


def render_newsletter(markdown_content: str, date: str = None, newsletter_name: str = "Daily AI Papers") -> str:
    """
    Convenience function to render markdown to HTML newsletter.
    
    Args:
        markdown_content: The markdown content to render
        date: Date string for the newsletter header
        newsletter_name: Name of the newsletter
    
    Returns:
        Complete HTML document string
    """
    renderer = NewsletterRenderer(newsletter_name=newsletter_name)
    return renderer.render(markdown_content, date)
