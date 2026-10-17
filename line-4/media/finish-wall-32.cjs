// Read-only workspace inputs; transfer generated pigment, never generated rock.
// Run once after generation: the draft path becomes the completed wall.
const fs=require('node:fs'),crypto=require('node:crypto');
const {decode,encode,thumbnail}=require('../../line-1/media/finish-wall.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const previous=fs.readFileSync('artifacts/line-4/wall-v12.png');
if(JSON.parse(fs.readFileSync('dist/line-4/31.json')).image!==
   'https://api.imd.fun/artifacts/'+sha(previous))throw Error('ancestor mismatch');
const draft=fs.readFileSync('artifacts/line-4/wall-v13.png');
const old=decode(previous),gen=decode(draft),out={...old,pixels:Buffer.from(old.pixels)};
const bounds=[900,230,980,385];
let changed=0;
for(let y=bounds[1];y<=bounds[3];y++)for(let x=bounds[0];x<=bounds[2];x++){
 const sx0=495+(x-bounds[0])*250/81,sy0=365+(y-bounds[1])*500/156;
 let n=0,ochre=0,black=0;
 for(let sy=Math.floor(sy0);sy<Math.ceil(sy0+500/156);sy++)for(let sx=Math.floor(sx0);sx<Math.ceil(sx0+250/81);sx++){
  const j=(sy*gen.width+sx)*3,r=gen.pixels[j],g=gen.pixels[j+1],b=gen.pixels[j+2];
  n++;
  // Select bright ochre rather than orange rock. Black only near the knot,
  // so unrelated dark cracks cannot be transferred to the wall.
  if(r>190&&g>113&&g/r>.51&&b/g<.52)ochre++;
  else if(sy>578&&sy<720&&sx>540&&sx<740&&r<112&&g<85&&b<60)black++;
 }
 const j=(y*old.width+x)*3;
 const grain=.75+.25*(old.pixels[j]+old.pixels[j+1])/510;
 const ao=.88*grain*ochre/n,ab=.82*grain*black/n,a=ao+ab;
 for(let c=0;c<3;c++)out.pixels[j+c]=Math.round(old.pixels[j+c]*(1-a)+[199,135,46][c]*ao+[39,29,20][c]*ab);
 if(!out.pixels.subarray(j,j+3).equals(old.pixels.subarray(j,j+3)))changed++;
}
let outside=0;
for(let y=0;y<old.height;y++)for(let x=0;x<old.width;x++){
 if(x>=bounds[0]&&x<=bounds[2]&&y>=bounds[1]&&y<=bounds[3])continue;
 const j=(y*old.width+x)*3;
 if(!old.pixels.subarray(j,j+3).equals(out.pixels.subarray(j,j+3)))outside++;
}
if(outside||changed<800)throw Error('preservation/addition check failed');
const png=encode(out),jpg=thumbnail(out);
if(jpg.length>100000||!decode(png).pixels.equals(out.pixels))throw Error('encoding check failed');
fs.writeFileSync('artifacts/line-4/wall-v13.png',png);
// Unlink canonical alias before writing so an inherited hardlink is untouched.
fs.unlinkSync('artifacts/line-4/wall.png');
fs.linkSync('artifacts/line-4/wall-v13.png','artifacts/line-4/wall.png');
fs.writeFileSync('artifacts/line-4/32.jpg',jpg);
fs.linkSync('artifacts/line-4/32.jpg','dist/line-4/32.jpg');
const report={ancestor_sha256:sha(previous),generated_insert_sha256:sha(draft),
 wall:'artifacts/line-4/wall-v13.png',canonical_wall:'artifacts/line-4/wall.png',
 sha256:sha(png),dimensions:[out.width,out.height],format:'RGB PNG',bytes:png.length,
 preview:'dist/line-4/32.jpg',preview_dimensions:[512,512],preview_format:'JPEG',
 preview_bytes:jpg.length,preview_sha256:sha(jpg),addition_bounds_inclusive:bounds,
 changed_pixels:changed,pixels_changed_outside_addition:outside,png_roundtrip_passed:true,
 method:'Installed image generator; isolated pigment area-sampled and blended into original rock.',
 visual_review:'Pending full PNG and JPEG inspection.',
 unmet_visual_requirements:['Inherited photographic rock texture retained to preserve the existing wall.']};
fs.writeFileSync('line-4/review-32.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
