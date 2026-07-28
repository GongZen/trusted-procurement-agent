"""Agent 루프가 **죽지 않는지** 확인한다 — Scaffolding §4 의 7개 통과 조건.

    python tests/test_loop.py

🔴 정상 동작을 확인하는 시험이 아니다. **망가뜨려도 계속 도는지**를 본다.
   실제 실행에서는 잘 돌던 것이 API 가 죽거나 한도를 넘겼을 때 함께 죽는다.
   그 상황을 여기서 일부러 만든다.

호출 비용을 아끼려고 파이프라인은 실제로 돌리지 않는다. `agent.파이프라인실행`
과 `agent.오늘시세` 를 가짜로 바꿔치기해 **루프의 판단만** 검사한다.
"""
from __future__ import annotations

import copy
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import agent      # noqa: E402
import compare    # noqa: E402
from api import use_utf8_stdout  # noqa: E402

통과: list[tuple[bool, str]] = []


def 확인(조건: bool, 설명: str) -> None:
    통과.append((조건, 설명))
    print(f"  {'⭕' if 조건 else '🔴'} {설명}")


def 가짜시세(가격: int, n: int = 3) -> list[dict]:
    return [{"exmn_ymd": "20260727", "ctgry_cd": "200", "item_cd": f"2{i:02d}",
             "vrty_cd": "00", "grd_cd": "04", "se_cd": "01",
             "exmn_dd_prc": str(가격 + i)} for i in range(n)]


def 판정(품목순서: list[str], 배수: float = 1.1) -> list[dict]:
    return [{"품목": 이름, "순위": i, "평년평균": 1000, "올해": int(1000 * 배수)}
            for i, 이름 in enumerate(품목순서, 1)]


class 가짜클라이언트:
    def __init__(self, 행들, 오류=None):
        self.행들, self.오류, self.call_count = 행들, 오류, 1

    def fetch_all(self, *a, **k):
        from api import CallResult
        if self.오류:
            return CallResult("recent/price", False, error=self.오류)
        return CallResult("recent/price", True, len(self.행들), self.행들)


def 판놓기(시세, 파이프라인=None, 판정결과=None, 오류=None):
    """루프 바깥의 세계를 통째로 가짜로 바꾼다."""
    agent.Client = lambda *a, **k: 가짜클라이언트(시세, 오류)          # noqa: E731
    agent.파이프라인실행 = 파이프라인 or (lambda: (True, []))
    agent.판정읽기 = lambda: (판정결과 or [])                          # noqa: E731


def 상태초기화():
    if agent.STATE.exists():
        agent.STATE.unlink()


def main() -> None:
    use_utf8_stdout()
    원래 = (agent.Client, agent.파이프라인실행, agent.판정읽기)
    print("Agent 루프 — Scaffolding §4 통과 조건 검증\n")

    # ── ① 연속 3회 완주 ─────────────────────────────────────────────
    print("① 사람 개입 없이 연속 3회 트리거 → 완주")
    상태초기화()
    판놓기(가짜시세(1000), 판정결과=판정(["사과", "수박"]))
    결과들 = [agent.한바퀴() for _ in range(3)]
    확인(all(r.상태 != "실패" for r in 결과들),
        f"3회 모두 완주 — {[r.상태 for r in 결과들]}")

    # ── ③ 같은 데이터는 중복 처리하지 않는다 ────────────────────────
    print("\n③ 같은 데이터를 다시 줘도 중복 처리하지 않음")
    확인(결과들[0].상태 == "새로운자료" and 결과들[1].상태 == "변화없음",
        "1회차만 처리하고 2·3회차는 건너뜀")
    확인(len({r.지문 for r in 결과들}) == 1, "지문이 세 번 모두 같음")

    # ── ④ 새 데이터에는 이전 결과와의 차이가 남는다 ──────────────────
    print("\n④ 새 데이터에는 이전 결과와의 차이(재판정 사유)가 남음")
    판놓기(가짜시세(2000), 판정결과=판정(["풋고추", "사과", "호박"]))
    바뀜 = agent.한바퀴()
    확인(바뀜.상태 == "새로운자료", "지문이 바뀌자 다시 처리함")
    확인(any("새로 올라옴" in v for v in 바뀜.변화),
        f"차이가 문장으로 남음 — {바뀜.변화[:2]}")

    # ── ⑤ 실행 중 오류가 나도 루프가 죽지 않는다 ────────────────────
    print("\n⑤ 실행 중 오류가 나도 루프가 죽지 않음")

    def 터지는파이프라인():
        raise RuntimeError("일부러 낸 오류")

    판놓기(가짜시세(3000), 파이프라인=터지는파이프라인)
    터짐 = agent.한바퀴()
    확인(isinstance(터짐, agent.주기결과), "예외가 밖으로 나오지 않고 값으로 돌아옴")
    확인(터짐.상태 == "실패" and 터짐.문제, f"실패로 기록됨 — {터짐.문제[0][:52]}")

    상태 = agent.상태읽기()
    확인(상태.get("지문") != 터짐.지문,
        "실패한 지문을 저장하지 않음 — 다음 주기가 다시 시도한다")

    판놓기(가짜시세(3000), 판정결과=판정(["오이"]))
    회복 = agent.한바퀴()
    확인(회복.상태 in ("새로운자료", "이월재개"),
        f"다음 주기에 같은 데이터를 다시 처리함 — {회복.상태}")

    # ── ⑥ API 실패·트래픽 초과에도 죽지 않는다 ──────────────────────
    print("\n⑥ API 트래픽 초과·조회 실패에도 루프가 죽지 않음")
    판놓기(가짜시세(4000), 오류="HTTP 429 (일 트래픽 초과)")
    막힘 = agent.한바퀴()
    확인(막힘.상태 == "실패" and "429" in 막힘.문제[0],
        f"한도 초과를 기록하고 계속 — {막힘.문제[0][:44]}")

    판놓기(가짜시세(4000), 판정결과=판정(["감자"]))
    재개 = agent.한바퀴()
    확인(재개.상태 in ("새로운자료", "이월재개"), "한도가 풀리자 이어받아 처리함")

    # ── ⑦ 승인 필요 사안에 멈추지 않는다 ────────────────────────────
    print("\n⑦ 승인이 필요한 사안에 멈추지 않고 표시만 함")
    확인필요판정 = 판정(["배추"])
    확인필요판정[0]["확인필요"] = True
    판놓기(가짜시세(5000), 판정결과=확인필요판정)
    표시 = agent.한바퀴()
    확인(표시.상태 == "새로운자료" and 표시.산출,
        "확인 필요 항목이 있어도 산출물을 내고 완주함")

    # ── 상태 파일이 깨져도 시작한다 ─────────────────────────────────
    print("\n부가 · 상태 파일이 깨져 있어도 시작함")
    agent.STATE.write_text("{망가진 JSON", encoding="utf-8")
    판놓기(가짜시세(6000), 판정결과=판정(["무"]))
    복구 = agent.한바퀴()
    확인(복구.상태 != "실패", f"빈 상태로 시작해 완주 — {복구.상태}")

    # ── compare 단독 검증 ───────────────────────────────────────────
    print("\n부가 · 차이 문장")
    문장 = compare.차이문장(판정(["사과", "수박", "풋고추"]),
                        판정(["풋고추", "사과", "호박"]))
    확인(any("순위 올라옴" in v for v in 문장), f"순위 이동 — {문장[0]}")
    확인(any("빠짐" in v for v in 문장), "빠진 품목 감지")
    같음 = compare.차이문장(판정(["사과"]), 판정(["사과"]))
    확인("같은 순서" in 같음[0], f"변화가 없으면 그렇게 말함 — {같음[0]}")

    agent.Client, agent.파이프라인실행, agent.판정읽기 = 원래
    상태초기화()

    실패 = [s for ok, s in 통과 if not ok]
    print("\n" + "=" * 58)
    print(f"{len(통과) - len(실패)}/{len(통과)} 통과")
    for s in 실패:
        print(f"  🔴 {s}")
    sys.exit(1 if 실패 else 0)


if __name__ == "__main__":
    main()
