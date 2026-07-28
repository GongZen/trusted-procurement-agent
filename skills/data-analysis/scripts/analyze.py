"""수집한 원본에서 「오늘 먼저 볼 것」을 골라 판정 JSON을 만든다.

**이 파일이 숫자에 대한 유일한 권한을 가진다.** 렌더러(HTML 카드·텍스트 보고)는
여기서 나온 JSON만 읽고 계산하지 않는다. LLM도 마찬가지다 —
Solar 는 문장을 다듬을 뿐 숫자를 만들거나 바꾸지 못한다(Scaffolding S2).

판정 방법 — **임의 임계치를 쓰지 않는다**

    기준가   같은 품목·같은 구분·같은 등급·**같은 달**의 과거 N년 월평균
    이상도   올해 값이 그 관측들 사이에서 **몇 번째로 높은가**
    순위     이상도가 큰 순

    「1.5배 넘으면 이상」 같은 우리가 고른 선이 없다. 비교 대상은 전부
    API 가 준 과거 관측이고, 판정은 그 관측들 사이의 **순위**다.
    이것이 Step 4 통과 기준(「임의 임계치가 하나도 없음」)을 만족시키는 방법이다.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta

SCHEMA_VERSION = "1.0"
KST = timezone(timedelta(hours=9))


# ── 판정 결과 ────────────────────────────────────────────────────────
@dataclass
class 단계판정:
    """유통 한 단계에서 관측된 것. 원인이 아니라 **관측**이다."""
    단계: str                    # 산지 · 도매 · 소매
    올해: float | None
    평년평균: float | None
    배수: float | None
    순위: str | None             # "1/6" — 과거 포함 몇 개 중 몇 번째
    관측: str                    # 높음 · 평년수준 · 낮음 · 자료없음


@dataclass
class 품목판정:
    순위: int
    품목: str
    구분: str                    # 소매 · 중도매
    등급: str
    올해: float
    평년평균: float
    배수: float
    순위표기: str                # "1/6"
    사람말: str                  # 통계 용어를 쓰지 않은 한 문장
    단계추적: list[단계판정] = field(default_factory=list)
    해석: str = ""
    확인사항: list[str] = field(default_factory=list)
    모르는것: list[str] = field(default_factory=list)
    확인필요: bool = False        # HITL — 멈추지 않고 표시만 한다


# ── 기준가와 순위 ────────────────────────────────────────────────────
def 같은달_관측(월별행: list[dict], 대상월: str) -> dict[tuple, list[tuple[str, float]]]:
    """(품목·구분·등급)별로 **같은 달** 관측을 연도와 함께 모은다.

    같은 달끼리만 비교하는 이유 — 농산물은 계절성이 지배적이라 7월 값을
    1월 값과 비교하면 계절을 이상으로 잘못 읽는다.
    """
    버킷: dict[tuple, list[tuple[str, float]]] = {}
    for 행 in 월별행:
        조사연월 = 행.get("exmn_ym", "")
        if len(조사연월) != 6 or 조사연월[4:] != 대상월:
            continue
        try:
            평균가 = float(행.get("pmm_avgprc") or 0)
        except (TypeError, ValueError):
            continue
        if 평균가 <= 0:
            continue
        키 = (행.get("item_nm"), 행.get("se_nm"), 행.get("grd_nm"))
        버킷.setdefault(키, []).append((조사연월[:4], 평균가))
    return 버킷


def 순위판정(올해값: float, 과거: list[float]) -> tuple[int, int, float]:
    """올해 값이 과거를 포함한 전체에서 몇 번째로 높은지.

    반환: (순위, 전체개수, 평년평균 대비 배수)
    """
    더높은것 = sum(1 for v in 과거 if v > 올해값)
    return 더높은것 + 1, len(과거) + 1, 올해값 / statistics.mean(과거)


# ── 사람 말로 옮기기 ─────────────────────────────────────────────────
def 사람말로(순위: int, 전체: int, 배수: float, 대상월: str) -> str:
    """🔴 통계 용어를 쓰지 않는다.

    사용자는 구매 담당자이지 통계 전공자가 아니다. 「표준편차 2.3배」는
    행동으로 이어지지 않지만 「지난 5년 중 가장 비싸다」는 이어진다.
    """
    달 = f"{int(대상월)}월"
    과거연수 = 전체 - 1

    if 순위 == 1:
        return f"지난 {과거연수}년 {달} 가격을 늘어놓으면 **올해가 가장 비쌉니다.**"
    if 순위 == 전체:
        return f"지난 {과거연수}년 {달} 가격 중 **올해가 가장 쌉니다.**"
    if 순위 == 2:
        return f"지난 {과거연수}년 {달} 중 **두 번째로 비쌉니다.**"

    if 배수 >= 1.0:
        정도 = f"평소 이맘때보다 {round((배수 - 1) * 100)}% 높습니다"
    else:
        정도 = f"평소 이맘때보다 {round((1 - 배수) * 100)}% 낮습니다"
    return f"{과거연수}년 {달} 중 {순위}번째입니다. {정도}."


def 관측표현(배수: float | None) -> str:
    """단계별 관측을 한 단어로. **원인을 말하지 않는다.**"""
    if 배수 is None:
        return "자료없음"
    if 배수 >= 1.15:
        return "높음"
    if 배수 <= 0.85:
        return "낮음"
    return "평년수준"


def 단계해석(단계들: list[단계판정]) -> str:
    """어느 단계에서 이탈이 **처음 관측되는가**.

    🔴 원인을 단정하지 않는다. 「산지가 원인이다」가 아니라
    「산지에서 이미 관측된다」까지만 말한다. 선행성을 측정하지 않았다.
    """
    유효 = [d for d in 단계들 if d.관측 != "자료없음"]
    if not 유효:
        return "유통 단계별 자료가 없어 어디서 벌어진 일인지 확인하지 못했습니다."

    높은단계 = [d for d in 유효 if d.관측 == "높음"]
    if not 높은단계:
        return "유통 세 단계 모두 평년 수준입니다."

    첫단계 = 유효[0]
    if 첫단계.관측 == "높음":
        if len(높은단계) == len(유효):
            return ("**산지 단계에서 이미 높게 관측됩니다.** 아래 단계도 모두 높습니다. "
                    "거래처를 바꾸는 것으로는 달라지기 어려운 종류입니다.")
        return "**산지 단계에서 이미 높게 관측됩니다.**"

    이름 = 높은단계[0].단계
    return (f"**산지는 평년 수준인데 {이름} 단계에서 벌어집니다.** "
            f"다른 시장·법인의 가격을 확인해 볼 가치가 있습니다.")


# ── 산출물 조립 ──────────────────────────────────────────────────────
def 보고서만들기(판정들: list[품목판정], 설정: dict,
              수집기록: dict, 검증기록: dict, 기준일: str) -> dict:
    """렌더러가 읽을 **유일한** 산출물. 여기 없는 숫자는 화면에 못 나온다."""
    return {
        "schema_version": SCHEMA_VERSION,
        "생성시각": datetime.now(KST).isoformat(timespec="seconds"),
        "기준일": 기준일,
        "설정":설정,
        "수집": 수집기록,
        "검증": 검증기록,
        "우선검토": [asdict(p) for p in 판정들],
        "미판정": {
            "2층_매입가": "입력 없음 — 사용자 매입가가 없어 판정하지 않았습니다",
        },
        "한계": [
            "귀사의 계약단가·재고·발주 일정을 모릅니다. 계약이 걸려 있으면 이 변동과 무관할 수 있습니다.",
            "앞으로 오를지 내릴지 예측하지 않습니다. 선행성을 측정하지 않았기 때문입니다.",
            "유통 단계별 관측은 원인 규명이 아닙니다. 어디서 벌어졌는지까지만 말합니다.",
        ],
    }


def 저장(보고서: dict, 경로) -> None:
    with open(경로, "w", encoding="utf-8") as fp:
        json.dump(보고서, fp, ensure_ascii=False, indent=2)
