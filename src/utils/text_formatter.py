import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.footnotes import FootnoteExtension
from markdown.extensions.attr_list import AttrListExtension
from markdown.extensions.def_list import DefListExtension
from markdown.extensions.abbr import AbbrExtension
from markdown.extensions.admonition import AdmonitionExtension
from markdown.extensions.meta import MetaExtension
from markdown.extensions.sane_lists import SaneListExtension
from markdown.extensions.smarty import SmartyExtension
from markdown.extensions.toc import TocExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from mdx_math import MathExtension
import re
import html

class TextFormatter:
    """Utility class for text formatting with comprehensive Markdown and LaTeX support."""
    
    @staticmethod
    def format_text(text: str) -> str:
        """Convert markdown and LaTeX text to HTML with full feature support.
        Returns ONLY the core HTML content, without CSS or MathJax scripts.
        """
        # Initialize Markdown with comprehensive extensions
        md = markdown.Markdown(extensions=[
            'markdown.extensions.extra',  # Includes tables, attr_list, def_list, fenced_code, footnotes, abbr, md_in_html
            FencedCodeExtension(),
            TableExtension(),
            FootnoteExtension(),
            AttrListExtension(),
            DefListExtension(),
            AbbrExtension(),
            AdmonitionExtension(),
            MetaExtension(),
            SaneListExtension(),
            SmartyExtension(),
            TocExtension(permalink=True),
            CodeHiliteExtension(guess_lang=True),
            MathExtension(enable_dollar_delimiter=True),  # Enable $...$ for inline math
        ])
        
        # Pre-process LaTeX equations to protect them from markdown processing
        text = TextFormatter._protect_latex(text)
        
        # Convert markdown to HTML
        html_content = md.convert(text)
        
        # Post-process protected LaTeX equations
        html_content = TextFormatter._process_latex(html_content)
        
        # REMOVED CSS and MathJax script embedding
        # The surrounding HTML structure (head, body, scripts, styles)
        # should be handled by the component displaying the content (e.g., MainWindow).
        
        return html_content # Return only the core HTML content

    @staticmethod
    def _protect_latex(text: str) -> str:
        """Protect LaTeX equations from markdown processing."""
        # Protect display math
        text = re.sub(
            r'\$\$(.*?)\$\$',
            lambda m: f'<div class="math-display">$${m.group(1)}$$</div>',
            text,
            flags=re.DOTALL
        )
        
        # Protect inline math
        text = re.sub(
            r'\$(.*?)\$',
            lambda m: f'<span class="math-inline">${m.group(1)}$</span>',
            text
        )
        
        return text

    @staticmethod
    def _process_latex(html: str) -> str:
        """Process protected LaTeX equations."""
        # No additional processing needed as MathJax will handle the rendering
        return html

    @staticmethod
    def escape_html(text: str) -> str:
        """Safely escapes HTML special characters."""
        return html.escape(text)

# --- Syntax Highlighter Class (If needed for QSyntaxHighlighter) ---
# This is generally used with QTextEdit/QPlainTextEdit, not QWebEngineView
# Keeping it here for reference if you switch display widgets later

# class PythonHighlighter(QSyntaxHighlighter): # Comment out or remove if not used
#     # ... (implementation for QSyntaxHighlighter)
#     pass 