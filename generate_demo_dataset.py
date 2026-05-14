from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np


SAMPLE_RATE = 16000
DURATION_SECONDS = 3.0


def save_wav(path: Path, signal: np.ndarray) -> None:
    clipped = np.clip(signal, -1.0, 1.0)
    samples = (clipped * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(samples.tobytes())


def tone(frequency: float, amplitude: float = 0.5) -> np.ndarray:
    t = np.linspace(0.0, DURATION_SECONDS, int(SAMPLE_RATE * DURATION_SECONDS), endpoint=False)
    return amplitude * np.sin(2.0 * math.pi * frequency * t)


def main() -> None:
    root = Path("demo_dataset")
    root.mkdir(exist_ok=True)

    samples = {
        "tone_220.wav": tone(220.0),
        "tone_224.wav": tone(224.0),
        "tone_330.wav": tone(330.0),
        "tone_440.wav": tone(440.0),
        "tone_mix.wav": tone(220.0) + 0.4 * tone(440.0),
    }

    for name, signal in samples.items():
        save_wav(root / name, signal.astype(np.float32))

    print(f"Demo WAV files generated in: {root.resolve()}")


if __name__ == "__main__":
    main()
