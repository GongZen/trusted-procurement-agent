# DATA_SOURCES — API 레퍼런스

> **호출에 필요한 것만 담는다.** 선정 근거와 판정은 [DATA_CRITERIA.md](DATA_CRITERIA.md)에 있다.
> 원본 데이터는 `.gitignore`로 저장소에서 제외한다. 이 문서와 재현 절차만 커밋한다.
> **모든 제출물·발표자료에 아래 출처를 표기한다.**

---

## 요약

| 제공기관 | 소스 | 이용허락 | 인증 |
|---|---|---|---|
| 한국농수산식품유통공사 | 가격·유통 11종 | 제한 없음 | `serviceKey` |
| 기상청 | 작물별 농업주산지 상세날씨 | 제한 없음 | `serviceKey` |
| 관세청 | 품목별 수출입실적(GW) | 제한 없음 | `serviceKey` |

**전부 [공공데이터포털](https://www.data.go.kr/)에서 제공하며 인증키 하나로 호출된다.**
IP 등록·로그인·수동 승인이 필요 없으므로 **제3자가 자기 키로 재현할 수 있다.**

> 이용허락범위는 각 상세 페이지의 **「이용허락범위: 제한 없음」** 표기를 근거로 한다(2026-07-28 확인).
> 심의유형은 전부 **개발·운영 단계 자동승인**이다.

---

## 1. 한국농수산식품유통공사 (`B552845`)

모든 서비스가 `https://apis.data.go.kr/B552845/{서비스}/{오퍼레이션}` 형태다.
공통 파라미터: `serviceKey` · `returnType`(JSON/XML) · `pageNo` · `numOfRows`(**상한 1,000**)

> 🔴 **조건 파라미터는 반드시 `cond[...]`로 감싼다.** 실측 확인 2026-07-28.
>
> ```
> ⭕ cond[exmn_ymd::GTE]=20250701&cond[ctgry_cd::EQ]=200&cond[item_cd::EQ]=211   → 565건
> ❌ exmn_ymd::GTE=20250701&ctgry_cd=200&item_cd=211                              → 0건
> ```
>
> **감싸지 않으면 오류가 아니라 `totalCount: 0`이 온다.** 조건이 조용히 무시되므로
> *"데이터가 없다"*로 오판하기 쉽다. 아래 표의 조건 파라미터는 전부 이 형식으로 넣는다.

| 데이터 ID | 서비스/오퍼레이션 | 필수 조건 파라미터 | 용도 |
|---|---|---|---|
| [15156057](https://www.data.go.kr/data/15156057/openapi.do) | `perDay/price` | `exmn_ymd::GTE` `LTE` · `ctgry_cd` · `item_cd` | **본체 — 일별 도소매 가격** |
| [15156070](https://www.data.go.kr/data/15156070/openapi.do) | `risesAndFalls/info` | `exmn_ymd::EQ` | **등락률 — 전일·전주·전월·전년** |
| [15156060](https://www.data.go.kr/data/15156060/openapi.do) | `perYearMonth/price` | `exmn_ym::GTE` `LTE` | **월별 통계 — 평균·최고·최저·표준편차·변동계수** |
| [15156063](https://www.data.go.kr/data/15156063/openapi.do) | `recent/price` | **없음** | **당일 시세 — 트리거용** |
| [15156054](https://www.data.go.kr/data/15156054/openapi.do) | `originTrialHall/dealings` | `clcln_ymd::EQ` · **`trhl_cd::EQ`** | **산지공판장 거래** |
| [15141809](https://www.data.go.kr/data/15141809/openapi.do) | `katSale/trades` | `whsl_mrkt_cd::EQ` · `trd_clcln_ymd::EQ` | **도매시장 정산 — 법인·산지·물량** |
| [15156062](https://www.data.go.kr/data/15156062/openapi.do) | `perRegion/price` | `exmn_ymd::GTE` `LTE` · **`sgg_cd::EQ`** | 지역별 비교 |
| [15156064](https://www.data.go.kr/data/15156064/openapi.do) | `periodWholesale/price` | `exmn_ymd::GTE` `LTE` | 기간별 중도매인 가격 |
| [15156065](https://www.data.go.kr/data/15156065/openapi.do) | `periodRetail/price` | `exmn_ymd::GTE` `LTE` | 기간별 소매가격 |
| [15156073](https://www.data.go.kr/data/15156073/openapi.do) | `ecoFriendly/price` | `exmn_ymd::GTE` `LTE` | 친환경 프리미엄 |
| [15156069](https://www.data.go.kr/data/15156069/openapi.do) | `priceSequel/info` | `exmn_ymd::EQ` | 가격 추이 |
| ~~[15141808](https://www.data.go.kr/data/15141808/openapi.do)~~ | ~~`katRealTime2/trades2`~~ | — | **탈락** (당일분만) |

> **`recent/price`는 필수 조건 파라미터가 없다.** 품목 조건(`ctgry_cd`·`item_cd` 등)은 전부 선택이며, 생략하면 당일 전 품목이 나온다.
> **그래서 이것이 `perDay` 계열의 품목 코드 전체를 얻는 가장 싼 경로다** — 호출 1회로 부류·품목·품종·등급 조합이 나온다.

> 🔴 **`perDay/price`는 `item_cd`까지 있어야 응답한다.** 부류(`ctgry_cd`)만으로는 `totalCount: 0`이다(실측 2026-07-28).

> 🔴 **`originTrialHall/dealings`는 `trhl_cd` 없이 어떤 날짜로도 0건을 반환한다.** 날짜만·기간·조건 없음·이름 `LIKE` 검색 전부 0건으로 확인했다(실측 2026-07-28).
> **공판장 코드표는 상세 페이지의 참고문서** *「전국 산지공판장 거래정보 API명세 및 관련 코드 정보.zip」* **안에만 있다.**
> 이 파일을 받기 전에는 산지 단계를 수집할 수 없다 — **3단계 분석의 선행 조건**이다.

> 🔴 **날짜 형식이 서비스마다 다르다.** `perDay`·`originTrialHall`은 `YYYYMMDD`, `katSale`은 **`YYYY-MM-DD`**.

> 🔴 **품목 키 체계가 두 계열로 갈린다.**
> - `perDay` 계열(`perDay` · `recent` · `risesAndFalls` · `perYearMonth` · `perRegion` · `periodWholesale` · `periodRetail` · `ecoFriendly` · `priceSequel`) → **`ctgry_cd` · `item_cd` · `vrty_cd` · `grd_cd`**
> - 거래 계열(`originTrialHall` · `katSale`) → **`gds_lclsf_cd` · `gds_mclsf_cd` · `gds_sclsf_cd` · `grd_cd`**
>
> **두 계열을 잇는 대응표가 필요하다** — [DATA_CRITERIA §3](DATA_CRITERIA.md)

### 1.1 본체 — `perDay/price`

```
exmn_ymd          조사일자
se_cd / se_nm     구분 (01 소매 · 02 중도매 · 03 친환경 · 07 친환경(신규))
ctgry_cd / _nm    부류 (100 식량작물 · 200 채소류 · 300 특용작물 · 400 과일류 · 500 축산물 · 600 수산물)
item_cd / _nm     품목 136 · vrty_cd / _nm 품종 333 · grd_cd / _nm 등급 694조합
sgg_cd / _nm      시군구 39 · mrkt_cd / _nm 시장 217
unit / unit_sz    단위 · 단위크기
exmn_dd_prc       조사일가격
exmn_dd_cnvs_prc  조사일kg환산가격      ← 규격이 섞여도 비교 가능
```

### 1.2 등락률 — `risesAndFalls/info`

```
exmn_dd_avg_prc        조사일 평균가
dd1_bfr_cmpr_rafrt     전일 대비 등락률(%)
ww1_bfr_cmpr_rafrt     전주 대비
mm1_bfr_cmpr_rafrt     전월 대비
yy1_bfr_cmpr_rafrt     전년 대비      ← 「평소와 다름」의 직접 지표
```

### 1.3 월별 통계 — `perYearMonth/price`

```
exmn_ym          조사연월
pmm_avgprc       평균가      pmm_hgprc 최고   pmm_lwprc 최저
pmm_stddvtn      표준편차    pmm_cfcntvrtn 변동계수   pmm_cfcntrng 범위계수
pyy_*            다른 기준의 같은 통계
```

> **표준편차·변동계수가 있어 「이상」을 통계적으로 판정할 수 있다.** 임의 임계치를 쓰지 않는다는 원칙과 맞는다.

### 1.4 당일 시세 — `recent/price`

```
exmn_ymd            조사일자 (당일)
exmn_dd_prc         조사일 가격
dd1_bfr_prc         1일 전 가격
mm1_bfr_prc         1개월 전 가격
```

### 1.5 산지공판장 — `originTrialHall/dealings`

```
clcln_ymd            정산일자
trhl_cd / trhl_nm    공판장 (코드표 157곳 · 당일 거래는 45곳 안팎)
gds_lclsf~sclsf      상품 대/중/소분류   ← 도매시장과 같은 코드 체계
grd_cd / grd_nm      등급
scsbd_prc            낙찰가      tot_prc 총가격
unit_qty / unit_nm   단위 물량·단위      unit_tot_qty 총물량
plor_cd / plor_nm    산지        trd_se 매매구분
```

### 1.6 도매시장 정산 — `katSale/trades`

```
trd_clcln_ymd        거래정산일자 (YYYY-MM-DD)
whsl_mrkt_cd / _nm   도매시장
corp_cd / corp_nm    도매법인      ← 같은 시장 안에서 법인별 가격 비교
gds_lclsf~sclsf      상품 대/중/소분류
grd_cd / grd_nm      등급
unit_qty · unit_nm   단위 물량·단위    unit_tot_qty 총물량
totprc               총금액        → 실현단가 = totprc ÷ unit_tot_qty
hgprc / lwprc / avgprc  최고·최저·평균가
plor_cd / plor_nm    원산지 (시군 단위)
trd_se               거래구분 (경매 / 정가수의)
```

> **`perDay`와 관측 단위가 다르다.** `perDay`는 *조사* 가격(시장별 대표가), `katSale`은 *정산* 실적(실제 거래).
> **둘을 같은 가격으로 취급하지 않는다.**

---

## 2. 기상청 — 작물별 농업주산지 상세날씨

| 항목 | 값 |
|---|---|
| 데이터 | [15059518](https://www.data.go.kr/data/15059518/openapi.do) |
| End Point | `http://apis.data.go.kr/1360000/FmlandWthrInfoService/getDayStatistics` |
| 오퍼레이션 | `getDayStatistics`(일통계) · `getPureStatistics`(순통계) · `getMmStatistics`(월통계) · 주산지 예보·실황·특보 |
| 필수 | `serviceKey`(**소문자 s**) · `ST_YMD` · `ED_YMD` · `AREA_ID` · `PA_CROP_SPE_ID` |

```
areaId / areaName                        지역
paCropName / paCropSpeId / paCropSpeName  작물 · 특성(계절)
dayAvgTa / dayMaxTa / dayMinTa            일 평균·최고·최저기온
dayAvgRhm / dayMinRhm / dayAvgWs          습도 · 풍속
daySumRn / daySumSs                       강수량 · 일조시간
wrnCd / wrnCount                          특보
```

> 🔴 **작물명이 계절별로 갈리고 문자열 매칭이 위험하다.** 배추 하나에 특성 ID가 **9개**이고, `"배추"` 검색에 **양배추**가 걸린다.
> 예측 용도로는 기각됐다 — [DATA_CRITERIA §6](DATA_CRITERIA.md)

| 계절 | 특성 ID | 주산지 |
|---|---|---|
| 고랭지 | `PA170301` | 강릉 · 태백 · 삼척 |
| 가을 | `PA170401` · `PA240301` | 대전 · 서산 · 해남 · 장흥 |
| 겨울 | `PA170101` · `PA240401` | 해남 · 무안 · 진도 |
| 봄 | `PA170201` · `PA240101` | 부산 · 대구 |

---

## 3. 관세청 — 품목별 수출입실적(GW)

| 항목 | 값 |
|---|---|
| 데이터 | [15101609](https://www.data.go.kr/data/15101609/openapi.do) |
| End Point | `https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList` |
| 필수 | `serviceKey` · `strtYymm` · `endYymm` · `hsSgn` |
| 갱신 | **월 1회** — 매월 15일경 전월까지 현행화 |

```
hsCode      HS 품목코드 (2·4·6·10자리)
statKor     품목명 (한글)      year 연월 (2025.10)
impWgt / impDlr   수입 중량·금액(달러)
expWgt / expDlr   수출 중량·금액
balPayments       수지
```

> **시간 단위가 다르다**(월별 ↔ 일별). 결합 시 **월로 올려서** 비교하고 월 값을 일별로 펴지 않는다.

---

## 4. 재현 절차

### 4.1 인증키 발급

[공공데이터포털](https://www.data.go.kr/)에 가입한 뒤 §1~§3의 데이터를 **활용신청**한다. 전부 자동승인이며, **계정당 인증키 하나가 모든 신청 건에 공통 적용**된다.

> ⚠️ **승인 직후에는 게이트웨이 반영이 지연되어 `HTTP 403 Forbidden`이 날 수 있다.** 잠시 후 재시도한다.
> `serviceKey`는 **일반 인증키(Decoding)** 를 쓴다. Encoding 키를 코드에서 다시 인코딩하면 이중 인코딩으로 거부된다.

### 4.2 키 저장

**저장소에 커밋하지 않는다.** 홈 디렉터리에 **BOM 없이** 저장한다.

```bash
printf '%s' "발급받은_인증키" > ~/.datago-key
```

### 4.3 호출 예시

```bash
KEY=$(cat ~/.datago-key)

# 일별 가격 — 배추 2025년 10월
curl -sG "https://apis.data.go.kr/B552845/perDay/price" \
  --data-urlencode "serviceKey=$KEY" --data-urlencode "returnType=JSON" \
  --data-urlencode "numOfRows=1000" --data-urlencode "pageNo=1" \
  --data-urlencode "cond[exmn_ymd::GTE]=20251001" \
  --data-urlencode "cond[exmn_ymd::LTE]=20251031" \
  --data-urlencode "cond[ctgry_cd::EQ]=200" --data-urlencode "cond[item_cd::EQ]=211"

# 등락률 — 특정일
curl -sG "https://apis.data.go.kr/B552845/risesAndFalls/info" \
  --data-urlencode "serviceKey=$KEY" --data-urlencode "returnType=JSON" \
  --data-urlencode "cond[exmn_ymd::EQ]=20260724" \
  --data-urlencode "cond[ctgry_cd::EQ]=200" --data-urlencode "cond[item_cd::EQ]=211"

# 산지공판장 — 대관령
curl -sG "https://apis.data.go.kr/B552845/originTrialHall/dealings" \
  --data-urlencode "serviceKey=$KEY" --data-urlencode "returnType=JSON" \
  --data-urlencode "cond[clcln_ymd::EQ]=20260724" \
  --data-urlencode "cond[trhl_cd::EQ]=2268212268"

# 도매시장 정산 — 가락 (날짜 형식 주의)
curl -sG "https://apis.data.go.kr/B552845/katSale/trades" \
  --data-urlencode "serviceKey=$KEY" --data-urlencode "returnType=JSON" \
  --data-urlencode "cond[whsl_mrkt_cd::EQ]=110001" \
  --data-urlencode "cond[trd_clcln_ymd::EQ]=2026-07-24"
```

### 4.4 페이지네이션

`numOfRows` 상한이 **1,000**이므로 전량 수집에는 페이지 순회가 필수다. `totalCount`를 종료 조건으로 쓴다.

```
page = 1
while 누적 < totalCount:
    요청(pageNo=page, numOfRows=1000)
    page += 1
```

> **일 트래픽 10,000회 제약을 넘지 않도록 수집 범위를 나눈다.** 근거: [DATA_CRITERIA §7](DATA_CRITERIA.md)

---

## 5. 코드표

각 API 상세 페이지의 **참고문서**(zip/xlsx)에 코드표가 있다. 주요 규모:

| 코드 | 규모 | 출처 |
|---|---|---|
| 품목 · 품종 · 등급 | 136 · 333 · 694조합 | `perDay` 참고문서 |
| 시군구 · 시장 | 39 · 217 | 〃 |
| 산지공판장 | **157곳** | `originTrialHall` 참고문서 |
| HS 품목 | **17,526** | 관세청 참고문서 |
| 주산지 지역 × 작물 | 682행 | 기상청 참고문서 |

---

## 6. 폐기한 데이터

| 데이터 | 폐기 사유 |
|---|---|
| **AdventureWorks** · **Contoso V2** | 갱신되지 않는 완결 파일 · 가상 기업이라 공공데이터와 결합 불가 |
| ~~공영도매시장 실시간 경매정보~~ | 과거 시계열이 보관되지 않는다 ([DATA_CRITERIA §8.1](DATA_CRITERIA.md)) |
