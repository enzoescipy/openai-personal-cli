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

class TextFormatter:
    """Utility class for text formatting with comprehensive Markdown and LaTeX support."""
    
    @staticmethod
    def format_text(text: str) -> str:
        """Convert markdown and LaTeX text to HTML with full feature support."""
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
        html = md.convert(text)
        
        # Post-process protected LaTeX equations
        html = TextFormatter._process_latex(html)
        
        # Add CSS for enhanced styling and MathJax configuration
        html = f'''
        <style>
            /* General text styling */
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #24292e;
            }}
            
            /* Math display styling */
            .math-display {{
                text-align: center;
                margin: 1.2em 0;
                padding: 1em;
                overflow-x: auto;
            }}
            .math-inline {{
                display: inline-block;
                vertical-align: middle;
                margin: 0 0.2em;
            }}
            
            /* Code block styling */
            pre {{
                background-color: #f6f8fa;
                border-radius: 6px;
                padding: 16px;
                overflow: auto;
                font-size: 85%;
                line-height: 1.45;
                border: 1px solid #e1e4e8;
            }}
            code {{
                font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
                background-color: rgba(27, 31, 35, 0.05);
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-size: 85%;
            }}
            
            /* Table styling */
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
            }}
            th, td {{
                border: 1px solid #e1e4e8;
                padding: 6px 13px;
            }}
            th {{
                background-color: #f6f8fa;
                font-weight: 600;
            }}
            tr:nth-child(2n) {{
                background-color: #f8f9fa;
            }}
            
            /* Blockquote styling */
            blockquote {{
                margin: 1em 0;
                padding: 0 1em;
                color: #6a737d;
                border-left: 0.25em solid #dfe2e5;
            }}
            
            /* List styling */
            ul, ol {{
                padding-left: 2em;
            }}
            li {{
                margin: 0.25em 0;
            }}
            
            /* Heading styling */
            h1, h2, h3, h4, h5, h6 {{
                margin-top: 24px;
                margin-bottom: 16px;
                font-weight: 600;
                line-height: 1.25;
            }}
            h1 {{ font-size: 2em; padding-bottom: 0.3em; border-bottom: 1px solid #eaecef; }}
            h2 {{ font-size: 1.5em; padding-bottom: 0.3em; border-bottom: 1px solid #eaecef; }}
            
            /* Admonition styling */
            .admonition {{
                padding: 1em;
                margin: 1em 0;
                border-left: 4px solid #2196F3;
                background-color: #E3F2FD;
            }}
            .admonition-title {{
                font-weight: bold;
                margin-bottom: 0.5em;
            }}
            
            /* Footnote styling */
            .footnote {{
                font-size: 0.8em;
                color: #6a737d;
            }}
            .footnote-ref {{
                text-decoration: none;
                font-weight: bold;
            }}
            
            /* TOC styling */
            .toc {{
                background-color: #f8f9fa;
                padding: 1em;
                border-radius: 4px;
                margin: 1em 0;
            }}
            .toc-title {{
                font-weight: bold;
                margin-bottom: 0.5em;
            }}
        </style>
        
        <!-- MathJax Configuration -->
        <script type="text/javascript" async
            src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-MML-AM_CHTML">
        </script>
        <script type="text/x-mathjax-config">
            MathJax.Hub.Config({{
                tex2jax: {{
                    inlineMath: [['$','$']],
                    displayMath: [['$$','$$']],
                    processEscapes: true,
                    processEnvironments: true
                }},
                displayAlign: "center",
                "HTML-CSS": {{
                    styles: {{'.MathJax_Display': {{"margin": "0.8em 0"}}}}
                }}
            }});
        </script>
        
        {html}
        '''
        
        return html

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