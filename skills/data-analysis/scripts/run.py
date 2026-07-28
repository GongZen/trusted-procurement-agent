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

import paths                                                        # noqa: E402

ROOT = paths.SKILL
DATA = paths.SAMPLE
OUT = paths.OUTPUT


def 읽기(이름: str) -> list[dict]:
    """`.json` 과 `.json.gz` 를 모두 읽는다. 심사자가 어느 쪽을 받든 돌아간다."""
    경로 = paths.어디에(이름)
    if not 경로.exists():
        raise SystemExit(f"수집본이 없습니다: {경로} — 먼저 collect.py 를 실행하세요.")
    if 경로.suffix == ".gz":
        with gzip.open(경로, "rt", encoding="utf-8") as fp:
            자료 = json.load(fp)
    else:
        자료 = json.loads(경로.read_text(encoding="utf-8"))

    # 🔴 {"메타":…, "행":…} 형태면 받다 만 파일인지 검사한다.
    #    받기로 한 날짜 수와 실제로 받은 수가 다르면 쓰지 않는다 —
    #    반쪽 자료로 「최근 5년」을 계산하면 기준가가 조용히 틀어진다.
    if isinstance(자료, dict) and "행" in 자료:
        메타 = 자료.get("메타", {})
        if 메타.get("완전함") is False:
            raise SystemExit(
                f"🔴 {경로.name} 은 받다 만 파일입니다 "
                f"({메타.get('받은날짜수')}/{메타.get('요청날짜수')}일). "
                f"빠진 날짜: {메타.get('빠진날짜')} — "
                f"다시 수집하거나 온전한 스냅샷을 쓰세요.")
        return 자료["행"]
    return 자료


def 대응표() -> dict[str, dict]:
    path = paths.REFERENCE / "item_map.csv"
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
        return analyze.단계판정("산지", "원/kg", None, None, None, None, "자료없음")
    과거 = list(연도별.values())
    if len(과거) < 최소관측수:
        return analyze.단계판정("산지", "원/kg", round(당일), None, None, None,
                            analyze.비교불가)
    순위, 전체, 배수 = analyze.순위판정(당일, 과거)
    평년 = round(statistics.mean(과거))
    return analyze.단계판정(
        "산지", "원/kg", round(당일), 평년, round(배수, 2), f"{순위}/{전체}",
        analyze.관측표현(f"{순위}/{전체}"),
        자리=analyze.자리표현(f"{순위}/{전체}"),
        대비=analyze.대비표현(round(당일), 평년))


# ── 판정 ─────────────────────────────────────────────────────────────
def 시계열뽑기(소매행: list[dict], 대표: dict, 품목: str) -> list[dict]:
    """대표 구간의 **월별 가격을 시간 순서대로** 뽑는다.

    카드의 한 문장이 「지금 어디쯤인가」를 말한다면, 이 선은 「어떤 길로
    여기 왔는가」를 보여준다. 문장으로는 대체할 수 없는 정보다.
    같은 비교 단위(구분·품종·등급·지역)로 고정해야 선이 튀지 않는다.
    """
    # 🔴 그래프는 **카드가 지목한 바로 그 구간**을 그려야 한다.
    #
    #    처음에는 중앙값 구간을 그렸는데, 문장은 최고가 구간을 말하고 있어서
    #    사과 카드가 「가장 비싸다」고 하면서 내려가는 선을 보여줬다.
    #    둘 다 실측이었지만 **서로 다른 구간이라 반대 방향을 가리켰다.**
    #    한 카드 안에서 문장과 그림이 다른 것을 가리키면 둘 다 못 믿게 된다.
    점: dict[str, float] = {}
    for 행 in 소매행:
        if (행.get("item_nm") != 품목
                or 행.get("se_nm") != 대표["구분"]
                or 행.get("vrty_nm") != 대표["품종"]
                or 행.get("grd_nm") != 대표["등급"]
                or 행.get("sgg_nm") != 대표["지역"]):
            continue
        try:
            값 = float(행.get("pmm_avgprc") or 0)
        except (TypeError, ValueError):
            continue
        if 값 > 0:
            점[행.get("exmn_ym", "")] = 값
    return [{"ym": ym, "값": round(v)} for ym, v in sorted(점.items()) if ym]


def 중앙시계열(소매행: list[dict], 기준: dict, 품목: str) -> list[dict]:
    """같은 품종·등급·판매형태의 **전 도시 중앙값**을 연월별로 낸다.

    한 구간만 그리면 그 선이 높은 것인지 낮은 것인지 알 수 없다.
    전국선을 같이 그려야 「이 구간이 유별난가」가 눈으로 판정된다.
    """
    모음: dict[str, list[float]] = {}
    for 행 in 소매행:
        if (행.get("item_nm") != 품목
                or 행.get("se_nm") != 기준["구분"]
                or 행.get("vrty_nm") != 기준["품종"]
                or 행.get("grd_nm") != 기준["등급"]
                or 행.get("sgg_nm") == "온라인"):
            continue
        try:
            값 = float(행.get("pmm_avgprc") or 0)
        except (TypeError, ValueError):
            continue
        if 값 > 0:
            모음.setdefault(행.get("exmn_ym", ""), []).append(값)
    return [{"ym": ym, "값": round(statistics.median(vs))}
            for ym, vs in sorted(모음.items()) if ym and vs]


def 판정하기(설정: dict, 기준일: str, 소매행: list[dict],
          도매행: list[dict], 산지행: list[dict], 산지과거: list[dict],
          지도: dict[str, dict]) -> tuple[list, dict]:
    대상월 = 기준일[4:6]
    올해 = 기준일[:4]
    최소 = 설정["기준가"]["최소관측수"]

    버킷 = analyze.같은달_관측(소매행, 대상월)
    집계, 버림 = analyze.품목별_집계(버킷, 올해, 최소)

    # 🔴 우리가 고른 수 둘(최소관측수·표시 품목수)을 **검증에 적어 둔다.**
    #    판정 자체에는 임계치를 쓰지 않지만 이 둘은 우리가 고른 값이다.
    #    적어 두지 않으면 산출물이 그것을 숨기게 된다.
    # 🔴 이제 우리가 고른 수는 **최소관측수 하나뿐**이다. 표시 품목 수는
    #    고르지 않고 자료가 정한다(아래 「올릴것」 참조).
    검증 = {"비교구간": sum(d["구간수"] for d in 집계.values()),
           "판정품목": len(집계), "경고": [],
           "최소관측수": 최소, "제외구간": 버림}
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
                단계.append(analyze.단계판정(
                    이름, c.get("단위", ""), c["올해"], c["평년평균"],
                    c["배수"], c["순위"], analyze.관측표현(c["순위"]),
                    자리=analyze.자리표현(c["순위"]),
                    대비=analyze.대비표현(c["올해"], c["평년평균"])))
            else:
                단계.append(analyze.단계판정(이름, "", None, None, None, None, "자료없음"))

        # 그래프가 그릴 구간을 먼저 정한다 — 문장·블록·그림이 같은 것을 가리켜야 한다
        최고 = analyze.최고지점(d)
        그릴구간 = (max(d["최고목록"], key=lambda x: (x["배수"], x["지역"],
                                                x["품종"], x["등급"]))
                if d.get("최고목록") else 대표)

        확인 = ["이번 주 발주 예정 물량이 있는지 확인 바랍니다."]
        높은단계 = [s.단계 for s in 단계 if s.대비 == "평년보다 높음"]
        if 높은단계:
            확인.append(f"**{'·'.join(높은단계)}** 단계의 다른 시장 가격을 비교해 보세요.")
        # 어느 품종·등급이 튀는지 알면 대체 선택지가 바로 보인다
        # 🔴 「최고가 목록에 없다」를 「평년 수준이다」로 바꿔 말하면 안 된다.
        #    실제로 애호박은 최고가가 아니면서 평년 대비 +15% 였다.
        #    **평년 대비 부호로만** 판정한다.
        # 🔴 오른 품종을 「평년 이하」로도 부르면 안 된다. 품종 하나에 여러
        #    구간이 있어 둘 다 참일 수 있지만, 읽으면 모순이다.
        #    **어느 구간에서도 오르지 않은 품종**만 대체 후보로 부른다.
        오른품종 = {c["품종"] for c in (d.get("최고목록") or [])}
        오른품종 |= {c["품종"] for c in d["구간"] if c["올해"] > c["평년평균"]}
        평년이하품종 = sorted({c["품종"] for c in d["구간"]} - 오른품종)
        if 평년이하품종:
            확인.append(f"**{'·'.join(평년이하품종)}** 품종은 평년 이하입니다. "
                       f"대체 가능한지 확인해 보세요.")
        모름 = ["귀사의 계약이 이미 존재한다면 이러한 변동과 무관할 수 있습니다."]
        미판정 = [s.단계 for s in 단계 if s.대비 in (analyze.비교불가, "", "자료없음")]
        if 미판정:
            모름.append(f"**{'·'.join(미판정)}** 단계는 비교할 과거 자료가 모자라 "
                      f"판정하지 못했습니다.")

        결과.append(analyze.품목판정(
            순위=0, 품목=품목, 구분=대표["구분"], 등급=대표["등급"],
            올해=대표["올해"], 평년평균=대표["평년평균"], 배수=대표["배수"],
            순위표기=대표["순위"],
            사람말=analyze.사람말로(d, 대상월, 기준연수),
            시계열=시계열뽑기(소매행, 그릴구간, 품목),
            전국선=중앙시계열(소매행, 그릴구간, 품목),
            도시=analyze.도시비교(d, 그릴구간),
            그린구간=f"{그릴구간['지역']} {그릴구간['품종']} {그릴구간['등급']}"
                    f" · {그릴구간['구분']}",
            최고=최고,
            단계추적=단계,
            해석=analyze.단계해석(단계),
            확인사항=확인, 모르는것=모름,
            # 🔴 「비율 0.5 이상」이라는 임계치를 쓰지 않는다. 그 0.5 는 내가
            #    고른 값이었다. 대신 **조사한 모든 도시에서 최고가일 때만**
            #    표시한다 — 이건 고른 선이 아니라 관측의 끝값이다
            확인필요=(d["최고도시수"] > 0
                  and d["최고도시수"] == d["도시수"]),
        ))
        검증.setdefault("품목별", []).append(
            {"품목": 품목, "도시수": d["도시수"], "최고도시수": d["최고도시수"],
             "최고도시비율": d["최고도시비율"], "중앙배수": d["중앙배수"]})

    # 🔴 「몇 곳에서 최고가인가」의 비율이 1순위, 중앙배수가 2순위.
    #    한 구간의 극단값이 아니라 **얼마나 널리 그런가**로 줄을 세운다.
    # 조사 도시 중 몇 %에서 최근 5년 같은 달 최고가인가 — 한 줄로 설명되는 기준
    # 동점이면 품목명으로 가른다 — 실행마다 순서가 같아야 한다
    # 🔴 **자르지 않는다.** 전에는 상위 5개를 잘랐는데 그 5 는 우리가
    #    고른 값이었다. 「상위 5개만 보여준다고 밝힌다」는 숨김을 공개할
    #    뿐 자르는 숫자를 없애지 못한다(PR #14 검토 지적).
    #
    #    🔴 처음에는 **「최고가인 도시가 1곳이라도 있는가」**로 바꿨는데
    #       10종 중 8종이 통과했다. 거른 것이 아니었다.
    #
    #       원인은 **세는 단위가 너무 잘게 쪼개져 있던 것**이다. 한 도시
    #       안에 품종×등급×판매형태가 여러 구간이라, 「그중 하나라도 5년
    #       최고」는 우연으로도 자주 일어난다. **잘게 쪼갤수록 통과가
    #       쉬워지는 기준은 기준이 아니다.**
    #
    #    그래서 세는 단위를 **유통 단계**로 올린다 —
    #    **「산지·도매·소매 중 어느 한 단계에서든 올해가 최근 5년 같은 달
    #      관측 중 1번째인가」.** 여전히 세는 것이지 고르는 것이 아니고,
    #    쪼개서 통과하는 길이 막힌다. 실측 8종 → 2종.
    #
    #    몇 개가 나올지는 그날 자료가 정한다. **0개면 아무것도 안 나온다**
    #    — 그게 「오늘은 볼 것 없다」의 정확한 의미다.
    #    화면은 캐러셀이라 길어져도 무너지지 않는다.
    def 최고단계수(p) -> int:
        return sum(1 for s in p.단계추적
                   if (s.순위 or "").split("/")[0] == "1")

    올릴것 = [p for p in 결과 if 최고단계수(p) > 0]
    # 더 많은 단계에서 최고인 것이 앞. 동점이면 널리 퍼진 것, 그다음 이름
    올릴것.sort(key=lambda p: (-최고단계수(p),
                             -집계[p.품목]["최고도시비율"],
                             -집계[p.품목]["중앙배수"], p.품목))
    for i, p in enumerate(올릴것, 1):
        p.순위 = i
    검증["표시품목"] = len(올릴것)
    return 올릴것, 검증


def main() -> None:
    use_utf8_stdout()
    paths.준비()
    설정 = json.loads((paths.CONFIG / "settings.json").read_text(encoding="utf-8"))

    보고경로 = paths.어디에("collect_report")
    수집기록 = json.loads(보고경로.read_text(encoding="utf-8"))
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
