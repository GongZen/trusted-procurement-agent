---
name: trusted-procurement-agent
description: 매일 아침 식자재 시세를 점검해 먼저 볼 품목 다섯 개를 골라 브리핑 한 장으로 남긴다
model: solar-open2
schedule: "0 6 * * *"
trigger_prompt: |
  1. 환경변수 DATAGO_KEY 가 없으면 request_env_var 로 요청한다.
     (공공데이터포털 인증키. 없으면 동봉 스냅샷으로 진행한다)
  2. export TPA_DATA_DIR=./tpa 를 설정한다.
     🔴 .pi/ 아래에 쓰면 다음 턴에 사라져 중복 감지가 작동하지 않는다.
  3. python3 .pi/skills/trusted-procurement-agent/scripts/agent.py 를 실행한다.
  4. 출력에서 상태를 확인한다.
     · 「변화 없음」이면 여기서 끝낸다. 화면을 다시 만들지 않는다.
     · 「새 자료 처리」면 5번으로 간다.
  5. create_artifact(from_path="./tpa/output/report.html",
                     title="오늘 먼저 볼 것") 로 화면을 띄운다.
  6. 응답에 다음 셋만 적는다 — 상태 · 어제와 달라진 것 · 문제가 있었으면 그것.
     산출물 내용을 다시 요약하지 않는다. 화면에 이미 있다.
---

# Trusted Procurement Agent

매일 아침 6시(Asia/Seoul), 사람이 없어도 혼자 돈다.

## 하는 일

```
오늘 시세 조회 (호출 1회)
   └ 어제와 같으면 → 여기서 끝
   └ 다르면 ↓
수집 → 판정 → 어제와 비교 → 화면
```

## 지켜야 할 것

**① 데이터는 워크스페이스 루트 아래에 쓴다**

`.pi/skills/` 는 매 턴 라이브러리에서 다시 만들어지므로 그 안에 쓴 파일은
사라진다. `TPA_DATA_DIR=./tpa` 를 반드시 설정한다.
`./tpa/state/last_run.json` 이 살아 있어야 「어제와 같은가」를 판정할 수 있다.

**② 변화가 없으면 아무것도 만들지 않는다**

같은 화면을 매일 다시 그리면 사람이 읽지 않게 된다.
`agent.py` 가 「변화 없음」을 반환하면 거기서 멈춘다.

**③ 사람을 기다리지 않는다**

확인이 필요한 사안이 있어도 **표시만 하고 계속 간다.**
입력을 요구하며 멈추지 않는다. 실패도 기록하고 다음 주기로 넘긴다.

**④ 숫자를 만들지 않는다**

`report.json` 에 있는 값만 옮긴다. 계산하거나 추정하지 않는다.
응답에 쓸 문장이 필요하면 `agent.py` 출력의 「↳」 줄을 그대로 쓴다.

## 처음 실행할 때

취급 품목을 정하지 않았으면 `config/settings.json` 의 기본값
(산지공판장 취급처가 넓은 10종)으로 돈다. **묻지 않고 진행한다.**

사용자가 품목을 지정하고 싶어 하면 `create_spreadsheet` 로 대응표
(`reference/item_map.csv`)를 띄워 고르게 하고, 결과를
`./tpa/config/my_items.json` 에 저장한다. **이것은 선택이지 실행 조건이 아니다.**
