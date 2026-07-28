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
import hashlib
import json
import shutil
import subprocess
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from api import use_utf8_stdout   # noqa: E402
import paths                      # noqa: E402


# 🔴 **쓰지 않는 열이 용량의 절반이다.** 응답에는 등록시각·포장·규격코드 등이
#    함께 오는데 판정에 쓰는 것은 아래뿐이다. 제출 zip 은 20MB 제한이 있으므로
#    행만 거르지 말고 **열도 거른다.**
#
#    🔴 원본은 지우지 않는다. 나중에 다른 열이 필요해지면 다시 뽑으면 된다 —
#       실제로 그런 일이 있었다(관측으로 카탈로그를 만들었다가 코드표로 교체).
쓰는열 = {
    "retail": ["exmn_ym", "ctgry_cd", "ctgry_nm", "item_cd", "item_nm",
               "vrty_cd", "vrty_nm", "grd_cd", "grd_nm", "se_cd", "se_nm",
               "sgg_cd", "sgg_nm", "unit", "unit_sz", "pmm_avgprc"],
    "wholesale": ["trd_clcln_ymd", "whsl_mrkt_cd", "gds_lclsf_cd",
                  "gds_mclsf_cd", "gds_mclsf_nm", "grd_nm",
                  "totprc", "unit_tot_qty", "unit_nm"],
    "origin": ["clcln_ymd", "trhl_cd", "trhl_nm", "gds_lclsf_cd",
               "gds_mclsf_cd", "gds_mclsf_nm", "grd_nm",
               "tot_prc", "unit_tot_qty", "unit_nm", "plor_nm"],
}
쓰는열["origin_history"] = 쓰는열["origin"]


def 열거르기(이름: str, rows: list[dict]) -> list[dict]:
    열 = 쓰는열.get(이름.replace("_slim", ""))
    if not 열:
        return rows
    return [{k: r[k] for k in 열 if k in r} for r in rows]


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


def 판정지문(경로: pathlib.Path) -> str:
    """판정 결과에서 **숫자만** 뽑아 지문을 만든다.

    생성시각처럼 매번 달라지는 것은 뺀다. 슬림 전후로 이 지문이 같아야
    「열을 버려도 결과가 같다」가 증명된다.
    """
    보고 = json.loads(경로.read_text(encoding="utf-8"))
    핵심 = [
        (p.get("품목"), p.get("올해"), p.get("평년평균"), p.get("순위표기"),
         tuple((s.get("단계"), s.get("단위"), s.get("올해"), s.get("평년평균"))
               for s in p.get("단계추적", [])),
         p.get("사람말"))
        for p in 보고.get("우선검토", [])
    ]
    return hashlib.sha256(
        json.dumps(핵심, ensure_ascii=False, sort_keys=True, default=str)
        .encode("utf-8")).hexdigest()[:16]


def 대조(원본판정: pathlib.Path) -> None:
    """🔴 **열을 버려도 판정이 같은지 확인한다.**

    빠진 열은 예외를 내지 않는다. `.get()` 이 None 을 돌려주므로 잘못된
    결과가 조용히 나온다. 실제로 「단위」 기능을 추가했을 때 슬림본에 그
    열이 없었다면 아무도 모르게 빈칸으로 통과했을 것이다.

    그래서 **슬림 전 판정과 슬림 후 판정을 대조**한다. 다르면 멈춘다.
    용량 몇 MB 보다 조용히 틀린 결과가 훨씬 비싸다.
    """
    전 = 판정지문(원본판정)
    r = subprocess.run([sys.executable, str(paths.SKILL / "scripts" / "run.py")],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("\n🔴 슬림본으로 판정이 실패했습니다. 열이 빠졌을 수 있습니다.")
        print((r.stderr or r.stdout).strip()[-400:])
        raise SystemExit(1)
    후 = 판정지문(paths.OUTPUT / "report.json")
    if 전 != 후:
        print(f"\n🔴 슬림 전후로 판정이 달라졌습니다 ({전} → {후}).")
        print("   버린 열 중에 판정에 쓰이는 것이 있습니다. 쓰는열 을 확인하세요.")
        raise SystemExit(1)
    print(f"\n  대조 통과 — 판정 지문 {전} 동일. 열을 버려도 결과가 같습니다.")


def main() -> None:
    use_utf8_stdout()
    설정 = json.loads((paths.CONFIG / "settings.json").read_text(encoding="utf-8"))
    대상 = set(설정["대상품목"]["목록"])

    지도 = {r["품목명"]: r for r in csv.DictReader(
        (paths.REFERENCE / "item_map.csv").open(encoding="utf-8-sig"))}
    코드 = {(지도[n]["산지대분류"], 지도[n]["산지중분류"])
          for n in 대상 if n in 지도 and 지도[n]["산지중분류"]}

    print(f"대상 {len(대상)}품목 · gds 코드 {len(코드)}개")

    # 슬림 전 판정을 먼저 남겨 둔다 — 나중에 대조할 기준이다
    기준 = paths.OUTPUT / "report_before_slim.json"
    현재 = paths.OUTPUT / "report.json"
    if 현재.exists():
        paths.OUTPUT.mkdir(parents=True, exist_ok=True)
        shutil.copy(현재, 기준)
    else:
        기준 = None
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
        남김 = 열거르기(이름, 남김)
        경로 = 쓰기(f"{이름}_slim", 남김)
        print(f"  {이름:16} {len(rows):>7,} → {len(남김):>7,}행"
              f"  ({경로.stat().st_size/1e6:.2f}MB)")

    if 기준 and 기준.exists():
        대조(기준)
        기준.unlink()
    else:
        print("\n  ⚠️ 대조할 기준 판정이 없습니다. run.py 를 먼저 돌리면 검증됩니다.")


if __name__ == "__main__":
    main()
