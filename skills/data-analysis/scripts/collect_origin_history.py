"""산지공판장의 **과거 같은 달** 낙찰 실적을 모은다 — 3단계 판정의 마지막 조각.

**왜 별도 스크립트인가** — 소매·중도매는 `perYearMonth` 가 5년치 월별 통계를
한 번에 주지만, 산지는 **날짜별·공판장별로만** 부를 수 있다. 과거를 받으려면
호출 구조가 완전히 달라서 매일 도는 수집기와 분리한다.

    한 날짜 = 157곳 탐색 + 활성 55곳 수집 ≈ 212 호출
    5년 × 표본 3일 = 15날짜             ≈ 3,180 호출  (일 한도 10,000)

**이건 매일 돌지 않는다.** 기준가는 1년에 한 번 그 달이 지날 때만 늘어난다.

    python scripts/collect_origin_history.py [기준일 YYYYMMDD]
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
import pathlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from api import Client, use_utf8_stdout  # noqa: E402

import paths                                                        # noqa: E402

ROOT = paths.SKILL
DATA = paths.SAMPLE

# 한 달에서 고를 표본일. 월초·중순·하순을 하나씩 — 특정 시기 편향을 피한다.
표본일 = ["08", "15", "22"]
동시호출 = 24


def 대상날짜(기준일: str, 기준연수: int) -> list[str]:
    올해, 월 = int(기준일[:4]), 기준일[4:6]
    return [f"{y}{월}{d}"
            for y in range(올해 - 기준연수, 올해)
            for d in 표본일]


def 하루수집(client: Client, 날짜: str, 공판장: list[str]) -> tuple[list[dict], int]:
    """🔴 `trhl_cd` 없이는 0건이므로 **어느 곳에 거래가 있는지 먼저 찾아야** 한다.

    활성 목록을 캐시하지 않는 이유 — 어느 공판장이 언제 여는지는 **계절마다
    바뀌고, 그 변화 자체가 우리가 잡으려는 신호다.** 참외 철에는 성주가 열리고
    제주 출하기에는 제주가 열린다. 명단을 얼리면 산지 이동을 못 본다.
    """
    def 탐색(코드: str):
        r = client.call("originTrialHall/dealings",
                        {"clcln_ymd::EQ": 날짜, "trhl_cd::EQ": 코드}, rows=1)
        return 코드 if (r.ok and r.total) else None

    with ThreadPoolExecutor(max_workers=동시호출) as ex:
        활성 = [c for c in ex.map(탐색, 공판장) if c]

    def 받기(코드: str):
        r = client.fetch_all("originTrialHall/dealings",
                             {"clcln_ymd::EQ": 날짜, "trhl_cd::EQ": 코드},
                             max_pages=10)
        return r.rows if r.ok else []

    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=동시호출) as ex:
        for 부분 in ex.map(받기, 활성):
            rows.extend(부분)
    return rows, len(활성)


def main() -> None:
    use_utf8_stdout()
    기준일 = sys.argv[1] if len(sys.argv) > 1 else "20260727"
    설정 = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))
    기준연수 = 설정["기준가"]["기준연수"]

    공판장 = [r["공판장코드"] for r in csv.DictReader(
        (ROOT / "reference" / "trial_halls.csv").open(encoding="utf-8-sig"))]
    날짜들 = 대상날짜(기준일, 기준연수)

    print(f"산지 과거 {기준연수}년 · {기준일[4:6]}월 표본 {len(표본일)}일"
          f" = {len(날짜들)}개 날짜 · 공판장 {len(공판장)}곳")

    client = Client()
    전체: list[dict] = []
    기록 = {"기준일": 기준일, "날짜별": [], "실패": []}

    for 날짜 in 날짜들:
        try:
            rows, 활성수 = 하루수집(client, 날짜, 공판장)
        except Exception as exc:                                   # noqa: BLE001
            기록["실패"].append(f"{날짜}: {type(exc).__name__}")
            print(f"  {날짜}  🔴 실패 — 기록하고 계속합니다")
            continue
        전체.extend(rows)
        기록["날짜별"].append({"날짜": 날짜, "공판장": 활성수, "행": len(rows)})
        print(f"  {날짜}  공판장 {활성수:>3}곳 · {len(rows):>6}행"
              f"  (누적 {len(전체):,} · 호출 {client.call_count:,})", flush=True)

    DATA.mkdir(parents=True, exist_ok=True)
    with gzip.open(DATA / "origin_history.json.gz", "wt",
                   encoding="utf-8", compresslevel=9) as fp:
        json.dump(전체, fp, ensure_ascii=False)
    기록["호출수"] = client.call_count
    기록["행수"] = len(전체)
    (DATA / "origin_history_report.json").write_text(
        json.dumps(기록, ensure_ascii=False, indent=2), encoding="utf-8")

    크기 = (DATA / "origin_history.json.gz").stat().st_size / 1e6
    print(f"\n총 {len(전체):,}행 · 호출 {client.call_count:,}회"
          f" → sample-data/origin_history.json.gz ({크기:.1f}MB)")


if __name__ == "__main__":
    main()
