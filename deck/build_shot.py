"""포스터에 심을 **화면 사진**을 줄여 data URI 로 만든다.

    python deck/build_shot.py

🔴 Artifact 의 CSP 는 외부 호스트 요청을 막는다. 사진을 파일로 걸어 두면
   포스터를 옮길 때마다 깨진다. **본문에 심어야** 한 파일로 완결된다.

원본은 1676×928 PNG(342KB)다. 그대로 base64 로 넣으면 456KB가 되는데,
A4 한 장에 들어갈 크기(폭 90mm 남짓)에는 과하다. 인쇄 300dpi 기준
1100px면 충분하다.

🔴 **JPEG 로 바꾼다.** 스크린샷은 보통 PNG가 유리하지만, 이 사진은
   그라디언트 배경과 SVG 곡선이 많아 PNG 압축이 잘 듣지 않는다.
   실측으로 둘 다 만들어 작은 쪽을 쓴다.
"""
from __future__ import annotations

import base64
import io
import re
import sys
import pathlib

from PIL import Image

DECK = pathlib.Path(__file__).resolve().parent
ROOT = DECK.parent
HTML = DECK / "onepager.html"
# 🔴 파일명이 아니라 **역할**로 잡는다. 스크린샷을 다시 찍을 때마다 이
#    표만 고치면 되고, 없으면 담기 전에 멈춘다 — 옛 화면이 조용히 남는
#    일이 실제로 있었다(10종 시절 화면이 포스터에 그대로 박혀 있었다).
원본들 = [
    ("대시보드", ROOT / "assets" / "발표자료용 스크린샷 2.png", 1100),
    ("등록", ROOT / "assets" / "발표자료용 스크린샷.png", 620),
]


def 만들기(경로: pathlib.Path, 목표폭: int) -> tuple[str, int]:
    im = Image.open(경로)
    if im.mode in ("RGBA", "P", "LA"):
        바탕 = Image.new("RGB", im.size, "#ffffff")
        바탕.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        im = 바탕
    if im.width > 목표폭:
        im = im.resize((목표폭, round(im.height * 목표폭 / im.width)),
                       Image.LANCZOS)

    후보 = []
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=84, optimize=True, progressive=True)
    후보.append(("jpeg", buf.getvalue()))
    buf = io.BytesIO()
    im.convert("P", palette=Image.ADAPTIVE, colors=256).save(
        buf, "PNG", optimize=True)
    후보.append(("png", buf.getvalue()))

    종류, 데이터 = min(후보, key=lambda x: len(x[1]))
    uri = (f"data:image/{종류};base64,"
           + base64.b64encode(데이터).decode("ascii"))
    return uri, len(데이터)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not HTML.exists():
        print(f"🔴 {HTML.name} 이 없습니다.")
        raise SystemExit(1)
    html = HTML.read_text(encoding="utf-8")

    for 이름, 경로, 폭 in 원본들:
        if not 경로.exists():
            print(f"🔴 {경로.name} 이 없습니다. assets/ 에 넣어 주세요.")
            raise SystemExit(1)
        표시 = f"/* SHOT:{이름} */"
        if 표시 not in html:
            print(f"🔴 {HTML.name} 에 {표시} 자리가 없습니다.")
            raise SystemExit(1)
        uri, 크기 = 만들기(경로, 폭)
        원크기 = 경로.stat().st_size
        print(f"  {이름:8} {원크기/1024:>6.0f}KB → {크기/1024:.0f}KB (폭 {폭}px)")
        html = re.sub(re.escape(표시) + r"[^;]*;",
                      lambda _: f"{표시} url({uri});", html, count=1)

    HTML.write_text(html, encoding="utf-8")
    print(f"\n→ {HTML.name} 에 심었습니다 ({len(html.encode())/1024:.0f}KB)")


if __name__ == "__main__":
    main()
