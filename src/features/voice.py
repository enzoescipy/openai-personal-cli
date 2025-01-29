import threading
from typing import Optional, Tuple
import keyboard
from ..core.api_client import APIClient
from ..core.settings import Settings
from ..utils.audio import AudioRecorder
import numpy as np
from PyQt6.QtWidgets import QApplication

class VoiceManager:
    def __init__(self, api_client: APIClient, settings: Settings):
        self.api_client = api_client
        self.settings = settings
        self.recorder = AudioRecorder(
            sample_rate=settings.get("voice_settings", "sample_rate"),
            channels=settings.get("voice_settings", "channels")
        )
        self.stop_processing = threading.Event()

    def record_with_dialog(self, parent_window=None) -> Optional[np.ndarray]:
        """Record audio with a modal dialog. Returns None if cancelled."""
        from ..gui.dialogs import RecordingDialog
        
        dialog = RecordingDialog(parent_window)
        dialog.show()
        QApplication.processEvents()
        
        # Setup keyboard controls
        self.stop_processing.clear()
        self.recorder.setup_keyboard_control()
        
        # Start recording
        recording = self.recorder.record(
            duration=self.settings.get("voice_settings", "duration"),
            stop_processing=self.stop_processing
        )
        
        dialog.close()
        keyboard.unhook_all()
        return recording

    def transcribe_with_dialog(self, recording: np.ndarray, parent_window=None) -> Optional[str]:
        """Transcribe audio with a modal dialog. Returns None if failed."""
        from ..gui.dialogs import ProcessingDialog
        
        if recording is None:
            return None
            
        dialog = ProcessingDialog("Transcribing your voice...", parent_window)
        dialog.show()
        QApplication.processEvents()
        
        # Save to file and transcribe
        audio_file = self.recorder.save_to_file(recording)
        if not audio_file:
            dialog.close()
            return None
            
        result = self.api_client.transcribe_audio(
            audio_file_path=audio_file,
            model=self.settings.get("voice_settings", "model"),
            language=self.settings.get("voice_settings", "language")
        )
        
        dialog.close()
        return result

    def record_and_transcribe_with_dialog(self, parent_window=None) -> Optional[str]:
        """Record and transcribe audio with modal dialogs."""
        recording = self.record_with_dialog(parent_window)
        if recording is None:
            return None
            
        return self.transcribe_with_dialog(recording, parent_window)

    def force_stop(self):
        """Force stop recording."""
        self.stop_processing.set()
        keyboard.unhook_all()

    def setup_force_stop(self):
        """Setup force stop keyboard shortcut."""
        keyboard.on_press_key('esc', lambda _: self.stop_processing.set())

    def record_and_transcribe(self) -> Optional[str]:
        """Record audio and transcribe it."""
        self.stop_processing.clear()
        self.recorder.setup_keyboard_control()
        self.setup_force_stop()

        print("\n🔴 Recording... (Press SPACEBAR to stop, ESC to cancel)")
        recording = self.record_with_dialog()  # Use the same record method

        if recording is None:
            keyboard.unhook_all()
            return None

        print("\n⚙️ Processing audio...")
        audio_file = self.recorder.save_to_file(recording)
        keyboard.unhook_all()

        if audio_file:
            return self.api_client.transcribe_audio(
                audio_file_path=audio_file,
                model=self.settings.get("voice_settings", "model"),
                language=self.settings.get("voice_settings", "language")
            )
        return None

    def continuous_voice_mode(self, callback) -> None:
        """Enter continuous voice recording mode."""
        print("\n🎤 Welcome to continuous voice chat mode!")
        print("Have a continuous conversation with the AI using your voice.")
        print("\nInstructions:")
        print("- Press ENTER to start recording your message")
        print("- Press SPACEBAR to stop recording")
        print("- Press ESC to force-stop current recording")
        print("- Type 'exit' to quit this mode")

        while True:
            command = input("\n⏳ Ready - Press ENTER to speak (or type 'exit' to quit): ").strip().lower()
            
            if command == 'exit':
                print("\nExiting voice chat mode...")
                break
            
            if command == '':
                transcription = self.record_and_transcribe()
                if transcription:
                    callback(transcription)

    def voice_copy_mode(self) -> None:
        """Enter voice copy mode."""
        import pyperclip
        
        print("\n🎤 Welcome to OpenAI Whisper-model based voice copying mode!")
        print("This mode will allow you to rapidly record and transcribe voice samples.")
        print("Your voice will be automatically converted to text and copied to clipboard.")
        print("\nInstructions:")
        print("- Press ENTER to start recording")
        print("- Press SPACEBAR to stop recording")
        print("- Press ESC to force-stop (cancels current recording)")
        print("- Type 'exit' to quit this mode")

        while True:
            command = input("\n⏳ Ready - Press ENTER to start recording (or type 'exit' to quit): ").strip().lower()
            
            if command == 'exit':
                print("\nExiting voice copy mode...")
                break
            
            if command == '':
                transcription = self.record_and_transcribe()
                if transcription:
                    print(f"\n📝 Transcribed text: {transcription}")
                    pyperclip.copy(transcription)
                    print("✨ Text copied to clipboard!") 