/*
 * Watch together: audio decoder for formats browsers can't play (AC-3, E-AC-3, DTS, TrueHD, ...).
 * Built on FFmpeg's demuxers and decoders (LGPL 2.1+), compiled to WebAssembly.
 * Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later.
 *
 * The file is read through js_read() (the browser worker reads the user's local file);
 * decoded audio comes out as 32-bit float stereo, planar (left block, then right block).
 * It can also repackage a file's video track, unchanged, as fragmented MP4 (see the end).
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libswresample/swresample.h>
#include <libavutil/opt.h>
#include <libavutil/channel_layout.h>
#include <libavutil/pixdesc.h>

#define WT_EXPORT(name) __attribute__((export_name(#name)))
#define WT_IMPORT(name) __attribute__((import_module("env"), import_name(#name)))

WT_IMPORT(js_read) int js_read(double pos, uint8_t *buf, int len);

static int64_t file_size, file_pos;
static AVFormatContext *fmt;
static AVIOContext *avio;
static AVCodecContext *dec;
static SwrContext *swr;
static AVPacket *pkt;
static AVFrame *frame;
static int sel = -1, out_rate, eof_flag;
static double time_offset;
static float *out_buf;
static int out_cap, out_frames;
static double chunk_start;
static char info_buf[16384];

static int read_cb(void *opaque, uint8_t *buf, int size) {
    if (file_pos >= file_size) return AVERROR_EOF;
    if (size > file_size - file_pos) size = (int)(file_size - file_pos);
    int n = js_read((double)file_pos, buf, size);
    if (n <= 0) return AVERROR_EOF;
    file_pos += n;
    return n;
}
static int64_t seek_cb(void *opaque, int64_t offset, int whence) {
    whence &= ~AVSEEK_FORCE;
    if (whence == AVSEEK_SIZE) return file_size;
    int64_t p = whence == SEEK_SET ? offset : whence == SEEK_CUR ? file_pos + offset : whence == SEEK_END ? file_size + offset : -1;
    if (p < 0 || p > file_size) return -1;
    file_pos = p;
    return p;
}

static void close_decoder(void) {
    if (dec) avcodec_free_context(&dec);
    if (swr) swr_free(&swr);
    sel = -1;
}

static void v_forget(void);

WT_EXPORT(wt_close) void wt_close(void) {
    close_decoder();
    v_forget();
    if (fmt) avformat_close_input(&fmt);
    if (avio) { av_freep(&avio->buffer); avio_context_free(&avio); }
    if (pkt) av_packet_free(&pkt);
    if (frame) av_frame_free(&frame);
}

/* Opens the file and reads its track list. Returns the number of streams, or a negative error. */
WT_EXPORT(wt_open) int wt_open(double size) {
    wt_close();
    av_log_set_level(AV_LOG_QUIET);
    file_size = (int64_t)size; file_pos = 0; eof_flag = 0;
    unsigned char *iobuf = av_malloc(1 << 16);
    if (!iobuf) return -1;
    avio = avio_alloc_context(iobuf, 1 << 16, 0, NULL, read_cb, NULL, seek_cb);
    fmt = avformat_alloc_context();
    if (!avio || !fmt) return -2;
    fmt->pb = avio;
    fmt->probesize = 8 << 20;
    fmt->max_analyze_duration = 5 * AV_TIME_BASE;
    if (avformat_open_input(&fmt, "", NULL, NULL) < 0) { fmt = NULL; return -3; }
    if (avformat_find_stream_info(fmt, NULL) < 0) return -4;
    pkt = av_packet_alloc(); frame = av_frame_alloc();
    /* Transport and program streams start at an arbitrary clock; browsers show time from zero. */
    time_offset = 0;
    if (fmt->start_time != AV_NOPTS_VALUE && fmt->start_time > AV_TIME_BASE) time_offset = fmt->start_time / (double)AV_TIME_BASE;
    return fmt->nb_streams;
}

static void json_str(char **p, char *end, const char *s) {
    *p += snprintf(*p, end - *p, "\"");
    for (; s && *s && *p < end - 8; s++) {
        unsigned char c = *s;
        if (c == '"' || c == '\\') *p += snprintf(*p, end - *p, "\\%c", c);
        else if (c < 0x20) *p += snprintf(*p, end - *p, " ");
        else { **p = c; (*p)++; }
    }
    *p += snprintf(*p, end - *p, "\"");
}

/* JSON description of every stream: type, codec, channels, language, title, default flag. */
WT_EXPORT(wt_info) const char *wt_info(void) {
    char *p = info_buf, *end = info_buf + sizeof info_buf - 64;
    p += snprintf(p, end - p, "{\"duration\":%.3f,\"format\":", fmt->duration > 0 ? fmt->duration / (double)AV_TIME_BASE : 0);
    json_str(&p, end, fmt->iformat ? fmt->iformat->name : "");
    p += snprintf(p, end - p, ",\"streams\":[");
    for (unsigned i = 0; i < fmt->nb_streams && p < end - 512; i++) {
        AVStream *st = fmt->streams[i];
        AVCodecParameters *cp = st->codecpar;
        const char *type = cp->codec_type == AVMEDIA_TYPE_AUDIO ? "audio" : cp->codec_type == AVMEDIA_TYPE_VIDEO ? "video" :
                           cp->codec_type == AVMEDIA_TYPE_SUBTITLE ? "subtitle" : "other";
        const AVCodecDescriptor *d = avcodec_descriptor_get(cp->codec_id);
        const char *prof = avcodec_profile_name(cp->codec_id, cp->profile);
        AVDictionaryEntry *lang = av_dict_get(st->metadata, "language", NULL, 0);
        AVDictionaryEntry *title = av_dict_get(st->metadata, "title", NULL, 0);
        p += snprintf(p, end - p, "%s{\"index\":%u,\"type\":\"%s\",\"codec\":", i ? "," : "", i, type);
        json_str(&p, end, d ? d->name : "unknown");
        p += snprintf(p, end - p, ",\"profile\":");
        json_str(&p, end, prof ? prof : "");
        p += snprintf(p, end - p, ",\"decodable\":%d,\"channels\":%d,\"rate\":%d,\"default\":%d,\"lang\":",
                      avcodec_find_decoder(cp->codec_id) != NULL, cp->ch_layout.nb_channels, cp->sample_rate,
                      (st->disposition & AV_DISPOSITION_DEFAULT) ? 1 : 0);
        json_str(&p, end, lang ? lang->value : "");
        p += snprintf(p, end - p, ",\"title\":");
        json_str(&p, end, title ? title->value : "");
        p += snprintf(p, end - p, "}");
    }
    snprintf(p, end - p, "]}");
    return info_buf;
}

/* Prepares the decoder for one audio stream. Returns the output sample rate, or a negative error. */
WT_EXPORT(wt_select) int wt_select(int index) {
    close_decoder();
    if (!fmt || index < 0 || index >= (int)fmt->nb_streams) return -1;
    AVStream *st = fmt->streams[index];
    if (st->codecpar->codec_type != AVMEDIA_TYPE_AUDIO) return -2;
    const AVCodec *c = avcodec_find_decoder(st->codecpar->codec_id);
    if (!c) return -3;
    dec = avcodec_alloc_context3(c);
    avcodec_parameters_to_context(dec, st->codecpar);
    dec->pkt_timebase = st->time_base;
    /* Let AC-3 / E-AC-3 decoders downmix to stereo themselves (they know the right levels). */
    AVChannelLayout stereo = AV_CHANNEL_LAYOUT_STEREO;
    if (c->id == AV_CODEC_ID_AC3 || c->id == AV_CODEC_ID_EAC3)
        av_opt_set_chlayout(dec, "downmix", &stereo, AV_OPT_SEARCH_CHILDREN);
    if (avcodec_open2(dec, c, NULL) < 0) { avcodec_free_context(&dec); return -4; }
    for (unsigned i = 0; i < fmt->nb_streams; i++) fmt->streams[i]->discard = (int)i == index ? AVDISCARD_DEFAULT : AVDISCARD_ALL;
    sel = index;
    out_rate = dec->sample_rate > 0 ? dec->sample_rate : 48000;
    eof_flag = 0;
    av_seek_frame(fmt, -1, fmt->start_time != AV_NOPTS_VALUE ? fmt->start_time : 0, AVSEEK_FLAG_BACKWARD);
    return out_rate;
}

static int ensure_swr(AVFrame *f) {
    if (swr) return 0;
    AVChannelLayout stereo = AV_CHANNEL_LAYOUT_STEREO;
    AVChannelLayout in = f->ch_layout;
    if (in.order == AV_CHANNEL_ORDER_UNSPEC) av_channel_layout_default(&in, in.nb_channels);
    if (swr_alloc_set_opts2(&swr, &stereo, AV_SAMPLE_FMT_FLTP, out_rate, &in, f->format, f->sample_rate, 0, NULL) < 0) return -1;
    av_opt_set_double(swr, "center_mix_level", 0.7071, 0);
    av_opt_set_double(swr, "surround_mix_level", 0.7071, 0);
    av_opt_set_double(swr, "lfe_mix_level", 0, 0);
    return swr_init(swr);
}

static int append(AVFrame *f) {
    if (ensure_swr(f) < 0) return -1;
    int max_out = swr_get_out_samples(swr, f->nb_samples) + 64;
    if (out_frames + max_out > out_cap) {
        int ncap = (out_frames + max_out) * 2;
        float *nb = av_realloc(out_buf, sizeof(float) * 2 * ncap);
        if (!nb) return -1;
        /* planar layout: move the right channel block to its new place */
        memmove(nb + ncap, nb + out_cap, sizeof(float) * out_frames);
        out_buf = nb; out_cap = ncap;
    }
    uint8_t *outp[2] = { (uint8_t *)(out_buf + out_frames), (uint8_t *)(out_buf + out_cap + out_frames) };
    int n = swr_convert(swr, outp, max_out, (const uint8_t **)f->extended_data, f->nb_samples);
    if (n > 0) out_frames += n;
    return n;
}

/* Decodes at least `seconds` of audio (or until the end). Returns the number of stereo frames in
 * the output, 0 when nothing more is coming, negative on error. */
WT_EXPORT(wt_decode) int wt_decode(double seconds) {
    if (!dec) return -1;
    out_frames = 0; chunk_start = -1;
    int want = (int)(seconds * out_rate);
    while (out_frames < want && !eof_flag) {
        int r = av_read_frame(fmt, pkt);
        if (r < 0) { eof_flag = 1; avcodec_send_packet(dec, NULL); }
        else if (pkt->stream_index != sel) { av_packet_unref(pkt); continue; }
        else { avcodec_send_packet(dec, pkt); av_packet_unref(pkt); }
        while (avcodec_receive_frame(dec, frame) == 0) {
            if (chunk_start < 0) {
                int64_t ts = frame->best_effort_timestamp;
                AVRational tb = fmt->streams[sel]->time_base;
                chunk_start = ts == AV_NOPTS_VALUE ? 0 : ts * av_q2d(tb) - time_offset;
            }
            append(frame);
            av_frame_unref(frame);
        }
    }
    return out_frames;
}

WT_EXPORT(wt_seek) int wt_seek(double seconds) {
    if (!fmt || sel < 0) return -1;
    AVStream *st = fmt->streams[sel];
    int64_t ts = (int64_t)((seconds + time_offset) / av_q2d(st->time_base));
    int r = av_seek_frame(fmt, sel, ts, AVSEEK_FLAG_BACKWARD);
    if (r < 0) r = av_seek_frame(fmt, -1, (int64_t)((seconds + time_offset) * AV_TIME_BASE), AVSEEK_FLAG_BACKWARD);
    avcodec_flush_buffers(dec);
    if (swr) swr_free(&swr);
    eof_flag = 0;
    return r;
}

WT_EXPORT(wt_chunk_start) double wt_chunk_start(void) { return chunk_start; }
WT_EXPORT(wt_out_left) float *wt_out_left(void) { return out_buf; }
WT_EXPORT(wt_out_right) float *wt_out_right(void) { return out_buf + out_cap; }
WT_EXPORT(wt_buf) uint8_t *wt_buf(int len) { static uint8_t *b; static int cap; if (len > cap) { av_free(b); b = av_malloc(len); cap = len; } return b; }

/* ---------- Repackaging the video track as fragmented MP4, for the browser's MediaSource player ----------
 * Some browsers (Firefox, whose MKV support is new) play MKV less smoothly than MP4. The video track
 * is copied unchanged (not re-encoded) into MP4 fragments. Matroska only stores display times, while
 * MP4 also needs decode times; those are worked out here from the display times of the next frames.
 * Times are shifted by V_SHIFT seconds so that decode times never go below zero; the page undoes the
 * shift with the MediaSource timestampOffset. */
#define V_SHIFT 2.0
#define VQ 16
static AVFormatContext *mux;
static uint8_t *mux_out;
static int mux_len, mux_cap;
static int vsel = -1, v_eof, v_started;
static int64_t v_base, v_delay, v_frame_dur, v_last_dts;
static AVPacket *vq[VQ + 2];
static int vq_n;
static int64_t vpool[VQ + 2];
static int vpool_n;
static char v_codec[64];

static int mux_write(void *opaque, const uint8_t *buf, int size) {
    if (mux_len + size > mux_cap) {
        int ncap = (mux_len + size) * 2;
        uint8_t *nb = av_realloc(mux_out, ncap);
        if (!nb) return AVERROR(ENOMEM);
        mux_out = nb; mux_cap = ncap;
    }
    memcpy(mux_out + mux_len, buf, size);
    mux_len += size;
    return size;
}

static void v_reset_queue(void) {
    for (int i = 0; i < vq_n; i++) av_packet_free(&vq[i]);
    vq_n = 0; vpool_n = 0; v_last_dts = AV_NOPTS_VALUE;
}

static void mux_close(void) {
    v_reset_queue();
    if (mux) {
        if (mux->pb) { av_freep(&mux->pb->buffer); avio_context_free(&mux->pb); }
        avformat_free_context(mux);
        mux = NULL;
    }
}

static void make_codec_string(const AVCodecParameters *cp) {
    const uint8_t *e = cp->extradata;
    const AVPixFmtDescriptor *pd = av_pix_fmt_desc_get(cp->format);
    int depth = pd ? pd->comp[0].depth : 8;
    v_codec[0] = 0;
    if (cp->codec_id == AV_CODEC_ID_H264 && e && cp->extradata_size >= 4 && e[0] == 1)
        snprintf(v_codec, sizeof v_codec, "avc1.%02X%02X%02X", e[1], e[2], e[3]);
    else if (cp->codec_id == AV_CODEC_ID_HEVC)
        snprintf(v_codec, sizeof v_codec, "hev1.%d.6.L%d.90", cp->profile > 0 ? cp->profile : 1, cp->level > 0 ? cp->level : 120);
    else if (cp->codec_id == AV_CODEC_ID_VP9)
        snprintf(v_codec, sizeof v_codec, "vp09.%02d.%02d.%02d", cp->profile > 0 ? cp->profile : 0, cp->level > 0 ? cp->level : 40, depth);
    else if (cp->codec_id == AV_CODEC_ID_AV1)
        snprintf(v_codec, sizeof v_codec, "av01.%d.08M.%02d", cp->profile > 0 ? cp->profile : 0, depth);
}

/* Starts (or restarts, after a jump) the MP4 output at the keyframe at or before `seconds`.
 * The output buffer then holds the MP4 header (init segment). Returns its length, or < 0. */
WT_EXPORT(wt_vstart) int wt_vstart(double seconds) {
    mux_close();
    mux_len = 0; v_eof = 0; v_started = 0;
    if (!fmt) return -1;
    if (vsel < 0) vsel = av_find_best_stream(fmt, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    if (vsel < 0) return -2;
    AVStream *in = fmt->streams[vsel];
    for (unsigned i = 0; i < fmt->nb_streams; i++) fmt->streams[i]->discard = (int)i == vsel ? AVDISCARD_DEFAULT : AVDISCARD_ALL;
    v_base = av_rescale_q((int64_t)((time_offset - V_SHIFT) * AV_TIME_BASE), AV_TIME_BASE_Q, in->time_base);
    v_delay = av_rescale_q(AV_TIME_BASE / 2, AV_TIME_BASE_Q, in->time_base);
    AVRational fr = in->avg_frame_rate.num > 0 ? in->avg_frame_rate : in->r_frame_rate.num > 0 ? in->r_frame_rate : (AVRational){ 25, 1 };
    v_frame_dur = av_rescale_q(1, av_inv_q(fr), in->time_base);
    if (v_frame_dur <= 0) v_frame_dur = 1;
    int64_t ts = av_rescale_q((int64_t)((seconds + time_offset) * AV_TIME_BASE), AV_TIME_BASE_Q, in->time_base);
    if (av_seek_frame(fmt, vsel, ts, AVSEEK_FLAG_BACKWARD) < 0)
        av_seek_frame(fmt, -1, (int64_t)((seconds + time_offset) * AV_TIME_BASE), AVSEEK_FLAG_BACKWARD);

    if (avformat_alloc_output_context2(&mux, NULL, "mp4", NULL) < 0 || !mux) return -3;
    uint8_t *iob = av_malloc(1 << 16);
    if (!iob) return -3;
    mux->pb = avio_alloc_context(iob, 1 << 16, 1, NULL, NULL, mux_write, NULL);
    if (!mux->pb) { av_free(iob); return -3; }
    AVStream *out = avformat_new_stream(mux, NULL);
    if (!out || avcodec_parameters_copy(out->codecpar, in->codecpar) < 0) return -3;
    out->codecpar->codec_tag = 0;
    /* There's no video decoder here to learn the picture format; VP9's MP4 header needs one. */
    if (out->codecpar->codec_id == AV_CODEC_ID_VP9 && out->codecpar->format < 0) out->codecpar->format = AV_PIX_FMT_YUV420P;
    out->time_base = in->time_base;
    mux->avoid_negative_ts = AVFMT_AVOID_NEG_TS_DISABLED;
    AVDictionary *o = NULL;
    av_dict_set(&o, "movflags", "frag_keyframe+empty_moov+default_base_moof+frag_discont", 0);
    av_dict_set(&o, "use_editlist", "0", 0);
    int r = avformat_write_header(mux, &o);
    av_dict_free(&o);
    if (r < 0) { mux_close(); return -4; }
    avio_flush(mux->pb);
    make_codec_string(in->codecpar);
    return mux_len;
}

/* Writes the oldest waiting frame, with its decode time: the next unused display time (in
 * display order) minus half a second, never after its own display time, always increasing. */
static int v_emit(void) {
    AVStream *in = fmt->streams[vsel], *out = mux->streams[0];
    AVPacket *p = vq[0];
    memmove(vq, vq + 1, sizeof(AVPacket *) * (--vq_n));
    int64_t s = vpool[0];
    memmove(vpool, vpool + 1, sizeof(int64_t) * (--vpool_n));
    int64_t dts = s - v_delay;
    if (dts > p->pts) dts = p->pts;
    if (v_last_dts != AV_NOPTS_VALUE && dts <= v_last_dts) dts = v_last_dts + 1;
    v_last_dts = dts;
    p->dts = dts - v_base;
    p->pts -= v_base;
    p->stream_index = 0;
    p->pos = -1;
    av_packet_rescale_ts(p, in->time_base, out->time_base);
    int r = p->pts >= p->dts ? av_write_frame(mux, p) : 0;   /* a frame that can't be timed is skipped */
    av_packet_free(&p);
    return r;
}

/* Adds about `seconds` of video (whole fragments, which end at keyframes). Returns the number
 * of bytes now in the output buffer (0 at the end of the file), or < 0 on an error. */
WT_EXPORT(wt_vread) int wt_vread(double seconds) {
    if (!mux || vsel < 0) return -1;
    AVStream *in = fmt->streams[vsel];
    mux_len = 0;
    int64_t goal = AV_NOPTS_VALUE;
    while (1) {
        if (v_eof) {
            while (vq_n) if (v_emit() < 0) return -5;
            av_write_frame(mux, NULL);   /* flush the last fragment */
            avio_flush(mux->pb);
            break;
        }
        avio_flush(mux->pb);
        if (mux_len > 0 && goal != AV_NOPTS_VALUE && v_last_dts != AV_NOPTS_VALUE && v_last_dts >= goal) break;
        int r = av_read_frame(fmt, pkt);
        if (r < 0) { v_eof = 1; continue; }
        if (pkt->stream_index != vsel || pkt->pts == AV_NOPTS_VALUE) { av_packet_unref(pkt); continue; }
        if (!v_started) {
            if (!(pkt->flags & AV_PKT_FLAG_KEY)) { av_packet_unref(pkt); continue; }
            v_started = 1;
        }
        if (goal == AV_NOPTS_VALUE) goal = pkt->pts + av_rescale_q((int64_t)(seconds * AV_TIME_BASE), AV_TIME_BASE_Q, in->time_base);
        if (pkt->duration <= 0) pkt->duration = v_frame_dur;
        AVPacket *q = av_packet_alloc();
        if (!q) return -6;
        av_packet_move_ref(q, pkt);
        vq[vq_n++] = q;
        int i = vpool_n++;
        while (i > 0 && vpool[i - 1] > q->pts) { vpool[i] = vpool[i - 1]; i--; }
        vpool[i] = q->pts;
        if (vq_n > VQ && v_emit() < 0) return -5;
    }
    return mux_len;
}

WT_EXPORT(wt_vbuf) uint8_t *wt_vbuf(void) { return mux_out; }
WT_EXPORT(wt_vcodec) const char *wt_vcodec(void) { return v_codec; }
WT_EXPORT(wt_vshift) double wt_vshift(void) { return V_SHIFT; }
WT_EXPORT(wt_vend) int wt_vend(void) { return v_eof; }

static void v_forget(void) { mux_close(); vsel = -1; v_eof = 0; }

/* ---------- Subtitles inside the file (text ones: SRT, ASS/SSA, WebVTT, MP4 timed text) ----------
 * Subtitles are spread through the whole file, so the page reads them in the background (with its
 * own copy of this module), starting where the viewer is. Each cue comes out as a record:
 * int32 stream, float64 start, float64 end, int32 length, then that many bytes of raw text. */
static uint8_t *sub_out;
static int sub_len, sub_cap, s_eof;
static double s_at;

static int text_sub(enum AVCodecID id) {
    return id == AV_CODEC_ID_SUBRIP || id == AV_CODEC_ID_TEXT || id == AV_CODEC_ID_ASS || id == AV_CODEC_ID_SSA ||
           id == AV_CODEC_ID_WEBVTT || id == AV_CODEC_ID_MOV_TEXT;
}

static int sub_put(const void *d, int n) {
    if (sub_len + n > sub_cap) {
        int ncap = (sub_len + n) * 2 + 4096;
        uint8_t *nb = av_realloc(sub_out, ncap);
        if (!nb) return -1;
        sub_out = nb; sub_cap = ncap;
    }
    memcpy(sub_out + sub_len, d, n);
    sub_len += n;
    return 0;
}

/* Prepares to read subtitles from `seconds` on. Returns the number of text subtitle streams. */
WT_EXPORT(wt_sstart) int wt_sstart(double seconds) {
    if (!fmt) return -1;
    int n = 0;
    for (unsigned i = 0; i < fmt->nb_streams; i++) {
        int t = fmt->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_SUBTITLE && text_sub(fmt->streams[i]->codecpar->codec_id);
        fmt->streams[i]->discard = t ? AVDISCARD_DEFAULT : AVDISCARD_ALL;
        n += t;
    }
    s_eof = 0; s_at = seconds;
    av_seek_frame(fmt, -1, (int64_t)((seconds + time_offset) * AV_TIME_BASE), AVSEEK_FLAG_BACKWARD);
    return n;
}

/* Reads up to `max_cues` cues, stopping early once past `stop_at` seconds (if > 0) or at the end
 * of the file. Returns the number of bytes of records in the output buffer. */
WT_EXPORT(wt_sread) int wt_sread(int max_cues, double stop_at) {
    sub_len = 0;
    for (int got = 0; got < max_cues && !s_eof; ) {
        if (av_read_frame(fmt, pkt) < 0) { s_eof = 1; break; }
        AVStream *st = fmt->streams[pkt->stream_index];
        if (st->codecpar->codec_type != AVMEDIA_TYPE_SUBTITLE || !text_sub(st->codecpar->codec_id) ||
            pkt->pts == AV_NOPTS_VALUE || pkt->size <= 0) { av_packet_unref(pkt); continue; }
        double start = pkt->pts * av_q2d(st->time_base) - time_offset;
        double end = pkt->duration > 0 ? start + pkt->duration * av_q2d(st->time_base) : -1;
        const uint8_t *text = pkt->data;
        int32_t len = pkt->size, idx = pkt->stream_index;
        if (st->codecpar->codec_id == AV_CODEC_ID_MOV_TEXT) {   /* 2-byte length, then the text */
            len = pkt->size >= 2 ? (pkt->data[0] << 8 | pkt->data[1]) : 0;
            if (len > pkt->size - 2) len = pkt->size - 2;
            text = pkt->data + 2;
        }
        if (len > 0 && (sub_put(&idx, 4) || sub_put(&start, 8) || sub_put(&end, 8) || sub_put(&len, 4) || sub_put(text, len))) {
            av_packet_unref(pkt); return -2;
        }
        s_at = start;
        av_packet_unref(pkt);
        got++;
        if (stop_at > 0 && start >= stop_at) break;
    }
    return sub_len;
}

WT_EXPORT(wt_sbuf) uint8_t *wt_sbuf(void) { return sub_out; }
WT_EXPORT(wt_send) int wt_send(void) { return s_eof; }
WT_EXPORT(wt_sat) double wt_sat(void) { return s_at; }
