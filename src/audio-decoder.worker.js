/*
 * Watch together: background worker that converts audio formats the browser can't play.
 * Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).
 *
 * It runs wt_audio.wasm (FFmpeg's demuxers, audio decoders and MP4 muxer, LGPL 2.1+, compiled
 * to WebAssembly; source and build steps in tools/audio-decoder/). A second copy of it can
 * repackage a video track as MP4 for smoother playback. The user's file is read
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

// Reads the file in 1 MB blocks: each read from a file is slow on phones, and the decoder
// asks for small pieces at a time.
const BLOCK = 1 << 20;
let block = null, blockAt = 0;
function jsRead(pos, ptr, len) {
  if (!file) return 0;
  if (!block || pos < blockAt || pos >= blockAt + block.length) {
    block = new Uint8Array(reader.readAsArrayBuffer(file.slice(pos, pos + Math.max(BLOCK, len))));
    blockAt = pos;
  }
  const off = pos - blockAt, n = Math.min(len, block.length - off);
  if (n <= 0) return 0;
  new Uint8Array(mem.buffer, ptr, n).set(block.subarray(off, off + n));
  return n;
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
      file = m.file; block = null;
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
    } else if (m.cmd === 'vstart') {       // repackage the video track as MP4, from time t
      const n = x.wt_vstart(m.t);
      if (n <= 0) throw new Error('this video can\'t be repackaged (' + n + ')');
      const init = new Uint8Array(mem.buffer, x.wt_vbuf(), n).slice();
      reply({ init, codec: cString(x.wt_vcodec()), shift: x.wt_vshift() }, [init.buffer]);
    } else if (m.cmd === 'vread') {
      const n = x.wt_vread(m.seconds);
      if (n < 0) throw new Error('repackaging stopped (' + n + ')');
      const data = n > 0 ? new Uint8Array(mem.buffer, x.wt_vbuf(), n).slice() : null;
      reply({ data, end: !!x.wt_vend() }, data ? [data.buffer] : []);
    } else if (m.cmd === 'sstart') {       // read the text subtitles inside the file, from time t
      reply({ n: x.wt_sstart(m.t) });
    } else if (m.cmd === 'sread') {
      const n = x.wt_sread(m.max, m.stopAt || 0);
      if (n < 0) throw new Error('reading subtitles stopped (' + n + ')');
      const buf = n > 0 ? new Uint8Array(mem.buffer, x.wt_sbuf(), n).slice() : null;
      reply({ buf, end: !!x.wt_send(), at: x.wt_sat() }, buf ? [buf.buffer] : []);
    } else if (m.cmd === 'close') {
      x.wt_close(); file = null; block = null;
      reply({ ok: true });
    }
  } catch (err) {
    reply({ error: String(err && err.message || err) });
  }
};
