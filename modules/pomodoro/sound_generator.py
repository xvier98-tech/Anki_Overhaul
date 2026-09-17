# -*- coding: utf-8 -*-
"""
Generates clean, pleasant synthesized sound effects for Pomodoro transitions
using Python standard library (wave, struct, math). Zero external dependencies.
"""

import os
import wave
import struct
import math


def generate_audio_assets(target_dir: str):
    """Generates preset WAV files if they do not already exist."""
    os.makedirs(target_dir, exist_ok=True)
    sample_rate = 44100

    def write_wav(filename: str, samples: list):
        filepath = os.path.join(target_dir, filename)
        with wave.open(filepath, 'w') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            raw_data = bytearray()
            for s in samples:
                val = max(-32767, min(32767, int(s * 32767)))
                raw_data.extend(struct.pack('<h', val))
            wf.writeframes(raw_data)
        return filepath

    # 1. Sino / Chime Suave (Harmonic Bell with exponential decay)
    bell_file = os.path.join(target_dir, "bell.wav")
    if not os.path.exists(bell_file):
        duration = 1.6
        num_samples = int(duration * sample_rate)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-3.2 * t)
            # Harmonic chime: 587.33 Hz (D5), 880 Hz (A5), 1174.66 Hz (D6)
            s = (
                0.55 * math.sin(2 * math.pi * 587.33 * t) +
                0.30 * math.sin(2 * math.pi * 880.00 * t) +
                0.15 * math.sin(2 * math.pi * 1174.66 * t)
            ) * env
            samples.append(s)
        write_wav("bell.wav", samples)

    # 2. Sinal / Campainha (Two-tone warm Ding-Dong)
    school_bell_file = os.path.join(target_dir, "school_bell.wav")
    if not os.path.exists(school_bell_file):
        duration = 1.4
        num_samples = int(duration * sample_rate)
        samples = []
        half = int(0.6 * sample_rate)
        for i in range(num_samples):
            t = i / sample_rate
            if i < half:
                env = math.exp(-3.5 * t)
                s = (0.6 * math.sin(2 * math.pi * 659.25 * t) + 0.3 * math.sin(2 * math.pi * 1318.5 * t)) * env
            else:
                t2 = t - 0.6
                env = math.exp(-3.0 * t2)
                s = (0.6 * math.sin(2 * math.pi * 523.25 * t2) + 0.3 * math.sin(2 * math.pi * 1046.5 * t2)) * env
            samples.append(s)
        write_wav("school_bell.wav", samples)

    # 3. Alarme de Relógio Analógico (Tick-tick and mechanical bell ring)
    analog_file = os.path.join(target_dir, "analog_alarm.wav")
    if not os.path.exists(analog_file):
        duration = 1.5
        num_samples = int(duration * sample_rate)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            # 8 pulses of mechanical ringing
            pulse_mod = math.sin(2 * math.pi * 12.0 * t)
            env = 0.5 + 0.5 * pulse_mod
            ring = (
                0.5 * math.sin(2 * math.pi * 987.77 * t) +
                0.3 * math.sin(2 * math.pi * 1480.0 * t) +
                0.2 * math.sin(2 * math.pi * 1975.5 * t)
            ) * env * (1.0 - t / duration)
            samples.append(ring * 0.8)
        write_wav("analog_alarm.wav", samples)

    # 4. Alarme Relógio Digital (Electronic Triple Beep-Beep-Beep)
    digital_file = os.path.join(target_dir, "digital_alarm.wav")
    if not os.path.exists(digital_file):
        duration = 1.2
        num_samples = int(duration * sample_rate)
        samples = []
        beep_dur = 0.12
        pause_dur = 0.08
        freq = 2048.0
        for i in range(num_samples):
            t = i / sample_rate
            cycle_time = t % (beep_dur + pause_dur)
            is_beep = (cycle_time < beep_dur) and (t < 0.8)
            if is_beep:
                # Square-ish sine wave for digital watch beep
                s = 0.6 * math.sin(2 * math.pi * freq * t) + 0.2 * math.sin(2 * math.pi * freq * 3 * t)
            else:
                s = 0.0
            samples.append(s)
        write_wav("digital_alarm.wav", samples)


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(current_dir, "..", "..", "assets", "sounds")
    generate_audio_assets(assets_dir)
    print("Audio assets generated successfully!")
