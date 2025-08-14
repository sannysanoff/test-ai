import scipy.io.wavfile as wavfile
import numpy as np

try:
    samplerate, data = wavfile.read('sample.wav')
    print(f"Sample Rate: {samplerate} Hz")
    print(f"Data Shape: {data.shape}")
    print(f"Data Type: {data.dtype}")

    if len(data.shape) > 1:
        print(f"Number of Channels: {data.shape[1]}")
        num_samples = data.shape[0]
    else:
        print("Number of Channels: 1")
        num_samples = len(data)

    duration = num_samples / samplerate
    print(f"Duration: {duration:.2f} seconds")

except FileNotFoundError:
    print("Error: sample.wav not found.")
except Exception as e:
    print(f"An error occurred: {e}")
