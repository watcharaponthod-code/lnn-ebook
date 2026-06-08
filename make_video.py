#!/usr/bin/env python3
"""
Short-form video generator — Zach Yadegari / Cal AI story
Pipeline: Gemini TTS → PIL frames → MoviePy merge → MP4 with Thai subs
"""

import os
import sys
import wave
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    sys.exit("Error: set GEMINI_API_KEY environment variable before running")
client = genai.Client(api_key=API_KEY)

# ── Paths ──────────────────────────────────────────────────────────────────────
OUT_DIR = Path("/home/user/lnn-ebook/video_output")
OUT_DIR.mkdir(exist_ok=True)

FONT_BOLD    = "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf"

# ── Video settings (9:16 vertical for TikTok / Reels) ─────────────────────────
W, H        = 720, 1280   # 720p saves ~75% RAM vs 1080p
FPS         = 24
SAMPLE_RATE = 24000

# ── Story segments ─────────────────────────────────────────────────────────────
SEGMENTS = [
    {
        "id":    "hook",
        "label": "HOOK",
        "voice_text": "ไม่มีใครเชื่อว่าเด็กที่ Harvard Yale Stanford ปฏิเสธ จะสร้าง AI ที่มีคนใช้กว่า 8 ล้านคนทั่วโลก",
        "sub_text":  "ไม่มีใครเชื่อว่าเด็กที่\nHarvard • Yale • Stanford ปฏิเสธ\nจะสร้าง AI ที่มีคนใช้\nกว่า 8 ล้านคนทั่วโลก",
        "color_top":    (10,  10,  30),
        "color_bottom": (40,  10,  80),
        "accent":       (180, 100, 255),
    },
    {
        "id":    "context",
        "label": "เรื่องราวของ Zach",
        "voice_text": "Zach เริ่มเรียนเขียนโค้ดจาก YouTube ตั้งแต่อายุ 7 ขวบ ไม่มีครู ไม่มีโรงเรียนพิเศษ แค่หน้าจอ อินเทอร์เน็ต และความอยากรู้ที่ไม่มีวันหยุด พออายุ 12 เขาปล่อยแอพแรก พออายุ 16 เขาขายเว็บไซต์ได้ 3 ล้านบาท",
        "sub_text":  "เรียนโค้ดจาก YouTube\nตั้งแต่อายุ 7 ขวบ\nไม่มีครู • ไม่มีโรงเรียนพิเศษ\nอายุ 16 → ขายเว็บได้ 3 ล้านบาท",
        "color_top":    (5,   20,  40),
        "color_bottom": (10,  60,  90),
        "accent":       (80,  200, 255),
    },
    {
        "id":    "but",
        "label": "จุดพลิก",
        "voice_text": "แต่เมื่อเขาสมัครมหาวิทยาลัยชั้นนำ 19 แห่ง เกรด 4.0 เต็ม มี startup สำเร็จในมือ ผลที่ได้คือ ถูกปฏิเสธ 15 แห่ง Harvard ไม่เอา Yale ไม่เอา MIT ไม่เอา ระบบบอกว่าเขาไม่พอ",
        "sub_text":  "GPA 4.0 • มี startup สำเร็จแล้ว\nสมัคร 19 มหาลัยชั้นนำ\nถูกปฏิเสธ 15 แห่ง\nHarvard ✗  Yale ✗  MIT ✗",
        "color_top":    (40,  5,   5),
        "color_bottom": (90,  15,  15),
        "accent":       (255, 80,  80),
    },
    {
        "id":    "reveal",
        "label": "บทสรุป",
        "voice_text": "แทนที่จะรอคนยอมรับ เขาเปิดคอมพิวเตอร์ในบ้านพ่อแม่ สร้าง Cal AI แอปนับแคลอรี่จากรูปถ่ายอาหาร ภายใน 1 ปี ดาวน์โหลด 8.3 ล้านครั้ง รายได้ 30 ล้านดอลลาร์ แล้วขายให้ MyFitnessPal ตอนนั้นเขาอายุแค่ 18 ปี สิ่งที่เปลี่ยนชีวิตเขาไม่ใช่มหาวิทยาลัยชั้นนำ แต่คือการไม่รอให้ใครมาอนุมัติฝัน",
        "sub_text":  "สร้าง Cal AI ในบ้านพ่อแม่\n8.3 ล้านดาวน์โหลด\nรายได้ $30 ล้าน • อายุ 18 ปี\n\"ไม่รอให้ใครมาอนุมัติฝัน\"",
        "color_top":    (5,   30,  10),
        "color_bottom": (10,  70,  30),
        "accent":       (80,  255, 120),
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# 1. GENERATE TTS AUDIO  (Gemini 2.5 Flash TTS)
# ══════════════════════════════════════════════════════════════════════════════

def generate_tts(seg: dict) -> Path:
    audio_path = OUT_DIR / f"audio_{seg['id']}.wav"
    if audio_path.exists():
        print(f"  [TTS] {seg['id']} — ใช้ไฟล์ที่มีอยู่")
        return audio_path

    print(f"  [TTS] สร้างเสียง: {seg['id']} ...")
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=seg["voice_text"],
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore"
                    )
                )
            ),
        ),
    )

    pcm_data = response.candidates[0].content.parts[0].inline_data.data

    with wave.open(str(audio_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)         # 16-bit PCM
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)

    print(f"  [TTS] บันทึก → {audio_path}  ({len(pcm_data)//2} samples)")
    return audio_path


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


# ══════════════════════════════════════════════════════════════════════════════
# 2. RENDER FRAMES  (PIL)
# ══════════════════════════════════════════════════════════════════════════════

def gradient_bg(w, h, top, bottom) -> np.ndarray:
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        t = y / h
        arr[y, :] = [int(top[i]*(1-t) + bottom[i]*t) for i in range(3)]
    return arr


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_px: int) -> list:
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.getbbox(test)[2] <= max_px:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def render_frame(seg: dict, progress: float) -> np.ndarray:
    # Background
    bg = gradient_bg(W, H, seg["color_top"], seg["color_bottom"])
    img = Image.fromarray(bg, "RGB").convert("RGBA")
    draw = ImageDraw.Draw(img)

    acc = seg["accent"]

    # ── decorative dots ───────────────────────────────────────────────────────
    rng = np.random.default_rng(99)
    dot_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dot_layer)
    for _ in range(50):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, H))
        r = int(rng.integers(2, 5))
        a = int(rng.integers(20, 80))
        dd.ellipse([x-r, y-r, x+r, y+r], fill=(*acc, a))
    img = Image.alpha_composite(img, dot_layer)
    draw = ImageDraw.Draw(img)

    # ── top accent line ───────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 8], fill=(*acc, 220))

    # ── label pill ────────────────────────────────────────────────────────────
    font_lbl = ImageFont.truetype(FONT_BOLD, 40)
    label    = seg["label"]
    lb       = font_lbl.getbbox(label)
    lw, lh   = lb[2]-lb[0]+64, lb[3]-lb[1]+28
    lx       = (W - lw) // 2
    ly       = 140

    pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd   = ImageDraw.Draw(pill)
    pd.rounded_rectangle([lx, ly, lx+lw, ly+lh], radius=35,
                         fill=(*acc, 210))
    img  = Image.alpha_composite(img, pill)
    draw = ImageDraw.Draw(img)
    draw.text((lx+32, ly+14), label, font=font_lbl, fill=(10, 10, 20))

    # ── main subtitle text ────────────────────────────────────────────────────
    font_main = ImageFont.truetype(FONT_BOLD, 72)
    max_w     = W - 120
    lines     = wrap_text(seg["sub_text"], font_main, max_w)
    line_h    = 96
    total_h   = len(lines) * line_h
    start_y   = (H - total_h) // 2 - 20

    for i, line in enumerate(lines):
        bb  = font_main.getbbox(line)
        lw2 = bb[2] - bb[0]
        x   = (W - lw2) // 2
        y   = start_y + i * line_h
        # glow / shadow
        for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2),(0,3),(3,0)]:
            draw.text((x+dx, y+dy), line, font=font_main,
                      fill=(0, 0, 0, 120))
        draw.text((x, y), line, font=font_main, fill=(255, 255, 255))

    # ── highlight accent on key numbers ──────────────────────────────────────
    font_hl = ImageFont.truetype(FONT_BOLD, 72)
    accented_words = ["8.3","30","18","4.0","15","19","16","12","7","Harvard",
                      "Yale","MIT","Cal AI","YouTube","MyFitnessPal"]
    for i, line in enumerate(lines):
        bb  = font_hl.getbbox(line)
        lw2 = bb[2] - bb[0]
        x   = (W - lw2) // 2
        y   = start_y + i * line_h
        for kw in accented_words:
            if kw in line:
                # Find pixel position of keyword
                pre = line[:line.index(kw)]
                pre_w = font_hl.getbbox(pre)[2] if pre else 0
                kw_bb = font_hl.getbbox(kw)
                kw_w  = kw_bb[2] - kw_bb[0]
                draw.text((x + pre_w, y), kw,
                          font=font_hl, fill=(*acc, 255))

    # ── progress bar ──────────────────────────────────────────────────────────
    bar_y = H - 90
    bar_w = int((W - 120) * max(0.0, min(1.0, progress)))
    draw.rounded_rectangle([60, bar_y, W-60, bar_y+10],
                           radius=5, fill=(60, 60, 60, 120))
    if bar_w > 2:
        draw.rounded_rectangle([60, bar_y, 60+bar_w, bar_y+10],
                               radius=5, fill=(*acc, 230))

    # ── watermark ─────────────────────────────────────────────────────────────
    font_sm = ImageFont.truetype(FONT_REGULAR, 30)
    draw.text((60, H-150), "Cal AI Story  •  Zach Yadegari",
              font=font_sm, fill=(200, 200, 200, 100))

    return np.array(img.convert("RGB"))


# ══════════════════════════════════════════════════════════════════════════════
# 3. BUILD CLIP PER SEGMENT  (MoviePy)
# ══════════════════════════════════════════════════════════════════════════════

def build_clip(seg: dict, audio_path: Path):
    from moviepy import VideoClip, AudioFileClip

    duration = wav_duration(audio_path) + 0.4
    print(f"  [RENDER] on-demand  duration={duration:.2f}s")

    # Pre-render static background (dots + gradient) once, only update progress bar
    static_bg = _render_static(seg)

    def make_frame(t):
        progress = t / duration
        return _render_with_progress(static_bg, seg, progress)

    video = VideoClip(make_frame, duration=duration).with_fps(FPS)
    audio = AudioFileClip(str(audio_path))
    return video.with_audio(audio)


def _render_static(seg: dict) -> Image.Image:
    """Render everything except the progress bar (called once per segment)."""
    bg  = gradient_bg(W, H, seg["color_top"], seg["color_bottom"])
    img = Image.fromarray(bg).convert("RGBA")
    acc = seg["accent"]

    # decorative dots
    dot_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd  = ImageDraw.Draw(dot_layer)
    rng = np.random.default_rng(99)
    for _ in range(50):
        x = int(rng.integers(0, W));  y = int(rng.integers(0, H))
        r = int(rng.integers(2, 4));  a = int(rng.integers(20, 70))
        dd.ellipse([x-r, y-r, x+r, y+r], fill=(*acc, a))
    img = Image.alpha_composite(img, dot_layer)
    draw = ImageDraw.Draw(img)

    # top accent line
    draw.rectangle([0, 0, W, 6], fill=(*acc, 220))

    # label pill
    font_lbl = ImageFont.truetype(FONT_BOLD, 32)
    label    = seg["label"]
    lb       = font_lbl.getbbox(label)
    lw, lh   = lb[2]-lb[0]+48, lb[3]-lb[1]+22
    lx       = (W - lw) // 2;  ly = 100
    pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd   = ImageDraw.Draw(pill)
    pd.rounded_rectangle([lx, ly, lx+lw, ly+lh], radius=28, fill=(*acc, 210))
    img  = Image.alpha_composite(img, pill)
    draw = ImageDraw.Draw(img)
    draw.text((lx+24, ly+11), label, font=font_lbl, fill=(10, 10, 20))

    # main text
    font_main = ImageFont.truetype(FONT_BOLD, 52)
    max_w     = W - 80
    lines     = wrap_text(seg["sub_text"], font_main, max_w)
    line_h    = 70
    total_h   = len(lines) * line_h
    start_y   = (H - total_h) // 2 - 20

    accented  = ["8.3","30","18","4.0","15","19","16","12","7",
                 "Harvard","Yale","MIT","Cal AI","YouTube","MyFitnessPal"]

    for i, line in enumerate(lines):
        bb  = font_main.getbbox(line)
        x   = (W - (bb[2]-bb[0])) // 2
        y   = start_y + i * line_h
        for dx, dy in [(-2,-2),(2,2),(0,3)]:
            draw.text((x+dx, y+dy), line, font=font_main, fill=(0,0,0,100))
        draw.text((x, y), line, font=font_main, fill=(255, 255, 255))
        # re-draw accented words in colour
        for kw in accented:
            if kw in line:
                pre   = line[:line.index(kw)]
                pre_w = font_main.getbbox(pre)[2] if pre else 0
                draw.text((x + pre_w, y), kw, font=font_main, fill=(*acc, 255))

    # watermark
    font_sm = ImageFont.truetype(FONT_REGULAR, 24)
    draw.text((40, H-110), "Cal AI Story  •  Zach Yadegari",
              font=font_sm, fill=(200, 200, 200, 90))

    return img   # RGBA static layer


def _render_with_progress(static: Image.Image, seg: dict, progress: float) -> np.ndarray:
    """Compose static layer with animated progress bar."""
    frame = static.copy()
    draw  = ImageDraw.Draw(frame)
    acc   = seg["accent"]
    bar_y = H - 60
    full_w = W - 80
    bar_w  = int(full_w * max(0.0, min(1.0, progress)))
    draw.rounded_rectangle([40, bar_y, 40+full_w, bar_y+8],
                           radius=4, fill=(60,60,60,120))
    if bar_w > 2:
        draw.rounded_rectangle([40, bar_y, 40+bar_w, bar_y+8],
                               radius=4, fill=(*acc, 230))
    return np.array(frame.convert("RGB"))


# ══════════════════════════════════════════════════════════════════════════════
# 4. CONCAT + EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n═══ สร้างวิดีโอ: Zach Yadegari / Cal AI ═══\n")
    from moviepy import concatenate_videoclips

    clips = []
    for seg in SEGMENTS:
        print(f"\n▶ {seg['id'].upper()}")
        ap   = generate_tts(seg)
        clip = build_clip(seg, ap)
        clips.append(clip)
        print(f"  duration = {clip.duration:.2f}s")

    print("\n[MERGE] รวม segments ...")
    final    = concatenate_videoclips(clips, method="compose")
    out_path = OUT_DIR / "zach_yadegari_story.mp4"

    print(f"[EXPORT] → {out_path}  (total {final.duration:.1f}s)")
    final.write_videofile(
        str(out_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(OUT_DIR / "tmp_audio.m4a"),
        remove_temp=True,
        logger="bar",
    )
    print(f"\n✅ เสร็จแล้ว! → {out_path}")
    return out_path


if __name__ == "__main__":
    main()
