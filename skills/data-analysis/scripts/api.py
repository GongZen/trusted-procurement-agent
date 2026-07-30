"""공공데이터포털 농수산 API 호출부.

이 파일이 존재하는 이유는 하나다 — **조건 파라미터를 `cond[...]`로 감싸는 규칙**이
지켜지지 않으면 오류가 아니라 빈 결과가 오기 때문이다. 호출을 한 곳에 모아
그 실수를 구조적으로 막는다. 근거: DATA_SOURCES.md §1

인증키는 저장소에 두지 않는다. 홈 디렉터리의 `.datago-key` 또는
환경변수 `DATAGO_KEY`에서 읽는다(참가 서약의 보안 조항).
"""
from __future__ import annotations

import os
import sys
import ssl
import json
import threading
import time
import pathlib
from dataclasses import dataclass, field
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

BASE = "https://apis.data.go.kr/B552845"
MAX_ROWS = 1000          # numOfRows 상한. DATA_SOURCES.md §1
KEY_FILE = ".datago-key"

# 🔴 **표준 라이브러리만 쓴다.** 처음에는 `requests` 로 짰는데, 실행 환경에
#    설치돼 있지 않았다(타임리 확인: Python 3.14.5 · openpyxl ⭕ · requests ❌).
#
#    `uv pip install requests` 한 줄이면 되지만 그렇게 하지 않는다 —
#    심사자가 어느 환경에서 열든 **설치 단계 없이 돌아야** 하기 때문이다.
#    우리가 하는 일은 GET 과 JSON 파싱뿐이라 `urllib` 로 충분하다.
_SSL = ssl.create_default_context()


class ApiKeyMissing(RuntimeError):
    pass


def use_utf8_stdout() -> None:
    """Windows 콘솔 기본 코드페이지(cp949)에서 한글 출력이 깨지는 것을 막는다.

    심사자가 어느 환경에서 실행하든 같은 화면이 나와야 하므로 스크립트마다
    맨 앞에서 호출한다.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:                              # noqa: BLE001
                pass


def load_key() -> str:
    """환경변수 → 홈 디렉터리 순으로 인증키를 찾는다."""
    key = os.environ.get("DATAGO_KEY", "").strip()
    if key:
        return key
    path = pathlib.Path.home() / KEY_FILE
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    raise ApiKeyMissing(
        f"인증키를 찾지 못했습니다. 환경변수 DATAGO_KEY 를 설정하거나 "
        f"{path} 에 키를 저장하세요. (키는 저장소에 커밋하지 않습니다)"
    )


@dataclass
class CallResult:
    """한 번의 호출 결과. 실패를 예외로 던지지 않고 값으로 돌려준다.

    Agent 루프가 사람 없이 계속 돌아야 하므로, 실패는 기록 대상이지
    중단 사유가 아니다. 근거: Scaffolding.md §4
    """
    op: str
    ok: bool
    total: int = 0
    rows: list[dict] = field(default_factory=list)
    error: str | None = None
    attempts: int = 1


class Client:
    def __init__(self, key: str | None = None, timeout: int = 30,
                 retries: int = 3, backoff: float = 2.0):
        self.key = key or load_key()
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.call_count = 0          # 일 트래픽 10,000 한도를 추적한다
        self._lock = threading.Lock()   # 병렬 호출에서도 카운트가 맞아야 한다

    # ── 요청 URL 조립 ────────────────────────────────────────────
    def _url(self, op: str, cond: dict | None, page: int, rows: int) -> str:
        parts = [
            f"serviceKey={quote(self.key, safe='')}",
            "returnType=JSON",
            f"pageNo={page}",
            f"numOfRows={rows}",
        ]
        for field_op, value in (cond or {}).items():
            # 🔴 여기가 핵심이다. cond[...] 로 감싸지 않으면 조건이 조용히 무시된다.
            parts.append(
                f"{quote(f'cond[{field_op}]', safe='[]:')}={quote(str(value), safe='')}"
            )
        return f"{BASE}/{op}?" + "&".join(parts)

    # ── 단일 페이지 ──────────────────────────────────────────────
    def call(self, op: str, cond: dict | None = None,
             page: int = 1, rows: int = MAX_ROWS) -> CallResult:
        rows = min(rows, MAX_ROWS)
        url = self._url(op, cond, page, rows)
        last_error = None

        for attempt in range(1, self.retries + 1):
            try:
                with self._lock:
                    self.call_count += 1
                req = Request(url, headers={"Accept": "application/json"})
                with urlopen(req, timeout=self.timeout, context=_SSL) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                body = payload["response"]["body"]
                items = body.get("items", {}).get("item", []) or []
                if isinstance(items, dict):
                    items = [items]
                return CallResult(op, True, int(body.get("totalCount", 0)),
                                  items, attempts=attempt)
            except HTTPError as exc:
                # 승인 직후 403은 게이트웨이 반영 지연이다. 재시도로 풀린다.
                last_error = f"HTTP {exc.code}"
                time.sleep(self.backoff * attempt)
            except (URLError, TimeoutError) as exc:
                last_error = f"연결 실패: {exc}"
                time.sleep(self.backoff * attempt)
            except Exception as exc:                       # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(self.backoff * attempt)

        return CallResult(op, False, error=last_error, attempts=self.retries)

    # ── 전량 수집 ────────────────────────────────────────────────
    def fetch_all(self, op: str, cond: dict | None = None,
                  max_pages: int = 50) -> CallResult:
        """`totalCount` 를 다 받을 때까지 페이지를 넘긴다.

        수신 건수가 `totalCount` 와 다르면 그 사실을 error 에 남긴다 —
        Step 1 통과 기준이 「totalCount 와 수신 건수 일치」다.
        """
        first = self.call(op, cond, page=1)
        if not first.ok:
            return first

        rows = list(first.rows)
        total = first.total
        page = 2
        중단됨 = False
        while len(rows) < total and page <= max_pages:
            nxt = self.call(op, cond, page=page)
            if not nxt.ok:
                first.error = f"{page}페이지에서 중단: {nxt.error}"
                중단됨 = True
                break
            if not nxt.rows:
                중단됨 = True
                break
            rows.extend(nxt.rows)
            page += 1
        if len(rows) < total and page > max_pages:
            중단됨 = True

        first.rows = rows

        # 🔴 **부분 응답은 실패다.**
        #
        #    처음에는 error 만 적고 ok=True 로 뒀는데, 그러면 collect.py 가
        #    반쪽 자료를 파일에 쓰고 종료코드 0 을 내며, agent.py 가 성공 지문을
        #    저장한다. **그 자료는 영영 다시 받지 않는다.**
        #
        #    `fetch_all` 은 「전량을 받겠다」는 선언이므로 못 받으면 실패다.
        #    받은 행은 함께 돌려주되(진단에 쓰인다) ok 는 False 로 둔다.
        #    첫 페이지만 쓰는 호출은 `call()` 을 직접 쓰므로 이 규칙과 무관하다.
        if first.ok and (중단됨 or len(rows) != total):
            first.ok = False
            if first.error is None:
                first.error = f"부분 응답: totalCount={total} 수신={len(rows)}"
        return first
