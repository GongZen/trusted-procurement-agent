"""설계 전제를 실측으로 검증한다.

이 스크립트는 산출물이 아니라 **검증 도구**다. 문서에 적은 전제가 두 공개
데이터에서 실제로 성립하는지 확인하고, 성립하지 않으면 그 사실을 남긴다.

검증 대상 네 가지
    ① 집계가 상쇄를 숨기는가 — grain을 낮추면 반대 방향 변동이 드러나는가
    ② 마진율이 실제로 변하는가 — 변하지 않으면 "마진 진단"의 대상이 없다
    ③ 원가 전가율을 계산할 수 있는가 — Δ단가 / Δ단위원가
    ④ 가격 변화와 수량 변화의 관계를 관측할 수 있는가

실행:
    python analysis/measure_premises.py

데이터는 저장소에 포함되지 않는다. DATA_SOURCES.md의 재현 절차로 먼저 받는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CONTOSO = ROOT / "contoso"
AW = ROOT / "adventureworks"


def load_contoso() -> pd.DataFrame:
    prod = pd.read_csv(CONTOSO / "product.csv", usecols=["ProductKey", "CategoryName", "SubCategoryName"])
    sales = pd.read_csv(
        CONTOSO / "sales.csv",
        usecols=["OrderDate", "ProductKey", "Quantity", "NetPrice", "UnitCost", "ExchangeRate"],
        parse_dates=["OrderDate"],
    )
    df = sales.merge(prod, on="ProductKey", how="left")
    # 행 단위 환율로 단일 통화 환산
    df["rev"] = df["Quantity"] * df["NetPrice"] * df["ExchangeRate"]
    df["cogs"] = df["Quantity"] * df["UnitCost"] * df["ExchangeRate"]
    df = df.rename(columns={"Quantity": "qty"})
    return df


def load_aw() -> pd.DataFrame:
    # AW의 CSV는 탭 구분·헤더 없음. 컬럼 순서는 instawdb.sql의 CREATE TABLE 정의를 따른다.
    sod = pd.read_csv(AW / "SalesOrderDetail.csv", sep="\t", header=None, usecols=[0, 3, 4, 6, 7],
                      names=["SalesOrderID", "qty", "ProductID", "UnitPrice", "UnitPriceDiscount"])
    soh = pd.read_csv(AW / "SalesOrderHeader.csv", sep="\t", header=None, usecols=[0, 2],
                      names=["SalesOrderID", "OrderDate"], parse_dates=["OrderDate"])
    prod = pd.read_csv(AW / "Product.csv", sep="\t", header=None, usecols=[0, 8, 18],
                       names=["ProductID", "StandardCost", "ProductSubcategoryID"])
    psc = pd.read_csv(AW / "ProductSubcategory.csv", sep="\t", header=None, usecols=[0, 1, 2],
                      names=["ProductSubcategoryID", "CategoryID", "SubCategoryName"])

    df = (sod.merge(soh, on="SalesOrderID")
             .merge(prod, on="ProductID", how="left")
             .merge(psc, on="ProductSubcategoryID", how="left"))
    df = df[df["ProductSubcategoryID"].notna()].copy()
    df["rev"] = df["qty"] * df["UnitPrice"] * (1 - df["UnitPriceDiscount"])
    df["cogs"] = df["qty"] * df["StandardCost"]
    return df


def prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["gp"] = df["rev"] - df["cogs"]
    df["year"] = df["OrderDate"].dt.year
    df["quarter"] = df["OrderDate"].dt.to_period("Q")
    return df


# ── ① 상쇄 비율 ──────────────────────────────────────────────────
def offset_ratio(df: pd.DataFrame, level: str, prev: int, curr: int):
    """상쇄 비율 = 1 - |Σδ| / Σ|δ|

    모든 세그먼트가 같은 방향이면 0%. 반대 방향이 섞일수록 100%에 가까워진다.
    100%에 가까울수록 '전사 순변동이 상쇄로 가려져 있다'는 뜻이다.
    """
    a = df[df["year"] == prev].groupby(level)["gp"].sum()
    b = df[df["year"] == curr].groupby(level)["gp"].sum()
    d = (b - a).dropna()
    if len(d) == 0 or d.abs().sum() == 0:
        return None
    return {
        "세그먼트": len(d),
        "증가": int((d > 0).sum()),
        "순변동": d.sum(),
        "상쇄%": (1 - abs(d.sum()) / d.abs().sum()) * 100,
    }


# ── ② 마진율 추이 ────────────────────────────────────────────────
def margin_trend(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("year").agg(rev=("rev", "sum"), gp=("gp", "sum"), rows=("qty", "size"))
    g["GPM%"] = g["gp"] / g["rev"] * 100
    return g


# ── ③④ 전가율과 가격-수량 관계 ──────────────────────────────────
def passthrough_and_response(df: pd.DataFrame, level: str = "SubCategoryName"):
    g = df.groupby([level, "quarter"]).agg(q=("qty", "sum"), rev=("rev", "sum"), cogs=("cogs", "sum")).reset_index()
    g["p"] = g["rev"] / g["q"]
    g["c"] = g["cogs"] / g["q"]
    g = g.sort_values([level, "quarter"])

    # 전년 동기 대비 (4분기 전) — 계절성을 제거한다
    for col in ("p", "c", "q"):
        g[f"{col}_prev"] = g.groupby(level)[col].shift(4)
    d = g.dropna(subset=["p_prev", "c_prev", "q_prev"])
    d = d[(d["p_prev"] > 0) & (d["c_prev"] > 0) & (d["q_prev"] > 0)].copy()

    d["dp"] = (d["p"] / d["p_prev"] - 1) * 100
    d["dc"] = (d["c"] / d["c_prev"] - 1) * 100
    d["dq"] = (d["q"] / d["q_prev"] - 1) * 100

    # 전가율: 원가가 유의미하게 움직인 경우에만 의미가 있다
    moved = d[d["dc"].abs() >= 1].copy()
    moved["pt"] = moved["dp"] / moved["dc"]
    pt = moved["pt"].replace([np.inf, -np.inf], np.nan).dropna()
    pt = pt[(pt > -3) & (pt < 5)]  # 분모가 0에 가까운 극단값 제거

    return d, pt


def report(name: str, df: pd.DataFrame) -> None:
    print(f"\n{'=' * 70}\n  {name}\n{'=' * 70}")

    trend = margin_trend(df)
    print("\n[②] 연도별 매출총이익률")
    print(trend[["rows", "rev", "gp", "GPM%"]].round(1).to_string())
    gpm_range = trend["GPM%"].max() - trend["GPM%"].min()
    print(f"  → GPM 변동폭 {gpm_range:.2f}%p"
          f"{'  (마진 진단의 대상이 존재)' if gpm_range > 1 else '  (사실상 불변 — 마진 진단의 대상이 없다)'}")

    years = sorted(df["year"].unique())
    prev, curr = years[-3], years[-2]  # 마지막 해는 부분 연도일 수 있어 제외
    print(f"\n[①] 상쇄 비율 ({prev} → {curr})")
    for level in ["SubCategoryName"]:
        r = offset_ratio(df, level, prev, curr)
        if r:
            print(f"  {level:<18} 세그먼트 {r['세그먼트']:>4}개 (증가 {r['증가']:>3})  상쇄 {r['상쇄%']:>5.1f}%")
    print("  연도 쌍별:")
    for p, c in zip(years, years[1:]):
        r = offset_ratio(df, "SubCategoryName", p, c)
        if r:
            print(f"    {p}→{c}  세그먼트 {r['세그먼트']:>3}  순변동 {r['순변동']:>15,.0f}  상쇄 {r['상쇄%']:>5.1f}%")

    d, pt = passthrough_and_response(df)
    print(f"\n[③] 원가 전가율 — 세그먼트×분기 관측치 {len(d)}건 중 계산 가능 {len(pt)}건")
    if len(pt):
        print(f"  중앙값 {pt.median():.2f}  사분위 [{pt.quantile(.25):.2f}, {pt.quantile(.75):.2f}]")
        print(f"  과소전가(<0.9) {(pt < .9).sum():>4}  완전(0.9~1.1) {((pt >= .9) & (pt <= 1.1)).sum():>4}  과잉(>1.1) {(pt > 1.1).sum():>4}")

    print("\n[④] 가격 방향별 수량 변화 (중앙값)")
    for label, sub in [("가격 +2% 이상", d[d["dp"] >= 2]),
                       ("가격 변동 2% 미만", d[d["dp"].abs() < 2]),
                       ("가격 -2% 이하", d[d["dp"] <= -2])]:
        if len(sub):
            print(f"  {label:<18} n={len(sub):>4}  수량변화 {sub['dq'].median():>7.1f}%")
    if len(d) > 10:
        print(f"  가격변화율 ↔ 수량변화율 상관계수 {d[['dp', 'dq']].corr().iloc[0, 1]:.3f}")


def main() -> int:
    missing = [p for p in (CONTOSO, AW) if not p.exists()]
    if missing:
        print("원본 데이터가 없습니다. DATA_SOURCES.md의 재현 절차를 먼저 실행하세요.")
        for p in missing:
            print(f"  없음: {p}")
        return 1

    report("Contoso V2 (SQLBI)", prep(load_contoso()))
    report("AdventureWorks (Microsoft)", prep(load_aw()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
