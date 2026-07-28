"""Agent 루프 — 사람이 없어도 계속 돈다.

    python scripts/agent.py            한 바퀴만 돌고 끝난다 (스케줄러가 부를 때)
    python scripts/agent.py --loop 3   3회 연속으로 돈다 (검증용)

**플랫폼을 모른다.** 타임리도, cron 도, 사람도 모른다. 그냥 `한바퀴()` 를
호출하면 한 주기를 완주하고 무슨 일이 있었는지 돌려준다. 누가 언제 부를지는
바깥의 문제다(Scaffolding S2 — 플랫폼 연결부는 교체 가능하게 얇게).

┌─ 구조 ─────────────────────────────────────────────────────────────┐
│                                                                     │
│   ① 감지   오늘 시세를 받아 **지문**을 만든다                        │
│            └ 지난번과 같으면 여기서 끝. 수집도 판정도 하지 않는다     │
│                                                                     │
│   ② 실행   수집 → 판정 → 산출물                                     │
│            └ 실패는 예외가 아니라 값이다. 기록하고 다음으로 넘어간다  │
│                                                                     │
│   ③ 비교   어제 판정과 오늘 판정의 **차이**를 문장으로 만든다         │
│            └ 이것이 Agent 를 대시보드와 가르는 지점이다              │
│                                                                     │
│   ④ 기록   지문·판정·미완 범위를 상태 파일에 남긴다                  │
│            └ 다음 주기가 여기서부터 이어받는다                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

🔴 **어떤 경우에도 예외를 밖으로 던지지 않는다.** 루프가 죽으면 Agent 가
   아니다. 모든 실패는 `주기결과.문제` 에 담겨 값으로 돌아온다.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
import pathlib
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from api import Client, ApiKeyMissing, use_utf8_stdout   # noqa: E402
import compare                                           # noqa: E402

import paths                                                        # noqa: E402

ROOT = paths.SKILL
STATE = paths.STATE / "last_run.json"
OUT = paths.OUTPUT
KST = timezone(timedelta(hours=9))


@dataclass
class 주기결과:
    """한 바퀴의 결과. **성공/실패가 아니라 무슨 일이 있었나**를 담는다."""
    시각: str
    상태: str                       # 새로운자료 · 변화없음 · 실패 · 이월재개
    지문: str = ""
    기준일: str = ""
    산출: bool = False
    변화: list[str] = field(default_factory=list)
    문제: list[str] = field(default_factory=list)
    호출수: int = 0


# ── 상태 ─────────────────────────────────────────────────────────────
def 상태읽기() -> dict:
    """상태 파일이 없거나 깨져 있어도 **빈 상태로 시작한다.**

    첫 실행과 파일 손상을 구분하지 않는다 — 어느 쪽이든 처음부터 돌면 되고,
    여기서 멈추면 루프가 죽기 때문이다.
    """
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:                                      # noqa: BLE001
        return {"지문": "", "기준일": "", "판정": [], "이월": [], "이력": []}


def 상태쓰기(상태: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    상태["이력"] = 상태.get("이력", [])[-20:]              # 최근 20회만 남긴다
    STATE.write_text(json.dumps(상태, ensure_ascii=False, indent=2),
                     encoding="utf-8")


# ── ① 감지 ───────────────────────────────────────────────────────────
def 지문만들기(행들: list[dict]) -> str:
    """응답에서 **순서에 흔들리지 않는 지문**을 만든다.

    🔴 조사일자만 보면 같은 날 갱신된 값을 놓치고, 해시만 보면 응답 순서가
       바뀔 때 매번 새 데이터로 오인한다. 그래서 **정렬한 뒤 해시**한다.

    가격을 결정하는 열만 넣는다 — 등록시각 같은 열이 섞이면 내용이 같아도
    지문이 매번 달라진다.
    """
    핵심 = sorted(
        f"{r.get('exmn_ymd')}|{r.get('ctgry_cd')}|{r.get('item_cd')}|"
        f"{r.get('vrty_cd')}|{r.get('grd_cd')}|{r.get('se_cd')}|"
        f"{r.get('exmn_dd_prc')}"
        for r in 행들)
    return hashlib.sha256("\n".join(핵심).encode("utf-8")).hexdigest()[:16]


def 오늘시세(client: Client) -> tuple[list[dict], str | None]:
    """`recent/price` 는 필수 조건이 없어 **호출 1회**로 당일 전 품목이 온다.

    트리거 감지에 이보다 싼 방법이 없다. 변화가 없으면 여기서 끝나므로
    한 주기의 최소 비용이 1회다.
    """
    r = client.fetch_all("recent/price")
    if not r.ok:
        return [], r.error
    return r.rows, None


# ── ② 실행 ───────────────────────────────────────────────────────────
def 파이프라인실행() -> tuple[bool, list[str]]:
    """수집·판정·산출을 **별도 프로세스로** 돌린다.

    같은 프로세스에서 import 해 부르면 한쪽이 죽을 때 루프가 함께 죽는다.
    프로세스를 나누면 어떤 예외가 나도 이쪽은 종료코드만 받는다 —
    **루프가 죽지 않는 가장 확실한 방법**이다.
    """
    문제: list[str] = []
    for 이름, 인자 in [("수집", ["collect.py"]), ("판정", ["run.py"])]:
        try:
            p = subprocess.run(
                [sys.executable, str(paths.SKILL / "scripts" / 인자[0])],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=3600)
            if p.returncode != 0:
                꼬리 = (p.stderr or p.stdout or "").strip().splitlines()[-3:]
                문제.append(f"{이름} 실패(코드 {p.returncode}): {' / '.join(꼬리)}")
                if 이름 == "수집":
                    continue          # 수집이 실패해도 기존 수집본으로 판정은 해본다
                return False, 문제
        except subprocess.TimeoutExpired:
            문제.append(f"{이름} 시간 초과 — 다음 주기로 넘깁니다")
            return False, 문제
        except Exception as exc:                           # noqa: BLE001
            문제.append(f"{이름} 예외: {type(exc).__name__}: {exc}")
            return False, 문제
    return True, 문제


def 판정읽기() -> list[dict]:
    try:
        return json.loads((OUT / "report.json").read_text(
            encoding="utf-8")).get("우선검토", [])
    except Exception:                                      # noqa: BLE001
        return []


# ── 한 바퀴 ──────────────────────────────────────────────────────────
def 한바퀴() -> 주기결과:
    """🔴 **여기서 예외가 밖으로 나가면 안 된다.** 전부 값으로 담아 돌려준다."""
    시각 = datetime.now(KST).isoformat(timespec="seconds")
    결과 = 주기결과(시각=시각, 상태="실패")
    상태 = 상태읽기()

    try:
        client = Client()
    except ApiKeyMissing:
        # 인증키가 없는 환경(심사자)에서는 수집본만으로 한 바퀴를 돈다
        결과.문제.append("인증키 없음 — 수집본으로 판정만 수행합니다")
        됨, 문제 = 파이프라인실행()
        결과.문제.extend(문제)
        결과.상태 = "새로운자료" if 됨 else "실패"
        결과.산출 = 됨
        if 됨:
            결과.변화 = compare.차이문장(상태.get("판정", []), 판정읽기())
            상태["판정"] = 판정읽기()
        상태.setdefault("이력", []).append(asdict(결과))
        상태쓰기(상태)
        return 결과

    try:
        # ① 감지 — 호출 1회
        행들, 오류 = 오늘시세(client)
        결과.호출수 = client.call_count
        if 오류:
            결과.문제.append(f"시세 조회 실패: {오류}")
            결과.상태 = "실패"
            상태.setdefault("이력", []).append(asdict(결과))
            상태쓰기(상태)
            return 결과                     # 다음 주기에 다시 시도한다

        결과.지문 = 지문만들기(행들)
        결과.기준일 = (행들[0].get("exmn_ymd") if 행들 else "") or ""

        if 결과.지문 == 상태.get("지문") and not 상태.get("이월"):
            # ③ 같은 데이터 — **중복 처리하지 않는다**
            결과.상태 = "변화없음"
            상태.setdefault("이력", []).append(asdict(결과))
            상태쓰기(상태)
            return 결과

        # ② 실행
        이전판정 = 상태.get("판정", [])
        됨, 문제 = 파이프라인실행()
        결과.문제.extend(문제)
        결과.산출 = 됨

        if not 됨:
            # 실패해도 지문을 갱신하지 않는다 — 다음 주기가 다시 시도한다
            결과.상태 = "실패"
            상태.setdefault("이월", []).append(
                {"기준일": 결과.기준일, "사유": "; ".join(문제)[:200]})
            상태["이월"] = 상태["이월"][-5:]
            상태.setdefault("이력", []).append(asdict(결과))
            상태쓰기(상태)
            return 결과

        # ③ 비교
        오늘판정 = 판정읽기()
        결과.변화 = compare.차이문장(이전판정, 오늘판정)
        결과.상태 = "이월재개" if 상태.get("이월") else "새로운자료"

        # ④ 기록
        상태.update({"지문": 결과.지문, "기준일": 결과.기준일,
                    "판정": 오늘판정, "이월": []})
        상태.setdefault("이력", []).append(asdict(결과))
        상태쓰기(상태)
        return 결과

    except Exception as exc:                               # noqa: BLE001
        결과.문제.append(f"예상 못 한 오류: {type(exc).__name__}: {exc}")
        결과.문제.append(traceback.format_exc(limit=2).strip().splitlines()[-1])
        결과.상태 = "실패"
        try:
            상태.setdefault("이력", []).append(asdict(결과))
            상태쓰기(상태)
        except Exception:                                  # noqa: BLE001
            pass
        return 결과


def 요약(결과: 주기결과) -> str:
    표 = {"새로운자료": "새 자료 처리", "변화없음": "변화 없음 — 건너뜀",
         "실패": "실패 — 기록하고 계속", "이월재개": "이월분 재개"}
    줄 = [f"[{결과.시각[11:19]}] {표.get(결과.상태, 결과.상태)}"
         f" · 지문 {결과.지문 or '—'} · 호출 {결과.호출수}"]
    for v in 결과.변화:
        줄.append(f"    ↳ {v}")
    for v in 결과.문제:
        줄.append(f"    ⚠ {v}")
    return "\n".join(줄)


def main() -> None:
    use_utf8_stdout()
    반복 = 1
    간격 = 0
    argv = sys.argv[1:]
    if "--loop" in argv:
        i = argv.index("--loop")
        반복 = int(argv[i + 1]) if len(argv) > i + 1 else 3
    if "--every" in argv:
        i = argv.index("--every")
        간격 = int(argv[i + 1]) if len(argv) > i + 1 else 3600

    for 회차 in range(1, 반복 + 1):
        결과 = 한바퀴()
        print(f"── {회차}/{반복} " + "─" * 46)
        print(요약(결과), flush=True)
        if 회차 < 반복 and 간격:
            time.sleep(간격)


if __name__ == "__main__":
    main()
