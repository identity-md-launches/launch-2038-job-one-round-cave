// One-time assembly; generated input is replaced by the finished wall.
// Assemble only the new upper-middle seed-pod patch onto the inherited wall.
// The generated source is deliberately not used outside this bounded area.
const fs = require('node:fs');
const crypto = require('node:crypto');
const {decode, encode, thumbnail} = require('../line-1/media/finish-wall.cjs');

const oldPath = 'artifacts/line-2/wall-v12.png';
const generatedPath = 'artifacts/line-2/wall-v13.png';
const oldBytes = fs.readFileSync(oldPath);
const generatedBytes = fs.readFileSync(generatedPath);
const old = decode(oldBytes);
const generated = decode(generatedBytes);
if (old.width !== generated.width || old.height !== generated.height)
  throw new Error('wall dimensions changed');
const result = {...old, pixels: Buffer.from(old.pixels)};
const bounds = {left: 680, top: 180, right: 825, bottom: 320};
const feather = 12;
for (let y = bounds.top; y < bounds.bottom; y++) {
  for (let x = bounds.left; x < bounds.right; x++) {
    const edge = Math.min(x - bounds.left, bounds.right - 1 - x,
      y - bounds.top, bounds.bottom - 1 - y);
    const alpha = Math.max(0, Math.min(1, edge / feather));
    const i = (y * old.width + x) * 3;
    for (let c = 0; c < 3; c++)
      result.pixels[i + c] = Math.round(old.pixels[i + c] * (1 - alpha) +
        generated.pixels[i + c] * alpha);
  }
}
let changed = 0, outside = 0;
for (let y = 0; y < old.height; y++) for (let x = 0; x < old.width; x++) {
  const i = (y * old.width + x) * 3;
  let differs = false;
  for (let c = 0; c < 3; c++) differs ||= old.pixels[i + c] !== result.pixels[i + c];
  if (differs) { changed++; if (x < bounds.left || x >= bounds.right || y < bounds.top || y >= bounds.bottom) outside++; }
}
if (!changed || outside) throw new Error('bounded preservation failed');
const png = encode(result);
const jpg = thumbnail(result);
if (!decode(png).pixels.equals(result.pixels)) throw new Error('PNG roundtrip failed');
if (jpg.length > 100000) throw new Error('JPEG exceeds 100 KB');
fs.writeFileSync('artifacts/line-2/wall-v13.png', png);
fs.writeFileSync('artifacts/line-2/wall.png', png);
fs.writeFileSync('dist/line-2/32.jpg', jpg);
const sha256 = crypto.createHash('sha256').update(png).digest('hex');
fs.writeFileSync('line-2/media-check-32.json', JSON.stringify({
  previous_sha256: crypto.createHash('sha256').update(oldBytes).digest('hex'),
  sha256, format: 'PNG', width: result.width, height: result.height,
  png_bytes: png.length, preview_format: 'JPEG', preview_width: 512,
  preview_height: 512, preview_bytes: jpg.length, bounds, feather,
  changed_pixels: changed, outside_mark_changed_pixels: outside,
  png_roundtrip_passed: true
}, null, 2) + '\n');
console.log(JSON.stringify({sha256, changed_pixels: changed, outside_mark_changed_pixels: outside,
  png_bytes: png.length, preview_bytes: jpg.length}, null, 2));
