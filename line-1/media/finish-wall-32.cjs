// Keep only the small gate edit and all ancestral pixels from the inherited wall.
const fs = require('node:fs');
const crypto = require('node:crypto');
const {decode, encode, thumbnail} = require('./finish-wall.cjs');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const previousBytes = fs.readFileSync('artifacts/line-1/wall.png');
const generatedBytes = fs.readFileSync('artifacts/line-1/wall-v13.png');
const old = decode(previousBytes);
const generated = decode(generatedBytes);
if (old.width !== generated.width || old.height !== generated.height) throw Error('size changed');
const result = {...old, pixels: Buffer.from(old.pixels)};
const bounds = {left: 1020, top: 800, right: 1152, bottom: 926};
const feather = 12;
let changed = 0, protectedPixels = 0, outsideMaskChanged = 0;
for (let y = 0; y < old.height; y++) for (let x = 0; x < old.width; x++) {
  const a = Math.max(0, Math.min(1, (x-bounds.left)/feather,
    (bounds.right-x)/feather, (y-bounds.top)/feather,
    (bounds.bottom-y)/feather));
  if (!a) protectedPixels++;
  const offset = (y*old.width+x)*3;
  let differs = false;
  for (let c = 0; c < 3; c++) {
    result.pixels[offset+c] = Math.round(old.pixels[offset+c]*(1-a) + generated.pixels[offset+c]*a);
    differs ||= result.pixels[offset+c] !== old.pixels[offset+c];
  }
  if (!a && differs) outsideMaskChanged++;
  if (differs) changed++;
}
if (outsideMaskChanged !== 0) throw Error('pixel outside mask changed');
if (changed < 1000) throw Error('new mark missing');
const png = encode(result), jpeg = thumbnail(result);
if (!decode(png).pixels.equals(result.pixels)) throw Error('PNG roundtrip failed');
if (jpeg.length > 100000) throw Error('JPEG over 100 KB');
fs.writeFileSync('artifacts/line-1/wall-v13.png', png);
fs.unlinkSync('artifacts/line-1/wall.png');
fs.writeFileSync('artifacts/line-1/wall.png', png);
fs.writeFileSync('dist/line-1/32.jpg', jpeg);
const report = {previous_sha256: hash(previousBytes), sha256: hash(png),
  format: 'PNG', width: old.width, height: old.height, png_bytes: png.length,
  preview_format: 'JPEG', preview_width: 512, preview_height: 512,
  preview_bytes: jpeg.length, bounds, feather_pixels: feather,
  changed_pixels: changed, protected_pixels: protectedPixels,
  total_pixels: old.width*old.height, outside_mask_changed_pixels: outsideMaskChanged,
  png_roundtrip_passed: true};
fs.writeFileSync('line-1/media-check-32.json', JSON.stringify(report, null, 2)+'\n');
console.log(JSON.stringify(report, null, 2));
