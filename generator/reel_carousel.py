"""카드뉴스 이미지 → 무음 릴스 (1080x1920)
카드가 읽기 좋은 속도로 옆으로 넘어간다. 소리는 없음(호환용 무음 트랙만 포함).
사용법: python3 reel_carousel.py out/kr_2026-10-29
"""
import sys, subprocess, pathlib
from PIL import Image
from brand import PAPER

W, H = 1080, 1920
SCALE = 0.95                 # 카드를 살짝 줄여 위·아래 UI 안전영역 확보
TOP = 220                    # 상단 여백 (인스타 상단 UI 영역)
FADE = 0.45                  # 넘김 전환 시간(초)

# 장별 노출 시간: 표지는 짧게, 본문은 읽을 시간 확보, 요약은 길게
def durations(n):
    return [3.5] + [5.5] * (n - 2) + [6.5]

def frame(card_path, out_path):
    bg = Image.new("RGB", (W, H), PAPER)
    c = Image.open(card_path).convert("RGB")
    c = c.resize((int(c.width * SCALE), int(c.height * SCALE)), Image.LANCZOS)
    bg.paste(c, ((W - c.width) // 2, TOP))
    bg.save(out_path)

def make(folder):
    folder = pathlib.Path(folder)
    cards = sorted(folder.glob("card_*.png"))
    fr = folder / "carousel_frames"; fr.mkdir(exist_ok=True)
    frames = []
    for i, c in enumerate(cards):
        p = fr / f"f_{i:02d}.png"; frame(c, p); frames.append(p)
    durs = durations(len(frames))
    inputs, filt = [], []
    for k, (f, d) in enumerate(zip(frames, durs)):
        extra = FADE if k < len(frames) - 1 else 0
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{d + extra:.2f}", "-i", str(f)]
        filt.append(f"[{k}:v]format=yuv420p,setsar=1[v{k}]")
    last, off = "v0", 0.0
    for k in range(1, len(frames)):
        off += durs[k - 1]
        filt.append(f"[{last}][v{k}]xfade=transition=slideleft:duration={FADE}:offset={off:.2f}[x{k}]")
        last = f"x{k}"
    total = sum(durs)
    out = folder / "reel.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs,
                    "-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo",
                    "-filter_complex", ";".join(filt), "-map", f"[{last}]", "-map", f"{len(frames)}:a",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "64k", "-shortest", "-movflags", "+faststart", str(out)], check=True)
    return out, total

if __name__ == "__main__":
    out, total = make(sys.argv[1])
    print(f"reel ok: {out} ({total:.1f}s)")
