#!/usr/bin/env python3
"""
Short-form video v2 — Zach Yadegari / Cal AI
• Real background images (YouTube thumbs + stock)
• Sarabun font → Thai + English + Numbers render correctly
• Karaoke subtitles (word-by-word highlight) via faster-whisper alignment
• 720×1280 portrait 24fps AAC
"""

import os, sys, wave, re
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── google genai TTS ───────────────────────────────────────────────────────────
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    sys.exit("Error: set GEMINI_API_KEY before running")
client = genai.Client(api_key=API_KEY)

# ── paths ──────────────────────────────────────────────────────────────────────
BASE       = Path("/home/user/lnn-ebook")
OUT        = BASE / "video_output_v2";  OUT.mkdir(exist_ok=True)
ASSETS     = BASE / "assets"
IMG_DIR    = ASSETS / "images"
FONT_BOLD  = str(ASSETS / "fonts/Sarabun-Bold.ttf")
FONT_REG   = str(ASSETS / "fonts/Sarabun-Regular.ttf")
SAMPLE_RATE = 24000

# ── video settings ─────────────────────────────────────────────────────────────
W, H = 720, 1280
FPS  = 24

# ── segment definitions ────────────────────────────────────────────────────────
SEGMENTS = [
    {
        "id": "hook",
        "label": "🔥 HOOK",
        "voice": (
            "ไม่มีใครเชื่อว่าเด็กที่ Harvard Yale Stanford ปฏิเสธ "
            "จะสร้าง AI ที่มีคนใช้กว่า 8 ล้านคนทั่วโลก"
        ),
        "bg_image": "zach_thumb_hq.jpg",
        "accent": (255, 210, 60),
        "overlay_alpha": 160,
    },
    {
        "id": "context",
        "label": "📖 เรื่องราวของ Zach",
        "voice": (
            "Zach เริ่มเรียนเขียนโค้ดจาก YouTube ตั้งแต่อายุ 7 ขวบ "
            "ไม่มีครู ไม่มีโรงเรียนพิเศษ "
            "แค่หน้าจอ อินเทอร์เน็ต และความอยากรู้ที่ไม่มีวันหยุด "
            "พออายุ 12 เขาปล่อยแอพแรก "
            "พออายุ 16 เขาขายเว็บไซต์ได้ 3 ล้านบาท"
        ),
        "bg_image": "laptop_code.jpg",
        "accent": (80, 220, 255),
        "overlay_alpha": 150,
    },
    {
        "id": "but",
        "label": "❌ จุดพลิก",
        "voice": (
            "แต่เมื่อเขาสมัครมหาวิทยาลัยชั้นนำ 19 แห่ง "
            "เกรด 4.0 เต็ม มี startup สำเร็จในมือแล้ว "
            "ผลที่ได้คือถูกปฏิเสธ 15 แห่ง "
            "Harvard ไม่เอา Yale ไม่เอา MIT ไม่เอา "
            "ระบบบอกว่าเขาไม่พอ"
        ),
        "bg_image": "coding_dark.jpg",
        "accent": (255, 90, 90),
        "overlay_alpha": 170,
    },
    {
        "id": "reveal",
        "label": "✅ บทสรุป",
        "voice": (
            "แทนที่จะรอคนยอมรับ เขาเปิดคอมพิวเตอร์ในบ้านพ่อแม่ "
            "สร้าง Cal AI แอปถ่ายรูปอาหาร แล้ว AI นับแคลอรี่ทันที "
            "ภายใน 1 ปี ดาวน์โหลด 8.3 ล้านครั้ง รายได้ 30 ล้านดอลลาร์ "
            "แล้วขายให้ MyFitnessPal ตอนอายุแค่ 18 ปี "
            "สิ่งที่เปลี่ยนชีวิตเขาไม่ใช่มหาวิทยาลัยชั้นนำ "
            "แต่คือการไม่รอให้ใครมาอนุมัติฝัน"
        ),
        "bg_image": "success_jump.jpg",
        "accent": (80, 255, 140),
        "overlay_alpha": 150,
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# 1. GEMINI TTS
# ══════════════════════════════════════════════════════════════════════════════

def gen_tts(seg: dict) -> Path:
    out = OUT / f"audio_{seg['id']}.wav"
    if out.exists():
        print(f"  [TTS] {seg['id']} cached"); return out
    print(f"  [TTS] generating {seg['id']} ...")
    r = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=seg["voice"],
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
                )
            ),
        ),
    )
    pcm = r.candidates[0].content.parts[0].inline_data.data
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)
    print(f"  [TTS] saved {out.name}  {len(pcm)//2} samples")
    return out


def wav_dur(p: Path) -> float:
    with wave.open(str(p), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


# ══════════════════════════════════════════════════════════════════════════════
# 2. FASTER-WHISPER  →  word timestamps
# ══════════════════════════════════════════════════════════════════════════════

_whisper_model = None

def load_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        print("  [Whisper] loading model (tiny) ...")
        _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _whisper_model


def get_word_times(wav_path: Path, voice_text: str) -> list[dict]:
    """Return list of {word, start, end} aligned to the TTS audio."""
    model = load_whisper()
    segs, _ = model.transcribe(str(wav_path), language="th",
                               word_timestamps=True, beam_size=1)
    words = []
    for seg in segs:
        if seg.words:
            for w in seg.words:
                words.append({"word": w.word.strip(), "start": w.start, "end": w.end})

    if not words:
        # Fallback: distribute evenly based on char count
        duration = wav_dur(wav_path)
        tokens   = voice_text.split()
        total_chars = sum(len(t) for t in tokens)
        t = 0.0
        for tok in tokens:
            dur = (len(tok) / max(total_chars, 1)) * duration
            words.append({"word": tok, "start": t, "end": t + dur})
            t += dur
    return words


# ══════════════════════════════════════════════════════════════════════════════
# 3. FRAME RENDERER
# ══════════════════════════════════════════════════════════════════════════════

_bg_cache: dict[str, Image.Image] = {}

def prepare_bg(seg: dict) -> Image.Image:
    fname = seg["bg_image"]
    if fname not in _bg_cache:
        src = Image.open(IMG_DIR / fname).convert("RGB")
        # Ken Burns-ready: crop to 9:16 centre
        sw, sh = src.size
        target_ratio = H / W
        if sh / sw > target_ratio:
            new_h = int(sw * target_ratio)
            top   = (sh - new_h) // 2
            src   = src.crop((0, top, sw, top + new_h))
        else:
            new_w = int(sh / target_ratio)
            left  = (sw - new_w) // 2
            src   = src.crop((left, 0, left + new_w, sh))
        src = src.resize((W, H), Image.LANCZOS)
        # soft blur for depth
        src = src.filter(ImageFilter.GaussianBlur(radius=3))
        _bg_cache[fname] = src
    return _bg_cache[fname].copy()


def make_subtitle_image(words: list[dict], current_time: float,
                        accent: tuple) -> Image.Image:
    """
    Karaoke bar — shows ±1 lines around current word.
    Current word is accent-coloured; past/future words are white/grey.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)

    font_sub  = ImageFont.truetype(FONT_BOLD, 52)
    font_sm   = ImageFont.truetype(FONT_REG,  40)

    # Find active word index
    active_idx = 0
    for i, w in enumerate(words):
        if w["start"] <= current_time <= w["end"]:
            active_idx = i; break
        if w["start"] > current_time:
            active_idx = max(0, i - 1); break

    # Group words into display lines (max ~20 chars each)
    lines: list[list[int]] = []
    cur_line: list[int] = []
    cur_len = 0
    for i, w in enumerate(words):
        token_len = len(w["word"].replace(" ",""))
        if cur_len + token_len > 18 and cur_line:
            lines.append(cur_line); cur_line = []; cur_len = 0
        cur_line.append(i); cur_len += token_len
    if cur_line:
        lines.append(cur_line)

    # Find which line contains active word
    active_line_idx = 0
    for li, line_ids in enumerate(lines):
        if active_idx in line_ids:
            active_line_idx = li; break

    # Show active line + one above
    visible = []
    if active_line_idx > 0:
        visible.append((lines[active_line_idx - 1], False))
    visible.append((lines[active_line_idx], True))
    if active_line_idx + 1 < len(lines):
        visible.append((lines[active_line_idx + 1], False))

    # ── semi-transparent backdrop ──────────────────────────────────────────
    n_lines   = len(visible)
    line_h    = 70
    pad       = 24
    box_h     = n_lines * line_h + pad * 2
    box_y     = H - box_h - 100
    backdrop  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd        = ImageDraw.Draw(backdrop)
    bd.rounded_rectangle([30, box_y - pad, W - 30, box_y + box_h],
                         radius=20, fill=(0, 0, 0, 160))
    layer = Image.alpha_composite(layer, backdrop)
    draw  = ImageDraw.Draw(layer)

    # ── draw each visible line ─────────────────────────────────────────────
    for row, (line_ids, is_active_line) in enumerate(visible):
        y = box_y + row * line_h

        # Build the line text to measure total width
        line_text = "".join(words[i]["word"] for i in line_ids)
        bb        = font_sub.getbbox(line_text)
        total_w   = bb[2] - bb[0]
        x         = (W - total_w) // 2

        for wi in line_ids:
            word  = words[wi]["word"]
            wbb   = font_sub.getbbox(word)
            ww    = wbb[2] - wbb[0]

            if wi == active_idx and is_active_line:
                colour = (*accent, 255)
                # glow behind active word
                for dx in [-2, 0, 2]:
                    for dy in [-2, 0, 2]:
                        draw.text((x + dx, y + dy), word,
                                  font=font_sub, fill=(*accent, 60))
            elif is_active_line:
                if wi < active_idx:
                    colour = (220, 220, 220, 200)   # spoken — lighter white
                else:
                    colour = (180, 180, 180, 150)   # upcoming — grey
            else:
                colour = (160, 160, 160, 120)       # other lines

            draw.text((x, y), word, font=font_sub, fill=colour)
            x += ww

    return layer


def render_frame(seg: dict, bg: Image.Image, words: list[dict],
                 t: float, duration: float) -> np.ndarray:
    frame = bg.convert("RGBA")
    draw  = ImageDraw.Draw(frame)
    acc   = seg["accent"]

    # ── dark vignette ────────────────────────────────────────────────────────
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd  = ImageDraw.Draw(vig)
    for grad_y in range(H):
        # darker at top and bottom
        tv = grad_y / H
        alpha = int(120 * (1 - 4 * (tv - 0.5) ** 2) + 60)
        vd.line([(0, grad_y), (W, grad_y)], fill=(0, 0, 0, alpha))
    frame = Image.alpha_composite(frame, vig)
    draw  = ImageDraw.Draw(frame)

    # ── top accent line ───────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 6], fill=(*acc, 240))

    # ── label pill (top centre) ───────────────────────────────────────────────
    font_lbl = ImageFont.truetype(FONT_BOLD, 34)
    lbl      = seg["label"]
    lb       = font_lbl.getbbox(lbl)
    lw, lh   = lb[2]-lb[0]+48, lb[3]-lb[1]+22
    lx = (W - lw) // 2; ly = 80
    pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd   = ImageDraw.Draw(pill)
    pd.rounded_rectangle([lx, ly, lx+lw, ly+lh], radius=28, fill=(*acc, 210))
    frame = Image.alpha_composite(frame, pill)
    draw  = ImageDraw.Draw(frame)
    draw.text((lx+24, ly+11), lbl, font=font_lbl, fill=(10, 10, 20))

    # ── watermark ─────────────────────────────────────────────────────────────
    font_wm = ImageFont.truetype(FONT_REG, 26)
    draw.text((40, H - 60), "Zach Yadegari • Cal AI Story",
              font=font_wm, fill=(220, 220, 220, 120))

    # ── karaoke subtitle ──────────────────────────────────────────────────────
    sub = make_subtitle_image(words, t, acc)
    frame = Image.alpha_composite(frame, sub)

    # ── progress bar ──────────────────────────────────────────────────────────
    draw2  = ImageDraw.Draw(frame)
    prog   = t / max(duration, 0.01)
    bar_w  = int((W - 80) * max(0, min(1, prog)))
    bar_y  = H - 28
    draw2.rounded_rectangle([40, bar_y, W-40, bar_y+6],
                            radius=3, fill=(60, 60, 60, 120))
    if bar_w > 2:
        draw2.rounded_rectangle([40, bar_y, 40+bar_w, bar_y+6],
                                radius=3, fill=(*acc, 230))

    return np.array(frame.convert("RGB"))


# ══════════════════════════════════════════════════════════════════════════════
# 4. BUILD SEGMENT CLIP
# ══════════════════════════════════════════════════════════════════════════════

def build_clip(seg: dict, audio_path: Path):
    from moviepy import VideoClip, AudioFileClip

    duration  = wav_dur(audio_path) + 0.3
    words     = get_word_times(audio_path, seg["voice"])
    bg        = prepare_bg(seg)
    print(f"  [CLIP] {seg['id']}  dur={duration:.1f}s  words={len(words)}")

    def make_frame(t):
        return render_frame(seg, bg.copy(), words, t, duration)

    video = VideoClip(make_frame, duration=duration).with_fps(FPS)
    audio = AudioFileClip(str(audio_path))
    return video.with_audio(audio)


# ══════════════════════════════════════════════════════════════════════════════
# 5. MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n═══ VIDEO v2: Karaoke subtitles + Real images ═══\n")
    from moviepy import concatenate_videoclips

    clips = []
    for seg in SEGMENTS:
        print(f"\n▶ {seg['id'].upper()}")
        ap   = gen_tts(seg)
        clip = build_clip(seg, ap)
        clips.append(clip)

    print("\n[MERGE] ...")
    final    = concatenate_videoclips(clips, method="compose")
    out_path = OUT / "zach_story_v2.mp4"
    print(f"[EXPORT] → {out_path}  ({final.duration:.1f}s)")
    final.write_videofile(
        str(out_path), fps=FPS,
        codec="libx264", audio_codec="aac",
        temp_audiofile=str(OUT / "tmp.m4a"),
        remove_temp=True, logger="bar",
    )
    print(f"\n✅ Done → {out_path}")


if __name__ == "__main__":
    main()
