# Beat tracking example
import librosa


def run_beat_track():
  # 1. Get the file path to an included audio example
  # filename = librosa.example('/Users/freshly/Downloads/Bad Bunny - BAILE INoLVIDABLE (Dirty).mp3')
  # filename = librosa.example('nutcracker')


  # 2. Load the audio as a waveform `y`
  #    Store the sampling rate as `sr`
  y, sr = librosa.load('/Users/freshly/Downloads/Bad Bunny - BAILE INoLVIDABLE (Dirty).mp3')

  # 3. Run the default beat tracker
  tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

  print(f"Estimated tempo: {tempo:.2f} beats per minute")

  # 4. Convert the frame indices of beat events into timestamps
  beat_times = librosa.frames_to_time(beat_frames, sr=sr)

  return beat_times