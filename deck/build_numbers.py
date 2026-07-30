"""발표자료·포스터의 숫자를 **판정 결과에서 직접 채운다.**

    python deck/build_numbers.py

🔴 왜 만드는가 — 화면을 고칠 때마다 발표자료의 숫자가 조용히 낡았다.
   실제로 「대구 637원 ↔ 대전 1,237원 · 94%」가 발표자료와 포스터에
   박혀 있었는데, 화면은 그 사이 **소매 → 중도매**로 바뀌어 있었다.
   제출물끼리 어긋나면 심사자가 먼저 알아챈다.

   그래서 숫자를 손으로 적지 않는다. `output/report.json` 을 읽어
   `@@표시@@` 자리에 채운다. 판정이 바뀌면 이 스크립트만 다시 돌린다.

🔴 채운 뒤에는 `build_font.py` 를 다시 돌려야 한다 — 새 글자가 서브셋에
   없으면 그 글자만 다른 글꼴로 튄다.
"""
from __future__ import annotations

import json
import re
import sys
import pathlib

DECK = pathlib.Path(__file__).resolve().parent
REPORT = DECK.parent / "skills" / "data-analysis" / "output" / "report.json"


def 단계말(단계: dict) -> str:
    이름 = {"산지": "산지", "도매": "도매", "소매": "소매"}[단계["단계"]]
    율 = round((단계["올해"] / 단계["평년평균"] - 1) * 100)
    return f"{이름} {율:+d}%"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not REPORT.exists():
        print(f"🔴 {REPORT} 가 없습니다. 먼저 run.py 를 돌리세요.")
        raise SystemExit(1)
    보고 = json.loads(REPORT.read_text(encoding="utf-8"))
    판정 = 보고.get("우선검토") or []
    if not 판정:
        print("🔴 우선검토가 비어 있습니다 — 오늘은 올라온 품목이 없습니다.")
        print("   발표자료의 실측 예시는 손으로 정하거나 다른 날 자료를 쓰세요.")
        raise SystemExit(1)

    p = 판정[0]
    큰 = p.get("높은단계") or {}
    도시 = p.get("도시") or {}
    전체 = (p.get("주인공순위") or "/6").split("/")[-1]
    단계 = {s["단계"]: s for s in p.get("단계추적", [])}
    쓸단계 = [단계말(s) for s in p.get("단계추적", [])
            if s.get("올해") and s.get("평년평균")]

    값 = {
        "품목": p["품목"],
        "불릿1": (f'<b>{p.get("주인공단계")}</b>에서 올해가 '
                f'최근 {int(전체) - 1}년 {보고["기준일"][4:6].lstrip("0")}월보다 높습니다'),
        "불릿2": (f'{큰.get("이름", "")} '
                f'<b>{큰.get("평년", 0):,} → {큰.get("올해", 0):,}원</b> '
                f'({큰.get("증감", "")})' if 큰 else "—"),
        "불릿3": " · ".join(쓸단계) if 쓸단계 else "—",
        "불릿4": (f'도시 간 도매 가격이 <b>{도시.get("차이율", 0)}%</b> 벌어져 있습니다'
                if 도시 else "—"),
    }
    if 도시:
        값.update({
            "싼도시": 도시["싼곳"]["지역"], "싼값": f'{도시["싼곳"]["값"]:,}',
            "비싼도시": 도시["비싼곳"]["지역"], "비싼값": f'{도시["비싼곳"]["값"]:,}',
            "차이율": str(도시["차이율"]), "조건": 도시["조건"],
            "포스터문장": (f'{도시["조건"]} 기준 {도시["도시수"]}개 도시에서 '
                      f'{도시["싼곳"]["지역"]} {도시["싼곳"]["값"]:,}원 ↔ '
                      f'{도시["비싼곳"]["지역"]} {도시["비싼곳"]["값"]:,}원, '
                      f'{도시["차이율"]}% 차이.'),
        })

    for 이름 in ("presentation.html", "onepager.html"):
        경로 = DECK / 이름
        if not 경로.exists():
            continue
        글 = 경로.read_text(encoding="utf-8")
        남은 = set(re.findall(r"@@(\w+)@@", 글))
        for k, v in 값.items():
            글 = 글.replace(f"@@{k}@@", v)
        못채움 = 남은 - set(값)
        경로.write_text(글, encoding="utf-8")
        print(f"  {이름:20} 채운 자리 {len(남은 & set(값))}개"
              + (f" · 🔴 못 채움 {sorted(못채움)}" if 못채움 else ""))

    print(f"\n  1위 {p['품목']} · 주인공 {p.get('주인공단계')} {p.get('주인공순위')}")
    if 도시:
        print(f"  도시 {도시['조건']} · {도시['도시수']}곳 · "
              f"{도시['싼곳']['지역']} {도시['싼곳']['값']:,} ↔ "
              f"{도시['비싼곳']['지역']} {도시['비싼곳']['값']:,} ({도시['차이율']}%)")
    print("\n🔴 이어서 `python deck/build_font.py` 를 돌리세요 — 새 글자가 "
          "서브셋에 없으면 그 글자만 다른 글꼴로 튑니다.")


if __name__ == "__main__":
    main()
