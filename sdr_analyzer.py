import numpy as np
from scipy.io import wavfile
from scipy import signal
import matplotlib.pyplot as plt

# Constants
SAMPLE_RATE = 384000  # Hz
FFT_SIZE = 2048  # FFT size for spectrogram - Reduced to save memory

def load_iq_data(filename):
    """
    Loads I/Q data from a stereo WAV file.

    Args:
        filename (str): The path to the WAV file.

    Returns:
        np.ndarray: A complex numpy array representing the signal.
                    Returns None if the file cannot be read.
    """
    try:
        samplerate, data = wavfile.read(filename)
        if samplerate != SAMPLE_RATE:
            print(f"Warning: Sample rate mismatch. Expected {SAMPLE_RATE}, got {samplerate}")

        # Ensure data is in a floating point format for complex conversion
        data = data.astype(np.float32)

        # Normalize to [-1, 1]
        data /= 32767.0

        # Combine I and Q channels into a complex signal
        # Assuming channel 0 is I and channel 1 is Q
        if data.shape[1] == 2:
            iq_signal = data[:, 0] + 1j * data[:, 1]
            return iq_signal
        else:
            print("Error: WAV file is not stereo (I/Q).")
            return None

    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred while reading the WAV file: {e}")
        return None

def compute_spectrogram(iq_signal):
    """
    Computes the spectrogram of the I/Q signal.

    Args:
        iq_signal (np.ndarray): The complex I/Q signal.

    Returns:
        tuple: A tuple containing:
               - freqs (np.ndarray): Array of sample frequencies.
               - times (np.ndarray): Array of segment times.
               - Sxx (np.ndarray): Spectrogram of x.
    """
    freqs, times, Sxx = signal.spectrogram(
        iq_signal,
        fs=SAMPLE_RATE,
        nperseg=FFT_SIZE,
        noverlap=FFT_SIZE // 2,
        window='hann',
        scaling='density',
        return_onesided=False  # We want both positive and negative frequencies
    )

    # Shift the frequency axis to be centered at 0
    freqs = np.fft.fftshift(freqs)
    Sxx = np.fft.fftshift(Sxx, axes=0)

    return freqs, times, Sxx

import math

def float_gcd(a, b, rtol=1e-05, atol=1e-08):
    "Computes the GCD of two floats"
    t = min(abs(a), abs(b))
    while t > atol + rtol * abs(b):
        if abs(a % t) < atol + rtol * abs(a) and abs(b % t) < atol + rtol * abs(b):
            return t
        t -= atol + rtol*t # Decrement t
    return 0.0

def find_harmonics(peak_freqs, f0_range=(150, 250), tolerance=100):
    """
    Finds f0 and fc by assuming the lowest peak is a low-order harmonic.
    """
    if len(peak_freqs) < 2:
        return None, None

    peak_freqs = np.sort(peak_freqs)

    best_f0 = None
    best_fc = None
    max_matches = 0

    # 1. Hypothesize f0
    for f0_hz in range(f0_range[0], f0_range[1], 5): # Step by 5Hz for speed

        # 2. Hypothesize that the lowest peak is the n=2 or n=3 harmonic
        for n_low in [2, 3, 4]: # Check a few low harmonics
            p_low = peak_freqs[0]
            fc_candidate = p_low - n_low * f0_hz

            # 3. Score the hypothesis
            matches = 0
            for p in peak_freqs:
                if p < fc_candidate + 300: # high-pass filter hint
                    continue

                ratio = (p - fc_candidate) / f0_hz
                # Check if ratio is close to an integer and it's a plausible harmonic number
                if abs(ratio - round(ratio)) * f0_hz < tolerance and round(ratio) > 1:
                    matches += 1

            if matches > max_matches:
                # We have a new best candidate
                max_matches = matches
                best_f0 = f0_hz
                best_fc = fc_candidate

    if max_matches >= 2: # Require at least 2 matching peaks
        return best_fc, best_f0

    return None, None

def find_transmissions(freqs, times, Sxx):
    """
    Analyzes the spectrogram to find USB transmissions.
    """
    print("\nStarting transmission analysis over all time segments...")
    detections = []

    for i, t in enumerate(times):
        spectrogram_slice = Sxx[:, i]

        # Use a percentile-based threshold
        power_threshold = np.percentile(spectrogram_slice, 98.5)

        peaks, properties = signal.find_peaks(spectrogram_slice, height=power_threshold, distance=5)

        if len(peaks) < 2:
            continue

        peak_freqs = freqs[peaks]
        peak_powers = properties['peak_heights']

        # --- ITERATION: Focus on positive frequencies based on hints ---
        positive_mask = peak_freqs > 0
        peak_freqs = peak_freqs[positive_mask]
        peak_powers = peak_powers[positive_mask]

        if len(peak_freqs) < 2:
            continue
        # --- END ---

        # Group peaks into clusters
        clusters = []
        current_cluster = [(peak_freqs[0], peak_powers[0])]
        for j in range(1, len(peak_freqs)):
            if peak_freqs[j] - peak_freqs[j-1] < 3000: # 3kHz bandwidth
                current_cluster.append((peak_freqs[j], peak_powers[j]))
            else:
                if len(current_cluster) > 1:
                    clusters.append(current_cluster)
                current_cluster = [(peak_freqs[j], peak_powers[j])]
        if len(current_cluster) > 1:
            clusters.append(current_cluster)

        for cluster in clusters:
            cluster_freqs = np.array([item[0] for item in cluster])
            cluster_powers = np.array([item[1] for item in cluster])

            fc, f0 = find_harmonics(cluster_freqs)
            if fc is not None:
                avg_power = np.mean(cluster_powers)
                detections.append({'fc': fc, 'f0': f0, 'time': t, 'power': avg_power})

    print(f"\nFound {len(detections)} raw harmonic detections.")
    return detections

def cluster_and_rank_detections(detections, Sxx, freqs, times, freq_tolerance=500, bandwidth=3000):
    """
    Clusters raw detections, calculates SNR, ranks them, and returns the final list.
    """
    if not detections:
        return []

    detections.sort(key=lambda d: d['fc'])
    clusters = []
    if detections:
        current_cluster = [detections[0]]
        for i in range(1, len(detections)):
            if abs(detections[i]['fc'] - current_cluster[-1]['fc']) < freq_tolerance:
                current_cluster.append(detections[i])
            else:
                clusters.append(current_cluster)
                current_cluster = [detections[i]]
        clusters.append(current_cluster)

    transmissions = []
    all_signal_bands = []
    for cluster in clusters:
        if not cluster: continue

        avg_fc = np.mean([d['fc'] for d in cluster])

        # Define signal and noise bands
        signal_band_mask = (freqs >= avg_fc) & (freqs < avg_fc + bandwidth)
        noise_band_mask = (freqs >= avg_fc + bandwidth) & (freqs < avg_fc + 2 * bandwidth)
        all_signal_bands.append(signal_band_mask)

        # Get the time indices where this signal was detected
        active_time_indices = [np.argmin(np.abs(times - d['time'])) for d in cluster]

        # Calculate signal power
        signal_power = np.mean(Sxx[np.ix_(signal_band_mask, active_time_indices)])

        # Calculate noise power from the same time segments but in the noise band
        noise_power = np.mean(Sxx[np.ix_(noise_band_mask, active_time_indices)])

        snr = 10 * np.log10(signal_power / noise_power) if noise_power > 0 else 99.0

        persistence = len(cluster)
        quality_score = persistence * (snr if snr > 0 else 0.1) # More robust quality score

        transmissions.append({
            'carrier_freq': avg_fc,
            'snr_db': snr,
            'persistence': persistence,
            'quality': quality_score
        })

    transmissions.sort(key=lambda t: t['quality'], reverse=True)
    return transmissions

if __name__ == '__main__':
    print("Starting SDR analysis...")
    iq_data = load_iq_data('sample.wav')

    if iq_data is not None:
        print("I/Q data loaded successfully.")

        freqs, times, Sxx = compute_spectrogram(iq_data)
        print("Spectrogram computed successfully.")

        # Find all potential harmonic signals
        raw_detections = find_transmissions(freqs, times, Sxx)

        # Cluster, rank, and calculate SNR for the raw detections
        final_transmissions = cluster_and_rank_detections(raw_detections, Sxx, freqs, times)

        print("\n--- Final Detected Transmissions (Top 25) ---")
        if not final_transmissions:
            print("No transmissions found.")
        else:
            print(" # | Freq (kHz) | Persistence | SNR (dB) | Quality")
            print("---|------------|-------------|----------|---------")
            for i, trans in enumerate(final_transmissions[:25]):
                print(f"{i+1:2d} | {trans['carrier_freq']/1000:10.3f} | {trans['persistence']:11d} | {trans['snr_db']:8.2f} | {trans['quality']:.2f}")

        # Plot the final results
        print("\nGenerating final spectrogram with detected transmissions...")
        plt.figure(figsize=(15, 8))

        db_Sxx = 10 * np.log10(Sxx)
        db_min = np.percentile(db_Sxx, 25)
        db_max = np.percentile(db_Sxx, 99.5)

        plt.pcolormesh(times, freqs / 1000, db_Sxx, shading='auto', vmin=db_min, vmax=db_max)

        plt.ylabel('Frequency [kHz]')
        plt.xlabel('Time [s]')
        plt.title('Spectrogram with Detected USB Transmissions')
        plt.colorbar(label='Intensity [dB/Hz]')
        plt.ylim(0, 60)

        if final_transmissions:
            num_to_plot = min(len(final_transmissions), 25)
            colors = plt.cm.get_cmap('tab20', num_to_plot)
            for i, trans in enumerate(final_transmissions[:num_to_plot]):
                plt.axhline(y=trans['carrier_freq']/1000, color=colors(i), linestyle='--', alpha=0.9,
                            label=f"{trans['carrier_freq']/1000:.2f} kHz (SNR: {trans['snr_db']:.1f} dB)")

        plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0.)
        plt.tight_layout(rect=[0, 0, 0.85, 1])

        plt.savefig('final_spectrogram_with_detections.png')
        print("Final spectrogram saved to 'final_spectrogram_with_detections.png'")

    else:
        print("SDR analysis failed.")
