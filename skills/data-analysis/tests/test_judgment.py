"""판정이 **정직한지** 확인한다 — PR #14 검토가 짚은 항상 blocker 3건.

    python tests/test_judgment.py

`test_loop.py` 가 「루프가 죽지 않는가」를 본다면, 이 시험은
**「같은 입력에 같은 결과가 나오는가」와 「말이 숫자를 배신하지 않는가」**를 본다.

세 결함이 실제로 있었고, 셋 다 예외를 내지 않아 **조용히 통과했다.**
그래서 시험으로 고정한다.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import agent      # noqa: E402
import analyze    # noqa: E402
import collect    # noqa: E402
import paths      # noqa: E402
from api import CallResult, Client, use_utf8_stdout  # noqa: E402

통과: list[tuple[bool, str]] = []


def 확인(조건: bool, 설명: str) -> None:
    통과.append((조건, 설명))
    print(f"  {'⭕' if 조건 else '🔴'} {설명}")


def 보고서지문() -> str:
    """생성시각을 뺀 판정 결과의 지문."""
    보고 = json.loads((paths.OUTPUT / "report.json").read_text(encoding="utf-8"))
    보고.pop("생성시각", None)
    return hashlib.sha256(
        json.dumps(보고, ensure_ascii=False, sort_keys=True, default=str)
        .encode("utf-8")).hexdigest()[:16]


def main() -> None:
    use_utf8_stdout()
    print("판정의 정직성 — PR #14 항상 blocker 검증\n")

    # ── ① 결정성 ────────────────────────────────────────────────────
    print("① 같은 입력에 같은 결과 (해시 시드를 바꿔도)")
    지문들 = []
    for seed in ("101", "202", "303"):
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = seed
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "run.py")],
                           capture_output=True, env=env)
        if r.returncode != 0:
            확인(False, f"PYTHONHASHSEED={seed} 실행 실패")
            break
        지문들.append(보고서지문())
    else:
        확인(len(set(지문들)) == 1,
            f"세 시드에서 같은 보고서 — {지문들[0] if 지문들 else '—'}")

    print("\n① 전역 상태가 없다 (호출 순서에 결과가 좌우되지 않음)")
    행 = [{"exmn_ym": "202507", "item_nm": "x", "se_nm": "소매", "vrty_nm": "v",
          "grd_nm": "상품", "sgg_nm": "서울", "unit": "kg", "unit_sz": "10",
          "pmm_avgprc": "1000"}]
    가 = analyze.같은달_관측(행, "07")
    나 = analyze.같은달_관측(행, "07")
    확인(가 == 나 and list(가.values())[0]["단위"] == "10kg",
        "버킷이 단위를 스스로 담는다 — 함수 밖 상태를 보지 않는다")

    # ── ② 부분 응답은 실패다 ────────────────────────────────────────
    print("\n② 부분 응답이 성공으로 계산되지 않는다")
    c = Client.__new__(Client)
    c.key, c.timeout, c.retries, c.backoff, c.call_count = "x", 1, 1, 0, 0
    import threading
    c._lock = threading.Lock()
    응답 = [CallResult("t", True, 1500, [{"a": i} for i in range(1000)]),
          CallResult("t", False, error="HTTP 429")]
    c.call = lambda *a, **k: 응답.pop(0)
    r = c.fetch_all("t")
    확인(not r.ok and len(r.rows) == 1000,
        f"2페이지 429 → ok={r.ok}, 받은 행은 함께 돌려준다({len(r.rows)}/1500)")

    # ── ③ 지문이 지역을 구분한다 ────────────────────────────────────
    print("\n③ 지역·시장이 바뀌면 지문도 바뀐다")
    바탕 = {"exmn_ymd": "20260727", "ctgry_cd": "200", "item_cd": "211",
          "vrty_cd": "00", "grd_cd": "04", "se_cd": "01"}
    갑 = [dict(바탕, sgg_cd="1101", mrkt_cd="0110200", exmn_dd_prc="1000"),
         dict(바탕, sgg_cd="2100", mrkt_cd="2100200", exmn_dd_prc="2000")]
    을 = [dict(바탕, sgg_cd="1101", mrkt_cd="0110200", exmn_dd_prc="2000"),
         dict(바탕, sgg_cd="2100", mrkt_cd="2100200", exmn_dd_prc="1000")]
    확인(agent.지문만들기(갑) != agent.지문만들기(을),
        "서울/부산 가격을 맞바꾸면 다른 지문이 된다")

    # ── ④ 말이 숫자를 배신하지 않는다 ───────────────────────────────
    print("\n④ 증감 부호와 문장의 방향이 일치한다")
    보고 = json.loads((paths.OUTPUT / "report.json").read_text(encoding="utf-8"))
    어긋남 = []
    for p in 보고.get("우선검토", []):
        for s in p.get("단계추적", []):
            올해, 평년 = s.get("올해"), s.get("평년평균")
            if not 올해 or not 평년:
                continue
            실제 = ("평년보다 높음" if 올해 > 평년 else
                  "평년보다 낮음" if 올해 < 평년 else "평년 수준")
            if s.get("대비") != 실제:
                어긋남.append(f"{p['품목']} {s['단계']}: {평년}→{올해} 인데 "
                            f"'{s.get('대비')}'")
    확인(not 어긋남, f"모든 단계에서 일치 ({len(보고.get('우선검토', []))}품목)"
        if not 어긋남 else f"불일치 {len(어긋남)}건 — {어긋남[:2]}")

    print("\n④ 순위와 평균 대비를 섞지 않는다")
    확인(analyze.자리표현("3/6") == "6년 중 3번째"
        and analyze.대비표현(350, 300) == "평년보다 높음",
        "3/6위(하위권)이면서 평년보다 높을 수 있다 — 두 축이 분리됐다")

    # ── ⑤ 관측 밖 권고를 단정하지 않는다 ────────────────────────────
    print("\n⑤ 공개 가격으로 뒷받침되지 않는 권고를 단정하지 않는다")
    문장 = " ".join(p.get("해석", "") for p in 보고.get("우선검토", []))
    확인("거래처를 바꾸는 것으로는" not in 문장,
        "「거래처를 바꿔도 달라지지 않는다」를 단정하지 않는다")

    # ── ⑥ 반쪽 수집이 온전한 파일을 덮지 않는다 ──────────────────────
    print("\n⑥ 반쪽 수집이 온전한 수집본을 덮지 않는다")
    with tempfile.TemporaryDirectory() as d:
        원래OUT, collect.OUT = collect.OUT, pathlib.Path(d)
        try:
            기록 = {"실패": [], "경고": []}
            본 = collect.OUT / "retail.json"
            조각 = collect.OUT / "retail.PARTIAL.json"

            collect.저장("retail", [{"a": i} for i in range(100)], True, 기록)
            온전본 = 본.read_bytes()

            collect.저장("retail", [{"a": i} for i in range(3)], False, 기록)
            확인(본.read_bytes() == 온전본 and 조각.exists(),
                "3행 반쪽이 100행 온전본을 덮지 않고 PARTIAL 로 빠진다")

            collect.저장("retail", [], True, 기록)
            확인(본.read_bytes() == 온전본,
                "실패가 없어도 0행이면 덮지 않는다 — 조용한 실패와 구분이 안 된다")

            collect.저장("retail", [{"a": i} for i in range(200)], True, 기록)
            확인(len(json.loads(본.read_text(encoding="utf-8"))) == 200
                and not 조각.exists(),
                "온전한 수집은 갈아 끼우고 PARTIAL 을 치운다")

            남김 = list(collect.OUT.glob("*.tmp"))
            확인(not 남김, f"임시 파일이 남지 않는다 (원자 교체) — {len(남김)}개")
        finally:
            collect.OUT = 원래OUT

    # ── ⑦ 스냅샷 지문이 수정시각이 아니라 내용을 본다 ────────────────
    print("\n⑦ 스냅샷 지문이 수정시각이 아니라 내용을 본다")
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "x.json"
        p.write_bytes("같은 내용".encode("utf-8"))
        가 = agent.파일지문(p)
        os.utime(p, (0, 0))                       # 수정시각만 바꾼다
        나 = agent.파일지문(p)
        p.write_bytes("다른 내용".encode())
        다 = agent.파일지문(p)
        확인(가 == 나 and 가 != 다,
            "시각만 바뀌면 지문 유지, 내용이 바뀌면 달라진다")

    전 = agent.스냅샷지문()
    for 이름 in ("retail", "wholesale", "origin", "origin_history"):
        경로 = paths.어디에(이름)
        if 경로.exists():
            os.utime(경로, None)                  # touch — 내용은 그대로
    확인(전 != "" and 전 == agent.스냅샷지문(),
        f"동봉 스냅샷을 touch 해도 지문이 그대로 — {전 or '파일 없음'}")

    # ── ⑧ 우리가 고른 수를 숨기지 않는다 ────────────────────────────
    print("\n⑧ 우리가 고른 수는 최소관측수 하나뿐이고, 그것을 산출물이 밝힌다")
    검증 = 보고.get("검증", {})
    확인(검증.get("최소관측수") and "제외구간" in 검증
        and "우선검토_품목수" not in (보고.get("설정", {}).get("산출물") or {}),
        f"판정 JSON 에 남고, 자르는 수는 설정에서 사라졌다 — "
        f"최소관측 {검증.get('최소관측수')}개 · 제외 {검증.get('제외구간')}")

    # 🔴 **자르지 않는지**를 시험이 지킨다. 상위 N개로 되돌아가면 여기서 걸린다
    확인(검증.get("표시품목") == len(보고.get("우선검토", [])),
        f"올린 품목 수가 자료로 정해진다 — 판정 {검증.get('판정품목')}종 중 "
        f"{검증.get('표시품목')}종")

    화면 = (paths.OUTPUT / "report.html").read_text(encoding="utf-8")
    확인("판정하지 않은 것" in 화면
        and f"{검증.get('최소관측수')}개 미만" in 화면
        and "한 단계라도 올해가 평년에서" in 화면,
        "화면 가이드가 제외 기준과 고르는 기준을 밝힌다")

    # 🔴 화면 가이드에서는 분모를 뺐다(사용자 결정). 텍스트 산출물이
    #    「자르지 않았다」를 확인할 수 있는 **유일한 기록**이므로 여기를 지킨다.
    글 = (paths.OUTPUT / "report.txt").read_text(encoding="utf-8")
    확인(f"판정된 {검증.get('판정품목')}종 중" in 글 and "자르지 않고" in 글,
        "텍스트 산출물에 분모가 남는다 — 화면에서 뺐으므로 여기가 마지막 기록")

    # 「임계치를 쓰지 않는다」는 말이 남아 있다면 **가격을 가르는 선**에
    # 한정된 말이어야 한다. 무조건적인 문장이면 위 두 수와 모순이다
    확인("임의 임계치를 쓰지 않음" not in 화면,
        "무조건적인 「임의 임계치를 쓰지 않음」 문구가 남아 있지 않다")

    실패 = [s for ok, s in 통과 if not ok]
    print("\n" + "=" * 58)
    print(f"{len(통과) - len(실패)}/{len(통과)} 통과")
    for s in 실패:
        print(f"  🔴 {s}")
    sys.exit(1 if 실패 else 0)


if __name__ == "__main__":
    main()
