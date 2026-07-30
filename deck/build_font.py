"""발표자료에 **실제로 쓰인 글자만** 잘라 슬라이드 안에 심는다.

    python deck/build_font.py

🔴 왜 잘라 넣는가 — 세 가지 제약이 동시에 걸린다.

  1. 외부 폰트 링크(구글 폰트 등)는 Artifact 의 CSP 가 막는다. 조용히
     기본 글꼴로 떨어지고, 그러면 참조 디자인과 전혀 다르게 보인다.
  2. 한글 폰트 전체는 5MB가 넘는다. 통째로 data URI 로 넣을 수 없다.
  3. 시스템 글꼴에 기대면 **PDF 로 뽑는 사람의 PC 에 따라 달라진다.**

  그래서 슬라이드 HTML 에서 보이는 글자만 모아 서브셋 woff2 를 만들고,
  `/* FONT:BEGIN */ … /* FONT:END */` 블록에 data URI 로 갈아 끼운다.

🔴 **글을 고치면 다시 돌려야 한다.** 새로 넣은 글자는 서브셋에 없어서
   그 글자만 다른 글꼴로 튄다 — 오류가 나지 않으므로 눈으로만 잡힌다.
"""
from __future__ import annotations

import base64
import io
import pathlib
import re
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

DECK = pathlib.Path(__file__).resolve().parent
# 발표자료와 포스터 둘 다. 🔴 문서마다 쓰인 글자가 다르므로 **따로** 자른다 —
#    한쪽 글자로 다른 쪽을 덮으면 없는 글자가 조용히 다른 글꼴로 튄다.
문서들 = [DECK / "presentation.html", DECK / "onepager.html"]

# 시스템에 설치된 Noto Sans KR 가변폰트. 한 파일로 300~800 굵기를 모두 낸다.
후보 = [
    pathlib.Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf"),
    pathlib.Path(r"C:\Windows\Fonts\NotoSansKR-Regular.ttf"),
]

# 본문에 없더라도 늘 넣어 두는 글자 — 숫자·기호는 나중에 바뀌기 쉽다
기본 = (
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    " .,:;!?%&()[]{}'\"/\\|-+=_*#@~^<>"
    "·…‘’“”–—→←↑↓×÷−±≈≤≥°℃㎏㎡"
)


def 본문글자(html: str) -> str:
    """태그·주석·style 을 걷어내고 **화면에 보이는 글자만** 모은다."""
    본문 = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    본문 = re.sub(r"<style.*?</style>", " ", 본문, flags=re.S | re.I)
    본문 = re.sub(r"<title.*?</title>", " ", 본문, flags=re.S | re.I)
    본문 = re.sub(r"<[^>]+>", " ", 본문)
    본문 = (본문.replace("&nbsp;", " ").replace("&amp;", "&")
            .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return 본문


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    원본 = next((p for p in 후보 if p.exists()), None)
    if 원본 is None:
        print("🔴 Noto Sans KR 을 찾지 못했습니다. 다음 중 하나가 필요합니다:")
        for p in 후보:
            print(f"   {p}")
        raise SystemExit(1)

    print(f"원본  {원본.name}  ({원본.stat().st_size/1e6:.1f}MB)\n")
    for HTML in 문서들:
        if not HTML.exists():
            print(f"  {HTML.name:22} 없음 — 건너뜁니다")
            continue
        심기(원본, HTML)


def 심기(원본: pathlib.Path, HTML: pathlib.Path) -> None:
    html = HTML.read_text(encoding="utf-8")
    if "/* FONT:BEGIN */" not in html or "/* FONT:END */" not in html:
        print(f"🔴 {HTML.name} 에 FONT:BEGIN/END 표시가 없습니다.")
        raise SystemExit(1)

    글자 = set(본문글자(html)) | set(기본)
    글자 = {c for c in 글자 if c.isprintable() and not c.isspace()}
    text = "".join(sorted(글자))

    폰트 = TTFont(str(원본), fontNumber=0, lazy=True)
    가변 = "fvar" in 폰트
    옵션 = subset.Options()
    옵션.flavor = "woff2"
    옵션.desubroutinize = True
    옵션.layout_features = ["kern", "liga", "calt", "ccmp", "locl"]
    옵션.name_IDs = []
    옵션.drop_tables += ["GSUB", "GPOS"] if not 가변 else []
    옵션.retain_gids = False

    번역기 = subset.Subsetter(options=옵션)
    번역기.populate(text=text)
    번역기.subset(폰트)

    buf = io.BytesIO()
    폰트.save(buf)
    데이터 = buf.getvalue()

    b64 = base64.b64encode(데이터).decode("ascii")
    굵기 = "100 900" if 가변 else "400"
    블록 = (
        "/* FONT:BEGIN */\n"
        "/* Noto Sans KR — 이 문서에 쓰인 글자만 잘라 넣었다.\n"
        "   글을 고치면 `python deck/build_font.py` 를 다시 돌린다. */\n"
        "@font-face {\n"
        '  font-family: "NotoSansKR Deck";\n'
        "  font-style: normal;\n"
        f"  font-weight: {굵기};\n"
        "  font-display: block;\n"
        f'  src: url(data:font/woff2;base64,{b64}) format("woff2");\n'
        "}\n"
        "/* FONT:END */"
    )
    새html = re.sub(r"/\* FONT:BEGIN \*/.*?/\* FONT:END \*/", lambda _: 블록,
                   html, flags=re.S)
    HTML.write_text(새html, encoding="utf-8")
    print(f"  {HTML.name:22} 글자 {len(글자):>3}자 → 자형 {len(데이터)/1024:>5.1f}KB"
          f"  · 문서 {len(새html.encode())/1024:.0f}KB")


if __name__ == "__main__":
    main()
