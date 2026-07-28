"""어제 판정과 오늘 판정의 **차이**를 사람 말로 만든다.

🔑 **이것이 Agent 를 대시보드와 가르는 지점이다.**

    대시보드   매일 같은 표를 다시 그린다. 사용자가 어제와 비교해야 한다
    Agent      **어제와 무엇이 달라졌는지**를 말한다

같은 순위표를 다시 보여주는 것만으로는 「반복 동작」이지 「Agent」가 아니다.
어제를 기억하고 있어야 오늘의 의미가 생긴다.

🔴 여기서도 숫자를 새로 만들지 않는다. 두 판정 JSON 에 이미 있는 값만 쓴다.
"""
from __future__ import annotations


def _지도(판정들: list[dict]) -> dict[str, dict]:
    return {p["품목"]: p for p in 판정들 if p.get("품목")}


def _증감(p: dict) -> int | None:
    전, 후 = p.get("평년평균"), p.get("올해")
    if not 전 or not 후:
        return None
    return round((후 / 전 - 1) * 100)


def 차이문장(이전: list[dict], 오늘: list[dict]) -> list[str]:
    """네 가지만 본다 — 들어옴 · 빠짐 · 순위 이동 · 폭 변화.

    더 많이 보고할수록 좋은 게 아니다. **어제와 같은 것은 말하지 않는다** —
    그게 매일 읽히는 산출물의 조건이다.
    """
    if not 이전:
        if not 오늘:
            return []
        return [f"첫 판정입니다. 우선 검토 {len(오늘)}개 품목을 올렸습니다."]

    가, 나 = _지도(이전), _지도(오늘)
    문장: list[str] = []

    들어옴 = [p for 이름, p in 나.items() if 이름 not in 가]
    빠짐 = [이름 for 이름 in 가 if 이름 not in 나]

    for p in sorted(들어옴, key=lambda x: x.get("순위", 99)):
        율 = _증감(p)
        꼬리 = f" ({'+' if (율 or 0) > 0 else ''}{율}%)" if 율 is not None else ""
        문장.append(f"새로 올라옴 — {p['품목']}{꼬리}")

    for 이름 in 빠짐:
        문장.append(f"목록에서 빠짐 — {이름}")

    for 이름, 새 in 나.items():
        옛 = 가.get(이름)
        if not 옛:
            continue
        옛순, 새순 = 옛.get("순위"), 새.get("순위")
        if 옛순 and 새순 and 옛순 != 새순:
            방향 = "올라옴" if 새순 < 옛순 else "내려감"
            문장.append(f"순위 {방향} — {이름} {옛순}위 → {새순}위")
            continue
        # 순위가 같아도 폭이 크게 달라졌으면 말한다.
        # 🔴 「크게」의 기준을 우리가 고르지 않기 위해, 어제 폭 대비 절반 이상
        #    움직였을 때만 말한다 — 상대 기준이라 품목·단가와 무관하게 성립한다
        옛율, 새율 = _증감(옛), _증감(새)
        if 옛율 is None or 새율 is None:
            continue
        if abs(새율 - 옛율) >= max(abs(옛율) * 0.5, 5):
            문장.append(
                f"폭 변화 — {이름} {'+' if 옛율 > 0 else ''}{옛율}%"
                f" → {'+' if 새율 > 0 else ''}{새율}%")

    if not 문장:
        문장.append("어제와 같은 순서입니다. 새로 볼 것이 없습니다.")
    return 문장
