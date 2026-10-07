/*
 * Watch together: background worker that converts audio formats the browser can't play.
 * Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).
 *
 * It runs wt_audio.wasm (FFmpeg's demuxers and audio decoders, LGPL 2.1+, compiled to
 * WebAssembly; source and build steps in tools/audio-decoder/). The user's file is read
 * locally with FileReaderSync; nothing is uploaded anywhere.
 */
'use strict';
let x = null, mem = null, file = null;
const reader = new FileReaderSync();

function view() { return new DataView(mem.buffer); }
// Minimal WASI: no files, no environment; only the clock and stderr (ignored) are used.
const wasi = new Proxy({}, {
  get: (_, name) => (...a) => {
    if (name === 'clock_time_get') { view().setBigUint64(a[2], BigInt(Math.round(performance.now() * 1e6)), true); return 0; }
    if (name === 'environ_sizes_get' || name === 'args_sizes_get') { view().setUint32(a[0], 0, true); view().setUint32(a[1], 0, true); return 0; }
    if (name === 'environ_get' || name === 'args_get') return 0;
    if (name === 'fd_write') {
      let n = 0;
      for (let i = 0; i < a[2]; i++) n += view().getUint32(a[1] + i * 8 + 4, true);
      view().setUint32(a[3], n, true);
      return 0;
    }
    if (name === 'proc_exit') throw new Error('decoder stopped');
    return 8; // EBADF
  },
});

function jsRead(pos, ptr, len) {
  if (!file) return 0;
  const buf = reader.readAsArrayBuffer(file.slice(pos, pos + len));
  new Uint8Array(mem.buffer, ptr, buf.byteLength).set(new Uint8Array(buf));
  return buf.byteLength;
}

async function init(packed) {
  const raw = await new Response(new Blob([packed]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).arrayBuffer();
  const { instance } = await WebAssembly.instantiate(raw, { wasi_snapshot_preview1: wasi, env: { js_read: jsRead } });
  x = instance.exports; mem = x.memory;
  x._initialize();
}

function cString(ptr) {
  const b = new Uint8Array(mem.buffer, ptr);
  return new TextDecoder().decode(b.subarray(0, b.indexOf(0)));
}

self.onmessage = async (e) => {
  const m = e.data, reply = (data, transfer) => self.postMessage(Object.assign({ id: m.id }, data), transfer || []);
  try {
    if (m.cmd === 'init') { await init(m.wasm); reply({ ok: true }); return; }
    if (!x) throw new Error('not ready');
    if (m.cmd === 'open') {
      file = m.file;
      const n = x.wt_open(file.size);
      if (n < 0) { file = null; throw new Error('unreadable file (' + n + ')'); }
      reply({ info: JSON.parse(cString(x.wt_info())) });
    } else if (m.cmd === 'select') {
      const rate = x.wt_select(m.index);
      if (rate <= 0) throw new Error('track not decodable (' + rate + ')');
      reply({ rate });
    } else if (m.cmd === 'seek') {
      x.wt_seek(m.t);
      reply({ ok: true });
    } else if (m.cmd === 'decode') {
      const n = x.wt_decode(m.seconds);
      if (n <= 0) { reply({ end: true }); return; }
      const l = new Float32Array(mem.buffer, x.wt_out_left(), n).slice();
      const r = new Float32Array(mem.buffer, x.wt_out_right(), n).slice();
      reply({ start: x.wt_chunk_start(), l, r }, [l.buffer, r.buffer]);
    } else if (m.cmd === 'close') {
      x.wt_close(); file = null;
      reply({ ok: true });
    }
  } catch (err) {
    reply({ error: String(err && err.message || err) });
  }
};
