"""수집본을 읽어 판정하고 산출물까지 한 번에 만든다.

    python scripts/run.py            수집본으로 판정 → output/
    python scripts/run.py --collect  수집부터 다시

**인증키가 없어도 끝까지 돈다** — `sample-data/` 만 있으면 전 과정이 재현된다.
"""
from __future__ import annotations

import csv
import json
import gzip
import sys
import pathlib
import statistics
import collections

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from api import use_utf8_stdout                                    # noqa: E402
import analyze                                                     # noqa: E402
import render                                                      # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "sample-data"
OUT = ROOT / "output"


def 읽기(이름: str) -> list[dict]:
    """`.json` 과 `.json.gz` 를 모두 읽는다. 심사자가 어느 쪽을 받든 돌아간다."""
    gz, plain = DATA / f"{이름}.json.gz", DATA / f"{이름}.json"
    if gz.exists():
        with gzip.open(gz, "rt", encoding="utf-8") as fp:
            return json.load(fp)
    if plain.exists():
        return json.loads(plain.read_text(encoding="utf-8"))
    raise SystemExit(f"수집본이 없습니다: {plain} — 먼저 collect.py 를 실행하세요.")


def 대응표() -> dict[str, dict]:
    path = ROOT / "reference" / "item_map.csv"
    return {r["품목명"]: r for r in
            csv.DictReader(path.open(encoding="utf-8-sig"))}


# ── 유통 단계별 관측 ─────────────────────────────────────────────────
def 거래단가(행: dict, 총액: str, 물량: str) -> float | None:
    """정산 실적에서 **실현단가**를 만든다 — 총금액 ÷ 총물량.

    조사가격(perDay)과 관측 단위가 다르므로 같은 가격으로 취급하지 않는다
    (DATA_CRITERIA §5). 단계 간에는 **각자의 평소와 비교**할 뿐이다.
    """
    try:
        금액, 양 = float(행.get(총액) or 0), float(행.get(물량) or 0)
        return 금액 / 양 if 금액 > 0 and 양 > 0 else None
    except (TypeError, ValueError):
        return None


def 단계별_당일(원본: list[dict], 코드: tuple[str, str],
             총액: str, 물량: str) -> float | None:
    """해당 품목의 당일 실현단가 중앙값. 이상 거래 한 건에 흔들리지 않게."""
    값 = [v for r in 원본
          if (r.get("gds_lclsf_cd"), r.get("gds_mclsf_cd")) == 코드
          and (v := 거래단가(r, 총액, 물량)) is not None]
    return statistics.median(값) if 값 else None


def 산지_연도별(과거: list[dict], 코드: tuple[str, str],
             총액: str, 물량: str) -> dict[str, float]:
    """과거 같은 달 표본일의 산지 실현단가를 **연도별 중앙값**으로 접는다.

    같은 연도 안의 여러 표본일·여러 공판장을 중앙값으로 모으는 이유 —
    공판장 구성이 해마다 바뀌므로 평균을 쓰면 큰 공판장 하나가 그 해를
    끌고 간다. 중앙값은 구성 변화에 덜 흔들린다.
    """
    연도별: dict[str, list[float]] = {}
    for r in 과거:
        if (r.get("gds_lclsf_cd"), r.get("gds_mclsf_cd")) != 코드:
            continue
        v = 거래단가(r, 총액, 물량)
        if v is not None:
            연도별.setdefault((r.get("clcln_ymd") or "")[:4], []).append(v)
    return {y: statistics.median(vs) for y, vs in 연도별.items() if vs}


def 산지판정(당일: float | None, 연도별: dict[str, float],
          최소관측수: int) -> analyze.단계판정:
    """산지도 **같은 방식으로** 판정한다 — 과거 같은 달 관측 중 몇 번째인가.

    처음에는 산지에 과거 자료가 없다고 보고 「비교불가」로 뒀는데, 재보니
    5년치가 전부 있었다. **재보지 않고 없다고 단정한 것이 잘못**이었다.
    """
    if 당일 is None:
        return analyze.단계판정("산지", None, None, None, None, "자료없음")
    과거 = list(연도별.values())
    if len(과거) < 최소관측수:
        return analyze.단계판정("산지", round(당일), None, None, None,
                            analyze.비교불가)
    순위, 전체, 배수 = analyze.순위판정(당일, 과거)
    return analyze.단계판정("산지", round(당일), round(statistics.mean(과거)),
                        round(배수, 2), f"{순위}/{전체}", analyze.관측표현(배수))


# ── 판정 ─────────────────────────────────────────────────────────────
def 판정하기(설정: dict, 기준일: str, 소매행: list[dict],
          도매행: list[dict], 산지행: list[dict], 산지과거: list[dict],
          지도: dict[str, dict]) -> tuple[list, dict]:
    대상월 = 기준일[4:6]
    올해 = 기준일[:4]
    최소 = 설정["기준가"]["최소관측수"]

    버킷 = analyze.같은달_관측(소매행, 대상월)
    집계 = analyze.품목별_집계(버킷, 올해, 최소)

    검증 = {"비교구간": sum(d["구간수"] for d in 집계.values()),
           "판정품목": len(집계), "경고": []}
    if not 집계:
        검증["경고"].append("올해 같은 달 관측이 없어 판정하지 못했습니다")

    기준연수 = 설정["기준가"]["기준연수"]
    결과 = []
    for 품목, d in 집계.items():
        대표 = d["대표"]
        코드 = (지도.get(품목, {}).get("산지대분류"),
              지도.get(품목, {}).get("산지중분류"))

        # 산지 — 과거 표본일과 비교해 판정한다
        단계 = [산지판정(단계별_당일(산지행, 코드, "tot_prc", "unit_tot_qty"),
                    산지_연도별(산지과거, 코드, "tot_prc", "unit_tot_qty"), 최소)]

        # 도매·소매 — 5년 월별 통계가 있으므로 같은 방식으로 판정한다
        #
        # 도매 단계는 `katSale`(정산 실적)이 아니라 `perDay` 의 **중도매 조사가격**을
        # 쓴다. 정산 실적은 3일치뿐이라 평년 비교가 안 되지만 중도매 조사가격은
        # 5년 월별 통계가 있다. 관측 단위가 다르므로 두 값을 섞지 않는다.
        for 이름, 구분명 in [("도매", "중도매"), ("소매", "소매")]:
            구간 = [c for c in d["구간"] if c["구분"] == 구분명]
            if 구간:
                c = 구간[len(구간) // 2]          # 여기서도 중앙값 구간을 쓴다
                단계.append(analyze.단계판정(이름, c["올해"], c["평년평균"],
                                        c["배수"], c["순위"],
                                        analyze.관측표현(c["배수"])))
            else:
                단계.append(analyze.단계판정(이름, None, None, None, None, "자료없음"))

        확인 = ["이번 주 발주 예정 물량이 있는지 확인해 보세요."]
        높은단계 = [s.단계 for s in 단계 if s.관측 == "높음"]
        if 높은단계:
            확인.append(f"**{'·'.join(높은단계)}** 단계의 다른 시장 가격을 비교해 보세요.")
        모름 = ["귀사의 계약단가 — 계약이 걸려 있으면 이 변동과 무관할 수 있습니다."]
        미판정 = [s.단계 for s in 단계 if s.관측 in (analyze.비교불가, "자료없음")]
        if 미판정:
            모름.append(f"**{'·'.join(미판정)}** 단계는 비교할 과거 자료가 모자라 "
                      f"판정하지 못했습니다.")

        결과.append(analyze.품목판정(
            순위=0, 품목=품목, 구분=대표["구분"], 등급=대표["등급"],
            올해=대표["올해"], 평년평균=대표["평년평균"], 배수=대표["배수"],
            순위표기=대표["순위"],
            사람말=analyze.사람말로(d, 대상월, 기준연수),
            단계추적=단계,
            해석=analyze.단계해석(단계),
            확인사항=확인, 모르는것=모름,
            확인필요=d["최고비율"] >= 0.5,   # 절반 넘는 구간에서 최고가일 때만
        ))
        검증.setdefault("품목별", []).append(
            {"품목": 품목, "구간수": d["구간수"], "최고구간": d["최고순위구간"],
             "중앙배수": d["중앙배수"]})

    # 🔴 「몇 곳에서 최고가인가」의 비율이 1순위, 중앙배수가 2순위.
    #    한 구간의 극단값이 아니라 **얼마나 널리 그런가**로 줄을 세운다.
    결과.sort(key=lambda p: -집계[p.품목]["최고비율"] * 1000 - 집계[p.품목]["중앙배수"])
    상위 = 결과[:설정["산출물"]["우선검토_품목수"]]
    for i, p in enumerate(상위, 1):
        p.순위 = i
    return 상위, 검증


def main() -> None:
    use_utf8_stdout()
    설정 = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))

    수집기록 = json.loads((DATA / "collect_report.json").read_text(encoding="utf-8"))
    기준일 = 수집기록.get("기준일", "")
    print(f"기준일 {기준일} · 수집본을 읽습니다")

    소매, 도매, 산지 = 읽기("retail"), 읽기("wholesale"), 읽기("origin")
    try:
        산지과거 = 읽기("origin_history")
    except SystemExit:
        산지과거 = []                      # 없으면 산지는 「비교불가」로 남는다
    print(f"  소매 {len(소매):,} · 도매 {len(도매):,} · 산지 {len(산지):,}"
          f" · 산지과거 {len(산지과거):,}행")

    판정들, 검증 = 판정하기(설정, 기준일, 소매, 도매, 산지, 산지과거, 대응표())
    print(f"  비교 구간 {검증['비교구간']:,}개 · 판정 품목 {검증['판정품목']}종"
          f" → 우선검토 {len(판정들)}종")

    보고서 = analyze.보고서만들기(판정들, 설정, 수집기록, 검증, 기준일)
    OUT.mkdir(parents=True, exist_ok=True)
    analyze.저장(보고서, OUT / "report.json")

    (OUT / "report.html").write_text(render.html으로(보고서), encoding="utf-8")
    본문 = render.텍스트로(보고서)
    (OUT / "report.txt").write_text(본문, encoding="utf-8")
    print("\n" + 본문)
    print("\n→ output/report.json · report.html · report.txt")


if __name__ == "__main__":
    main()
