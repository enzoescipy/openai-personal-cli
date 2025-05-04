from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, 
    QTextBrowser, QLineEdit, QLabel,
    QProgressDialog, QFileDialog
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import (
    QFont, QTextCursor, QKeySequence, 
    QShortcut, QDesktopServices, QTextCharFormat,
    QPageLayout, QPageSize
)
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings, QWebEngineProfile, QWebEngineScript
from ..features.controllers import MainController
from .workers import APIWorker, ImageGenerationWorker
from .dialogs import ProcessingDialog
from ..utils.text_formatter import TextFormatter
from PyQt6.QtWidgets import QApplication
from .gui_handler import GuiHandler
import json # Import json for JS escaping

class CustomWebEnginePage(QWebEnginePage):
    """Custom WebEnginePage to handle link clicks."""
    def __init__(self, parent=None):
        super().__init__(parent)
        # No need for setLinkDelegationPolicy in PyQt6
        # Instead, we override acceptNavigationRequest

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        """Handle navigation requests."""
        # Open links in default browser
        if _type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, _type, isMainFrame)

class MainWindow(QMainWindow):
    """Main window of the application."""
    # BASE_HTML template containing CSS, JS, and the chat body container
    BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        /* General text styling */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #24292e;
            margin: 15px; /* Add some margin */
            background-color: white;
        }
        /* Math display styling */
        .math-display { text-align: center; margin: 1.2em 0; padding: 1em; overflow-x: auto; }
        .math-inline { display: inline-block; vertical-align: middle; margin: 0 0.2em; }
        /* Code block styling */
        pre { background-color: #f6f8fa; border-radius: 6px; padding: 16px; overflow: auto; font-size: 85%; line-height: 1.45; border: 1px solid #e1e4e8; }
        code { font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; background-color: rgba(27, 31, 35, 0.05); padding: 0.2em 0.4em; border-radius: 3px; font-size: 85%; }
        /* Table styling */
        table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        th, td { border: 1px solid #e1e4e8; padding: 6px 13px; }
        th { background-color: #f6f8fa; font-weight: 600; }
        tr:nth-child(2n) { background-color: #f8f9fa; }
        /* Blockquote styling */
        blockquote { margin: 1em 0; padding: 0 1em; color: #6a737d; border-left: 0.25em solid #dfe2e5; }
        /* List styling */
        ul, ol { padding-left: 2em; }
        li { margin: 0.25em 0; }
        /* Heading styling */
        h1, h2, h3, h4, h5, h6 { margin-top: 24px; margin-bottom: 16px; font-weight: 600; line-height: 1.25; }
        h1 { font-size: 2em; padding-bottom: 0.3em; border-bottom: 1px solid #eaecef; }
        h2 { font-size: 1.5em; padding-bottom: 0.3em; border-bottom: 1px solid #eaecef; }
        /* Admonition styling */
        .admonition { padding: 1em; margin: 1em 0; border-left: 4px solid #2196F3; background-color: #E3F2FD; }
        .admonition-title { font-weight: bold; margin-bottom: 0.5em; }
        /* Other styles as needed */
        hr { border: none; height: 1px; background-color: #e1e4e8; margin: 15px 0; } /* Consistent HR */
    </style>
    <!-- MathJax Configuration -->
    <script type="text/javascript" async
        src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-MML-AM_CHTML">
    </script>
    <script type="text/x-mathjax-config">
        MathJax.Hub.Config({
            tex2jax: {
                inlineMath: [['$','$']],
                displayMath: [['$$','$$']],
                processEscapes: true,
                processEnvironments: true,
                skipTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'a']
            },
            "HTML-CSS": {
                linebreaks: { automatic: true },
                styles: {'.MathJax_Display': {"margin": "0.8em 0"}}
            },
            showProcessingMessages: false, // Hide MathJax processing messages
            messageStyle: "none" // Hide MathJax status messages
        });
    </script>
</head>
<body>
    <div id="chat-body">
        <!-- Chat content will be appended here -->
    </div>
    <script>
        // Initial scroll to bottom just in case
        window.scrollTo(0, document.body.scrollHeight);
    </script>
</body>
</html>
"""

    def __init__(self, controller: MainController):
        super().__init__()
        self.controller = controller
        self._current_progress_dialog = None # Keep track of the dialog
        # self.chat_content = "" # REMOVED - Content managed by JS in QWebEngineView

        self.gui_handler = GuiHandler(self, self.controller)

        self.init_ui()
        self.setup_shortcuts()

        # Connect GuiHandler signals to MainWindow slots
        self.gui_handler.set_input_enabled.connect(self._set_input_enabled)
        self.gui_handler.show_thinking_indicator.connect(self._show_thinking_indicator)
        # self.gui_handler.append_to_chat_signal.connect(self.append_to_chat) # REMOVED
        self.gui_handler.append_html_fragment_signal.connect(self._append_html_fragment) # Connect NEW signal

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('OpenAI CLI')
        self.setMinimumSize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.chat_display = QWebEngineView()
        self.chat_display.setMinimumSize(200, 200)

        self.web_page = CustomWebEnginePage(self.chat_display)
        self.chat_display.setPage(self.web_page)

        # Configure page settings
        page = self.chat_display.page()
        if page:
            page.setBackgroundColor(Qt.GlobalColor.white)
            settings = page.settings()
            if settings:
                settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True) # Enable smooth scrolling

        layout.addWidget(self.chat_display)

        # Set the base HTML structure
        # Using a base URL is good practice, even if local for now
        self.chat_display.setHtml(self.BASE_HTML, QUrl("file://"))

        # Create command input
        self.command_input = QLineEdit()
        self.command_input.setFont(QFont('Consolas', 10))
        self.command_input.setPlaceholderText('Type a command or message...')
        self.command_input.returnPressed.connect(self.gui_handler.handle_command)
        layout.addWidget(self.command_input)

        # Create shortcuts guide
        shortcuts_label = QLabel(
            "Shortcuts: "
            "Enter - Send message | "
            "Ctrl+L - Clear chat | "
            "ESC - Force stop | "
            "Ctrl+Q - Quit | "
            "Ctrl+I - Focus input | "
            "Ctrl+C - Copy selection | "
            "Ctrl+E - Export to PDF"
        )
        shortcuts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(shortcuts_label)

        # Display welcome message AFTER base HTML is loaded and JS is ready
        # Use a timer to ensure the page is ready
        # QTimer.singleShot(500, self.display_welcome_message)
        # Alternatively, connect to loadFinished signal
        if page:
             page.loadFinished.connect(self._on_page_load_finished)

    def _on_page_load_finished(self, ok):
        """Called when the base HTML page finishes loading."""
        if ok:
            # print("[DEBUG] Base HTML loaded successfully.")
            self.display_welcome_message()
        else:
            print("[ERROR] Failed to load base HTML for chat display.")
            # Optionally display an error message in a fallback way

    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self.clear_chat)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.force_stop)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(
            lambda: self.command_input.setFocus()
        )
        # Connect Ctrl+E to trigger the handler's PDF export request signal
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.gui_handler.export_pdf_requested.emit)

    def clear_chat(self):
        """Clear chat and reset to welcome message."""
        self.display_welcome_message() # display_welcome_message now handles clearing
        self.command_input.clear()

    def force_stop(self):
        """Force stop current operations by signaling the GuiHandler."""
        # If the thinking dialog is active when ESC is pressed globally,
        # ignore the shortcut here. Let the dialog's Cancel button trigger the stop.
        if self._current_progress_dialog and self._current_progress_dialog.isVisible():
             print("[DEBUG] force_stop called while dialog visible, likely ESC. Ignoring.")
             return

        print("[DEBUG] force_stop proceeding (dialog not visible or cancelled via button).")
        self.gui_handler.cancel_all_workers() # Ask handler to cancel
        # Use the new mechanism to append the stop message
        self._append_html_fragment("<div>❌ Operation force stopped!</div><br>")

        # Maintain mode state if in special mode - REMOVED (voice modes gone)

    # --- Command Handling Methods REMOVED ---
    # handle_command
    # _handle_special_command
    # _handle_chat_message
    # _handle_image_command
    # _handle_vision_command
    # _handle_image_generation

    # --- Worker/Dialog/State Management Methods REMOVED ---
    # _start_worker
    # _cleanup_worker
    # _show_loading_dialog
    # _cancel_current_operation
    # _handle_error
    # _handle_image_response
    # _disable_input
    # _enable_input

    # --- Slots for GuiHandler Signals ---

    def _set_input_enabled(self, enabled: bool):
        """Slot to enable/disable the command input."""
        self.command_input.setEnabled(enabled)
        if enabled:
            self.command_input.setPlaceholderText('Type a command or message...')
            self.command_input.setFocus() # Focus when enabled
        else:
            self.command_input.setPlaceholderText('Processing...')

    def _show_thinking_indicator(self, show: bool, message: str):
        """Slot to show/hide the thinking indicator (progress dialog)."""
        if show:
            if not self._current_progress_dialog: # Create dialog if it doesn't exist
                # Use the message provided by the handler
                self._current_progress_dialog = ProcessingDialog(message, self)
                # Connect the dialog's custom user_cancelled signal to force_stop
                self._current_progress_dialog.user_cancelled.connect(self.force_stop) # NEW connection
                self._current_progress_dialog.show()
            else: # Update message if dialog already exists
                self._current_progress_dialog.setLabelText(message)
                if not self._current_progress_dialog.isVisible():
                    self._current_progress_dialog.show() # Ensure visible
        else:
            if self._current_progress_dialog:
                self._current_progress_dialog.close()
                self._current_progress_dialog = None # Release reference 

    def _append_html_fragment(self, html_fragment: str):
        """Appends an HTML fragment to the chat display using direct JavaScript execution."""
        page = self.chat_display.page()
        if page:
            # Escape the HTML fragment for safe insertion into a JS string literal
            js_escaped_fragment = json.dumps(html_fragment)
            # Directly execute JS to append, typeset MathJax, and scroll, wrapped in IIFE
            # Use {{ and }} for literal JS curly braces within the Python f-string
            js_code = f"""
(function() {{ // Start IIFE
    let chatBody = document.getElementById('chat-body');
    if (chatBody) {{
        chatBody.innerHTML += {js_escaped_fragment}; // Python inserts variable here
        // Queue MathJax processing
        if (typeof MathJax !== 'undefined' && MathJax.Hub) {{
            MathJax.Hub.Queue(["Typeset", MathJax.Hub, chatBody]);
        }}
        // Scroll to bottom after a short delay
        setTimeout(() => {{ window.scrollTo(0, document.body.scrollHeight); }}, 100);
    }} else {{
        console.error('Chat body element not found when trying to append.');
    }}
}})(); // End IIFE
"""
            page.runJavaScript(js_code)

    # --- Chat Display Methods ---
    # append_to_chat REMOVED
    # update_chat_display REMOVED

    def display_welcome_message(self):
        """Clear the chat area and display the welcome message."""
        welcome_text = (
            "Welcome to the OpenAI Chat CLI!\n\n"
            "Special commands:\n"
            "- /image [description] : Generate an image using DALL-E 3\n"
            "- /vision <url_or_path> [prompt] [--detail=<auto|low|high>] : Analyze an image using GPT-4 Vision\n"
            "  • URL example: /vision https://example.com/image.jpg \"What's in this image?\"\n"
            "  • Local file: /vision local \"Describe this image\" --detail=high\n"
            "    (File picker dialog will open automatically)\n"
        )
        # Format as simple preformatted text within a div
        welcome_html = f"<div><pre>{TextFormatter.escape_html(welcome_text)}</pre></div>"

        page = self.chat_display.page()
        if page:
            # Clear existing content using direct JS execution wrapped in IIFE
            # No f-string needed here, use a regular string
            page.runJavaScript(
                "(function() {" # Start IIFE
                "    let chatBody = document.getElementById('chat-body'); "
                "    if (chatBody) { chatBody.innerHTML = ''; } else { console.error('Chat body not found for clearing.'); }"
                "})();" # End IIFE and immediately invoke
            )
            # Append the welcome message using the standard mechanism
            self._append_html_fragment(welcome_html)
    def closeEvent(self, event):
        """Handle window close event."""
        # Worker cancellation should be handled via user actions (ESC) or GuiHandler if needed upon close
        self.controller.cleanup() # Ensure controller cleanup is called
        event.accept()

    # export_to_pdf - Needs review and reimplementation based on current structure.
    # For now, it remains removed.