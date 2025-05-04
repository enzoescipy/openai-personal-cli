from PyQt6.QtCore import QObject, pyqtSignal, QTimer # Added QTimer for potential debouncing/delay if needed
from PyQt6.QtWidgets import QApplication, QFileDialog # Added QFileDialog
from PyQt6.QtGui import QPageLayout, QPageSize
from typing import TYPE_CHECKING, Any
from .workers import ChatWorker, ImageGenerationWorker, VisionWorker # Import workers
from .dialogs import ProcessingDialog # Import ProcessingDialog
from ..utils.text_formatter import TextFormatter # Import TextFormatter

if TYPE_CHECKING:
    from .main_window import MainWindow
    from ..features.controllers import MainController

class GuiHandler(QObject):
    """Handles GUI events and interactions, mediating between MainWindow and MainController."""
    # Define signals to communicate back to MainWindow
    set_input_enabled = pyqtSignal(bool)
    show_thinking_indicator = pyqtSignal(bool, str) # (show: bool, message: str)
    append_html_fragment_signal = pyqtSignal(str) # NEW signal for HTML fragments
    export_pdf_requested = pyqtSignal() # NEW signal for PDF export

    def __init__(self, main_window: 'MainWindow', controller: 'MainController'):
        super().__init__(main_window)
        self.main_window = main_window
        self.controller = controller
        self.active_workers = [] # Keep track of active workers
        self.current_progress_dialog = None # Manage dialog reference here

        # Connect the PDF export request signal to the handler slot
        self.export_pdf_requested.connect(self._handle_export_pdf_request)

    # --- Event Handling Methods ---

    def handle_command(self):
        """Handles user input from the command line edit."""
        command = self.main_window.command_input.text().strip()
        self.main_window.command_input.clear()

        if not command:
            return # No action if input is empty

        # Handle potential exit command (can be refined later)
        if command.lower() == 'exit':
             self.main_window.close() # Simple close for now
             return

        # Display user command immediately via HTML fragment signal
        # Simple formatting for user message
        # Use TextFormatter to escape user input to prevent basic HTML injection
        user_html = f"<div><b>You:</b> {TextFormatter.escape_html(command)}</div><br>"
        self.append_html_fragment_signal.emit(user_html)

        # Process command
        if command.startswith('/'):
            self._handle_special_command(command)
        else:
            self._handle_chat_message(command)

    def _handle_special_command(self, command: str):
        """Handles commands starting with '/'."""
        if command.startswith('/image'):
            self._handle_image_command(command)
        elif command.startswith('/vision'):
            self._handle_vision_command(command)
        elif command == '/quit':
            self.main_window.close()
        else:
            # Use helper to show error in MainWindow (will now emit HTML)
            # Escape the raw command before passing to helper
            self._format_and_append_response("❌ Unknown command:", TextFormatter.escape_html(command))

    def _handle_chat_message(self, message: str):
        """Handles regular chat messages by starting a ChatWorker."""
        worker = ChatWorker(self.controller, message)
        worker.response_ready.connect(self._handle_chat_worker_response)
        self._start_worker(worker, "Assistant is thinking...") # Use unified start method

    def _handle_image_command(self, command: str):
        """Handles '/image' commands by starting an ImageGenerationWorker."""
        prompt = command[6:].strip()
        if not prompt:
             # Use helper to show error in MainWindow (will now emit HTML)
             self._format_and_append_response("❌ Input Error:", "Please provide an image description")
             return

        # Add user command to chat history *before* starting worker
        self.controller.chat_manager.add_message("user", command)

        worker = ImageGenerationWorker(
            self.controller.image_manager,
            prompt,
            self.controller.chat_manager.conversation # Pass current conversation
        )
        worker.response_ready.connect(self._handle_image_worker_response)
        self._start_worker(worker, "Generating image with DALL-E...") # Use unified start method

    def _handle_vision_command(self, command: str):
        """Handles '/vision' commands by starting a VisionWorker."""
        parts = command[7:].strip().split()
        if not parts:
            # Use helper to show error in MainWindow (will now emit HTML)
            self._format_and_append_response("❌ Usage Error:", "Usage: /vision &lt;url_or_path&gt; [prompt] [--detail=...]", format_markdown=False) # Use format_markdown=False for preformatted usage text
            return

        # Handle local file selection if needed
        image_source = parts[0]
        if not image_source.startswith(('http://', 'https://')):
            # For local path, show file dialog
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile) # Ensure only one file
            file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.gif *.webp)")
            if file_dialog.exec():
                selected_files = file_dialog.selectedFiles()
                if selected_files:
                    image_source = selected_files[0]
                     # Reconstruct command with the selected file path for the worker
                    command = f"/vision {image_source} {' '.join(parts[1:])}"
                else:
                    # Use helper to show error in MainWindow (will now emit HTML)
                    self._format_and_append_response("❌ File Error:", "No file selected.")
                    return # Exit if no file selected
            else:
                 # Use helper to show error in MainWindow (will now emit HTML)
                 self._format_and_append_response("❌ Cancelled:", "File selection cancelled.")
                 return # Exit if dialog is cancelled

        # Validation for detail could be added here before worker starts
        # ...

        # Pass the potentially updated command (with file path) to the worker
        worker = VisionWorker(self.controller, command)
        worker.response_ready.connect(self._handle_vision_worker_response)
        self._start_worker(worker, "Analyzing image...") # Use unified start method

    # --- Worker Management ---
    def _start_worker(self, worker, thinking_message: str):
        """Starts a worker, manages UI state, and connects common signals."""
        # Disable input and show thinking indicator *before* adding worker
        # This prevents race conditions if the worker finishes very quickly
        self.set_input_enabled.emit(False)
        self.show_thinking_indicator.emit(True, thinking_message)

        # Connect common signals
        worker.error_occurred.connect(self._handle_worker_error)
        # Use worker instance directly in lambda to avoid scope issues if worker var is reassigned
        worker.finished.connect(lambda w=worker: self._cleanup_worker(w))

        self.active_workers.append(worker)
        worker.start()

    def _cleanup_worker(self, worker):
        """Cleans up after a worker finishes or is cancelled."""
        if worker in self.active_workers:
            self.active_workers.remove(worker)
        # Re-enable input only if no other workers are active
        if not self.active_workers:
             self.set_input_enabled.emit(True)
             self.show_thinking_indicator.emit(False, "") # Hide dialog

    def cancel_all_workers(self):
        """Used when MainWindow's force_stop is called."""
        for worker in self.active_workers[:]: # Iterate over a copy
            worker.cancel()
        # Don't re-enable input here, _cleanup_worker handles it via finished signal

    # --- Signal Handling Slots ---
    def _handle_chat_worker_response(self, response: Any):
        """Handles successful response from ChatWorker."""
        if isinstance(response, str):
            # Use helper to format and append
            self._format_and_append_response("🤖 Assistant's Response:", response, format_markdown=True)
        else:
            self._handle_unexpected_response(response)
        # Input re-enabled via _cleanup_worker

    def _handle_image_worker_response(self, response: Any):
        """Handles successful response from ImageGenerationWorker (expects URL)."""
        if isinstance(response, str) and response.startswith("http"):
            # Add the image URL to the conversation history via controller
            self.controller.chat_manager.add_message("assistant", f"Image URL: {response}")
            print(f"\n[DEBUG] Adding image URL to conversation: {response[:30]}...")
            print(f"[DEBUG] Conversation length after image: {len(self.controller.chat_manager.conversation)}")

            # Use helper to format and append
            self._format_and_append_response("🖼️ Image generated:", response, is_url=True)
        else:
            self._handle_unexpected_response(response)
        # Input re-enabled via _cleanup_worker

    def _handle_vision_worker_response(self, response: Any):
        """Handles successful response from VisionWorker."""
        if isinstance(response, str):
            # Use helper to format and append
            self._format_and_append_response("🔍 Image Analysis Result:", response, format_markdown=True)
        else:
            self._handle_unexpected_response(response)
        # Input re-enabled via _cleanup_worker

    def _handle_worker_error(self, error_message: str):
        """Handles errors reported by workers."""
        # Use helper for consistent error formatting (HTML)
        # Escape the raw error message before passing to helper
        self._format_and_append_response("❌ Error:", TextFormatter.escape_html(error_message))

    def _handle_unexpected_response(self, response: Any):
        """Handles unexpected response types from workers."""
        print(f"[GuiHandler] Received unexpected response type: {type(response)}")
        # Use helper for consistent formatting
        self._format_and_append_response("❌ System Message:", "Received unexpected response from assistant.")

    # --- Helper Methods ---
    def _format_and_append_response(self, title: str, content: str, is_url: bool = False, format_markdown: bool = False):
        """Formats the response as an HTML fragment and emits the signal."""
        separator_html = "<hr style='border: none; border-top: 1px solid #ccc; margin: 10px 0;'>"
        # Escape title just in case, though usually system-controlled
        title_html = f"<div><b>{TextFormatter.escape_html(title)}</b></div>"
        content_html = ""

        if is_url:
            escaped_url = TextFormatter.escape_html(content)
            # Basic image check (can be improved)
            if any(ext in escaped_url.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                 content_html = f'<a href="{escaped_url}" target="_blank"><img src="{escaped_url}" alt="Generated Image" style="max-width: 300px; height: auto; display: block; margin-top: 5px;"></a><br>' \
                               f'<a href="{escaped_url}" target="_blank" style="color: blue; text-decoration: underline; font-size: small;">{escaped_url}</a><br><br>'
            else:
                 content_html = f'<a href="{escaped_url}" target="_blank" style="color: blue; text-decoration: underline;">{escaped_url}</a><br><br>'
        else:
            if format_markdown:
                # Format text with Markdown and LaTeX support using TextFormatter
                # Assuming format_text returns safe HTML
                content_html = TextFormatter.format_text(content)
            else:
                # Just escape basic HTML for plain text, wrap in div
                content_html = f"<div>{TextFormatter.escape_html(content)}</div>"

        # Combine parts into a single fragment
        fragment = separator_html + title_html
        if not title.startswith("❌"): # Don't add separator after title for errors/system messages
             # Use a lighter separator after the title for better visual grouping
             fragment += "<hr style='border: none; border-top: 1px dashed #eee; margin: 5px 0;'>"
        fragment += content_html + separator_html

        self.append_html_fragment_signal.emit(fragment)

    # --- PDF Export Handling ---
    def _handle_export_pdf_request(self):
        """Handles the request to export the chat content to a PDF file."""
        print("[DEBUG] PDF export requested.") # Debug print
        page = self.main_window.chat_display.page()
        if not page:
            self._format_and_append_response("❌ Export Error:", "Cannot access chat page content.")
            return

        # Ask user for the save file name
        file_name, _ = QFileDialog.getSaveFileName(
            self.main_window, # Parent window
            "Save Chat as PDF",
            "", # Start directory (empty for default)
            "PDF Files (*.pdf)"
        )

        if file_name:
            if not file_name.lower().endswith('.pdf'):
                file_name += '.pdf'

            # Show processing dialog (use the main window as parent)
            dialog = ProcessingDialog("Exporting to PDF...", self.main_window)
            # We need to keep a reference or manage it better if multiple dialogs can exist
            # For simplicity, let's assume only one export at a time
            current_export_dialog = dialog # Keep local reference for the callback
            dialog.show()
            QApplication.processEvents() # Ensure dialog shows immediately

            try:
                # Define page layout for PDF
                layout = QPageLayout()
                # Use A4 Portrait as default
                layout.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
                layout.setOrientation(QPageLayout.Orientation.Portrait)
                # Set reasonable margins (in millimeters)
                # layout.setMargins(QMarginsF(15, 15, 15, 15))

                # Define the callback function to handle the PDF data
                def handle_pdf_data(pdf_data):
                    try:
                        if pdf_data:
                            try:
                                with open(file_name, 'wb') as f:
                                    f.write(pdf_data)
                                # Use helper to show success message
                                self._format_and_append_response("✅ Export Success:", f"Chat exported to {file_name}")
                            except Exception as e:
                                self._format_and_append_response("❌ Export Error:", f"Error saving PDF: {str(e)}")
                        else:
                            self._format_and_append_response("❌ Export Error:", "Failed to generate PDF data.")
                    finally:
                        # Ensure dialog is closed regardless of outcome
                        if current_export_dialog:
                            current_export_dialog.close()

                # Call printToPdf with the callback
                page.printToPdf(handle_pdf_data, layout)

            except Exception as e:
                self._format_and_append_response("❌ Export Error:", f"Error during PDF export setup: {str(e)}")
                # Close dialog immediately if setup fails
                if current_export_dialog:
                    current_export_dialog.close()
        else:
            print("[DEBUG] PDF export cancelled by user.") # Optional debug print 