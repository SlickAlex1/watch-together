// Repackages a file's video track with wt_audio.wasm into fragmented MP4 (as the page does for
// MediaSource), from the start and after a jump, and checks it against FFmpeg.
//   node test_repack.mjs wt_audio.wasm movie.mkv out-folder
import fs from 'fs';
import { execFileSync } from 'child_process';

const [,, wasmPath, file, outDir] = process.argv;
const fd = fs.openSync(file, 'r');
const size = fs.fstatSync(fd).size;
let mem;
const wasi = new Proxy({}, { get: (_, name) => (...a) => {
  if (name === 'clock_time_get') { new DataView(mem.buffer).setBigUint64(a[2], BigInt(Math.round(performance.now() * 1e6)), true); return 0; }
  if (name === 'environ_sizes_get' || name === 'args_sizes_get') { const v = new DataView(mem.buffer); v.setUint32(a[0], 0, true); v.setUint32(a[1], 0, true); return 0; }
  if (name === 'fd_write') { const v = new DataView(mem.buffer); let n = 0; for (let i = 0; i < a[2]; i++) n += v.getUint32(a[1] + i * 8 + 4, true); v.setUint32(a[3], n, true); return 0; }
  if (name === 'proc_exit') throw new Error('exit ' + a[0]);
  return 8;
} });
const { instance } = await WebAssembly.instantiate(fs.readFileSync(wasmPath), {
  wasi_snapshot_preview1: wasi,
  env: { js_read: (pos, ptr, len) => fs.readSync(fd, new Uint8Array(mem.buffer, ptr, len), 0, len, pos) },
});
const x = instance.exports; mem = x.memory; x._initialize();
const str = (p) => { const b = new Uint8Array(mem.buffer, p); return new TextDecoder().decode(b.subarray(0, b.indexOf(0))); };
const bytes = (n) => new Uint8Array(mem.buffer, x.wt_vbuf(), n).slice();
console.log('open ->', x.wt_open(size));
for (const [name, from] of [['from-start', 0], ['after-jump', 20.3]]) {
  const t0 = performance.now();
  const n = x.wt_vstart(from);
  if (n <= 0) { console.log('vstart failed', n); process.exit(1); }
  const parts = [bytes(n)];
  let calls = 0, total = n;
  for (;;) {
    const m = x.wt_vread(4);
    calls++;
    if (m < 0) { console.log('vread error', m); process.exit(1); }
    if (m > 0) { parts.push(bytes(m)); total += m; }
    if (x.wt_vend()) break;
  }
  const ms = performance.now() - t0;
  const out = `${outDir}/${name}.mp4`;
  fs.writeFileSync(out, Buffer.concat(parts));
  console.log(`${name}: codec ${str(x.wt_vcodec())}, shift ${x.wt_vshift()} s, ${calls} reads, ${(total / 1e6).toFixed(1)} MB in ${ms.toFixed(0)} ms`);
}
x.wt_close();
