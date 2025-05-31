# Beat tracking example
import librosa
import numpy as np


def run_beat_track(file_path):
  """
  Analyze a track and return beat times
  
  Args:
    file_path: Path to the audio file to analyze
    
  Returns:
    numpy array of beat times in seconds
  """
  try:
    # Load the audio as a waveform `y`
    # Store the sampling rate as `sr`
    y, sr = librosa.load(file_path)
    print("BEAT TRACK",y, sr)

    # Run the default beat tracker
    tempo = librosa.beat.tempo(y=y, sr=sr)
    # beat_frames = librosa.beat.beat_track(y=y, sr=sr)

    # Extract scalar value from tempo array
    # if isinstance(tempo, np.ndarray):
    #     tempo_value = tempo.item() if tempo.size == 1 else tempo[0]
    # else:
    #     tempo_value = tempo
    
    # print(f"Estimated tempo: {tempo:.2f} beats per minute")

    # Convert the frame indices of beat events into timestamps
    # beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    return tempo.item()
  except Exception as e:
    print(f"Error analyzing track: {str(e)}")
    raise