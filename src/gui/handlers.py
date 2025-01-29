from PyQt6.QtCore import QObject, pyqtSignal
import pyperclip
from .workers import VoiceRecordWorker, VoiceTranscriptionWorker

class VoiceHandler(QObject):
    """Handler for voice-related operations."""
    transcription_ready = pyqtSignal(str)  # Emits transcribed text
    chat_response_ready = pyqtSignal(str)  # Emits chat response
    error_occurred = pyqtSignal(str)  # Emits error messages
    status_update = pyqtSignal(str)  # Emits status messages
    
    def __init__(self, voice_manager, chat_manager, settings):
        super().__init__()
        self.voice_manager = voice_manager
        self.chat_manager = chat_manager
        self.settings = settings
        self.active_workers = []

    def start_recording(self, on_recording_ready):
        """Start voice recording in a thread."""
        worker = VoiceRecordWorker(
            self.voice_manager.recorder,
            self.settings.get("voice_settings", "duration"),
            self.voice_manager.stop_processing
        )
        worker.recording_ready.connect(on_recording_ready)
        worker.error_occurred.connect(self.error_occurred.emit)
        self.active_workers.append(worker)
        worker.start()
        return worker

    def transcribe_audio(self, recording, for_chat=False, for_copy=False):
        """Transcribe recorded audio."""
        if recording is None:
            self.error_occurred.emit("Recording failed or was cancelled")
            return

        self.status_update.emit("Processing audio...")
        
        # Save audio to file
        audio_file = self.voice_manager.recorder.save_to_file(recording)
        if not audio_file:
            self.error_occurred.emit("Failed to save audio file")
            return

        # Create transcription worker
        worker = VoiceTranscriptionWorker(
            self.voice_manager.api_client,
            audio_file,
            self.settings.get("voice_settings", "model"),
            self.settings.get("voice_settings", "language")
        )

        # Set up appropriate handler based on mode
        if for_chat:
            worker.response_ready.connect(self._handle_chat_transcription)
        elif for_copy:
            worker.response_ready.connect(self._handle_copy_transcription)
        else:
            worker.response_ready.connect(self.transcription_ready.emit)

        worker.error_occurred.connect(self.error_occurred.emit)
        self.active_workers.append(worker)
        worker.start()
        return worker

    def _handle_chat_transcription(self, transcription):
        """Handle transcription for chat mode."""
        if not transcription:
            self.error_occurred.emit("Transcription failed")
            return

        self.transcription_ready.emit(transcription)
        
        # Get chat response
        try:
            response = self.chat_manager.get_response(transcription)
            self.chat_response_ready.emit(response)
        except Exception as e:
            self.error_occurred.emit(f"Failed to get chat response: {str(e)}")

    def _handle_copy_transcription(self, transcription):
        """Handle transcription for copy mode."""
        if transcription:
            self.transcription_ready.emit(transcription)
            pyperclip.copy(transcription)
        else:
            self.error_occurred.emit("Transcription failed")

    def cleanup(self):
        """Clean up any active workers."""
        for worker in self.active_workers:
            worker.cancel()
            worker.wait()
        self.active_workers.clear() 