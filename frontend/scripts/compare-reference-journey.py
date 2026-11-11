"""Compare a real browser hero capture with the exact user-supplied painting."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

root = Path(__file__).resolve().parents[2]
folder = root / '.impeccable/review/diff/hero'
folder.mkdir(parents=True, exist_ok=True)
source = root / 'frontend/public/academy/great-wall/reference-v1/approved-layout.png'
expected = Image.open(source).convert('RGB').crop((271, 119, 1487, 723))
actual = Image.open(root / '.impeccable/review/reference-journey/reference-hero-art-1438.png').convert('RGB')
assert actual.size == expected.size == (1216, 604)
difference = ImageChops.difference(actual, expected)
above_controls = difference.crop((0, 0, 1216, 520))
report = {
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'viewport': [1438, 940],
    'hero_size': list(actual.size),
    'comparison': 'Real browser Bài 3 hero vs original source crop, no rescaling.',
    'whole_hero_mean_absolute_error_rgb': ImageStat.Stat(difference).mean,
    'difference_bounds': difference.getbbox(),
    'art_above_navigation_mean_absolute_error_rgb': ImageStat.Stat(above_controls).mean,
    'art_above_navigation_identical': above_controls.getbbox() is None,
    'limits': 'Native footer is intentionally functional HTML. This comparison does not certify the surrounding sidebar, mobile crops or enlarged 448x207 phase scenes as pixel-identical.',
}
expected.save(folder / 'reference.png')
actual.save(folder / 'browser.png')
pair = Image.new('RGB', (2432, 604))
pair.paste(expected, (0, 0))
pair.paste(actual, (1216, 0))
pair.save(folder / 'side-by-side.png')
difference.point(lambda value: min(255, value * 6)).save(folder / 'heatmap.png')
(folder / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
assert report['art_above_navigation_identical']
