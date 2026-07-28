"""수집본에서 **설정된 품목만** 남겨 다시 담는다.

    python scripts/slim.py

산지 과거는 404,428행인데 우리가 쓰는 것은 설정된 품목뿐이다. 매 실행마다
전부 읽으면 로드에만 7.7초가 든다. 실행 환경에 시간 제한이 있으므로
**쓰지 않을 행을 미리 버린다.**

🔴 원본을 덮어쓰지 않는다. `*_slim.json.gz` 로 따로 담고, 읽는 쪽이
   슬림본이 있으면 그것을 먼저 쓴다. 품목을 넓히면 다시 만들면 된다.
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from api import use_utf8_stdout   # noqa: E402
import paths                      # noqa: E402


def 쓰기(이름: str, rows: list[dict]) -> pathlib.Path:
    경로 = paths.SAMPLE / f"{이름}.json.gz"
    경로.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(경로, "wt", encoding="utf-8", compresslevel=9) as fp:
        json.dump(rows, fp, ensure_ascii=False)
    return 경로


def 읽기(이름: str) -> list[dict]:
    경로 = paths.어디에(이름)
    if not 경로.exists():
        return []
    opener = gzip.open if 경로.suffix == ".gz" else open
    with opener(경로, "rt", encoding="utf-8") as fp:
        return json.load(fp)


def main() -> None:
    use_utf8_stdout()
    설정 = json.loads((paths.CONFIG / "settings.json").read_text(encoding="utf-8"))
    대상 = set(설정["대상품목"]["목록"])

    지도 = {r["품목명"]: r for r in csv.DictReader(
        (paths.REFERENCE / "item_map.csv").open(encoding="utf-8-sig"))}
    코드 = {(지도[n]["산지대분류"], 지도[n]["산지중분류"])
          for n in 대상 if n in 지도 and 지도[n]["산지중분류"]}

    print(f"대상 {len(대상)}품목 · gds 코드 {len(코드)}개")
    for 이름, 걸기 in [
        ("origin_history", lambda r: (r.get("gds_lclsf_cd"),
                                      r.get("gds_mclsf_cd")) in 코드),
        ("origin", lambda r: (r.get("gds_lclsf_cd"),
                              r.get("gds_mclsf_cd")) in 코드),
        ("wholesale", lambda r: (r.get("gds_lclsf_cd"),
                                 r.get("gds_mclsf_cd")) in 코드),
        ("retail", lambda r: r.get("item_nm") in 대상),
    ]:
        rows = 읽기(이름)
        if not rows:
            print(f"  {이름:16} 없음 — 건너뜁니다")
            continue
        남김 = [r for r in rows if 걸기(r)]
        경로 = 쓰기(f"{이름}_slim", 남김)
        print(f"  {이름:16} {len(rows):>7,} → {len(남김):>7,}행"
              f"  ({경로.stat().st_size/1e6:.2f}MB)")


if __name__ == "__main__":
    main()
