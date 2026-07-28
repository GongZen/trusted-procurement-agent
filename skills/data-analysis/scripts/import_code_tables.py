"""공공데이터포털 참고문서(엑셀)의 코드표를 `reference/` 로 옮긴다.

**왜 이 스크립트가 필요한가** — `originTrialHall/dealings` 는 `trhl_cd`(공판장 코드)
없이는 어떤 조건으로도 0건을 반환한다. 그리고 그 코드는 **10자리**여서
(`7428200508` 원주원예농협공판장) 추측으로 찾을 수 없다. 코드표는 데이터 상세
페이지의 참고문서 엑셀 안에만 있다.

    출처: 공공데이터포털 15156054 「전국 산지공판장 거래정보」 참고문서
          (참고)전국 산지공판장 거래정보_코드.xlsx  · 이용허락범위 제한 없음

엑셀 원본은 저장소에 두지 않는다. 이 스크립트로 CSV만 뽑아 `reference/` 에 커밋한다.

    python scripts/import_code_tables.py <엑셀경로>
"""
from __future__ import annotations

import csv
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from api import use_utf8_stdout  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
REF = ROOT / "reference"

# 시트명 → (출력 파일명, 한국어 헤더)
SHEETS = {
    "공판장코드": ("trial_halls.csv", ["공판장코드", "공판장명"]),
    "상품대분류코드": ("goods_large.csv", ["대분류코드", "대분류명"]),
    "상품중분류코드": ("goods_medium.csv", ["대분류코드", "중분류코드", "중분류명"]),
    "상품소분류코드": ("goods_small.csv", ["대분류코드", "중분류코드", "소분류코드", "소분류명"]),
}


def main() -> None:
    use_utf8_stdout()
    if len(sys.argv) < 2:
        raise SystemExit("사용법: python scripts/import_code_tables.py <코드표.xlsx>")

    try:
        import openpyxl
    except ImportError:
        raise SystemExit("openpyxl 이 필요합니다: pip install openpyxl")

    src = pathlib.Path(sys.argv[1])
    if not src.exists():
        raise SystemExit(f"파일을 찾을 수 없습니다: {src}")

    REF.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.load_workbook(src, read_only=True)

    for sheet_name, (out_name, header) in SHEETS.items():
        if sheet_name not in workbook.sheetnames:
            print(f"  ⚠️ 시트 없음: {sheet_name}")
            continue

        sheet = workbook[sheet_name]
        rows = []
        for index, values in enumerate(sheet.iter_rows(values_only=True)):
            if index == 0:                       # 엑셀 헤더는 버리고 우리 헤더를 쓴다
                continue
            if values is None or values[0] is None:
                continue
            # 코드는 앞자리 0이 의미를 가지므로 반드시 문자열로 다룬다
            rows.append([("" if v is None else str(v).strip()) for v in values[:len(header)]])

        out = REF / out_name
        with out.open("w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(header)
            writer.writerows(rows)
        print(f"  → reference/{out_name}  {len(rows)}행")

    print("\n  출처: 공공데이터포털 15156054 참고문서 · 이용허락범위 제한 없음")


if __name__ == "__main__":
    main()
