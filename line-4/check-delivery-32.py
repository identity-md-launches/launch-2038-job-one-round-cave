#!/usr/bin/env python3
"""Offline output-contract and preservation checks; workspace files only."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jpeg_dimensions(path):
    data = Path(path).read_bytes()
    assert data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'
    pos = 2
    while pos < len(data):
        assert data[pos] == 255
        marker = data[pos + 1]
        pos += 2
        size = struct.unpack('>H', data[pos:pos+2])[0]
        if marker in (0xC0, 0xC2):
            height, width = struct.unpack('>HH', data[pos+3:pos+7])
            return width, height
        assert marker != 0xDA, 'missing JPEG size before scan'
        pos += size
    raise AssertionError('missing JPEG size')


def main():
    wall = Path('artifacts/line-4/wall-v13.png')
    raw = wall.read_bytes()
    assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    width, height, depth, color = struct.unpack('>IIBB', raw[16:26])
    assert (width, height, depth, color) == (1254, 1254, 8, 2)
    assert raw == Path('artifacts/line-4/wall.png').read_bytes()
    record = json.loads(Path('dist/line-4/32.json').read_text())
    assert list(record) == ['name', 'image', 'attributes']
    assert record['image'] == 'https://api.imd.fun/artifacts/' + sha(wall)
    attrs = record['attributes']
    assert all(list(a) == ['trait_type', 'value'] for a in attrs)
    assert [a['trait_type'] for a in attrs] == ['Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing']
    assert [a['value'] for a in attrs[:4]] == ['Lava', 'Line 4', 32, 'HeaderCheck']
    assert type(attrs[2]['value']) is int
    assert len(list(Path('dist/line-4').glob('[0-9][0-9].json'))) == 32
    jpg = Path('dist/line-4/32.jpg')
    assert jpeg_dimensions(jpg) == (512, 512)
    assert jpg.read_bytes() == Path('artifacts/line-4/32.jpg').read_bytes()
    assert jpg.stat().st_size <= 100000
    original_goal = subprocess.check_output(['git', 'show', 'HEAD:line-4/GOAL.md'])
    assert original_goal == Path('line-4/GOAL.md').read_bytes()
    changed = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], text=True).splitlines()
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
    allowed = ('line-4/', 'artifacts/line-4/', 'dist/line-4/')
    assert all(p.startswith(allowed) for p in changed + untracked), (changed, untracked)
    assert not any(p.startswith('dist/line-4/') and p not in ('dist/line-4/32.json', 'dist/line-4/32.jpg')
                   for p in changed + untracked)
    for p in changed + untracked:
        file = Path(p)
        if file.is_file() and not p.startswith('artifacts/'):
            assert file.stat().st_size <= 100000, p
    # Decode both PNGs independently of the recorded review and compare every pixel.
    code = r'''
const fs=require('fs'),m=require('./line-1/media/finish-wall.cjs');
const a=m.decode(fs.readFileSync('artifacts/line-4/wall-v12.png'));
const b=m.decode(fs.readFileSync('artifacts/line-4/wall-v13.png'));
let changed=0,outside=0;
for(let y=0;y<a.height;y++)for(let x=0;x<a.width;x++){
 const j=(y*a.width+x)*3;
 if(!a.pixels.subarray(j,j+3).equals(b.pixels.subarray(j,j+3))){
  changed++;if(x<900||x>980||y<230||y>385)outside++;
 }
}
if(outside||!changed)throw Error('preservation check failed');
console.log(JSON.stringify({changed_pixels:changed,pixels_changed_outside_addition:outside}));
'''
    preservation = json.loads(subprocess.check_output(['node', '-e', code], text=True))
    evidence = json.loads(Path('line-4/review-32.json').read_text())
    assert evidence['changed_pixels'] == preservation['changed_pixels']
    assert evidence['sha256'] == sha(wall)
    report = dict(passed=True, goal_unchanged=True, older_records_unchanged=True,
                  png_dimensions=[width, height], png_format='RGB PNG',
                  jpeg_dimensions=list(jpeg_dimensions(jpg)), jpeg_format='JPEG',
                  jpeg_bytes=jpg.stat().st_size, output_sha256=sha(wall),
                  preservation=preservation, visual_review='See review-32.json; local review only.',
                  unmet_visual_requirements=evidence['unmet_visual_requirements'],
                  scope_check='All tracked changes and nonignored new files are within allowed folders.')
    Path('line-4/delivery-check-32.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
