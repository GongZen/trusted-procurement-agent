"""`templates/fonts.css` 의 자형을 **숫자 자리에 필요한 글자만** 남긴다.

    python scripts/slim_font.py

🔴 왜 필요한가 — `report.html` 109KB 중 **61KB(57%)가 자형**이었다.

   타임리 모델이 `create_artifact(from_path=…)` 를 못 쓰는 경우, 파일을
   읽어 그대로 넘겨야 하는데 109KB 는 그 길에서 잘려 나갈 위험이 크다.
   실제로 모델이 우리 화면 대신 **자기가 만든 표**를 띄웠다.

   Geist Mono 는 라틴 전용이라 한글은 어차피 시스템 글꼴로 나온다.
   숫자·기호만 남기면 화면은 그대로인데 파일이 절반 이하가 된다.

🔴 남길 글자를 좁힐 때 **단위 표기를 빠뜨리지 않는다** — `kg` `개` 처럼
   자형이 필요한 라틴 조각이 화면에 섞여 있다.
"""
from __future__ import annotations

import base64
import io
import re
import sys
import pathlib

from fontTools import subset
from fontTools.ttLib import TTFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paths                      # noqa: E402

CSS = paths.TEMPLATES / "fonts.css"

# 숫자 자리에 실제로 오는 것 — 값·단위·기호. 넉넉히 잡아도 라틴은 싸다
남길글자 = (
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    " .,:;/%()[]{}'\"-+*=_|<>#&@?!"
    "·…–—→←↑↓×÷−±≈≤≥°"
)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    전 = len(css.encode())

    조각 = list(re.finditer(r"base64,([A-Za-z0-9+/=]+)\)", css))
    if not 조각:
        print("🔴 fonts.css 에서 data URI 를 찾지 못했습니다.")
        raise SystemExit(1)
    print(f"fonts.css {전/1024:.0f}KB · 자형 {len(조각)}개")

    새css = css
    for i, m in enumerate(조각, 1):
        원본 = base64.b64decode(m.group(1))
        폰트 = TTFont(io.BytesIO(원본), lazy=True)
        옵션 = subset.Options()
        옵션.flavor = "woff2"
        옵션.desubroutinize = True
        옵션.layout_features = ["kern", "liga", "calt", "tnum", "zero"]
        옵션.name_IDs = []
        번역기 = subset.Subsetter(options=옵션)
        번역기.populate(text=남길글자)
        번역기.subset(폰트)

        buf = io.BytesIO()
        폰트.save(buf)
        새것 = buf.getvalue()
        print(f"  {i}번  {len(원본)/1024:>5.1f}KB → {len(새것)/1024:.1f}KB")
        새css = 새css.replace(m.group(1),
                             base64.b64encode(새것).decode("ascii"))

    CSS.write_text(새css, encoding="utf-8")
    후 = len(새css.encode())
    print(f"\n→ fonts.css {전/1024:.0f}KB → {후/1024:.0f}KB")
    print("   render.py 를 다시 돌리면 report.html 에 반영됩니다.")


if __name__ == "__main__":
    main()
