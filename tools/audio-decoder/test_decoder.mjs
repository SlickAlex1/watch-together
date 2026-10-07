// Decodes every audio track of a file with wt_audio.wasm and compares it to FFmpeg's own output.
import fs from 'fs';
import { execFileSync } from 'child_process';

const [,, wasmPath, file] = process.argv;
const fd = fs.openSync(file, 'r');
const size = fs.fstatSync(fd).size;
let mem;
const wasi = new Proxy({}, { get: (_, name) => (...a) => {
  if (name === 'clock_time_get') { new DataView(mem.buffer).setBigUint64(a[2], BigInt(Math.round(performance.now() * 1e6)), true); return 0; }
  if (name === 'environ_sizes_get' || name === 'args_sizes_get') { const v = new DataView(mem.buffer); v.setUint32(a[0], 0, true); v.setUint32(a[1], 0, true); return 0; }
  if (name === 'fd_write') { const v = new DataView(mem.buffer); let n = 0; for (let i = 0; i < a[2]; i++) n += v.getUint32(a[1] + i * 8 + 4, true); v.setUint32(a[3], n, true); return 0; }
  if (name === 'proc_exit') throw new Error('exit ' + a[0]);
  return 8; // EBADF for everything else
} });
const { instance } = await WebAssembly.instantiate(fs.readFileSync(wasmPath), {
  wasi_snapshot_preview1: wasi,
  env: { js_read: (pos, ptr, len) => fs.readSync(fd, new Uint8Array(mem.buffer, ptr, len), 0, len, pos) },
});
const x = instance.exports; mem = x.memory; x._initialize();
const str = (p) => { const b = new Uint8Array(mem.buffer, p); return new TextDecoder().decode(b.subarray(0, b.indexOf(0))); };
let t = performance.now();
console.log('open ->', x.wt_open(size), `(${(performance.now() - t).toFixed(0)} ms)`);
const info = JSON.parse(str(x.wt_info()));
console.log('format', info.format, 'duration', info.duration);
for (const s of info.streams.filter((s) => s.type === 'audio')) {
  const rate = x.wt_select(s.index);
  t = performance.now();
  const L = [], R = []; let first = null;
  for (;;) {
    const n = x.wt_decode(2);
    if (n <= 0) break;
    if (first === null) first = x.wt_chunk_start();
    L.push(new Float32Array(mem.buffer, x.wt_out_left(), n).slice());
    R.push(new Float32Array(mem.buffer, x.wt_out_right(), n).slice());
  }
  const ms = performance.now() - t;
  const cat = (arr) => { const o = new Float32Array(arr.reduce((a, b) => a + b.length, 0)); let p = 0; for (const c of arr) { o.set(c, p); p += c.length; } return o; };
  const l = cat(L), r = cat(R);
  // reference: ffmpeg's own decode, downmixed to stereo
  const ref = new Float32Array(execFileSync('ffmpeg', ['-v', 'error', '-i', file, '-map', `0:${s.index}`, '-ac', '2', '-ar', String(rate), '-f', 'f32le', '-'], { maxBuffer: 1 << 28 }).buffer.slice(0));
  const refL = ref.filter((_, i) => i % 2 === 0);
  const n = Math.min(l.length, refL.length);
  let sab = 0, saa = 0, sbb = 0;
  for (let i = 0; i < n; i++) { sab += l[i] * refL[i]; saa += l[i] * l[i]; sbb += refL[i] * refL[i]; }
  const corr = sab / Math.sqrt(saa * sbb || 1);
  console.log(`  #${s.index} ${s.codec.padEnd(7)} ${s.channels}ch ${s.lang || '-'} "${s.title}" default=${s.default}: ${(l.length / rate).toFixed(2)} s decoded in ${ms.toFixed(0)} ms (${((l.length / rate) / (ms / 1000)).toFixed(0)}x realtime), starts at ${first.toFixed(3)} s, correlation with FFmpeg ${corr.toFixed(4)}, peak ${Math.max(...l.slice(0, 48000).map(Math.abs)).toFixed(3)}`);
  // seek check
  x.wt_seek(12.3); x.wt_decode(0.5);
  console.log(`     seek to 12.3 s -> chunk starts at ${x.wt_chunk_start().toFixed(3)} s`);
}
x.wt_close();
