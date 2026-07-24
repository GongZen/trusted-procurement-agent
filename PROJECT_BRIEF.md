# PROJECT_BRIEF — 설계 · 확정 사항 · 기각한 대안

> 최초 2026-07-20 · 개정 2026-07-25
> 이 문서는 **"지금까지 무엇이 정해졌는가"**를 한눈에 보는 용도다. 합의가 바뀌면 갱신한다.
> 진행 방식(단계·완료 기준)은 [Scaffolding.md](Scaffolding.md), 협업 절차는 [COLLABORATION.md](COLLABORATION.md) 참조.

---

## 0. 한 줄 요약

**"수익성 의사결정 Agent"를 만든다** — 이익이 왜 변했는지 진단하고, CEO에게 대응 결정을 근거와 함께 올린다.

**범용 CEO Agent가 아니라 수익성 특화다.** 값어치는 마진 계산(엔진)이 아니라 그 위의 **판단 지능 층**(Decision Boundary · 경쟁가설·반대증거 · 교차 신호 통합)과 **신뢰 층**(근거 추적·검증·HITL·재판정)에 있다. 공개 데이터 2종(AdventureWorks · Contoso V2)에서 동일 I/O로 동작해 일반화를 증명한다.

> ⚠️ 개정 사유: 초판은 "여러 데이터셋 공통 정규모델"을 전제했으나, 교차 검증에서 **원가(cost)의 의미가 데이터셋마다 다름**이 실측으로 밝혀져 전제를 기각했다. §4.3 참조.

---

## 1. 프로젝트 목적

**2026 제1회 Upstage × BDAI Harness Engineering Skillthon 제출** (마감 2026-07-29 14:00)

재현 가능한 데이터 분석 **Skill**과, 새 정보를 감지해 반복 동작하는 **Agent**를 만든다.

> 근거: 대회 평가 기준 — Skill·Agent가 전체 배점의 50%, 데이터 검증 20%, 통합분석 20%.

---

## 2. 합의 사항

상태 표기 — **확정**: 잠금 / **검증필요**: 근거 확보 후 확정 / **기각**: 검증에서 반증됨

| # | 내용 | 상태 | 근거 |
|---|---|---|---|
| 1 | 산출물에 **비즈니스 문서 생산 기능**(Decision Card·1p 브리핑) 포함 | 확정 | 분석 결과가 아니라 *결정 가능한 형태*로 나와야 의사결정 도구다 |
| 2 | 도메인 = **CEO 의사결정 지원 Agent** | 확정 | 프로젝트 방향 |
| 3 | **공개 데이터셋 2종 = AdventureWorks + Contoso V2**(SQLBI판, MIT). 같은 Skill이 둘 다에서 동일 I/O로 동작해야 함 | 확정 | 2026-07-20 라이선스 확정 / [DATA_SOURCES.md](DATA_SOURCES.md) |
| 4 | 원본 데이터는 `.gitignore` + **재현 스크립트 + `DATA_SOURCES.md`**(URL·버전·라이선스·다운로드일·SHA-256) | **완료** | [DATA_SOURCES.md](DATA_SOURCES.md) |
| 5 | 공통화 대상은 원시 원가 컬럼이 아니라 **의사결정 계약과 근거 추적 절차** | 확정 | 교차 검토 🔴1·🔴3 |
| 6 | 분석 엔진의 문제 = **수익성(마진) 진단 → 대응 결정** | 확정(방향) | 단, KPI 정의는 미정 → §6 |
| 7 | H1 원가발 / H2 가격발 / H3 믹스발은 **계산 결과를 해석하는 경쟁가설 계층**. 수학적 분해가 먼저 | 개정 | 교차 검토 🔴2 |
| 8 | **데이터 검증(`ValidationReport`)을 Skill의 일부로** 내장 | 확정 | 교차 검토 🟡6 + 데이터 검증 배점 20% 직결 |
| 9 | **이름 = "수익성 의사결정 Agent"** (범용 CEO Agent 아님 — 수익성 특화) | 확정 | 다룰 수 있는 범위에 맞춘 정직한 명명 |
| 10 | 마진 엔진 위에 **판단 지능 층**을 얹는다(**MVP 포함**): ① Decision Boundary ② 경쟁가설·반대증거 ③ 교차 신호 1개 | 확정 | "계산기 탈출"의 최소 요건. 차별점은 계산 난이도가 아니라 판단 |
| 11 | MVP 범위 제한 — **교차신호 1개 · 경계 1종 · 가설 3개** | 확정 | 범위를 넓히다 하나도 완성 못 하는 것을 막는다 |

**기각된 초판 합의**

- ~~"여러 데이터셋 공통 정규모델 + 어댑터 다수"~~ → 과설계·전제 오류로 기각 (§4.3)
- ~~"컬럼 공통분모 = 동일 계산 가능"~~ → 실측으로 반증 (§4.3)

---

## 3. 데이터셋 검증 결과

### 3.1 진짜 공통인 것 (재사용 가능한 코어)

`revenue` · `reported_cogs` · `gross_profit` · `quantity` · 제품 · 고객 · 기간

여기에 **필수 메타데이터**를 붙인다:
`cost_basis`(reported_cogs / standard_product_cost / transaction_cost) · `currency_basis` · `source_grain`

### 3.2 데이터셋별 고유 강점 (플러그인으로 분리)

| 데이터셋 | 고유 강점 |
|---|---|
| **AdventureWorks** | 제조 BOM·생산공정, 구매→Vendor 조달원가, **표준원가 이력**, 할인, 재고. Microsoft **MIT** |
| **Contoso V2 / SQLBI** | 행 단위 **다통화 + 환율**, `UnitPrice`↔`NetPrice`로 **할인 명시 분리**, 제품 카테고리 계층. SQLBI **MIT** |

> ⚠️ **재고는 AdventureWorks 전용이다.** Contoso V2는 8개 테이블(`currencyexchange, customer, date, orderrows, orders, product, sales, store`)로 구성되며 재고 테이블이 없다(실측). 공통 코어에 넣지 않는다.

### 3.3 검증에서 드러난 반증 (초판 전제를 깬 근거)

- **🔴 원가의 의미가 데이터셋마다 다르다** — AW `StandardCost`는 제품 마스터의 **표준원가**(계획된 원가, 시점별 이력), Contoso `UnitCost`는 판매 거래 행에 기록된 **실제 거래원가**다. 같은 `unit_cost` 필드로 적재하면 원가차이(표준↔실제)를 마진 변동으로 오해하게 된다. → `cost_basis` 메타데이터로 의미를 명시한다.
- **✅ Contoso 라이선스 해소 (2026-07-20)** — Microsoft 원본판은 오픈 라이선스가 없어(이용약관상 복제·배포 제한) **폐기**하고, **SQLBI Contoso V2(MIT)**로 교체. 두 공개 데이터셋 모두 재배포 가능한 MIT가 됐다. 상세: [DATA_SOURCES.md](DATA_SOURCES.md)
- **🟡 데이터 품질 이슈 실재** — AW 판매 121,317행 중 **64행**이 주문일 기준 유효 원가이력 결측. 숨기지 않고 `ValidationReport`와 Decision Card의 Unknowns에 반영한다.
- **🟡 KPI에 따라 분해가 달라진다** — `Gross Profit` 설명 시 volume 효과 필수, `GPM`(율) 설명 시 순수 volume은 상쇄. FX×단가 교차항은 귀속 규칙 없이는 분해 순서에 의존한다.
- **🟡 판관비·변동비 구분이 양쪽 모두 없다** — 영업이익·EBITDA 계열은 계산 불가. **CVP 손익분기점도 주장하지 않는다.** 이 한계는 Decision Card에 명시한다.
- **기각: "계획대비실적"** — 목표·쿼터의 grain 불일치(AW=영업사원별, Contoso=제품·매장별). 공통 주제로 부적합.

> 출처: 교차 검산 결과, 각 데이터셋 실제 CSV·`instawdb.sql`

---

## 4. 설계 방향

- **범위**: 공통 Skill 1개 + 공개 데이터 어댑터 2개. **하나의 vertical slice를 끝까지** 완성하되, 두 데이터셋에서 동일 I/O로 동작해 일반화를 증명
- **의사결정 계약** (재사용의 핵심): `DecisionRequest → EvidenceBundle → HypothesisScore → DecisionCard` + 상태 갱신
- **분석 계층(엔진)**: KPI 고정 → 수학적 waterfall(가격·수량·믹스·원가·조정[할인/반품/rebate]) → 교차항 고정 귀속 규칙
- **판단 지능 층 (계산기 탈출 · 차별점)**
  - ① **Decision Boundary** — 어떤 조건(원가·환율·수량)이 바뀌면 권고가 뒤집히는지 제시. **임의 임계치 대신 breakeven 역산.** 경계까지의 여유(headroom)를 확신도로 환산
  - ② **경쟁가설 + 반대증거 + 확신도** — H1/H2/H3를 점수화하되, 그를 약화시키는 증거까지 반영해 confidence 조정
  - ③ **교차 신호 1개** — 마진식이 답하지 못하는 것만 묻는다. **마진 분해와 중복되는 신호는 채택하지 않는다**(§5 참조)
- **검증 계층**: adapter 산출 전 schema·grain·키중복·기간·산식 reconciliation → `ValidationReport`. 원가 결측·FX 비적용은 숨기지 않고 Decision Card의 **Unknowns/Confidence**에 반영
- **산출물**: CEO Decision Card / 1p Briefing

---

## 5. 교차 신호 — 확정 대기

**철회된 후보** — "활성 고객 수 추세". 주문 건수와의 상관계수가 AW **0.999969**, Contoso **0.999258**로 측정됐다. 수량 효과를 다른 이름으로 반복하는 것이어서 철회했다.

**현재 후보와 상태**

| 후보 | 정의 | 상태 |
|---|---|---|
| 예상 반복구매량 (BG/NBD) | 고객별 Recency·Frequency로 다음 기간 예상 주문 수 | 1순위 후보 — **holdout 검증 + 설명 난이도 재평가 대기** |
| 예상 고객기반 GP | 위에 고객별 주문당 마진 결합 | 확장 과제 |
| 구매시점 규칙성 (BG/CNBD-k) | 구매 간격의 규칙성까지 반영 | 보류 — AW의 5회 이상 구매자가 **0.514%**에 불과 |

**데이터 적용성 (실측)**

| 데이터셋 | 고객 수 | 주문 건수 | 2회 이상 구매 | 기간 |
|---|---:|---:|---:|---:|
| AdventureWorks (온라인) | 18,484 | 27,659 | 37.14% | 38개월 |
| Contoso V2 | 86,908 | 980,666 | 93.40% | 116개월 |

**채택 전 공통 검증 기준** — ① 과거 구간 학습·이후 구간 holdout ② 기준모형(직전 기간·전년 동기·단순 활성 고객 수) 대비 ③ MAE/WAPE 개선 확인 ④ 최근 판매수량 기준보다 추가 예측력(수량 효과 재포장 방지) ⑤ 두 데이터가 동일 `EvidenceBundle` 필드 산출 ⑥ 논문에서 임의 기준치 차용 금지.

**추가 판정 기준** — 통계적으로 우수해도 **판단 근거를 설명할 수 없으면 채택하지 않는다.**

> 참고 문헌: Fader, Hardie & Lee (2005), ["Counting Your Customers" the Easy Way](https://doi.org/10.1287/mksc.1040.0098) / Reutterer, Platzer & Schröder (2021), [DOI](https://doi.org/10.1016/j.ijresmar.2020.09.002)

---

## 6. 다음에 반드시 잠글 결정

- [ ] **KPI 고정** — 분해 대상 1개: `Gross Profit` vs `Gross Margin Rate` vs `단위당 GP` (+ 보조 지표로 실현가격 검토)
- [ ] 분석 grain · baseline 기간 · `cost_basis` 선택
- [ ] 할인·반품·rebate 처리 규칙
- [ ] 교차항 귀속 방식 (Shapley vs 고정 규칙)
- [ ] **교차 신호 확정** — holdout 검증 통과 여부 + 설명 난이도
- [ ] **Decision Boundary 역산 설계** — 고정 변수·기준시점(look-ahead 차단)·headroom 정의·근소차 안정화 규칙
- [ ] Skill 입출력 계약(I/O) 정의
- [ ] Agent Trigger / Refresh / Escalation / HITL
- [ ] Live update 입력 형식 · 증거 lineage · 상태 버전
- [ ] 대용량 표본 / 성능 전략
- [ ] 기술 스택 / 플랫폼 (킥오프 2026-07-28에서 세부 확정)

---

## 7. 검토 이력

| 일자 | 검토 대상 | 결과 |
|---|---|---|
| 2026-07-20 | 설계 문서 1차 | blocker 4건 **전면 수용** → 정규모델 기각, 공통화 대상 전환, KPI 고정을 선결 과제로, `ValidationReport` 내장 |
| 2026-07-20 | 데이터 출처·라이선스 | Contoso 원본판 폐기 → SQLBI V2(MIT) 교체 |
| 2026-07-20 | 진행 단계 설계 2차 | Skill/Agent 단계 분리, 통합검증 단계 신설, 완료 기준 수치화 |
| 2026-07-21 | 명명·범위 3차 | "수익성 의사결정 Agent" 확정, MVP 범위 제한 |
| 2026-07-21 | 교차 신호 후보 | "활성 고객 수 추세" 철회 |

> 2026-07-25부터 검토는 GitHub PR에서 진행한다. 절차는 [COLLABORATION.md](COLLABORATION.md) 참조.
