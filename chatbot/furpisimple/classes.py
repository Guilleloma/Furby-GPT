# classes.py
import threading
from pydub import AudioSegment
from pydub.playback import play
import time

class PensandoPlayer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.playing = False
        self.thread = None

    def start_playing(self):
        if not self.playing:
            self.playing = True
            self.thread = threading.Thread(target=self._play_loop)
            self.thread.start()

    def stop_playing(self):
        self.playing = False
        if self.thread:
            self.thread.join()

    def _play_loop(self):
        audio = AudioSegment.from_mp3(self.file_path)
        while self.playing:
            play(audio)
            time.sleep(0.1)  # Para permitir la interrupción