/*
Copyright (c) 2021 Advanced Micro Devices, Inc. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

WGSL FP32 adaptation of AMD FSR1 EASU and RCAS.
Uses full-precision reciprocals instead of vendor approximation intrinsics.
Source and revision: third_party/fsr1/UPSTREAM.md
*/

struct Blit { width:u32, height:u32, current:u32, previous:u32, blend:u32, out_width:u32, out_height:u32, options:u32 }
@group(0) @binding(0) var<storage,read> pixels:array<u32>;
@group(0) @binding(1) var<uniform> blit:Blit;
@group(0) @binding(2) var easu_image:texture_2d<f32>;
struct VertexOut { @builtin(position) position:vec4<f32>, @location(0) uv:vec2<f32> }
@vertex fn vs(@builtin(vertex_index) i:u32)->VertexOut {
 let p=vec2<f32>(f32((i<<1u)&2u),f32(i&2u));
 var o:VertexOut;o.position=vec4<f32>(p*2.0-1.0,0.0,1.0);o.uv=vec2<f32>(p.x,1.0-p.y);return o;
}
fn source_px(p:vec2<i32>)->vec3<f32> {
 let c=vec2<u32>(clamp(p,vec2<i32>(0),vec2<i32>(i32(blit.width)-1,i32(blit.height)-1)));
 let offset=c.y*blit.width+c.x;
 var rgb=unpack4x8unorm(pixels[blit.current+offset]).rgb;
 if(blit.blend!=0u){rgb=(rgb+unpack4x8unorm(pixels[blit.previous+offset]).rgb)*0.5;}
 return rgb;
}
fn fsr_luma(c:vec3<f32>)->f32 {return c.b*0.5+(c.r*0.5+c.g);}
// EASU's four bilinearly weighted five-sample gradients.
fn easu_set(weight:f32,a:f32,b:f32,c:f32,d:f32,e:f32)->vec3<f32> {
 let dx=d-b;let dy=e-a;
 let lx=clamp(abs(dx)/max(max(abs(d-c),abs(c-b)),1e-6),0.0,1.0);
 let ly=clamp(abs(dy)/max(max(abs(e-c),abs(c-a)),1e-6),0.0,1.0);
 return vec3<f32>(dx,dy,lx*lx+ly*ly)*weight;
}
fn easu(uv:vec2<f32>)->vec3<f32> {
 let pos=uv*vec2<f32>(f32(blit.width),f32(blit.height))-0.5;
 let origin=vec2<i32>(floor(pos));let f=fract(pos);
 var offsets=array<vec2<i32>,12>(vec2<i32>(0,-1),vec2<i32>(1,-1),vec2<i32>(-1,0),vec2<i32>(0,0),vec2<i32>(1,0),vec2<i32>(2,0),vec2<i32>(-1,1),vec2<i32>(0,1),vec2<i32>(1,1),vec2<i32>(2,1),vec2<i32>(0,2),vec2<i32>(1,2));
 var c:array<vec3<f32>,12>;var l:array<f32,12>;
 for(var i=0u;i<12u;i++){c[i]=source_px(origin+offsets[i]);l[i]=fsr_luma(c[i]);}
 var gradient=easu_set((1.0-f.x)*(1.0-f.y),l[0],l[2],l[3],l[4],l[7]);
 gradient+=easu_set(f.x*(1.0-f.y),l[1],l[3],l[4],l[5],l[8]);
 gradient+=easu_set((1.0-f.x)*f.y,l[3],l[6],l[7],l[8],l[10]);
 gradient+=easu_set(f.x*f.y,l[4],l[7],l[8],l[9],l[11]);
 var direction=gradient.xy;let magnitude=dot(direction,direction);
 if(magnitude<1.0/32768.0){direction=vec2<f32>(1.0,0.0);}else{direction*=inverseSqrt(magnitude);}
 let edge=gradient.z*gradient.z*0.25;
 let stretch=dot(direction,direction)/max(max(abs(direction.x),abs(direction.y)),1e-6);
 let anisotropy=vec2<f32>(1.0+(stretch-1.0)*edge,1.0-0.5*edge);
 let lobe=0.5+((0.25-0.04)-0.5)*edge;let clip_distance=1.0/lobe;
 var color=vec3<f32>(0.0);var weights=0.0;
 for(var i=0u;i<12u;i++) {
  let offset=vec2<f32>(offsets[i])-f;
  let rotated=vec2<f32>(dot(offset,direction),dot(offset,vec2<f32>(-direction.y,direction.x)))*anisotropy;
  let distance=min(dot(rotated,rotated),clip_distance);
  let base=0.4*distance-1.0;let window=lobe*distance-1.0;
  let weight=(1.5625*base*base-0.5625)*window*window;
  color+=c[i]*weight;weights+=weight;
 }
 let low=min(min(c[3],c[4]),min(c[7],c[8]));let high=max(max(c[3],c[4]),max(c[7],c[8]));
 return clamp(color/max(weights,1e-6),low,high);
}
@fragment fn fs_easu(in:VertexOut)->@location(0) vec4<f32> {return vec4<f32>(easu(in.uv),1.0);}
fn easu_px(p:vec2<i32>)->vec3<f32> {
 return textureLoad(easu_image,clamp(p,vec2<i32>(0),vec2<i32>(i32(blit.out_width)-1,i32(blit.out_height)-1)),0).rgb;
}
@fragment fn fs_rcas(in:VertexOut)->@location(0) vec4<f32> {
 let p=vec2<i32>(floor(in.uv*vec2<f32>(f32(blit.out_width),f32(blit.out_height))));
 let b=easu_px(p+vec2<i32>(0,-1));let d=easu_px(p+vec2<i32>(-1,0));let e=easu_px(p);
 let f=easu_px(p+vec2<i32>(1,0));let h=easu_px(p+vec2<i32>(0,1));
 let low=min(min(b,d),min(f,h));let high=max(max(b,d),max(f,h));
 let hit_min=min(low,e)/max(4.0*high,vec3<f32>(1e-6));
 let hit_max=(1.0-max(high,e))/min(4.0*low-4.0,vec3<f32>(-1e-6));
 let limit=max(-hit_min,hit_max);
 let lobe=max(-0.1875,min(max(max(limit.r,limit.g),limit.b),0.0))*0.75;
 let color=(e+(b+d+f+h)*lobe)/(1.0+4.0*lobe);
 return vec4<f32>(clamp(color,vec3<f32>(0.0),vec3<f32>(1.0)),1.0);
}
