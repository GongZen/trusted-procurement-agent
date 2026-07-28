"""품목 대응표 후보를 생성한다 — **생성은 자동, 판정은 사람**.

DATA_CRITERIA §5의 규칙 4를 코드로 옮긴 것이다. 문자열 매칭은 실제로 틀렸다
(`"배추" in "양배추"` 가 참이라 양배추를 배추로 잡았다). 그래서 이 스크립트는
**후보만 만들고 `검수` 열을 비워 둔다.** 사람이 채우기 전에는 수집에 쓰지 않는다.

산출물: `reference/item_map.csv`

    python scripts/build_item_map.py

컬럼
    그룹          A(3단계 완비) · B(산지·도매 2단계)
    품목명        산지·도매에서 쓰는 이름
    부류코드      perDay ctgry_cd     부류명
    품목코드      perDay item_cd      품목명_perDay
    품종코드      perDay vrty_cd      품종명       (품종 레벨 지정이 필요한 것만)
    대응방식      완전일치 · 사람판정 · 미대응
    근거          왜 그 코드인가
    검수          🔴 비어 있다. 사람이 O/X 를 채운다
"""
from __future__ import annotations

import csv
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from api import Client, use_utf8_stdout  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "reference" / "item_map.csv"

# ── A그룹 — 이름이 그대로 대응되는 52종 (DATA_CRITERIA §4.1) ──────────
A_EXACT = [
    "복숭아", "참외", "풋고추", "포도", "수박", "오이", "사과", "깻잎",
    "토마토", "호박", "감자", "상추", "가지", "바나나", "방울토마토", "부추",
    "양파", "열무", "무", "배추", "배", "양배추", "얼갈이배추", "청경채",
    "새송이버섯", "팽이버섯", "표고버섯", "감귤", "고구마", "당근", "레몬", "멜론",
    "파인애플", "파프리카", "생강", "시금치", "양상추", "체리", "콩", "느타리버섯",
    "망고", "미나리", "오렌지", "자몽", "케일", "갓", "블루베리", "우엉",
    "콩나물", "딸기", "아보카도", "연근",
]

# ── A그룹 — 이름이 달라 사람이 판정한 9종 (DATA_CRITERIA §4.1) ────────
# 🔴 자동 매칭이 틀렸던 것들이다. 코드를 직접 박고 근거를 남긴다.
A_MANUAL = {
    "대파":   ("200", "246", "00", "파 > 대파. 27,649건 확인"),
    "쪽파":   ("200", "246", "02", "파 > 쪽파. 실파는 품종에 없어 제외"),
    "마늘":   ("200", "258", "",   "깐마늘(국산). 19,964건. 수입(259)은 0건"),
    "홍고추": ("200", "243", "",   "붉은고추. 13,872건. 자동 매칭은 풋고추로 오판했다"),
    "브로콜리": ("200", "280", "", "14,120건 일반 유통. 261은 유기농·백화점 전용(776건)"),
    "꽈리고추": ("200", "242", "02", "풋고추 > 꽈리고추. 품목이 아니라 품종 레벨에 있었다"),
    "참다래": ("400", "419", "",   "키위. 12,747건"),
    "피망":   ("200", "255", "",   "단고추. 12,685건"),
    "양송이": ("300", "321", "",   "버섯류"),
}

# ── 산지·도매(`gds_*`) 쪽 사람 판정 ──────────────────────────────────
# 이름이 다르거나 후보가 여럿이라 자동으로 정할 수 없던 것들이다.
# 판정 근거는 **실제 거래 건수**다 — 2026-07-10·17·24 사흘치를 가락시장과
# 산지공판장 상위 10곳에서 받아 코드별로 셌다. 후보가 여럿일 때 나머지가
# 전부 0건이면 그것은 「선택」이 아니라 「관측」이다.
GDS_MANUAL = {
    # 이름이 달라 자동 매칭이 실패한 것
    "새송이버섯": ("17", "11", "코드표 이름은 「새송이」. 17/02는 양송이로 다른 품목이다"),
    "멜론":     ("08", "05", "코드표 표기가 「메론」이다. 같은 품목"),
    "브로콜리":  ("13", "06", "「브로코리(녹색꽃양배추)」 산지 25 · 도매 76건. "
                            "13/12 칼리플라워는 콜리플라워로 다른 품목"),
    "참다래":    ("06", "11", "「참다래(키위)」 산지 29 · 도매 17건. 나머지 후보는 전부 0건"),
    "피망":     ("13", "02", "「피망(단고추)」 산지 40 · 도매 127건. "
                            "13/26 파프리카는 별개 품목이다"),
    # 후보가 여럿이었으나 나머지가 전부 0건이라 관측으로 갈린 것
    "사과":     ("06", "01", "과실류 산지 1,094 · 도매 568건. 19/I9 약용작물류는 0건"),
    "콩":       ("03", "01", "두류 산지 30 · 도매 126건. GMO(98/01)·LMO(99/01)는 0건"),
    "콩나물":    ("10", "16", "엽경채류 산지 64 · 도매 3건. GMO(98/06)는 0건"),
    "옥수수":    ("04", "01", "잡곡류 산지 123 · 도매 217건. GMO·LMO는 0건"),
    "새싹":     ("14", "24", "산채류 산지 17 · 도매 89건. 인삼류(18/08)는 0건"),
}

# ── B그룹 — perDay 소매 조사 대상이 아닌 30종 (DATA_CRITERIA §4.2) ────
B_GROUP = [
    "자두", "옥수수", "치커리", "로메인", "적채", "근대", "아욱", "비름",
    "고들빼기", "고사리", "도라지", "두릅", "머위대", "방풍나물", "참당귀",
    "숙주나물", "새싹", "쌈추", "겨자", "공심채", "고수", "방아", "비타민",
    "만가닥", "목이", "용과", "살구", "동부", "알로애", "식용허브",
]

# ── 제외 — 비슷한 이름이지만 별개 품목이다 (DATA_CRITERIA §4.3) ───────
EXCLUDED = {"고구마순", "호박잎", "알타리무", "강낭콩", "실파"}


def fetch_perday_items(client: Client, ym_from: str, ym_to: str) -> list[dict]:
    """perDay 계열의 **품목 카탈로그 전체**를 받는다.

    `recent/price` 는 호출 1회로 끝나지만 **그날 조사된 품목만** 나온다.
    실제로 그것만 쓰면 A그룹 61종 중 8종이 「미대응」으로 잘못 떨어졌다
    (청경채·표고버섯·양상추·케일·블루베리·우엉·콩나물·연근 — 그날 조사가
    없었을 뿐이다). 그래서 **월별 통계로 1년치를 훑어** 카탈로그를 만든다.
    """
    result = client.fetch_all(
        "perYearMonth/price",
        {"exmn_ym::GTE": ym_from, "exmn_ym::LTE": ym_to},
        max_pages=120,
    )
    if not result.ok:
        raise SystemExit(f"품목 목록 수집 실패: {result.error}")
    print(f"  perYearMonth/price {ym_from}~{ym_to} "
          f"수신 {len(result.rows)}행 (totalCount={result.total})")
    if result.error:
        print(f"  ⚠️ {result.error}")
    return result.rows


def index_by_name(rows: list[dict]) -> dict[str, list[dict]]:
    """품목명 → 후보 행. **부분 문자열이 아니라 완전일치만** 색인한다."""
    index: dict[str, list[dict]] = {}
    for row in rows:
        name = (row.get("item_nm") or "").strip()
        if not name:
            continue
        index.setdefault(name, []).append(row)
    return index


def load_gds_index() -> dict[str, list[dict]]:
    """산지·도매의 `gds_*` 중분류(=품목 레벨) 코드표를 이름으로 색인한다.

    산지(`originTrialHall`)와 도매(`katSale`)가 **같은 코드 체계**를 쓰므로
    이 표 하나가 두 단계를 함께 잇는다(DATA_CRITERIA §3 ①).
    """
    path = ROOT / "reference" / "goods_medium.csv"
    if not path.exists():
        raise SystemExit(
            f"{path} 가 없습니다. 먼저 코드표를 옮기세요:\n"
            f"  python scripts/import_code_tables.py <(참고)...코드.xlsx>"
        )
    index: dict[str, list[dict]] = {}
    with path.open(encoding="utf-8-sig") as fp:
        for row in csv.DictReader(fp):
            index.setdefault(row["중분류명"].strip(), []).append(row)
    return index


def attach_gds(entry: dict, gds_index: dict[str, list[dict]], name: str) -> None:
    """대응표 한 행에 `gds_*` 코드를 붙인다.

    후보가 둘 이상이면 **고르지 않고 둘 다 남긴다.** 자동으로 하나를 택하면
    사람이 검수할 기회가 사라진다(DATA_CRITERIA §5 규칙 4).
    """
    if name in GDS_MANUAL:
        lclsf, mclsf, why = GDS_MANUAL[name]
        match = next((h for h in gds_index.get(name, []) + [
            h for hs in gds_index.values() for h in hs
            if h["대분류코드"] == lclsf and h["중분류코드"] == mclsf
        ] if h["대분류코드"] == lclsf and h["중분류코드"] == mclsf), None)
        entry["산지대분류"] = lclsf
        entry["산지중분류"] = mclsf
        entry["산지품목명"] = match["중분류명"] if match else ""
        entry["산지대응"] = "사람판정"
        entry["산지근거"] = why
        return

    hits = gds_index.get(name, [])
    if len(hits) == 1:
        entry["산지대분류"] = hits[0]["대분류코드"]
        entry["산지중분류"] = hits[0]["중분류코드"]
        entry["산지품목명"] = hits[0]["중분류명"]
        entry["산지대응"] = "확정"
        entry["산지근거"] = "코드표에 같은 이름이 하나뿐이다"
    elif len(hits) > 1:
        entry["산지대분류"] = " | ".join(h["대분류코드"] for h in hits)
        entry["산지중분류"] = " | ".join(h["중분류코드"] for h in hits)
        entry["산지품목명"] = name
        entry["산지대응"] = f"🔴 후보 {len(hits)}개 — 사람이 고른다"
        entry["산지근거"] = "후보별 실제 거래 건수를 확인해야 한다"
    else:
        entry["산지대분류"] = ""
        entry["산지중분류"] = ""
        entry["산지품목명"] = ""
        entry["산지대응"] = "🔴 미대응 — 다른 이름을 찾아야 한다"
        entry["산지근거"] = "코드표에 같은 이름이 없다"


def build_rows(index: dict[str, list[dict]],
               gds_index: dict[str, list[dict]]) -> list[dict]:
    out: list[dict] = []

    def new_entry(group: str, name: str) -> dict:
        entry = {
            "그룹": group, "품목명": name,
            "산지대분류": "", "산지중분류": "", "산지품목명": "",
            "산지대응": "", "산지근거": "",
            "부류코드": "", "부류명": "", "품목코드": "", "품목명_perDay": "",
            "품종코드": "", "품종명": "", "소매대응": "", "근거": "", "검수": "",
        }
        attach_gds(entry, gds_index, name)
        return entry

    for name in A_EXACT:
        entry = new_entry("A", name)
        hits = index.get(name, [])          # 🔴 완전일치. in 연산자를 쓰지 않는다
        if hits:
            h = hits[0]
            entry.update({
                "부류코드": h.get("ctgry_cd", ""), "부류명": h.get("ctgry_nm", ""),
                "품목코드": h.get("item_cd", ""), "품목명_perDay": h.get("item_nm", ""),
                "소매대응": "완전일치",
                "근거": f"perDay 카탈로그에서 이름 완전일치 · {len(hits)}행",
            })
        else:
            entry.update({
                "소매대응": "🔴 미대응",
                "근거": "perDay 카탈로그에 같은 이름이 없다. 다른 이름을 찾아야 한다",
            })
        out.append(entry)

    for name, (ctgry, item, vrty, why) in A_MANUAL.items():
        entry = new_entry("A", name)
        # 코드로 직접 확인한다 — 이름으로 다시 찾지 않는다
        matched = [
            r for rows_ in index.values() for r in rows_
            if r.get("item_cd") == item and (not vrty or r.get("vrty_cd") == vrty)
        ]
        entry.update({
            "부류코드": ctgry,
            "부류명": matched[0].get("ctgry_nm", "") if matched else "",
            "품목코드": item,
            "품목명_perDay": matched[0].get("item_nm", "") if matched else "",
            "품종코드": vrty,
            "품종명": matched[0].get("vrty_nm", "") if matched and vrty else "",
            "소매대응": "사람판정",
            "근거": why + (f" · 카탈로그 {len(matched)}행 확인" if matched else " · 카탈로그 응답 없음"),
        })
        out.append(entry)

    for name in B_GROUP:
        entry = new_entry("B", name)
        entry.update({
            "소매대응": "해당없음",
            "근거": "perDay 소매 조사 대상이 아니다. 산지↔도매 구간만 비교한다",
        })
        out.append(entry)

    return out


def main() -> None:
    use_utf8_stdout()
    print("품목 대응표 후보를 만듭니다 — 생성은 자동, 판정은 사람입니다.")
    ym_from = sys.argv[1] if len(sys.argv) > 1 else "202507"
    ym_to = sys.argv[2] if len(sys.argv) > 2 else "202606"
    gds_index = load_gds_index()
    print(f"  산지·도매 품목 코드표 {len(gds_index)}개 이름")

    client = Client()
    rows = fetch_perday_items(client, ym_from, ym_to)
    index = index_by_name(rows)
    print(f"  perDay 고유 품목명 {len(index)}개")

    table = build_rows(index, gds_index)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)

    need_review = [r for r in table
                   if "🔴" in r["산지대응"] or "🔴" in r["소매대응"]]
    print(f"\n  → {OUT.relative_to(ROOT)} ({len(table)}행)")
    print(f"     산지 확정 {sum(1 for r in table if r['산지대응'] == '확정')}"
          f" · 소매 완전일치 {sum(1 for r in table if r['소매대응'] == '완전일치')}"
          f" · 소매 사람판정 {sum(1 for r in table if r['소매대응'] == '사람판정')}")
    print(f"     🔴 사람이 봐야 하는 행 {len(need_review)}개")
    for r in need_review:
        flags = [f for f in (r["산지대응"], r["소매대응"]) if "🔴" in f]
        print(f"        {r['그룹']} {r['품목명']:8} {' / '.join(flags)}")
    print(f"\n  호출 {client.call_count}회 사용")
    print("  🔴 「검수」 열이 비어 있습니다. 사람이 채우기 전에는 수집에 쓰지 않습니다.")


if __name__ == "__main__":
    main()
