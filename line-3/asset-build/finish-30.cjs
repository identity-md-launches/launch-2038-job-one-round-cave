// One-shot pigment transfer. Does not execute tools or access configuration.
const fs=require('node:fs'), crypto=require('node:crypto');
const media=require('./png_codec.cjs');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const source='artifacts/line-3/wall-v10.png', destination='artifacts/line-3/wall-v13.png';
const ancestral=fs.readFileSync(source), generatedBytes=fs.readFileSync(destination);
if(hash(ancestral)!=='cf31ce389bd0bcdadef74582c4dcde69740e23e92ee8eb519c7eaeeaf6e59aaa') throw Error('Wrong inherited wall');
if(hash(generatedBytes)!=='6133d4c9fb06ff386e0479c2be70227ca0d31b4c430e50e1d20875ace67d689e') throw Error('Original generated image required; do not rerun on the finished output');
const old=media.decode(ancestral), generated=media.decode(generatedBytes);
const out={...old,pixels:Buffer.from(old.pixels)}, box=[60,568,121,88];
let changed=0;
for(let y=box[1];y<box[1]+box[3];y++) for(let x=box[0];x<box[0]+box[2];x++) {
  const i=(y*old.width+x)*3, [r,g,b]=generated.pixels.subarray(i,i+3);
  // Only copy generated pigment, leaving original stone texture underneath.
  const pebble=(x-91)**2/16**2+(y-595)**2/17**2<1 || (x-120)**2/18**2+(y-586)**2/18**2<1;
  const basket=y>=599 && y<=652 && x>=65+Math.max(0,y-613)*.55 && x<=150-Math.max(0,y-613)*.45;
  const outsidePebble=(x-160)**2/17**2+(y-636)**2/20**2<1;
  if(!pebble && !basket && !outsidePebble) continue;
  const charcoal=r<76 && g<65 && b<51;
  const red=r>93 && r>g*1.55 && r-b>55 && g<95;
  const ochre=(x-160)**2/14**2+(y-636)**2/18**2<1 && r>115 && g>78 && g<150 && r-g>27 && g-b>28;
  if(!charcoal && !red && !ochre) continue;
  const color=charcoal?[43,32,22]:red?[151,65,31]:[182,124,48];
  const alpha=charcoal?.68:red?.67:.52;
  for(let c=0;c<3;c++) out.pixels[i+c]=Math.round(old.pixels[i+c]*(1-alpha)+color[c]*alpha);
  if(!out.pixels.subarray(i,i+3).equals(old.pixels.subarray(i,i+3))) changed++;
}
let outside=0;
for(let y=0;y<old.height;y++) for(let x=0;x<old.width;x++) {
  if(x>=box[0] && x<box[0]+box[2] && y>=box[1] && y<box[1]+box[3]) continue;
  const i=(y*old.width+x)*3;
  if(!out.pixels.subarray(i,i+3).equals(old.pixels.subarray(i,i+3))) outside++;
}
if(outside || changed<500) throw Error('Preservation failure');
const bytes=media.encode(out), preview=media.thumbnail(out);
if(!media.decode(bytes).pixels.equals(out.pixels) || preview.length>100000) throw Error('Format check failed');
fs.writeFileSync(destination,bytes);
fs.unlinkSync('artifacts/line-3/wall.png');
fs.symlinkSync('wall-v13.png','artifacts/line-3/wall.png');
fs.writeFileSync('dist/line-3/30.jpg',preview,{flag:'wx'});
const result={source,source_sha256:hash(ancestral),generated_sha256:hash(generatedBytes),output:destination,
  output_sha256:hash(bytes),patch_xywh:box,changed_pixels:changed,changed_pixels_outside_patch:outside,
  png_dimensions:[1254,1254],png_format:'RGB PNG',png_bytes:bytes.length,
  jpeg_dimensions:[512,512],jpeg_format:'JPEG',jpeg_bytes:preview.length,
  method:'Generated basket pigment blended onto original stone; all pixels outside the patch preserved.'};
fs.writeFileSync('line-3/asset-build/preservation-30.json',JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(result,null,2));
