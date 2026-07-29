"""유통 3단계를 수집해 `sample-data/` 에 떨군다.

    산지공판장(originTrialHall) → 도매시장(katSale) → 소매·중도매(perYearMonth)

**왜 `sample-data/` 인가** — 심사자가 인증키 없이 실행해도 전 과정이 돌아야 한다
(Scaffolding §0.2). 여기 떨어진 스냅샷만으로 이후 단계가 전부 재현된다.

**실패는 예외가 아니라 기록이다.** 한 소스가 죽어도 나머지는 계속 모으고,
무엇이 실패했는지 수집 보고서에 남긴다. 사람을 기다리며 멈추지 않는다.

    python scripts/collect.py [기준일 YYYYMMDD]
"""
from __future__ import annotations

import csv
import json
import os
import sys
import pathlib
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from api import Client, use_utf8_stdout  # noqa: E402

import paths                                                        # noqa: E402

ROOT = paths.SKILL
CONFIG = paths.CONFIG / "settings.json"
OUT = paths.SAMPLE
동시호출 = 16     # 공공데이터포털이 견디는 선. 실측으로 확인했다


# ── 대응표 ───────────────────────────────────────────────────────────
def 대응표읽기() -> list[dict]:
    """`item_map.csv` 에서 **근거가 있는 대응만** 골라낸다.

    🔴 열이 붙은 행은 코드가 비어 있으므로 자연히 빠진다. 「검수」 열은
    사람이 **뒤집는** 자리이며, `X` 가 적힌 행은 근거와 무관하게 제외한다.
    자동 매칭을 믿지 않는다는 규칙(DATA_CRITERIA §5)의 구현이다.
    """
    path = paths.REFERENCE / "item_map.csv"
    쓸것, 뺀것 = [], []
    with path.open(encoding="utf-8-sig") as fp:
        for row in csv.DictReader(fp):
            검수 = (row.get("검수") or "").strip().upper()
            소매있음 = bool(row.get("품목코드"))
            산지있음 = bool(row.get("산지중분류")) and "|" not in row.get("산지중분류", "")
            if 검수.startswith("X"):
                뺀것.append((row["품목명"], "사람이 X 로 표시"))
            elif not (소매있음 or 산지있음):
                뺀것.append((row["품목명"], "대응 코드가 없다"))
            else:
                쓸것.append(row)
    return 쓸것, 뺀것


def 최근조사일(기준일: str, 일수: int) -> list[str]:
    base = datetime.strptime(기준일, "%Y%m%d")
    return [(base - timedelta(days=i)).strftime("%Y%m%d") for i in range(일수)]


# ── 수집 ─────────────────────────────────────────────────────────────
def 소매수집(client: Client, 품목들: list[dict], 기준일: str,
           기준연수: int, 기록: dict) -> list[dict]:
    """소매·중도매 월별 통계. **품목별로 걸러 받는다** — 전 품목을 받으면
    5년치가 25만 행이지만, 품목을 지정하면 한 품목당 7,000행 안쪽이다."""
    끝연도 = int(기준일[:4])
    시작연도 = 끝연도 - 기준연수
    대상 = [i for i in 품목들 if i.get("품목코드")]

    # 🔴 순차로 돌면 품목 하나에 7호출 × 1.5초라 61종이면 15분이 넘는다.
    #    실행 환경에 시간 제한이 있으므로 병렬로 받는다. 한 품목의 페이지
    #    넘김은 `fetch_all` 안에서 순차이므로 순서가 깨지지 않는다.
    def 하나(item: dict):
        r = client.fetch_all("perYearMonth/price", {
            "exmn_ym::GTE": f"{시작연도}01",
            "exmn_ym::LTE": f"{끝연도}12",
            "ctgry_cd::EQ": item["부류코드"],
            "item_cd::EQ": item["품목코드"],
        }, max_pages=30)
        return item, r

    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=동시호출) as ex:
        for item, r in ex.map(하나, 대상):
            if r.ok:
                rows.extend(r.rows)
                if r.error:
                    기록["경고"].append(f"소매 {item['품목명']}: {r.error}")
            else:
                기록["실패"].append(f"소매 {item['품목명']}: {r.error}")
            print(f"    소매 {item['품목명']:8} {len(r.rows):>6}행", flush=True)
    return rows


def 도매수집(client: Client, 시장들: list[str], 날짜들: list[str],
           기록: dict) -> list[dict]:
    """도매시장 정산. 🔴 날짜 형식이 `YYYY-MM-DD` 로 다르다."""
    조합 = [(날짜, 시장) for 날짜 in 날짜들 for 시장 in 시장들]

    def 하나(쌍):
        날짜, 시장 = 쌍
        하이픈 = f"{날짜[:4]}-{날짜[4:6]}-{날짜[6:]}"
        return 쌍, client.fetch_all("katSale/trades", {
            "trd_clcln_ymd::EQ": 하이픈,
            "whsl_mrkt_cd::EQ": 시장,
        }, max_pages=15)

    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=동시호출) as ex:
        for (날짜, 시장), r in ex.map(하나, 조합):
            if r.ok:
                rows.extend(r.rows)
            else:
                기록["실패"].append(f"도매 {시장}/{날짜}: {r.error}")
    print(f"    도매 {len(rows):,}행", flush=True)
    return rows


def 산지수집(client: Client, 상위: int, 날짜들: list[str],
           기록: dict) -> list[dict]:
    """산지공판장. 🔴 `trhl_cd` 없이는 어떤 조건으로도 0건이다.

    157곳 중 당일 거래가 있는 곳은 45곳 안팎이다. 전수를 돌면 호출이
    낭비되므로, **하루를 훑어 거래가 많은 곳을 찾은 뒤** 그 목록으로
    나머지 날짜를 받는다.
    """
    halls = list(csv.DictReader(
        (paths.REFERENCE / "trial_halls.csv").open(encoding="utf-8-sig")))
    rows: list[dict] = []

    # 1) 거래가 있는 날짜로 활성 공판장을 찾는다 — 157곳을 병렬로 훑는다
    #
    # 🔴 **첫 날짜만 훑으면 안 된다.** 산지공판장 자료는 당일 오전에 아직
    #    올라오지 않는다. 실제로 아침 9시에 돌렸더니 그날 거래가 0/157 로
    #    나왔고, **선택이 비어 뒷날짜까지 통째로 건너뛰었다** — 전날·전전날
    #    자료는 멀쩡히 있는데 산지가 0행이 됐다.
    #
    #    거래가 나올 때까지 날짜를 넘겨 가며 훑는다. 탐색은 공판장당 1행만
    #    받으므로 하루 더 훑는 값이 157회로 싸다.
    활성: list[tuple[str, int]] = []
    기준날 = 날짜들[0]
    for 날 in 날짜들:
        def 탐색(h, _날=날):
            r = client.call("originTrialHall/dealings",
                            {"clcln_ymd::EQ": _날, "trhl_cd::EQ": h["공판장코드"]},
                            rows=1)
            return (h["공판장코드"], r.total) if (r.ok and r.total) else None

        with ThreadPoolExecutor(max_workers=동시호출) as ex:
            활성 = [x for x in ex.map(탐색, halls) if x]
        기준날 = 날
        if 활성:
            break
        print(f"    산지 {날} 거래 없음 — 하루 앞으로", flush=True)

    활성.sort(key=lambda x: -x[1])
    선택 = [코드 for 코드, _ in 활성[:상위]]
    print(f"    산지 {기준날} 거래 있는 곳 {len(활성)}/{len(halls)} → 상위 {len(선택)}곳 수집",
          flush=True)
    if not 활성:
        기록["실패"].append(
            f"산지: {날짜들[0]}~{날짜들[-1]} 어느 날짜에도 거래가 없다")

    # 2) 선택된 곳만 전 날짜 수집 — 병렬
    def 받기(쌍):
        날짜, 코드 = 쌍
        return 쌍, client.fetch_all("originTrialHall/dealings",
                                   {"clcln_ymd::EQ": 날짜, "trhl_cd::EQ": 코드},
                                   max_pages=10)

    조합 = [(날짜, 코드) for 날짜 in 날짜들 for 코드 in 선택]
    with ThreadPoolExecutor(max_workers=동시호출) as ex:
        for (날짜, 코드), r in ex.map(받기, 조합):
            if r.ok:
                rows.extend(r.rows)
            else:
                기록["실패"].append(f"산지 {코드}/{날짜}: {r.error}")
    print(f"    산지 {len(rows):,}행", flush=True)
    return rows


# ── 저장 ─────────────────────────────────────────────────────────────
def 원자쓰기(경로: pathlib.Path, rows: list[dict]) -> None:
    """🔴 **임시 파일에 다 쓴 뒤 바꿔치기한다.**

    `write_text` 는 대상 파일을 **먼저 비우고** 쓴다. 25MB 를 쓰는 중간에
    프로세스가 끊기면 원본도 새 자료도 아닌 반쪽 파일이 남고, 그것을 읽는
    쪽은 그냥 JSON 오류를 낸다 — 어제 것으로 돌아갈 방법이 없다.

    같은 폴더에 임시 파일을 만든 뒤 `os.replace` 로 갈아 끼우면, 어느
    시점에 끊겨도 **옛 파일 아니면 새 파일**이지 그 사이는 없다.
    """
    경로.parent.mkdir(parents=True, exist_ok=True)
    임시 = 경로.with_name(경로.name + ".tmp")
    임시.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    os.replace(임시, 경로)          # 같은 볼륨이므로 원자적이다


def 저장(이름: str, rows: list[dict], 온전: bool, 기록: dict) -> None:
    """🔴 **온전하지 않은 수집이 온전한 파일을 덮게 두지 않는다.**

    전에는 「실패가 있고 **받은 행이 하나도 없을 때만**」 기존 파일을
    지켰다. 그래서 61종 중 3종만 실패하고 나머지가 들어오면, 실패가
    기록된 채로 **반쪽 자료가 온전한 파일을 덮었다.** 행 수가 줄어도
    오류가 나지 않아 다음 판정이 조용히 바뀐다.

    판단 기준을 「행이 있느냐」에서 **「이 단계가 온전했느냐」**로 바꾼다.

        온전                 → 갈아 끼운다
        반쪽 + 기존 파일 있음 → **기존을 지키고**, 받은 것은 PARTIAL 로 따로
        반쪽 + 기존 파일 없음 → 없는 것보다 나으므로 쓰되, 실패로 기록해
                               다음 주기가 다시 받게 한다

    🔴 **0행은 온전으로 치지 않는다.** 조용한 실패와 구분이 안 되는데,
       빈 배열로 덮으면 그동안 모은 것이 통째로 사라진다.
    """
    본 = OUT / f"{이름}.json"
    조각 = OUT / f"{이름}.PARTIAL.json"

    if 온전 and rows:
        원자쓰기(본, rows)
        if 조각.exists():
            조각.unlink()                     # 온전한 것이 왔으니 반쪽은 치운다
        return

    if not rows:
        기록["경고"].append(
            f"{이름}: 받은 행이 0이라 기존 파일을 그대로 둡니다")
        return

    if 본.exists():
        원자쓰기(조각, rows)
        기록["경고"].append(
            f"{이름}: 수집이 온전하지 않아 기존 파일을 유지합니다 "
            f"(받은 {len(rows):,}행은 {조각.name} 에 따로 뒀습니다)")
        return

    원자쓰기(본, rows)
    기록["경고"].append(
        f"{이름}: 기존 파일이 없어 반쪽 수집본({len(rows):,}행)을 씁니다 "
        f"— 다음 주기에 다시 받습니다")


def 단계(이름: str, 기록: dict, 함수, *인자) -> tuple[list[dict], bool]:
    """한 단계를 돌리고 **그 단계에서 실패가 났는지**를 함께 돌려준다.

    🔴 실패 목록은 하나인데 세 단계가 같이 쓴다. 그것을 통째로 보면
       소매 한 종이 실패했다는 이유로 **멀쩡한 도매 수집까지 버려진다.**
       그래서 단계별로 앞뒤를 재어 자기 실패만 본다.
    """
    전 = len(기록["실패"])
    rows = 함수(*인자)
    return rows, len(기록["실패"]) == 전


# ── 실행 ─────────────────────────────────────────────────────────────
def main() -> None:
    use_utf8_stdout()
    기준일 = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d")
    설정 = json.loads(CONFIG.read_text(encoding="utf-8"))
    paths.준비()

    쓸것, 뺀것 = 대응표읽기()
    대상 = 설정["대상품목"]["목록"]
    품목들 = [r for r in 쓸것 if r["품목명"] in 대상]

    print(f"기준일 {기준일} · 대상 {len(품목들)}/{len(대상)}종")
    if 뺀것:
        print(f"  제외 {len(뺀것)}종 (대응 근거 없음)")

    기록 = {"기준일": 기준일, "실패": [], "경고": [],
           "제외품목": [{"품목": n, "사유": w} for n, w in 뺀것]}
    client = Client()
    한도 = 설정["수집"]["일_트래픽_상한"]

    print("\n[1/3] 소매·중도매")
    소매, 소매온전 = 단계("retail", 기록, 소매수집,
                      client, 품목들, 기준일, 설정["기준가"]["기준연수"], 기록)

    날짜들 = 최근조사일(기준일, 3)

    print("\n[2/3] 도매시장")
    if client.call_count < 한도:
        도매, 도매온전 = 단계("wholesale", 기록, 도매수집,
                          client, 설정["수집"]["도매시장"], 날짜들, 기록)
    else:
        # 🔴 상한에 걸려 건너뛴 것은 **성공이 아니다.** 예전에는 그냥 빈
        #    배열이 돼서, 온전한 파일을 `[]` 로 덮을 수 있었다.
        도매, 도매온전 = [], False
        기록["실패"].append(f"도매: 일 트래픽 상한 {한도}회 도달 — 건너뜁니다")

    print("\n[3/3] 산지공판장")
    if client.call_count < 한도:
        산지, 산지온전 = 단계("origin", 기록, 산지수집,
                          client, 설정["수집"]["산지공판장_상위"], 날짜들, 기록)
    else:
        산지, 산지온전 = [], False
        기록["실패"].append(f"산지: 일 트래픽 상한 {한도}회 도달 — 건너뜁니다")

    for 이름, rows, 온전 in [("retail", 소매, 소매온전),
                           ("wholesale", 도매, 도매온전),
                           ("origin", 산지, 산지온전)]:
        저장(이름, rows, 온전, 기록)

    기록.update({"호출수": client.call_count, "트래픽상한": 한도,
               "건수": {"소매": len(소매), "도매": len(도매), "산지": len(산지)},
               # 🔴 어느 단계가 온전했는지 남긴다 — 나중에 「그날 자료를
               #    믿어도 되는가」를 되짚을 수 있어야 한다
               "온전": {"소매": 소매온전, "도매": 도매온전, "산지": 산지온전}})
    (OUT / "collect_report.json").write_text(
        json.dumps(기록, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n소매 {len(소매):,} · 도매 {len(도매):,} · 산지 {len(산지):,}행")
    print(f"호출 {client.call_count}/{한도}회")
    if 기록["실패"]:
        print(f"🔴 실패 {len(기록['실패'])}건 — 기록하고 계속 진행했습니다")
        for f in 기록["실패"][:5]:
            print(f"     {f}")
    print(f"→ {OUT.relative_to(ROOT)}/")

    # 🔴 실패가 있으면 **종료코드로 알린다.** 0 을 내면 agent.py 가
    #    성공으로 보고 지문을 갱신해 다음 주기에 다시 받지 않는다.
    if 기록["실패"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
