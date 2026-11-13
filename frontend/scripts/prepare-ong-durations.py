"""Prepare pitch-preserving ong duration variants for matching device TTS zhong.

uv run --no-project --with numpy --with soundfile --with praat-parselmouth python frontend/scripts/prepare-ong-durations.py
Local review only; original v2 recording's unresolved rights still apply.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import soundfile as sf
import parselmouth
from parselmouth.praat import call

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'frontend/public/academy/audio/isolated-finals-v2'
DEST = ROOT/'frontend/public/academy/audio/isolated-finals-v4'


def pitch(sound):
    f = sound.to_pitch_ac(time_step=.005,pitch_floor=100,pitch_ceiling=500).selected_array['frequency']
    return float(np.median(f[f>0]))


def main():
    original = json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    source = BASE/'ong.wav'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original['sha256']
    x, sr = sf.read(source)
    assert np.all(x[-round(sr*.1):] == 0)
    speech = parselmouth.Sound(x[:-round(sr*.1)],sr)
    before_pitch = pitch(speech)
    manipulation = call(speech,'To Manipulation',.005,100,500)
    DEST.mkdir(exist_ok=True)
    clips = []
    for milliseconds in range(250,1251,50):
        quiet = round(sr*.06)
        ratio = (milliseconds/1000-.06)/speech.xmax
        tier = call('Create DurationTier','match',0,speech.xmax)
        call(tier,'Add point',0,ratio)
        call(tier,'Add point',speech.xmax,ratio)
        call([tier,manipulation],'Replace duration tier')
        shorter = call(manipulation,'Get resynthesis (overlap-add)')
        delta = float(12*np.log2(pitch(shorter)/before_pitch))
        assert abs(delta) < .15, (milliseconds,delta)
        y = shorter.values[0]
        expected = round(sr*milliseconds/1000)
        assert abs(expected-(len(y)+quiet)) < 3
        y = np.pad(y,(0,expected-len(y)))
        assert np.isfinite(y).all() and abs(y).max() < .881
        target = DEST/f'ong-{milliseconds}.wav'
        sf.write(target,y,sr,subtype='PCM_16')
        check, rate = sf.read(target)
        assert rate == sr and len(check) == expected and np.all(check[-round(sr*.05):] == 0)
        clips.append({'milliseconds':milliseconds,'file':target.name,
            'local_path':f'/academy/audio/isolated-finals-v4/{target.name}',
            'duration_seconds':len(check)/sr,'duration_ratio':ratio,
            'median_pitch_change_semitones':round(delta,5),
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'qa':'PENDING_QA'})
    (DEST/'manifest.json').write_text(json.dumps({
        'source_file':'../isolated-finals-v2/originals/ong.mp3',
        'source_url':original['source_url'],'source_sha256':original['source_sha256'],
        'prepared_input_file':'../isolated-finals-v2/ong.wav','prepared_input_sha256':original['sha256'],
        'license_status':original['license_status'],'sample_rate':sr,'default_milliseconds':550,
        'selection':'Nearest 50 ms to completed device-TTS zhong duration for the same voice; 250–1250 ms; otherwise default 550 ms. Reference is in-memory only.',
        'processing':'Praat overlap-add duration resynthesis with unchanged pitch tier; full articulation/release compressed, 60 ms trailing silence. No browser playback-rate shift, new voice or end-cut timer.',
        'clips':clips,
    },indent=2),encoding='utf-8')
    (DEST/'NOTICE.md').write_text(
        '# Device-duration-matched ong: LOCAL REVIEW ONLY\n\n'
        'Same SReading-labeled source as isolated-finals-v2; original MP3, source\n'
        'URL and rights status remain there. Speaker identity/redistribution\n'
        'permission unverified; resolve rights or replace before deployment.\n\n'
        'Modified 2026-11-13: pitch-preserving Praat duration resynthesis for\n'
        '250–1250 ms playback variants. Keep pitch tier; append 60 ms silence.\n'
        'The lesson selects the nearest 50 ms to the completed browser-TTS\n'
        'zhong duration, for that voice, in this session. Default is 550 ms.\n'
        'This is processed duration, not an untouched source take. Articulation\n'
        'quality still requires listening QA; status PENDING_QA. Source/input/\n'
        'output hashes and pitch checks are in manifest.json.\n',encoding='utf-8')
    print(json.dumps({'clips':len(clips),'default_ms':550,'max_pitch_change_semitones':max(abs(c['median_pitch_change_semitones']) for c in clips),'total_bytes':sum((DEST/c['file']).stat().st_size for c in clips)}))


if __name__ == '__main__':
    main()
