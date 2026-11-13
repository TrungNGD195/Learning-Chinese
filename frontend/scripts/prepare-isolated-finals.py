"""Prepare local-review ai/eng/ong/er takes from preserved standalone sources.

uv run --no-project --with numpy --with scipy --with soundfile python frontend/scripts/prepare-isolated-finals.py
Upstream has no declared license; these local candidates are NOT cleared for
commercial redistribution. Preserve provenance and resolve rights before deploy.
No TTS calls, consonant removal, vowel splice, pitch edit or time stretching.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT/'frontend/public/academy/audio/isolated-finals-v1'
COMMIT = '62453b2a5ca6873eac1f4293b6e9794715d0fc8a'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    clips = []
    for symbol in ['ai', 'eng', 'ong', 'er']:
        original = DEST/'originals'/f'{symbol}.mp3'
        x, sr = sf.read(original, dtype='float64')
        assert x.ndim == 1 and sr == 22050 and np.isfinite(x).all()
        y = sosfiltfilt(butter(4, 70, 'highpass', fs=sr, output='sos'), x)
        hop = round(sr*.02)
        frames = [y[i:i+hop] for i in range(0,len(y),hop)]
        power = np.array([np.mean(f**2) for f in frames])
        active = np.concatenate([f for f,p in zip(frames,power) if p > power.max()*.04])
        gain = min(.25/np.sqrt(np.mean(active**2)), .88/abs(y).max())
        y *= gain
        edge = round(sr*.005)
        assert np.sqrt(np.mean(y[-edge:]**2)) < .01
        y[:edge] *= np.linspace(0,1,edge)
        y[-edge:] *= np.linspace(1,0,edge)
        y = np.pad(y,(0,round(sr*.12)))
        target = DEST/f'{symbol}.wav'
        sf.write(target,y,sr,subtype='PCM_16')
        check, rate = sf.read(target)
        assert rate == sr and len(check) == len(x)+round(sr*.12)
        assert np.isfinite(check).all() and abs(check).max() < .881
        assert np.all(check[-round(sr*.12):] == 0)
        clips.append({
            'symbol':symbol,'file':target.name,'local_path':f'/academy/audio/isolated-finals-v1/{target.name}',
            'source_file':f'originals/{symbol}.mp3','source_sha256':digest(original),
            'source_url':f'https://raw.githubusercontent.com/cmguo/PinYinSound/{COMMIT}/{symbol}.mp3',
            'sha256':digest(target),'sample_rate':sr,'duration_seconds':round(len(check)/sr,5),
            'source_duration_seconds':round(len(x)/sr,5),'gain_db':round(float(20*np.log10(gain)),3),
            'peak':round(float(abs(check).max()),6),'tone':'level educational final (unmarked in UI)',
            'qa':'PENDING_QA',
        })
    (DEST/'manifest.json').write_text(json.dumps({
        'source':'cmguo/PinYinSound','source_commit':COMMIT,'speaker':'Not named upstream',
        'license_status':'UNDECLARED_UPSTREAM_LOCAL_REVIEW_ONLY',
        'scope':'Four complete standalone-final takes, never cut from feng/zhong. Local review only; not cleared for commercial redistribution.',
        'processing':'Complete source takes, original 22050 Hz, 70 Hz zero-phase rumble filter, constant level matching (.25 active RMS / .88 peak ceiling), 5 ms quiet file-edge ramps, 120 ms silence. No pitch/speed change, consonant removal, vowel splice, spoken-end cut or stretching.',
        'clips':clips,
    },indent=2),encoding='utf-8')
    (DEST/'NOTICE.md').write_text(
        '# Standalone finals: LOCAL REVIEW ONLY\n\n'
        'Source: https://github.com/cmguo/PinYinSound\n'
        f'Pinned commit: {COMMIT}\n'
        'Speaker not named upstream. No license is declared in that repository.\n'
        'Do not describe these recordings as MIT, public domain or cleared for\n'
        'commercial redistribution. Resolve recording rights or replace these\n'
        'local candidates before deployment.\n\n'
        'Preserved originals: originals/{ai,eng,ong,er}.mp3.\n'
        'Modified 2026-11-13: decoded full takes to PCM16 WAV, removed low rumble\n'
        'with a 70 Hz zero-phase high-pass, applied constant gain, 5 ms quiet\n'
        'file-edge ramps and appended 120 ms silence. No voice/pitch/speed change,\n'
        'vowel splice, consonant removal or time stretching. These are complete\n'
        'standalone-final files, not combined syllables renamed as eng or ong.\n'
        'Hashes, durations and levels: manifest.json. Listening QA: PENDING_QA.\n',encoding='utf-8')
    print(json.dumps([{k:c[k] for k in ['symbol','duration_seconds','gain_db','peak']} for c in clips]))


if __name__ == '__main__':
    main()
