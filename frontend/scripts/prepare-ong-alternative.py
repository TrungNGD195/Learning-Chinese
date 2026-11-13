"""Prepare the longer ong take for LOCAL listening review only.

uv run --no-project --with numpy --with scipy --with soundfile python frontend/scripts/prepare-ong-alternative.py
No TTS, time stretching, pitch edits, splicing or consonant removal.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT/'frontend/public/academy/audio/isolated-finals-v2'
SOURCE_SHA = '7e179709f6c07a69379de9a9ff25ee6388c4fb49292972515a658a8a83db3aab'
URL = 'https://raw.githubusercontent.com/zispace/hanyu-pinyin-audio/2b4e7e6ba31d6cc79ebca6c910729767d9168a7e/sreading.org/pinyin/ong.mp3'


def main():
    source = DEST/'originals/ong.mp3'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA
    x, sr = sf.read(source, dtype='float64')
    source_channels = 1 if x.ndim == 1 else x.shape[1]
    if x.ndim == 2:
        assert x.shape[1] == 2 and np.corrcoef(x.T)[0,1] > .98
        x = x.mean(axis=1)
    assert x.ndim == 1 and sr == 44100 and np.isfinite(x).all()
    # The source has ~.5 s of leading silence. Keep 60 ms ahead of any
    # detected signal and the entire recorded release; never lengthen the vowel.
    active = np.flatnonzero(abs(x) > .005)
    start = max(0, int(active[0])-round(sr*.06))
    end = min(len(x), int(active[-1])+round(sr*.12))
    assert abs(x[:start]).max() < .005 and abs(x[end:]).max() < .005
    y = sosfiltfilt(butter(4,70,'highpass',fs=sr,output='sos'),x)[start:end]
    hop = round(sr*.02)
    frames = [y[i:i+hop] for i in range(0,len(y),hop)]
    powers = np.array([np.mean(f**2) for f in frames])
    voiced = np.concatenate([f for f,p in zip(frames,powers) if p > powers.max()*.04])
    gain = min(.25/np.sqrt(np.mean(voiced**2)), .88/abs(y).max())
    y *= gain
    edge = round(sr*.005)
    assert np.sqrt(np.mean(y[-edge:]**2)) < .005
    y[:edge] *= np.linspace(0,1,edge)
    y[-edge:] *= np.linspace(1,0,edge)
    y = np.pad(y,(0,round(sr*.10)))
    target = DEST/'ong.wav'
    sf.write(target,y,sr,subtype='PCM_16')
    check, rate = sf.read(target)
    assert rate == sr and np.isfinite(check).all() and abs(check).max() < .881
    assert np.all(check[-round(sr*.1):] == 0)
    manifest = {
        'symbol':'ong','file':'ong.wav','local_path':'/academy/audio/isolated-finals-v2/ong.wav',
        'source_url':URL,'source_file':'originals/ong.mp3','source_sha256':SOURCE_SHA,
        'source_attribution':'SReading pinyin collection as labeled by zispace/hanyu-pinyin-audio mirror; speaker not named',
        'source_page':'https://www.sreading.org/zh-hans/pinyin-pathway',
        'license_status':'NOT_CLEARED_FOR_REDISTRIBUTION_LOCAL_REVIEW_ONLY',
        'sample_rate':sr,'source_channels':source_channels,'output_channels':1,'source_duration_seconds':round(len(x)/sr,5),
        'source_window_seconds':[round(start/sr,5),round(end/sr,5)],
        'duration_seconds':round(len(check)/sr,5),'gain_db':round(float(20*np.log10(gain)),3),
        'peak':round(float(abs(check).max()),6),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'processing':'Different complete ong take. Trim only low-level outside silence, 70 Hz zero-phase rumble filter, constant gain, 5 ms quiet edges, 100 ms quiet release. No speed/pitch edit, phoneme splice, repeated samples or consonant removal.',
        'qa':'PENDING_QA',
    }
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (DEST/'NOTICE.md').write_text(
        '# Alternative ong: LOCAL REVIEW ONLY\n\n'
        'Source collection labeled SReading in zispace/hanyu-pinyin-audio.\n'
        'https://www.sreading.org/zh-hans/pinyin-pathway\n'
        f'Pinned mirror URL: {URL}\n'
        'Speaker unspecified; no redistribution permission verified. Resolve\n'
        'recording rights or replace this local candidate before deploying.\n\n'
        'Modified 2026-11-13: remove only outside low-level silence, 70 Hz\n'
        'zero-phase rumble filter, constant level matching, 5 ms quiet edge\n'
        'ramps and appended silence. Keep the complete source articulation\n'
        'and release at native speed/pitch. No stretch, repeat, vowel splice\n'
        'or consonant removal. Original MP3 retained in originals/.\n'
        'Hashes and exact source window: manifest.json. Listening QA PENDING_QA.\n',encoding='utf-8')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
