from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def load_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Load a PCM WAV file and return mono audio in float32 range [-1, 1]."""
    wav_path = Path(path)
    with wave.open(str(wav_path), "rb") as wav_file:
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frame_rate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        raw_bytes = wav_file.readframes(n_frames)

    if sample_width == 1:
        audio = np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32)
        audio = (audio - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width} bytes")

    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)

    return audio, frame_rate


def resample_if_needed(audio: np.ndarray, source_sr: int, target_sr: int = 16000) -> np.ndarray:
    """Resample audio by linear interpolation when the source rate differs."""
    if source_sr == target_sr:
        return audio.astype(np.float32, copy=False)

    if audio.size == 0:
        return np.zeros(0, dtype=np.float32)

    duration = audio.shape[0] / float(source_sr)
    target_length = max(1, int(round(duration * target_sr)))
    source_positions = np.linspace(0.0, duration, num=audio.shape[0], endpoint=False)
    target_positions = np.linspace(0.0, duration, num=target_length, endpoint=False)
    resampled = np.interp(target_positions, source_positions, audio)
    return resampled.astype(np.float32)
