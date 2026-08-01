"""Tests for the HTML newsletter renderer."""

import pytest
from selfletter.renderer import NewsletterRenderer, render_newsletter


@pytest.fixture
def renderer():
    return NewsletterRenderer(newsletter_name="Test Newsletter")


class TestNewsletterRenderer:
    """Tests for the NewsletterRenderer class."""
    
    def test_init(self, renderer):
        assert renderer.newsletter_name == "Test Newsletter"
    
    def test_render_basic_markdown(self, renderer):
        """Test rendering basic markdown."""
        md = "# Hello World\n\nThis is a test."
        html = renderer.render(md, date="2026-01-15")
        
        assert "<!DOCTYPE html>" in html
        assert "<h1" in html and "Hello World</h1>" in html  # May have id attribute
        assert "<p>This is a test.</p>" in html
        assert "Test Newsletter" in html
        assert "2026-01-15" in html
    
    def test_render_includes_katex(self, renderer):
        """Test that KaTeX is included for LaTeX support."""
        md = "# Math Test"
        html = renderer.render(md)
        
        assert "katex" in html.lower()
        assert "cdn.jsdelivr.net/npm/katex" in html
    
    def test_render_includes_fonts(self, renderer):
        """Test that Google Fonts are included."""
        md = "# Font Test"
        html = renderer.render(md)
        
        assert "fonts.googleapis.com" in html
        assert "Inter" in html
    
    def test_render_tables(self, renderer):
        """Test rendering markdown tables."""
        md = """
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
"""
        html = renderer.render(md)
        
        assert "<table>" in html
        assert "<th>" in html
        assert "<td>" in html
    
    def test_render_code_blocks(self, renderer):
        """Test rendering code blocks."""
        md = """
```python
def hello():
    print("Hello")
```
"""
        html = renderer.render(md)
        
        assert "<code" in html
        assert 'class="k">def</span>' in html
        assert 'class="nf">hello</span>' in html
    
    def test_render_links_external(self, renderer):
        """Test that external links open in new tab."""
        md = "[Link](https://example.com)"
        html = renderer.render(md)
        
        assert 'target="_blank"' in html
        assert 'rel="noopener noreferrer"' in html
    
    def test_preprocess_image_sizing(self, renderer):
        """Test preprocessing of image sizing syntax."""
        md = "![Alt](https://example.com/img.png){width=600px}"
        processed = renderer._preprocess_markdown(md)
        
        assert 'style="max-width: 600px' in processed
        assert 'alt="Alt"' in processed
    
    def test_preprocess_latex_inline(self, renderer):
        """Test preprocessing of inline LaTeX."""
        md = "The formula $E = mc^2$ is famous."
        processed = renderer._preprocess_markdown(md)
        
        assert '<span class="math-inline">$E = mc^2$</span>' in processed
    
    def test_preprocess_latex_display(self, renderer):
        """Test preprocessing of display LaTeX."""
        md = "$$\\int_0^1 x^2 dx$$"
        processed = renderer._preprocess_markdown(md)
        
        assert '<span class="math-display">$$\\int_0^1 x^2 dx$$</span>' in processed
    
    def test_render_responsive_images(self, renderer):
        """Test that images get responsive class."""
        md = "![Test](https://example.com/image.png)"
        html = renderer.render(md)
        
        assert "responsive-img" in html or 'max-width' in html
    
    def test_render_header_structure(self, renderer):
        """Test newsletter header structure."""
        md = "# Content"
        html = renderer.render(md, date="2026-01-15")
        
        assert "newsletter-header" in html
        assert "newsletter-content" in html
        assert "newsletter-footer" in html
    
    def test_render_dark_mode_support(self, renderer):
        """Test that dark mode CSS is included."""
        md = "# Test"
        html = renderer.render(md)
        
        assert "prefers-color-scheme: dark" in html


class TestRenderNewsletterFunction:
    """Tests for the convenience function."""
    
    def test_render_newsletter_function(self):
        """Test the convenience function."""
        md = "# Hello"
        html = render_newsletter(md, date="2026-01-15", newsletter_name="My Newsletter")
        
        assert "<!DOCTYPE html>" in html
        assert "My Newsletter" in html
        assert "2026-01-15" in html
    
    def test_render_newsletter_default_date(self):
        """Test that default date is used when not provided."""
        md = "# Hello"
        html = render_newsletter(md)
        
        # Should contain some date
        assert "<!DOCTYPE html>" in html
