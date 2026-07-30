"""읽는 곳과 쓰는 곳을 나눈다 — 실행 환경이 둘을 다르게 다루기 때문이다.

🔴 **타임리는 `.pi/skills/` 를 매 턴 지우고 라이브러리에서 다시 만든다.**
   그래서 Skill 폴더 안에 상태를 쓰면 **다음 주기에 사라진다.** 그러면
   중복 감지가 영영 작동하지 않고, 매일 처음부터 도는 스크립트가 된다.

    .pi/skills/<name>/     코드·코드표·서식      매 턴 재생성 (읽기 전용으로 취급)
    ./ (워크스페이스 루트)  수집본·상태·산출물     자동 sync 로 생존

로컬에서는 둘 다 Skill 폴더 안이면 편하므로, **환경변수로 바꿀 수 있게** 한다.

    TPA_DATA_DIR    수집본·상태·산출물을 둘 곳 (기본: Skill 폴더)

타임리 AGENT.md 에서는 `TPA_DATA_DIR=./tpa` 를 주면 된다.
"""
from __future__ import annotations

import os
import pathlib

# 코드가 있는 곳 — 코드표·서식·설정을 읽는다
SKILL = pathlib.Path(__file__).resolve().parent.parent

# 데이터를 쓰는 곳 — 없으면 Skill 폴더를 쓴다(로컬 실행)
DATA_ROOT = pathlib.Path(
    os.environ.get("TPA_DATA_DIR", "").strip() or SKILL).resolve()

REFERENCE = SKILL / "reference"        # 읽기 — 코드표·대응표
CONFIG = SKILL / "config"              # 읽기 — 설정
TEMPLATES = SKILL / "templates"        # 읽기 — 서식

SAMPLE = DATA_ROOT / "sample-data"     # 쓰기 — 수집본
OUTPUT = DATA_ROOT / "output"          # 쓰기 — 산출물
STATE = DATA_ROOT / "state"            # 쓰기 — Agent 기억


def 준비() -> None:
    for d in (SAMPLE, OUTPUT, STATE):
        d.mkdir(parents=True, exist_ok=True)


def 어디에(이름: str) -> pathlib.Path:
    """수집본을 찾는다. **쓰는 곳을 먼저 보고 없으면 Skill 동봉본을 쓴다.**

    심사자가 인증키 없이 실행하면 Skill 에 동봉한 스냅샷으로 돌고,
    한 번이라도 수집했으면 그 결과가 우선한다.
    """
    # 🔴 **위치가 먼저다.** 이름(슬림 여부)을 먼저 순회하면 다른 위치의
    #    슬림본이 이 위치의 새 수집본을 이긴다. 실제로 오늘 수집한 자료를
    #    두고 어제 동봉본을 읽어 **두 날짜가 한 보고서에 섞였다.**
    #
    #    한 위치 안에서만 슬림본을 우선한다.
    for base in (SAMPLE, SKILL / "sample-data"):
        for 후보이름 in (f"{이름}_slim", 이름):
            for 확장 in (".json.gz", ".json"):
                후보 = base / f"{후보이름}{확장}"
                if 후보.exists():
                    return 후보
    return SAMPLE / f"{이름}.json.gz"
