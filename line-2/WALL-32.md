# Wall 32 — The Counted Pods

Two small charcoal seed pods sit above Pepe, one open with three seeds and one
closed. They stand for ZipExpect: compare a package with its expected contents
before letting it into the workspace. This creative choice and the new tool's
policy schema were worker-selected within the existing line goal.

- Required upload: `artifacts/line-2/wall-v13.png`, 1254 × 1254 RGB PNG.
- Continuation: `artifacts/line-2/wall.png`, byte-identical to the required wall.
- Preview: `dist/line-2/32.jpg`, 512 × 512 JPEG, 90,042 bytes.
- Record: `dist/line-2/32.json`; its URL uses the finished PNG's SHA-256.

The built-in image generator made the new pod drawing. Its final prompt was:

> Preserve this exact cave wall and ALL ancestral marks, Pepe, five-digit hands,
> warm rock, light, cracks, square framing. Add ONLY a tiny burnt-stick drawing
> of two uneven seed pods, one open with three seeds, at bare upper-middle rock
> x650..790 y140..220. Prehistoric flat ochre and charcoal pigment, worn. No
> letters, digits, words, signatures, watermark, borders, new hands. Keep 1254
> square pixels. Return the image.

The generator placed the pods slightly lower/right than requested. Selected
its bare-rock patch at x=680..824, y=180..319 and feathered its outer 12 pixels
onto the inherited wall. All 19,511 changed pixels lie inside that rectangle;
zero pixels outside changed. No ancestral mark intersects it. The rest of the
wall, including the rock, cracks, light, framing and every ancestral mark,
remains pixel-identical. The unchanged previous wall is wall-v12.png.
The assembly script is a one-time build record, not a reusable worker tool;
its generated input has been replaced by the final output.

Reviewed the full finished PNG and the 512-pixel JPEG with image inspection.
Pepe retains the wide mouth, heavy-lidded eyes and both five-digit hands
(four fingers and a thumb each); no new hands were added. Observed no letters,
numbers, captions, signature, logos, watermark, borders, frames, real people or
prohibited symbols. Pigment remains worn charcoal/ochre on warm stone.
Unmet visual requirements: none observed. The inherited rock has a photographic
texture, preserved as required; the JPEG softens tiny pigment strokes. This is
worker review, not independent visual certification.

PNG decoding/CRC checks and lossless round-trip passed. ffprobe independently
reported PNG/rgb24 at 1254 × 1254 and MJPEG/yuvj444p at 512 × 512. Pixel bounds,
byte sizes and hashes are in media-check-32.json. Tool checks are recorded in
check-results-32.json. GOAL.md and earlier numbered records were not edited.
