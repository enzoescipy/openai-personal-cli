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
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings, QWebEngineProfile
from ..features.controllers import MainController
from .workers import APIWorker, ImageGenerationWorker
from .dialogs import ProcessingDialog
from ..utils.text_formatter import TextFormatter
from PyQt6.QtWidgets import QApplication

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
    def __init__(self, controller: MainController):
        super().__init__()
        self.controller = controller
        
        # State tracking
        self.active_workers = []
        self.current_progress_dialog = None
        self.chat_content = ""  # Store chat content
        
        self.init_ui()
        self.setup_shortcuts()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('OpenAI CLI')
        self.setMinimumSize(800, 600)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create chat display with rich text and JavaScript support
        self.chat_display = QWebEngineView()
        self.chat_display.setMinimumSize(200, 200)
        
        # Set up custom page for link handling
        self.web_page = CustomWebEnginePage(self.chat_display)
        self.chat_display.setPage(self.web_page)
        page = self.chat_display.page()
        if page:
            page.setBackgroundColor(Qt.GlobalColor.white)
        
        # Enable JavaScript and local content
        if page:
            settings = page.settings()
            if settings:
                settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        
        layout.addWidget(self.chat_display)
        
        # Initialize with empty content
        self.update_chat_display()

        # Create command input
        self.command_input = QLineEdit()
        self.command_input.setFont(QFont('Consolas', 10))
        self.command_input.setPlaceholderText('Type a command or message...')
        self.command_input.returnPressed.connect(self.handle_command)
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

        # Display welcome message
        self.display_welcome_message()

    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self.clear_chat)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.force_stop)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(
            lambda: self.command_input.setFocus()
        )
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.export_to_pdf)

    def clear_chat(self):
        """Clear chat and reset to welcome message."""
        self.display_welcome_message()
        self.command_input.clear()

    def force_stop(self):
        """Force stop current operations."""
        self._cancel_current_operation()
        self.append_to_chat("\n❌ Operation force stopped!")
        
        # Maintain mode state if in special mode
        # Removed: if self.is_voice_copy_mode or self.is_continuous_voice_mode:
        # Removed:    self.append_to_chat("\n\n⏳ Press ENTER to start recording (or type 'exit' to quit)")

    def handle_command(self):
        """Handle command input."""
        command = self.command_input.text().strip()
        self.command_input.clear()

        if not command:
            # Removed: if self.is_voice_copy_mode:
            # Removed:    self._start_voice_copy()
            # Removed: elif self.is_continuous_voice_mode:
            # Removed:    self._start_voice_chat()
            return

        # Handle mode exits
        if command.lower() == 'exit':
            # Removed: if self.is_voice_copy_mode:
            # Removed:    self._exit_voice_copy_mode()
            # Removed: elif self.is_continuous_voice_mode:
            # Removed:    self._exit_continuous_voice_mode()
            # If not in a special mode, 'exit' does nothing special for now.
            # We might want to add a general exit confirmation later.
            return

        # Add command to display
        self.append_to_chat(f"\nYou: {command}")

        # Handle commands
        if command.startswith('/'):
            self._handle_special_command(command)
        else:
            self._handle_chat_message(command)

    def _handle_special_command(self, command: str):
        """Handle special commands."""
        if command.startswith('/image'):
            self._handle_image_command(command)
        elif command.startswith('/vision'):
            self._handle_vision_command(command)
        elif command == '/quit':
            self.close()
        else:
            self.append_to_chat(f"\nUnknown command: {command}")

    def _handle_chat_message(self, message: str):
        """Handle regular chat message."""
        self._disable_input()
        self.append_to_chat("\n💭 Assistant is thinking...", format_markdown=False)
        
        # Show thinking dialog
        dialog = ProcessingDialog("Assistant is thinking...", self)
        dialog.show()
        QApplication.processEvents()
        
        try:
            # Get response
            response = self.controller.handle_chat_message(message)
            
            if response:
                self.append_to_chat("\n\n" + "─" * 50 + "\n", format_markdown=False)
                self.append_to_chat("🤖 Assistant's Response:\n", format_markdown=False)
                self.append_to_chat("─" * 50 + "\n", format_markdown=False)
                self.append_to_chat(response)  # Format with Markdown and LaTeX
                self.append_to_chat("\n" + "─" * 50 + "\n", format_markdown=False)
        finally:
            dialog.close()
            QApplication.processEvents()
            self._enable_input()

    def _handle_image_command(self, command: str):
        """Handle image generation command."""
        parts = command[6:].strip().split()
        if not parts:
            self.append_to_chat("\nPlease provide an image description")
            return

        self._handle_image_generation(command[6:].strip())

    def _handle_image_generation(self, prompt: str):
        """Handle image generation."""
        # Add the image command to the conversation history for context
        full_command = f"/image {prompt}" if not prompt.startswith("/image") else prompt
        # Store in conversation history
        self.controller.chat_manager.add_message("user", full_command)
        
        # Debug information
        print(f"\n[DEBUG] Adding to conversation: {full_command}")
        print(f"[DEBUG] Conversation length: {len(self.controller.chat_manager.conversation)}")
        
        worker = ImageGenerationWorker(
            self.controller.image_manager,
            prompt,
            self.controller.chat_manager.conversation
        )
        worker.response_ready.connect(self._handle_image_response)
        worker.error_occurred.connect(self._handle_error)
        self._start_worker(worker, "Generating image with DALL-E...")

    def _start_worker(self, worker, loading_message: str):
        """Start a worker thread with optional loading dialog."""
        # Keep reference to prevent garbage collection
        self.active_workers.append(worker)
        
        # For image generation only
        if isinstance(worker, ImageGenerationWorker):
            worker.finished.connect(lambda: self._cleanup_worker(worker))
        
        worker.start()
        
        if loading_message:
            self._show_loading_dialog(loading_message)

    def _cleanup_worker(self, worker):
        """Clean up finished worker."""
        if worker in self.active_workers:
            self.active_workers.remove(worker)
        self._enable_input()
        if self.current_progress_dialog:
            self.current_progress_dialog.close()
            self.current_progress_dialog = None

    def _show_loading_dialog(self, message: str):
        """Show loading dialog."""
        dialog = QProgressDialog(message, "Cancel", 0, 0, self)
        dialog.setWindowTitle("Please Wait")
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(500)
        dialog.canceled.connect(self._cancel_current_operation)
        self.current_progress_dialog = dialog

    def _cancel_current_operation(self):
        """Cancel current operation."""
        for worker in self.active_workers:
            worker.cancel()
        self._enable_input()

    def _handle_error(self, error: str):
        """Handle error."""
        self.append_to_chat(f"\n❌ Error: {error}")
        self._enable_input()

    def _handle_image_response(self, image_url: str):
        """Handle image response."""
        if image_url:
            # Add the image URL to the conversation history
            self.controller.chat_manager.add_message("assistant", f"Image URL: {image_url}")
            
            # Debug information
            print(f"\n[DEBUG] Adding image URL to conversation: {image_url[:30]}...")
            print(f"[DEBUG] Conversation length after image: {len(self.controller.chat_manager.conversation)}")
            
            # Display in chat
            self.append_to_chat("\n" + "─" * 50)  # Add separator before
            self.append_to_chat("\n🖼️ Image generated:\n")
            self.append_to_chat(image_url, is_url=True)
            self.append_to_chat("\n" + "─" * 50 + "\n")  # Add separator after with extra newline

    def _disable_input(self):
        """Disable input."""
        self.command_input.setEnabled(False)
        self.command_input.setPlaceholderText("Please wait...")

    def _enable_input(self):
        """Enable input."""
        self.command_input.setEnabled(True)
        self.command_input.setPlaceholderText("Type a command or message...")

    def append_to_chat(self, text: str, is_url: bool = False, format_markdown: bool = True):
        """Append text to chat display with optional Markdown and LaTeX formatting."""
        if is_url:
            # Format URL
            formatted_text = f'<a href="{text}" style="color: blue; text-decoration: underline;">{text}</a><br><br>'
        else:
            if format_markdown and not text.startswith("\n💭") and not text.startswith("You:"):
                # Format text with Markdown and LaTeX support
                formatted_text = TextFormatter.format_text(text)
            else:
                formatted_text = f"<div>{text}</div>"
        
        # Append to stored content
        if "Welcome to the OpenAI Chat CLI" in self.chat_content:
            # First message after welcome
            self.chat_content = formatted_text
        else:
            if not self.chat_content:
                self.chat_content = formatted_text
            else:
                self.chat_content = self.chat_content.replace('</body></html>', '') + formatted_text + '</body></html>'
        
        # Update display
        self.update_chat_display()

    def update_chat_display(self):
        """Update the chat display with current content."""
        # Add a wrapper div for better scroll control
        wrapped_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    color: black;
                    visibility: visible !important;
                }}
                #chat-content {{
                    visibility: visible !important;
                    opacity: 1 !important;
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
                        processEnvironments: true,
                        skipTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'a']
                    }},
                    "HTML-CSS": {{
                        linebreaks: {{ automatic: true }},
                        styles: {{'.MathJax_Display': {{"margin": "0.8em 0"}}}}
                    }}
                }});
            </script>
            <script>
                // Ensure content is visible before MathJax loads
                document.addEventListener('DOMContentLoaded', function() {{
                    document.body.style.visibility = 'visible';
                    var content = document.getElementById('chat-content');
                    if (content) {{
                        content.style.visibility = 'visible';
                        content.style.opacity = '1';
                    }}
                }});

                // Initialize MathJax and ensure content visibility
                window.MathJax = {{
                    startup: {{
                        pageReady: () => {{
                            document.body.style.visibility = 'visible';
                            var content = document.getElementById('chat-content');
                            if (content) {{
                                content.style.visibility = 'visible';
                                content.style.opacity = '1';
                            }}
                            return MathJax.startup.defaultPageReady();
                        }}
                    }}
                }};
            </script>
        </head>
        <body>
            <div id="chat-content">
                {self.chat_content}
            </div>
            <script>
                // Ensure immediate visibility
                document.body.style.visibility = 'visible';
                var content = document.getElementById('chat-content');
                if (content) {{
                    content.style.visibility = 'visible';
                    content.style.opacity = '1';
                }}

                // Scroll handling
                function scrollToBottom() {{
                    window.scrollTo(0, document.body.scrollHeight);
                }}
                
                // Scroll immediately and after any content changes
                scrollToBottom();
                setTimeout(scrollToBottom, 100);
                window.addEventListener('load', scrollToBottom);
                
                // Create MutationObserver to watch for content changes
                const observer = new MutationObserver(function(mutations) {{
                    scrollToBottom();
                }});
                
                // Start observing content changes
                if (content) {{
                    observer.observe(content, {{
                        childList: true,
                        subtree: true
                    }});
                }}
            </script>
        </body>
        </html>
        '''
        
        self.chat_display.setHtml(wrapped_content)

    def display_welcome_message(self):
        """Display welcome message."""
        welcome_text = (
            "Welcome to the OpenAI Chat CLI!\n\n"
            "Special commands:\n"
            "- /image [description] : Generate an image using DALL-E 3\n"
            "- /vision <url_or_path> [prompt] [--detail=<auto|low|high>] : Analyze an image using GPT-4 Vision\n"
            "  • URL example: /vision https://example.com/image.jpg \"What's in this image?\"\n"
            "  • Local file: /vision local \"Describe this image\" --detail=high\n"
            "    (File picker dialog will open automatically)\n"
            "-"  # DO NOT edit this line
        )
        self.chat_content = f"<pre>{welcome_text}</pre>"
        self.update_chat_display()

    def closeEvent(self, event):
        """Close the application."""
        self._cancel_current_operation()
        self.controller.cleanup() # Ensure controller cleanup is called
        event.accept()

    def _handle_vision_command(self, command: str):
        """Handle vision analysis command."""
        parts = command[7:].strip().split()
        
        # Show usage if no arguments
        if not parts:
            self.append_to_chat("\n사용법: /vision <url_or_path> [prompt] [--detail=<auto|low|high>]")
            return
            
        # Check if first argument is URL or local path
        image_source = parts[0]
        if not image_source.startswith(('http://', 'https://')):
            # For local path, show file dialog
            file_dialog = QFileDialog()
            file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.gif *.webp)")
            if file_dialog.exec():
                image_source = file_dialog.selectedFiles()[0]
            else:
                return
        
        # Parse remaining arguments
        prompt = None
        detail = None
        remaining_args = parts[1:]
        
        for i, arg in enumerate(remaining_args):
            if arg.startswith("--detail="):
                detail_value = arg.split("=")[1].lower()
                if detail_value in ['auto', 'low', 'high']:
                    detail = detail_value
                else:
                    self.append_to_chat("\nError: detail must be one of: auto, low, high")
                    return
            else:
                if not prompt:
                    prompt_parts = []
                    for p in remaining_args[i:]:
                        if not p.startswith("--detail="):
                            prompt_parts.append(p)
                    prompt = " ".join(prompt_parts)
                    break
        
        # Show loading dialog
        self._disable_input()
        dialog = ProcessingDialog("이미지를 분석하는 중...", self)
        dialog.show()
        QApplication.processEvents()
        
        try:
            # Call vision analysis
            result = self.controller.handle_chat_message(f"/vision {image_source}" + 
                                                       (f" {prompt}" if prompt else "") +
                                                       (f" --detail={detail}" if detail else ""))
            
            if result:
                self.append_to_chat("\n\n" + "─" * 50 + "\n", format_markdown=False)
                self.append_to_chat("🔍 이미지 분석 결과:\n", format_markdown=False)
                self.append_to_chat("─" * 50 + "\n", format_markdown=False)
                self.append_to_chat(result)
                self.append_to_chat("\n" + "─" * 50 + "\n", format_markdown=False)
        except Exception as e:
            self.append_to_chat(f"\nError analyzing image: {str(e)}")
        finally:
            dialog.close()
            QApplication.processEvents()
            self._enable_input() 

    def export_to_pdf(self):
        """Export the current chat view to a PDF file."""
        file_name, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")

        if file_name:
            if not file_name.lower().endswith('.pdf'):
                file_name += '.pdf'
            
            # Show processing dialog
            dialog = ProcessingDialog("Exporting to PDF...", self)
            dialog.show()
            QApplication.processEvents()
            
            try:
                # Create page layout
                layout = QPageLayout()
                layout.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
                layout.setOrientation(QPageLayout.Orientation.Portrait)
                
                # Print to PDF using the callback version
                def handle_pdf_data(pdf_data):
                    if pdf_data:
                        try:
                            with open(file_name, 'wb') as f:
                                f.write(pdf_data)
                            self.append_to_chat("\n✨ Chat exported to PDF successfully!")
                        except Exception as e:
                            self.append_to_chat(f"\n❌ Error saving PDF: {str(e)}")
                    else:
                        self.append_to_chat("\n❌ Failed to export chat to PDF")
                    dialog.close()
                
                page = self.chat_display.page()
                if page:
                    page.printToPdf(handle_pdf_data, layout)
                
            except Exception as e:
                self.append_to_chat(f"\n❌ Error exporting to PDF: {str(e)}")
                dialog.close()
            
            QApplication.processEvents() 