"""발표자료·포스터를 **PDF 로 굽는다.**

    python deck/build_pdf.py

🔴 왜 사람이 Ctrl+P 로 하지 않는가 —

  · 브라우저 인쇄 대화상자는 **머리말·꼬리말**(날짜·URL·쪽번호)을 기본으로
    켠다. 그게 종이 맨 위에 찍혀 제출물이 지저분해진다.
  · **배경 그래픽** 체크가 기본으로 꺼져 있어 상자·카드가 통째로 사라진다.
    (`print-color-adjust: exact` 로 막아 두었지만 브라우저마다 다르다.)
  · 여백 설정을 매번 사람이 맞춰야 하고, 한 번이라도 틀리면 다시 뽑아야 한다.

  헤드리스 크롬으로 구우면 **셋 다 코드로 고정된다.** 같은 명령이 늘 같은
  PDF 를 낸다 — 제출 직전에 다시 뽑아도 어제와 같다.
"""
from __future__ import annotations

import pathlib
import subprocess
import tempfile
import sys
import time

DECK = pathlib.Path(__file__).resolve().parent
ROOT = DECK.parent
OUT = ROOT / "assets"

크롬후보 = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

굽기 = [
    ("presentation.html", "2026_Upstage_BDAI_발표자료_박현웅.pdf"),
    ("onepager.html",     "2026_Upstage_BDAI_OnePager_박현웅.pdf"),
]


def 크롬찾기() -> str:
    for c in 크롬후보:
        if pathlib.Path(c).exists():
            return c
    print("🔴 크롬·엣지를 찾지 못했습니다.")
    raise SystemExit(1)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    크롬 = 크롬찾기()
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"엔진  {pathlib.Path(크롬).name}")

    for 원본, 이름 in 굽기:
        src = DECK / 원본
        if not src.exists():
            print(f"  🔴 {원본} 이 없습니다"); continue
        목적 = OUT / 이름
        # 🔴 `--no-pdf-header-footer` 가 날짜·URL 을 없앤다.
        #    용지·여백은 문서의 `@page` 가 정한다 — 여기서 겹쳐 주면 어긋난다.
        # 🔴 **매번 새 프로필로 띄운다.** 프로필을 공유하면 크롬이 이미
        #    떠 있는 인스턴스에 붙어 버리고, 그러면 **옛 결과가 그대로
        #    남는다.** 실제로 그렇게 됐다 — 스크립트가 만든 PDF(410KB)와
        #    직접 호출한 PDF(352KB)의 크기가 달랐다. 파일은 바뀌었는데
        #    스크립트만 늘 같은 것을 냈다.
        #
        # 🔴 굽기 전에 옛 파일을 지운다. 크롬이 실패해도 옛 파일이 남으면
        #    「성공했다」로 보인다.
        if 목적.exists():
            목적.unlink()
        with tempfile.TemporaryDirectory() as 프로필:
            명령 = [
                크롬, "--headless=new", "--disable-gpu", "--no-sandbox",
                f"--user-data-dir={프로필}",
                "--no-first-run", "--no-default-browser-check",
                "--disable-extensions", "--disable-background-networking",
                "--no-pdf-header-footer",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=20000",
                f"--print-to-pdf={목적}",
                src.resolve().as_uri(),
            ]
            t0 = time.time()
            # text=True 로 받으면 크롬 로그의 한글이 cp949 로 안 풀려 터진다
            r = subprocess.run(명령, capture_output=True, timeout=180)
        if not 목적.exists() or 목적.stat().st_size < 10_000:
            print(f"  🔴 {이름} 굽기 실패")
            print((r.stderr or r.stdout or b"").decode("utf-8", "replace")[-400:])
            continue
        print(f"  ⭕ {이름}  {목적.stat().st_size/1e6:.2f}MB  ({time.time()-t0:.1f}초)")

    print("\n  assets/ 에 저장했습니다. 쪽 수와 잘림을 눈으로 한 번 보세요.")


if __name__ == "__main__":
    main()
