from pydub import AudioSegment
import os

class ScratchSim:
    def __init__(self, file_path):
        self.original = AudioSegment.from_file(file_path)
        self.sample_rate = self.original.frame_rate

    def _slice(self, start_ms, duration_ms):
        return self.original[start_ms:start_ms + duration_ms]

    def baby_scratch(self, start_ms, duration_ms=150, reps=4):
        scratch = AudioSegment.silent(duration=0)
        for _ in range(reps):
            fwd = self._slice(start_ms, duration_ms)
            rev = fwd.reverse()
            scratch += fwd + rev
        return scratch

    def forward_scratch(self, start_ms, duration_ms=150, reps=4):
        scratch = AudioSegment.silent(duration=0)
        for _ in range(reps):
            fwd = self._slice(start_ms, duration_ms)
            scratch += fwd + AudioSegment.silent(duration=duration_ms)
        return scratch

    def transformer_scratch(self, start_ms, duration_ms=100, reps=6):
        scratch = AudioSegment.silent(duration=0)
        for _ in range(reps):
            sound = self._slice(start_ms, duration_ms)
            silence = AudioSegment.silent(duration=duration_ms)
            scratch += sound + silence
        return scratch

    def tear_scratch(self, start_ms, duration_ms=100):
        first = self._slice(start_ms, duration_ms)
        pause = AudioSegment.silent(duration=duration_ms // 2)
        second = self._slice(start_ms + duration_ms, duration_ms)
        return first + pause + second

    def export(self, segment, filename="scratch_output.wav"):
        segment.export(filename, format="wav")
        return os.path.abspath(filename)