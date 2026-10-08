// Reads the text subtitles inside a file with wt_audio.wasm, from a given time on, the way the
// page does:  node test_subtitles.mjs wt_audio.wasm movie.mkv [start-seconds]
import fs from 'fs';

const [,, wasmPath, file, from = '0'] = process.argv;
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
x.wt_open(size);
const info = JSON.parse(str(x.wt_info()));
for (const s of info.streams.filter((s) => s.type === 'subtitle')) console.log(`stream #${s.index}: ${s.codec} ${s.lang || '-'} "${s.title}"`);
console.log('text subtitle streams:', x.wt_sstart(Number(from)));
const per = {};
let calls = 0;
const t0 = performance.now();
while (!x.wt_send()) {
  const n = x.wt_sread(50, 0);
  calls++;
  const v = new DataView(mem.buffer, x.wt_sbuf(), n);
  for (let p = 0; p < n; ) {
    const idx = v.getInt32(p, true), start = v.getFloat64(p + 4, true), end = v.getFloat64(p + 12, true), len = v.getInt32(p + 20, true);
    const text = new TextDecoder().decode(new Uint8Array(mem.buffer, x.wt_sbuf() + p + 24, len));
    p += 24 + len;
    (per[idx] = per[idx] || []).push([start, end, text]);
  }
}
console.log(`read in ${calls} calls, ${(performance.now() - t0).toFixed(0)} ms`);
for (const [idx, cues] of Object.entries(per)) console.log(`  #${idx}: ${cues.length} cues, first ${JSON.stringify(cues[0])}, last starts at ${cues[cues.length - 1][0]}`);
x.wt_close();
