from __future__ import annotations

from pathlib import Path

import numpy as np

from .audio import load_wav, resample_if_needed


TARGET_SR = 16000
FRAME_SIZE = 2048
HOP_SIZE = 512
SPECTRUM_BINS = 64
MEL_BANDS = 32
MFCC_COUNT = 13


def _frame_audio(audio: np.ndarray, frame_size: int = FRAME_SIZE, hop_size: int = HOP_SIZE) -> np.ndarray:
    if audio.size < frame_size:
        padded = np.pad(audio, (0, frame_size - audio.size))
        return padded.reshape(1, frame_size)

    frame_count = 1 + (audio.size - frame_size) // hop_size
    shape = (frame_count, frame_size)
    strides = (audio.strides[0] * hop_size, audio.strides[0])
    frames = np.lib.stride_tricks.as_strided(audio, shape=shape, strides=strides)
    return frames.copy()


def _safe_normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm == 0.0:
        return vector.astype(np.float32)
    return (vector / norm).astype(np.float32)


def _hz_to_mel(freq_hz: np.ndarray) -> np.ndarray:
    return 2595.0 * np.log10(1.0 + freq_hz / 700.0)


def _mel_to_hz(mel: np.ndarray) -> np.ndarray:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def _build_mel_filterbank(sample_rate: int, n_fft: int, n_mels: int = MEL_BANDS) -> np.ndarray:
    freq_bins = n_fft // 2 + 1
    mel_min = _hz_to_mel(np.array([0.0], dtype=np.float32))[0]
    mel_max = _hz_to_mel(np.array([sample_rate / 2.0], dtype=np.float32))[0]
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2, dtype=np.float32)
    hz_points = _mel_to_hz(mel_points)
    bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)
    bin_points = np.clip(bin_points, 0, freq_bins - 1)

    filters = np.zeros((n_mels, freq_bins), dtype=np.float32)
    for band in range(n_mels):
        left = bin_points[band]
        center = bin_points[band + 1]
        right = bin_points[band + 2]

        if center <= left:
            center = min(left + 1, freq_bins - 1)
        if right <= center:
            right = min(center + 1, freq_bins)

        for idx in range(left, center):
            filters[band, idx] = (idx - left) / max(center - left, 1)
        for idx in range(center, right):
            filters[band, idx] = (right - idx) / max(right - center, 1)

    return filters


def _build_dct_basis(n_mfcc: int, n_mels: int) -> np.ndarray:
    basis = np.zeros((n_mfcc, n_mels), dtype=np.float32)
    scale = np.pi / float(n_mels)
    norm0 = np.sqrt(1.0 / n_mels)
    norm = np.sqrt(2.0 / n_mels)
    for coeff in range(n_mfcc):
        for mel_idx in range(n_mels):
            value = np.cos((mel_idx + 0.5) * coeff * scale)
            basis[coeff, mel_idx] = value * (norm0 if coeff == 0 else norm)
    return basis


def _delta(features: np.ndarray) -> np.ndarray:
    if features.shape[0] < 2:
        return np.zeros_like(features)

    padded = np.pad(features, ((1, 1), (0, 0)), mode="edge")
    return 0.5 * (padded[2:] - padded[:-2])


def extract_features_from_array(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    audio = resample_if_needed(audio, sample_rate, TARGET_SR)
    if audio.size == 0:
        raise ValueError("Audio file is empty")

    audio = audio.astype(np.float32)
    audio = audio / max(np.max(np.abs(audio)), 1e-8)

    # Light pre-emphasis helps highlight timbral differences.
    emphasized = np.empty_like(audio)
    emphasized[0] = audio[0]
    emphasized[1:] = audio[1:] - 0.97 * audio[:-1]

    frames = _frame_audio(emphasized)
    window = np.hanning(FRAME_SIZE).astype(np.float32)
    windowed = frames * window

    spectrum = np.fft.rfft(windowed, axis=1)
    magnitude = np.abs(spectrum) + 1e-10
    power = (magnitude**2) / FRAME_SIZE
    freqs = np.fft.rfftfreq(FRAME_SIZE, d=1.0 / TARGET_SR).astype(np.float32)

    rms = np.sqrt(np.mean(windowed**2, axis=1))
    zcr = np.mean(np.abs(np.diff(np.signbit(frames), axis=1)), axis=1).astype(np.float32)

    magnitude_sum = np.sum(magnitude, axis=1) + 1e-10
    centroid = np.sum(magnitude * freqs, axis=1) / magnitude_sum
    bandwidth = np.sqrt(np.sum(magnitude * (freqs - centroid[:, None]) ** 2, axis=1) / magnitude_sum)

    cumulative_energy = np.cumsum(power, axis=1)
    total_energy = cumulative_energy[:, -1][:, None]
    rolloff_threshold = 0.85 * total_energy
    rolloff_indices = np.argmax(cumulative_energy >= rolloff_threshold, axis=1)
    rolloff = freqs[rolloff_indices]

    flatness = np.exp(np.mean(np.log(magnitude), axis=1)) / (np.mean(magnitude, axis=1) + 1e-10)

    log_spectrum = np.log1p(magnitude)
    compressed_spectrum = []
    splits = np.array_split(log_spectrum, SPECTRUM_BINS, axis=1)
    for chunk in splits:
        compressed_spectrum.append(np.mean(chunk, axis=1))
    compressed_spectrum = np.stack(compressed_spectrum, axis=1)

    mel_filterbank = _build_mel_filterbank(TARGET_SR, FRAME_SIZE, MEL_BANDS)
    mel_energy = np.maximum(power @ mel_filterbank.T, 1e-10)
    log_mel = np.log(mel_energy)

    dct_basis = _build_dct_basis(MFCC_COUNT, MEL_BANDS)
    mfcc = log_mel @ dct_basis.T
    delta_mfcc = _delta(mfcc)

    stat_vector = np.array(
        [
            np.mean(rms),
            np.std(rms),
            np.mean(zcr),
            np.std(zcr),
            np.mean(centroid),
            np.std(centroid),
            np.mean(bandwidth),
            np.std(bandwidth),
            np.mean(rolloff),
            np.std(rolloff),
            np.mean(flatness),
            np.std(flatness),
            float(audio.shape[0]) / TARGET_SR,
        ],
        dtype=np.float32,
    )

    spectrum_mean = np.mean(compressed_spectrum, axis=0).astype(np.float32)
    spectrum_std = np.std(compressed_spectrum, axis=0).astype(np.float32)
    mel_mean = np.mean(log_mel, axis=0).astype(np.float32)
    mel_std = np.std(log_mel, axis=0).astype(np.float32)
    mfcc_mean = np.mean(mfcc, axis=0).astype(np.float32)
    mfcc_std = np.std(mfcc, axis=0).astype(np.float32)
    delta_mean = np.mean(delta_mfcc, axis=0).astype(np.float32)
    delta_std = np.std(delta_mfcc, axis=0).astype(np.float32)

    feature_vector = np.concatenate(
        [
            stat_vector,
            spectrum_mean,
            spectrum_std,
            mel_mean,
            mel_std,
            mfcc_mean,
            mfcc_std,
            delta_mean,
            delta_std,
        ]
    ).astype(np.float32)
    return _safe_normalize(feature_vector)


def extract_features(path: str | Path) -> np.ndarray:
    audio, sample_rate = load_wav(path)
    return extract_features_from_array(audio, sample_rate)
