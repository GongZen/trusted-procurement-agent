"""⚠️ **가상 시나리오** — 실제로 급등한 날에 산출물이 어떻게 바뀌는지 보여준다.

2026년 7월은 전 품목이 평년보다 쌌다. 그래서 **급등 상황의 산출물을 실제
데이터로는 보여줄 수 없다.** 이 스크립트는 수집본의 올해 값에 배수를 곱해
그 상황을 재현한다.

🔴 **여기서 나온 숫자는 실측이 아니다.** 산출물의 형태를 확인하는 용도이며,
   실제 판정에는 절대 쓰지 않는다. 그래서 `scripts/` 가 아니라 `examples/` 에 둔다.

    python examples/demo_spike.py 풋고추 2.1
"""
from __future__ import annotations

import copy
import gzip
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from api import use_utf8_stdout      # noqa: E402
import analyze                       # noqa: E402
import render                        # noqa: E402
import run as 실행                    # noqa: E402


def 급등시키기(행들: list[dict], 품목: str, 배수: float, 올해: str) -> list[dict]:
    """올해 관측만 배수만큼 올린다. 과거는 그대로 둔다."""
    바뀐 = copy.deepcopy(행들)
    건수 = 0
    for r in 바뀐:
        if r.get("item_nm") != 품목:
            continue
        if not (r.get("exmn_ym") or "").startswith(올해):
            continue
        try:
            for 열 in ("pmm_avgprc", "pmm_hgprc", "pmm_lwprc"):
                if r.get(열):
                    r[열] = str(round(float(r[열]) * 배수))
            건수 += 1
        except (TypeError, ValueError):
            pass
    return 바뀐, 건수


def 산지급등(행들: list[dict], 코드: tuple[str, str], 배수: float) -> list[dict]:
    바뀐 = copy.deepcopy(행들)
    for r in 바뀐:
        if (r.get("gds_lclsf_cd"), r.get("gds_mclsf_cd")) == 코드 and r.get("tot_prc"):
            try:
                r["tot_prc"] = str(float(r["tot_prc"]) * 배수)
            except (TypeError, ValueError):
                pass
    return 바뀐


def main() -> None:
    use_utf8_stdout()
    품목 = sys.argv[1] if len(sys.argv) > 1 else "풋고추"
    배수 = float(sys.argv[2]) if len(sys.argv) > 2 else 2.1

    설정 = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))
    수집기록 = json.loads((실행.DATA / "collect_report.json").read_text(encoding="utf-8"))
    기준일 = 수집기록["기준일"]

    소매, 도매, 산지 = 실행.읽기("retail"), 실행.읽기("wholesale"), 실행.읽기("origin")
    산지과거 = 실행.읽기("origin_history")
    지도 = 실행.대응표()

    print("=" * 66)
    print(f"⚠️  가상 시나리오 — {품목} 올해 관측을 {배수}배로 올린 경우")
    print("     실측이 아닙니다. 산출물의 형태를 확인하는 용도입니다.")
    print("=" * 66)

    소매2, 건수 = 급등시키기(소매, 품목, 배수, 기준일[:4])
    코드 = (지도.get(품목, {}).get("산지대분류"), 지도.get(품목, {}).get("산지중분류"))
    산지2 = 산지급등(산지, 코드, 배수)
    print(f"  소매 {건수}행 · 산지도 함께 올림 (산지에서 시작된 급등을 가정)\n")

    판정들, 검증 = 실행.판정하기(설정, 기준일, 소매2, 도매, 산지2, 산지과거, 지도)
    보고서 = analyze.보고서만들기(판정들, 설정, 수집기록, 검증, 기준일)
    보고서["한계"].insert(0, "⚠️ 이 보고서는 가상 시나리오입니다. 숫자는 실측이 아닙니다.")

    (ROOT / "output").mkdir(exist_ok=True)
    (ROOT / "output" / "demo_spike.html").write_text(
        render.html으로(보고서), encoding="utf-8")
    analyze.저장(보고서, ROOT / "output" / "demo_spike.json")
    print(render.텍스트로(보고서))
    print("\n→ output/demo_spike.html · demo_spike.json")


if __name__ == "__main__":
    main()
