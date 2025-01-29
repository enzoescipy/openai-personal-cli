import threading
import tempfile
import wave
import numpy as np
import sounddevice as sd
import keyboard
from typing import Optional, Tuple
from PyQt6.QtWidgets import QApplication

class AudioRecorder:
    def __init__(self, sample_rate: int, channels: int, max_file_size: int = 25 * 1024 * 1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.max_file_size = max_file_size
        self.stop_recording = threading.Event()
        self.force_stop = threading.Event()

    def setup_keyboard_control(self):
        """Setup keyboard controls for recording."""
        # SPACEBAR = normal stop (will proceed to transcription)
        keyboard.on_press_key('space', lambda _: self.stop_recording.set())
        # ESC = force stop (will cancel everything)
        keyboard.on_press_key('esc', lambda _: self.force_stop.set())

    def cleanup_keyboard(self):
        """Clean up keyboard hooks."""
        keyboard.unhook_all()

    def record(self, duration: float, stop_processing: Optional[threading.Event] = None) -> Optional[np.ndarray]:
        """Record audio with keyboard controls."""
        self.stop_recording.clear()
        self.force_stop.clear()
        
        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.int16
        )
        
        frames = []
        current_size = 0
        
        with stream:
            while (not self.stop_recording.is_set() and 
                   not self.force_stop.is_set() and 
                   (stop_processing is None or not stop_processing.is_set())):
                data, _ = stream.read(1024)
                current_size += len(data.tobytes())
                
                if current_size >= self.max_file_size:
                    print("\nReached maximum file size (25MB). Stopping recording...")
                    break
                    
                if len(frames) * self.channels / self.sample_rate >= duration:
                    print(f"\nReached maximum duration ({duration:.1f} seconds). Stopping recording...")
                    break
                    
                frames.append(data.copy())
                QApplication.processEvents()  # Process Qt events during recording
        
        self.cleanup_keyboard()
        
        # If force stopped or no frames, return None
        if self.force_stop.is_set() or not frames:
            return None
            
        # Return the recording only if it wasn't force-stopped
        return np.concatenate(frames)

    def save_to_file(self, recording: np.ndarray) -> Optional[str]:
        """Save the recorded audio to a temporary WAV file."""
        if recording is None:
            return None
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(self.sample_rate)
                wf.writeframes(recording.tobytes())
            return temp_file.name 