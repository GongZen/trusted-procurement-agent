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


def _자리말(표기: str) -> str:
    """`"1/6"` 을 사람 말로. 「6개 중 1번째」가 「1/6」보다 읽힌다."""
    try:
        순위, 전체 = (int(v) for v in 표기.split("/"))
    except (ValueError, AttributeError):
        return 표기
    if 순위 == 1:
        return "최고"
    if 순위 == 전체:
        return "최저"
    return f"{전체}개 중 {순위}번째"


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
        # 🔴 목록 순위가 같아도 **과거 안에서의 자리**가 바뀌면 말한다.
        #
        #    처음에는 「어제 폭의 절반 이상 움직였을 때」로 만들었는데,
        #    그 0.5 는 내가 고른 임계치다. 「임의 임계치를 쓰지 않는다」는
        #    원칙을 여기서 스스로 어기고 있었다.
        #
        #    대신 이미 계산해 둔 것을 쓴다 — 각 품목은 과거 N년 중 몇 번째인지
        #    (`순위표기` "3/6")를 갖고 있다. 그 자리가 바뀌는 것은 우리가
        #    정한 사건이 아니라 **관측이 말해 주는 사건**이다.
        옛자리, 새자리 = 옛.get("순위표기"), 새.get("순위표기")
        if 옛자리 and 새자리 and 옛자리 != 새자리:
            문장.append(f"평년 안에서의 자리 이동 — {이름} "
                       f"{_자리말(옛자리)} → {_자리말(새자리)}")

    if not 문장:
        문장.append("어제와 같은 순서입니다. 새로 볼 것이 없습니다.")
    return 문장
