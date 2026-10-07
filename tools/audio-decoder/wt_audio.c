/*
 * Watch together: audio decoder for formats browsers can't play (AC-3, E-AC-3, DTS, TrueHD, ...).
 * Built on FFmpeg's demuxers and decoders (LGPL 2.1+), compiled to WebAssembly.
 * Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later.
 *
 * The file is read through js_read() (the browser worker reads the user's local file);
 * decoded audio comes out as 32-bit float stereo, planar (left block, then right block).
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libswresample/swresample.h>
#include <libavutil/opt.h>
#include <libavutil/channel_layout.h>

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

WT_EXPORT(wt_close) void wt_close(void) {
    close_decoder();
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
