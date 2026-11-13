"""Noise-profile cleanup of the seven unified, pinned v6 original takes.

uv run --no-project --with numpy --with scipy --with soundfile python frontend/scripts/clean-special-i-recordings.py
No network, TTS, voice change, pitch/speed edits or phoneme splicing.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import soundfile as sf
from scipy.ndimage import gaussian_filter, gaussian_filter1d
from scipy.signal import butter, sosfiltfilt, stft, istft

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'frontend/public/academy/audio/special-i-native-v6'
DEST = ROOT / 'frontend/public/academy/audio/special-i-native-v7'
FRICATION = {'zi': (.09, .16), 'ci': (.07, .27), 'si': (.08, .33),
             'zhi': (.38, .44), 'chi': (.055, .20), 'shi': (.19, .44)}


def rms(x):
    return float(np.sqrt(np.mean(x**2)))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def active_rms(x, sr):
    hop = round(sr*.02)
    frames = [x[i:i+hop] for i in range(0, len(x), hop)]
    power = np.array([np.mean(frame**2) for frame in frames])
    return rms(np.concatenate([frame for frame, p in zip(frames, power) if p > power.max()*.04]))


def clean(x, sr):
    filtered = sosfiltfilt(butter(6, 100, 'highpass', fs=sr, output='sos'), x)
    frequencies, times, spectrum = stft(filtered, sr, nperseg=1024, noverlap=768)
    # All seven sources have a quiet room-tone tail here, after natural release.
    # Never estimate noise from c/ch aspiration or s/sh frication at the start.
    duration = len(x)/sr
    noise_frames = (times >= duration-.09) & (times <= duration-.03)
    assert noise_frames.sum() >= 5
    noise_power = np.mean(abs(spectrum[:, noise_frames])**2, axis=1)
    noise_power = gaussian_filter1d(noise_power, .8)
    power = gaussian_filter(abs(spectrum)**2, sigma=(.6, 1.5))
    # Smooth, soft spectral attenuation. No binary/time-domain noise gate.
    gain = np.sqrt(np.maximum(1-1.35*noise_power[:, None]/(power+1e-20), .015))
    gain = gaussian_filter(gain, sigma=(1.0, 1.2))
    _, reconstructed = istft(spectrum*gain, sr, nperseg=1024, noverlap=768)
    return filtered, reconstructed[:len(x)], frequencies, times, gain


def main():
    baseline = json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    DEST.mkdir(parents=True, exist_ok=True)
    clips = []
    for row in baseline['clips']:
        source = BASE/row['source_file']
        assert digest(source) == row['source_sha256']
        x, sr = sf.read(source, dtype='float64')
        assert sr == 44100 and x.ndim == 1 and np.isfinite(x).all()
        before, y, frequencies, times, gain_map = clean(x, sr)
        tail = slice(round((len(x)/sr-.09)*sr), round((len(x)/sr-.03)*sr))
        noise_reduction = 20*np.log10((rms(before[tail])+1e-15)/(rms(y[tail])+1e-15))
        sound = row['pinyin']
        frication_change = None
        if sound in FRICATION:
            start, end = [round(t*sr) for t in FRICATION[sound]]
            highpass = butter(4, 2000, 'highpass', fs=sr, output='sos')
            old_band = sosfiltfilt(highpass, before)[start:end]
            new_band = sosfiltfilt(highpass, y)[start:end]
            frication_change = float(20*np.log10(rms(new_band)/rms(old_band)))
            assert frication_change > -2.5, (sound, 'Lost frication/aspiration', frication_change)
        # Leave headroom and avoid the old 17–20 dB blind boost of noisy clips.
        level = min(.25/active_rms(y, sr), .88/float(np.max(abs(y))))
        y *= level
        edge = round(sr*.02)
        y[:edge] *= np.linspace(0, 1, edge)
        y[-edge:] *= np.linspace(1, 0, edge)
        y = np.pad(y, (0, round(sr*.12)))
        target = DEST/row['file']
        sf.write(target, y, sr, subtype='PCM_16')
        check, check_rate = sf.read(target)
        assert check_rate == sr and len(check) == len(x)+round(sr*.12)
        assert np.isfinite(check).all() and abs(check).max() < .881
        assert np.all(check[-round(sr*.12):] == 0)
        assert noise_reduction > 6, (sound, 'Insufficient measured tail cleanup', noise_reduction)
        clips.append({
            **row, 'local_path': f'/academy/audio/special-i-native-v7/{target.name}',
            'source_file': f'../special-i-native-v6/{row["source_file"]}',
            'baseline_sha256': row['sha256'], 'sha256': digest(target),
            'bytes': target.stat().st_size, 'duration_seconds': round(len(check)/sr, 5),
            'gain_db': round(float(20*np.log10(level)), 3),
            'peak': round(float(abs(check).max()), 6), 'active_rms': round(active_rms(check, sr), 6),
            'noise_profile_seconds': [round(len(x)/sr-.09, 5), round(len(x)/sr-.03, 5)],
            'tail_noise_reduction_db_at_equal_gain': round(float(noise_reduction), 3),
            'frication_band_change_db_before_level_matching': None if frication_change is None else round(frication_change, 3),
            'qa': 'PENDING_QA',
        })
    (DEST/'manifest.json').write_text(json.dumps({
        **{k: baseline[k] for k in ['source', 'source_commit', 'speaker', 'license_as_stated', 'license_sha256']},
        'processing': 'Same original takes as v6. 100 Hz zero-phase high-pass, stationary tail-noise-profile spectral attenuation (1024-point Hann STFT, 256-sample hop, smoothed soft mask), active RMS target .25 with .88 peak ceiling, 20 ms quiet file-edge ramps, 120 ms trailing silence. No speech gate, pitch/speed/voice change, vowel splice, stretch or repeated cycles.',
        'scope': 'Noise cleanup of all seven special-i recordings. Original files and LICENSE retained in ../special-i-native-v6/originals/.',
        'clips': clips,
    }, indent=2), encoding='utf-8')
    (DEST/'NOTICE.md').write_text(
        '# Noise-cleaned unified special-i recordings\n\n'
        'Source: https://github.com/davinfifield/mp3-chinese-pinyin-sound\n'
        'Pinned commit: aa25ecce7b7fb02757b2c2b8e3c01aa975812edc\n'
        'Speaker: not named by upstream. Repository license: Unlicense.\n'
        'Exact LICENSE and unmodified MP3s remain in ../special-i-native-v6/originals/.\n\n'
        'Modified 2026-11-13: noise-profile spectral cleanup from originals,\n'
        '100 Hz high-pass, soft mask smoothed in time/frequency, constant gain,\n'
        '20 ms quiet file-edge ramps and 120 ms trailing silence. No speech\n'
        'gate, synthetic/replaced phonemes, speed/pitch edits, repeated cycles,\n'
        'voice change or time stretching. PCM16 WAV at original 44.1 kHz.\n'
        'Manifest records source/output hashes, measured noise reduction and\n'
        'frication-band preservation. Measures are technical checks, not a\n'
        'phonetic or perceptual certification. Human review: PENDING_QA.\n', encoding='utf-8')
    print(json.dumps([{k:r[k] for k in ['pinyin','tail_noise_reduction_db_at_equal_gain','frication_band_change_db_before_level_matching','peak']} for r in clips]))


if __name__ == '__main__':
    main()
