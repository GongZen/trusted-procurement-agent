"""제출용 zip 한 벌을 만든다.

    python submit.py

🔴 **1차 심사가 「필수 제출물 여부」를 기계적으로 검사한다.**
   하나라도 빠지거나 이름이 어긋나면 **내용과 무관하게 탈락**이다.
   그래서 사람이 눈으로 확인하지 않는다 — 담기 전에 코드가 막는다.

공지 요건(2026 제1회 Upstage × BDAI Harness Engineering Skillthon)

    개별 파일   2026_Upstage_BDAI_[유형]_팀명.[확장자]
    최종 제출   Upstage_BDAI_팀명.zip      ← ZIP 1개로 묶어 업로드
    제출 경로   LMS 해커톤 제출 탭 · 마감 2026-07-29(수) 14:00
    개인 참가는 팀명 자리에 성명을 쓴다.
"""
from __future__ import annotations

import hashlib
import re
import sys
import zipfile
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"
이름 = "박현웅"

# (설명, 파일명, 원본 경로) — 순서가 곧 공지의 제출물 번호다
제출물 = [
    ("① 참가신청서",       f"2026_Upstage_BDAI_참가신청서_{이름}.pdf",
     ASSETS / f"2026_Upstage_BDAI_참가신청서_{이름}.pdf"),
    ("② 데이터 분석 Skill", f"2026_Upstage_BDAI_Skill_{이름}.zip",
     DIST / "2026_Upstage_BDAI_Skill_CPAI.zip"),
    ("③ 스크린샷 1",        f"2026_Upstage_BDAI_TimelyAgent_스크린샷1_{이름}.png",
     ASSETS / f"2026_Upstage_BDAI_TimelyAgent_스크린샷1_{이름}.png"),
    ("③ 스크린샷 2",        f"2026_Upstage_BDAI_TimelyAgent_스크린샷2_{이름}.png",
     ASSETS / f"2026_Upstage_BDAI_TimelyAgent_스크린샷2_{이름}.png"),
    ("④ 데모 영상",         f"2026_Upstage_BDAI_TimelyAgent_데모영상_{이름}.mp4",
     ASSETS / f"2026_Upstage_BDAI_TimelyAgent_데모영상_{이름}.mp4"),
    ("⑤ 발표자료",          f"2026_Upstage_BDAI_발표자료_{이름}.pdf",
     ASSETS / f"2026_Upstage_BDAI_발표자료_{이름}.pdf"),
    ("⑥ One Pager",        f"2026_Upstage_BDAI_OnePager_{이름}.pdf",
     ASSETS / f"2026_Upstage_BDAI_OnePager_{이름}.pdf"),
]

# 🔴 인증키가 섞이면 참가 서약의 보안 조항 위반이다
위험 = re.compile(rb"(serviceKey=[A-Za-z0-9%]{20,}|DATAGO_KEY\s*=\s*['\"][^'\"]{20,})")
이름규칙 = re.compile(rf"^2026_Upstage_BDAI_.+_{이름}\.(pdf|png|mp4|zip)$")


def 해시(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fp:
        for 덩어리 in iter(lambda: fp.read(1 << 20), b""):
            h.update(덩어리)
    return h.hexdigest()[:12]


def 키검사(p: pathlib.Path) -> bool:
    """zip 안 텍스트까지 훑는다. 겉만 봐서는 알 수 없다."""
    if p.suffix == ".zip":
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.rsplit(".", 1)[-1].lower() not in {
                        "py", "md", "json", "csv", "html", "css", "txt", "yml"}:
                    continue
                if 위험.search(z.read(n)):
                    print(f"  🔴 {p.name} 안의 {n} 에 인증키로 보이는 문자열")
                    return False
        return True
    if p.suffix in {".pdf", ".png", ".mp4"}:
        return True
    return not 위험.search(p.read_bytes())


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"제출자 {이름}\n")

    빠짐 = [(설명, 원본) for 설명, _, 원본 in 제출물 if not 원본.exists()]
    if 빠짐:
        print("🔴 없는 파일이 있습니다. 묶지 않고 멈춥니다:")
        for 설명, 원본 in 빠짐:
            print(f"   {설명}  {원본}")
        raise SystemExit(1)

    어긋남 = [새이름 for _, 새이름, _ in 제출물 if not 이름규칙.match(새이름)]
    if 어긋남:
        print("🔴 이름 규칙에 어긋납니다:", 어긋남)
        raise SystemExit(1)

    for 설명, 새이름, 원본 in 제출물:
        if not 키검사(원본):
            print("🔴 인증키가 섞였습니다. 묶지 않고 멈춥니다.")
            raise SystemExit(1)
    print("  인증키 검사 통과 (zip 안 텍스트까지)")

    최종 = DIST / f"Upstage_BDAI_{이름}.zip"
    # 🔴 이미 담긴 것이 섞이지 않게 매번 새로 만든다
    if 최종.exists():
        최종.unlink()
    with zipfile.ZipFile(최종, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for _, 새이름, 원본 in 제출물:
            z.write(원본, 새이름)

    print(f"\n{'':2}{'제출물':16}{'파일명':52}{'크기':>9}  해시")
    print("  " + "─" * 88)
    합 = 0
    for 설명, 새이름, 원본 in 제출물:
        크기 = 원본.stat().st_size
        합 += 크기
        print(f"  {설명:16}{새이름:52}{크기/1e6:>7.2f}MB  {해시(원본)}")
    print("  " + "─" * 88)
    print(f"  {'':16}{'합계':52}{합/1e6:>7.2f}MB")
    print(f"\n  → {최종.relative_to(ROOT)}  "
          f"{최종.stat().st_size/1e6:.1f}MB  ({해시(최종)})")

    with zipfile.ZipFile(최종) as z:
        담김 = z.namelist()
    assert len(담김) == len(제출물), f"담긴 수가 다릅니다: {len(담김)}"
    print(f"  담긴 파일 {len(담김)}개 — 공지 6종(스크린샷 2장) 모두 확인")


if __name__ == "__main__":
    main()
