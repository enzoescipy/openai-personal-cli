from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, 
    QTextBrowser, QLineEdit, QLabel,
    QProgressDialog
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import (
    QFont, QTextCursor, QKeySequence, 
    QShortcut, QDesktopServices, QTextCharFormat
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from ..features.controllers import MainController
from .workers import APIWorker, ImageGenerationWorker
from .dialogs import RecordingDialog, ProcessingDialog
from ..utils.text_formatter import TextFormatter
from PyQt6.QtWidgets import QApplication

class MainWindow(QMainWindow):
    """Main window of the application."""
    def __init__(self, controller: MainController):
        super().__init__()
        self.controller = controller
        
        # State tracking
        self.is_voice_copy_mode = False
        self.is_continuous_voice_mode = False
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
        self.chat_display.page().setBackgroundColor(Qt.GlobalColor.white)
        
        # Enable JavaScript and local content
        settings = self.chat_display.page().settings()
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
            "Ctrl+C - Copy selection"
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

    def clear_chat(self):
        """Clear chat and reset to welcome message."""
        self.display_welcome_message()
        self.command_input.clear()

    def force_stop(self):
        """Force stop current operations."""
        self._cancel_current_operation()
        self.append_to_chat("\n❌ Operation force stopped!")
        
        # Maintain mode state if in special mode
        if self.is_voice_copy_mode or self.is_continuous_voice_mode:
            self.append_to_chat("\n\n⏳ Press ENTER to start recording (or type 'exit' to quit)")

    def handle_command(self):
        """Handle command input."""
        command = self.command_input.text().strip()
        self.command_input.clear()

        if not command:
            if self.is_voice_copy_mode:
                self._start_voice_copy()
            elif self.is_continuous_voice_mode:
                self._start_voice_chat()
            return

        # Handle mode exits
        if command.lower() == 'exit':
            if self.is_voice_copy_mode:
                self._exit_voice_copy_mode()
            elif self.is_continuous_voice_mode:
                self._exit_continuous_voice_mode()
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
        elif command.startswith('/voice'):
            self._handle_voice_command(command)
        elif command == '/cpyvoice':
            self._enter_voice_copy_mode()
        elif command == '/quit':
            self.close()

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

        if parts[0] in ['--with_voice', '-v']:
            # Use blocking voice recording approach
            self._disable_input()
            transcription = self.controller.voice_manager.record_and_transcribe_with_dialog(self)
            
            if transcription:
                # Show the transcription
                self.append_to_chat("\n" + "─" * 50)
                self.append_to_chat(f"\n📝 Voice description: {transcription}")
                self.append_to_chat("\n" + "─" * 50 + "\n")
                
                # Combine with any additional text
                image_prompt = transcription
                if len(parts) > 1:
                    additional_text = ' '.join(parts[1:])
                    image_prompt += f" {additional_text}"
                    self.append_to_chat(f"Additional text: {additional_text}\n")
                
                # Generate image
                self._handle_image_generation(image_prompt)
            else:
                self.append_to_chat("\n❌ Voice input cancelled or failed")
                self._enable_input()
        else:
            self._handle_image_generation(command[6:].strip())

    def _handle_voice_command(self, command: str):
        """Handle voice command."""
        if command in ['/voice --continuous', '/voice -c']:
            self._enter_continuous_voice_mode()
        else:
            self._handle_voice_recording()

    def _handle_voice_recording(self):
        """Handle single voice recording and transcription."""
        self._disable_input()
        
        # Record and transcribe
        transcription = self.controller.voice_manager.record_and_transcribe_with_dialog(self)
        
        if transcription:
            # Show the transcription
            self.append_to_chat("\n" + "─" * 50)
            self.append_to_chat(f"\n📝 Your voice input: {transcription}")
            self.append_to_chat("\n" + "─" * 50 + "\n")
            
            # Process as chat message
            self._handle_chat_message(transcription)
        else:
            self.append_to_chat("\n❌ Voice input cancelled or failed")
            self._enable_input()

    def _handle_image_generation(self, prompt: str):
        """Handle image generation."""
        worker = ImageGenerationWorker(
            self.controller.image_manager,
            prompt,
            self.controller.chat_manager.conversation
        )
        worker.response_ready.connect(self._handle_image_response)
        worker.error_occurred.connect(self._handle_error)
        self._start_worker(worker, "Generating image with DALL-E...")

    def _start_worker(self, worker, loading_message: str = None):
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
        self.controller.force_stop()
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
            self.append_to_chat("\n" + "─" * 50)  # Add separator before
            self.append_to_chat("\n🖼️ Image generated:\n")
            self.append_to_chat(image_url, is_url=True)
            self.append_to_chat("\n" + "─" * 50 + "\n")  # Add separator after with extra newline

    def _handle_transcription_response(self, transcription: str):
        """Handle transcription response."""
        print(f"\n[DEBUG] Received transcription response: {transcription}")
        if transcription:
            # Clear any previous status messages
            self.append_to_chat("\n" + "─" * 50)
            self.append_to_chat(f"\n📝 Your voice input: {transcription}")
            self.append_to_chat("\n" + "─" * 50 + "\n")
            print("[DEBUG] About to handle chat message with transcription")
            # Process the transcribed text as a chat message
            self._handle_chat_message(transcription)
        else:
            self.append_to_chat("\n❌ Voice input cancelled or failed")
            self._enable_input()

    def _disable_input(self):
        """Disable input."""
        self.command_input.setEnabled(False)
        self.command_input.setPlaceholderText("Please wait...")

    def _enable_input(self):
        """Enable input."""
        self.command_input.setEnabled(True)
        if self.is_voice_copy_mode:
            self.command_input.setPlaceholderText("Press ENTER to record, type 'exit' to quit")
        elif self.is_continuous_voice_mode:
            self.command_input.setPlaceholderText("Press ENTER to record, type 'exit' to quit")
        else:
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
            "- /image --with_voice (-v) : Generate an image using voice input\n"
            "- /voice : Record and transcribe voice input\n"
            "- /voice --continuous (-c) : Enter continuous voice chat mode\n"
            "- /cpyvoice : Enter the rapid voice copying mode\n"
            "-"  # DO NOT edit this line
        )
        self.chat_content = f"<pre>{welcome_text}</pre>"
        self.update_chat_display()

    def closeEvent(self, event):
        """Handle application shutdown."""
        self.controller.cleanup()
        for worker in self.active_workers:
            worker.cancel()
            worker.wait()
        super().closeEvent(event)

    def _enter_continuous_voice_mode(self):
        """Enter continuous voice chat mode."""
        self.is_continuous_voice_mode = True
        self.append_to_chat("\n🎤 Welcome to continuous voice chat mode!")
        self.append_to_chat("\nHave a continuous conversation with the AI using your voice.")
        self.append_to_chat("\nInstructions:")
        self.append_to_chat("\n- Press ENTER to start recording your message")
        self.append_to_chat("\n- Press SPACEBAR to stop recording")
        self.append_to_chat("\n- Press ESC to force-stop current recording")
        self.append_to_chat("\n- Type 'exit' to quit this mode")
        self.append_to_chat("\n\n⏳ Press ENTER to start recording (or type 'exit' to quit)")
        self.command_input.setPlaceholderText("Press ENTER to record, type 'exit' to quit")
        self.command_input.setFocus()
        QApplication.processEvents()  # Ensure focus is applied

    def _exit_continuous_voice_mode(self):
        """Exit continuous voice chat mode."""
        self.is_continuous_voice_mode = False
        self.append_to_chat("\nExiting continuous voice chat mode...")
        self.command_input.setPlaceholderText("Type a command or message...")
        self.command_input.setFocus()

    def _start_voice_chat(self):
        """Start voice recording for chat mode."""
        self._disable_input()
        
        # Record and transcribe
        transcription = self.controller.voice_manager.record_and_transcribe_with_dialog(self)
        
        if transcription:
            # Show the transcription
            self.append_to_chat("\n" + "─" * 50)
            self.append_to_chat(f"\n📝 Your voice input: {transcription}")
            self.append_to_chat("\n" + "─" * 50 + "\n")
            
            # Process as chat message
            self._handle_chat_message(transcription)
        else:
            self.append_to_chat("\n❌ Voice input cancelled or failed")
            
        # Re-enable input and show prompt for next recording
        if self.is_continuous_voice_mode:
            self.append_to_chat("\n\n⏳ Press ENTER to start recording (or type 'exit' to quit)")
            self._enable_input()
            # Auto-focus the input
            self.command_input.setFocus()
            QApplication.processEvents()  # Ensure focus is applied

    def _enter_voice_copy_mode(self):
        """Enter voice copy mode."""
        self.is_voice_copy_mode = True
        self.append_to_chat("\n🎤 Welcome to voice copying mode!")
        self.append_to_chat("\nYour voice will be automatically converted to text and copied to clipboard.")
        self.append_to_chat("\n\n⏳ Press ENTER to start recording (or type 'exit' to quit)")
        self.command_input.setPlaceholderText("Press ENTER to record, type 'exit' to quit")
        self.command_input.setFocus()
        QApplication.processEvents()  # Ensure focus is applied

    def _exit_voice_copy_mode(self):
        """Exit voice copy mode."""
        self.is_voice_copy_mode = False
        self.append_to_chat("\nExiting voice copy mode...")
        self.command_input.setPlaceholderText("Type a command or message...")
        self.command_input.setFocus()

    def _start_voice_copy(self):
        """Start voice recording for copy mode."""
        self._handle_voice_copy(None)

    def _handle_voice_copy(self, recording):
        """Handle voice recording for copy mode."""
        self._disable_input()
        
        # Record and transcribe
        transcription = self.controller.voice_manager.record_and_transcribe_with_dialog(self)
        
        if transcription:
            self.append_to_chat(f"\n📝 Transcribed text: {transcription}")
            import pyperclip
            pyperclip.copy(transcription)
            self.append_to_chat("\n✨ Text copied to clipboard!")
        else:
            self.append_to_chat("\n❌ Voice input cancelled or failed")
        
        self.append_to_chat("\n\n⏳ Press ENTER to start recording (or type 'exit' to quit)")
        self._enable_input()
        # Auto-focus the input
        self.command_input.setFocus()
        QApplication.processEvents()  # Ensure focus is applied 