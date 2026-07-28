# DATA_SOURCES — 데이터 출처 · 이용 조건 · 재현 절차

> 개정 2026-07-28 — **데이터를 공개 데이터셋 파일에서 공공데이터 API로 전면 교체했다.** 경위: [README §8](README.md)
> 원본 데이터는 `.gitignore`로 저장소에서 제외한다. 이 문서와 재현 절차만 커밋한다.
> **모든 제출물·발표자료에는 아래 출처를 표기한다.**

---

## 요약

| # | 소스 | 제공기관 | 역할 | 이용허락 | 인증 |
|---|---|---|---|---|---|
| **①** | 일별 도·소매 가격정보 | 한국농수산식품유통공사 | **본체** | 제한 없음 | `serviceKey` |
| **②** | 전국 공영도매시장 정산정보 | 한국농수산식품유통공사 | 보조 | 제한 없음 | `serviceKey` |
| **③** | 작물별 농업주산지 상세날씨 | 기상청 | 보조 | 제한 없음 | `serviceKey` |
| **④** | 품목별 수출입실적(GW) | 관세청 | 보조 | 제한 없음 | `serviceKey` |
| ~~⑤~~ | ~~전국 공영도매시장 실시간 경매정보~~ | 한국농수산식품유통공사 | **탈락** | — | — |

**네 소스 모두 [공공데이터포털](https://www.data.go.kr/)에서 제공하며 인증키 하나로 호출된다.**
IP 등록·로그인·수동 승인이 필요하지 않으므로 **제3자가 자기 키로 같은 데이터를 재현할 수 있다.**

> 이용허락범위는 각 상세 페이지의 **「이용허락범위」 항목이 *제한 없음*** 으로 표시된 것을 근거로 한다(2026-07-27 확인).
> 심의유형은 네 건 모두 **개발단계·운영단계 자동승인**이다.

---

## ① 일별 도·소매 가격정보 — 본체

| 항목 | 값 |
|---|---|
| 데이터 페이지 | https://www.data.go.kr/data/15156057/openapi.do |
| 서비스명(영문) | `perDay` · 오퍼레이션 `price` |
| End Point | `https://apis.data.go.kr/B552845/perDay/price` |
| 형식 | REST · JSON + XML |
| 갱신 주기 | 일별 |
| 신청가능 트래픽 | 개발계정 **10,000/일** |
| 참고문서 | `일별 도,소매 가격정보 API명세 및 관련 코드 정보.zip` (명세 xlsx + 코드표 7시트) |

### 요청 파라미터

| 이름 | 필수 | 설명 |
|---|---|---|
| `serviceKey` | 필수 | 공공데이터포털 인증키 |
| `returnType` | 필수 | `JSON` / `XML` (기본 JSON) |
| `pageNo` · `numOfRows` | 필수 | 페이지 번호 · 결과 수 (**최대 1,000**) |
| `cond[exmn_ymd::GTE]` · `cond[exmn_ymd::LTE]` | 필수 | 조사일자 범위 `YYYYMMDD` |
| `cond[ctgry_cd::EQ]` | 필수 | 부류코드 |
| `cond[item_cd::EQ]` | 필수 | 품목코드 |
| `cond[se_cd::EQ]` · `cond[vrty_cd::EQ]` · `cond[grd_cd::EQ]` · `cond[sgg_cd::EQ]` · `cond[mrkt_cd::EQ]` | 선택 | 구분·품종·등급·시군구·시장 |

### 응답 항목

```
exmn_ymd          조사일자
se_cd / se_nm     구분 (01 소매 · 02 중도매 · 03 친환경농산물 · 07 친환경농산물(신규))
ctgry_cd / _nm    부류 (100 식량작물 · 200 채소류 · 300 특용작물 · 400 과일류 · 500 축산물 · 600 수산물)
item_cd / _nm     품목 (136개)
vrty_cd / _nm     품종 (333개)
grd_cd / _nm      등급 (694 조합)
sgg_cd / _nm      시군구 (39개)
mrkt_cd / _nm     시장 (217개)
unit / unit_sz    단위 · 단위크기
exmn_dd_prc       조사일가격
exmn_dd_cnvs_prc  조사일kg환산가격      ← 규격이 섞여도 비교 가능
orgnl_reg_dt      원본등록일시
```

### 실측 결과 (2026-07-27)

- **레코드 확인 연도 14개** — 2013 ~ 2026 (각 연도 6월 한 달을 호출해 확인)
- **품질 진단** (배추 200/211 · 3년 전량 48,240건)

| 연도 | 수신/전체 | 평일 조사일/평일 | 핵심 컬럼 10개 결측 | 중복 키 | `kg환산가격 ≤ 0` |
|---|---|---|---|---|---|
| 2023 | 16,817 / 16,817 | 245 / 260 | 0건 | 0건 | 0건 |
| 2024 | 15,447 / 15,447 | 244 / 262 | 0건 | 0건 | 2건 |
| 2025 | 15,976 / 15,976 | 242 / 261 | 0건 | 0건 | 0건 |

- **유일 식별자** — `(exmn_ymd, mrkt_cd, se_cd, vrty_cd, grd_cd)` 중복 0건
- **`exmn_dd_prc ≠ exmn_dd_cnvs_prc`** — 3.8 ~ 4.3% (단위 정규화가 필요한 실제 범위)
- **수집 규모** — 품목별 편차 123배(표고버섯 749건 ↔ 소 92,136건). 136품목 3년 외삽 시 **9,792 ~ 37,944요청**으로 **일 트래픽 10,000을 초과**한다

> 상세 판정: [DATA_CRITERIA.md §2](DATA_CRITERIA.md)

---

## ② 전국 공영도매시장 정산정보 — 보조

| 항목 | 값 |
|---|---|
| 데이터 페이지 | https://www.data.go.kr/data/15141809/openapi.do |
| 서비스명(영문) | `katSale` · 오퍼레이션 `trades` |
| End Point | `https://apis.data.go.kr/B552845/katSale/trades` |
| 갱신 주기 | 일별 |
| 참고문서 | `전국 공영도매시장 정산정보 API 명세 및 컬럼변경내역.xlsx` |

### 요청 파라미터

| 이름 | 필수 | 설명 |
|---|---|---|
| `cond[whsl_mrkt_cd::EQ]` | 필수 | 도매시장코드 |
| `cond[trd_clcln_ymd::EQ]` | 필수 | 거래정산일자 **`YYYY-MM-DD`** (①과 형식이 다르다) |
| `cond[corp_cd::EQ]` · `cond[gds_lclsf_cd::EQ]` · `cond[gds_mclsf_cd::EQ]` · `cond[gds_sclsf_cd::EQ]` | 선택 | 법인 · 상품 대/중/소분류 |

### 응답 항목 — ①에 없는 축을 준다

```
unit_qty · unit_nm      단위 물량과 단위        → kg 환산 가능
unit_tot_qty            총물량
totprc                  총금액                 → 실현단가 = totprc ÷ unit_tot_qty
hgprc / lwprc / avgprc  최고 · 최저 · 평균가    → 가격 분포
grd_cd / grd_nm         등급
plor_cd / plor_nm       원산지 (시군 단위)
corp_cd / corp_nm       도매법인
trd_se                  거래구분 (경매 / 정가수의 등)
```

### 실측 결과 — 두 포털에 같은 데이터가 있고 공공데이터포털 경로가 더 길다

| | 농림축산식품 경로 `211.237.50.150` | **공공데이터포털 경로** |
|---|---|---|
| 레코드 확인 연도 | 2020~2026 (7개) | **2018~2026 (9개)** |
| 인증 | IP 등록 필수 | **`serviceKey`만** |
| 2026-07-24 서울가락 | 6,160건 | **6,160건** — 같은 값 |

> 처음에는 농림축산식품 경로만 보고 *"IP 등록 필수"*로 판정해 캐시로 강등했다.
> 교차 검토에서 공공데이터포털 자체 엔드포인트를 확인해 **보조 소스로 되돌렸다.**

**①과 관측 단위가 다르다.** ①은 *조사* 가격(시장별 대표가), ②는 *정산* 실적(실제 거래 물량과 금액)이다. **둘을 같은 가격으로 취급하지 않는다.**

---

## ③ 작물별 농업주산지 상세날씨 — 보조

| 항목 | 값 |
|---|---|
| 데이터 페이지 | https://www.data.go.kr/data/15059518/openapi.do |
| 서비스명(영문) | `FmlandWthrInfoService` |
| End Point | `http://apis.data.go.kr/1360000/FmlandWthrInfoService/getDayStatistics` |
| 오퍼레이션 | `getDayStatistics`(일통계) · `getPureStatistics`(순통계) · `getMmStatistics`(월통계) · 주산지 동네예보·실황·특보 |
| 갱신 주기 | 일별 |
| 참고문서 | 활용가이드 docx + `지역코드_20260105.xlsx` (682행) |

### 요청 파라미터 (일통계)

| 이름 | 필수 | 설명 |
|---|---|---|
| `serviceKey` | 필수 | 인증키 (**소문자 `s`**) |
| `ST_YMD` · `ED_YMD` | 필수 | 시작·종료 연월일 `YYYYMMDD` |
| `AREA_ID` | 필수 | 지역 아이디 (예: `4219000000` 태백) |
| `PA_CROP_SPE_ID` | 필수 | 주산지 작물 특성 아이디 (예: `PA170301` 배추(고랭지)) |
| `dataType` | 선택 | `XML` / `JSON` |

### 응답 항목

```
areaId / areaName                       지역
paCropName / paCropSpeId / paCropSpeName  작물 · 특성(계절)
dayAvgTa / dayMaxTa / dayMinTa           일 평균·최고·최저기온
dayAvgRhm / dayMinRhm                    일 평균·최저습도
dayAvgWs                                 일 평균풍속
daySumRn                                 일 강수량
daySumSs                                 일 일조시간
wrnCd / wrnCount                         특보 코드 · 건수
ymd                                      일자
```

### 실측 결과

- **레코드 확인 연도 13개** — 2014 ~ 2026 (각 연도 6월 한 달, 매일 30~32건)
- **작물 주산지 매핑이 데이터에 내장돼 있다** — 농작물 36종의 주산지가 지역코드표에 정의됨
- 🔴 **작물명이 계절별로 갈리고, 문자열 매칭이 위험하다** — 배추 하나에 특성 ID가 **9개**이고, `"배추"` 검색에 **양배추**가 걸린다

| 계절 | 특성 ID | 주산지 |
|---|---|---|
| 고랭지 | `PA170301` | 강릉 · 태백 · 삼척 |
| 가을 | `PA170401` · `PA240301` | 대전 · 서산 · 해남 · 장흥 |
| 겨울 | `PA170101` · `PA240401` | 해남 · 무안 · 진도 |
| 봄 | `PA170201` · `PA240101` | 부산 · 대구 |

---

## ④ 품목별 수출입실적(GW) — 보조

| 항목 | 값 |
|---|---|
| 데이터 페이지 | https://www.data.go.kr/data/15101609/openapi.do |
| 서비스명(영문) | `Itemtrade` · 오퍼레이션 `getItemtradeList` |
| End Point | `https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList` |
| 형식 | REST · XML |
| 갱신 주기 | **월 1회** — 매월 15일경 전월까지 현행화 |
| 참고문서 | 코드표 xlsx 11시트 (품목코드 17,526행 · 국가 · 성질분류 · 세관 등) |

### 요청 파라미터

| 이름 | 필수 | 설명 |
|---|---|---|
| `serviceKey` | 필수 | 인증키 |
| `strtYymm` · `endYymm` | 필수 | 조회 시작·종료 `YYYYMM` |
| `hsSgn` | 필수 | HS 품목코드 (2·4·6·10자리) |

### 응답 항목

```
hsCode        HS 품목코드
statKor       품목명 (한글)
year          연월 (예: 2025.10)
impWgt        수입 중량
impDlr        수입 금액 (달러)
expWgt        수출 중량
expDlr        수출 금액 (달러)
balPayments   수지
```

### 실측 결과

- **레코드 확인 연도 15개** — 2012 ~ 2026
- **품목 대응이 명시적이다** — 예: `0704902000` = 배추, `0704901000` = 양배추, `0704100000` = 꽃양배추와 브로콜리
- **①과 시간 단위가 다르다**(월별 ↔ 일별). 결합 시 **월로 올려서** 비교하고, 월 값을 일별로 펴지 않는다

---

## ⑤ 전국 공영도매시장 실시간 경매정보 — 탈락

| 항목 | 값 |
|---|---|
| 데이터 페이지 | https://www.data.go.kr/data/15141808/openapi.do |
| End Point | `https://apis.data.go.kr/B552845/katRealTime2/trades2` |

**탈락 사유: 과거 시계열이 보관되지 않는다.** 두 경로를 모두 확인했다.

| 조회 시점 | 농림축산식품 경로 | 공공데이터포털 경로 |
|---|---|---|
| 전일 (2026-07-24) | 있음 (119,729건) | **있음** |
| 2025년 12개월 전부 | 0 | **0** |
| 2024 · 2023 · 2022 · 2021 · 2020 | 파편적 | **전부 0** |

같은 날짜(2025-06-17)를 서울가락 · 서울강서 · 부산엄궁 · 대구북부에 던졌으나 **네 시장 모두 0**이었다.

> 경매 건 단위로 `auctn_seq`(경매고유번호) · `scsbd_dt`(낙찰일시, 초 단위) · `scsbd_prc`(낙찰가) · 면 단위 산지까지 주는 가장 두꺼운 데이터였다.
> 그러나 **갱신 주기가 "실시간"이라는 표시는 과거 시계열의 존재를 보장하지 않는다.**
> 같은 계열의 일별 집계본인 **②(정산정보)**로 대체했다.

---

## 재현 절차

### 1. 인증키 발급

[공공데이터포털](https://www.data.go.kr/)에 가입한 뒤 아래 네 건을 **활용신청**한다. 전부 자동승인이며, 계정당 인증키 하나가 모든 신청 건에 공통 적용된다.

| 데이터 ID | 이름 |
|---|---|
| `15156057` | 한국농수산식품유통공사_일별 도,소매 가격정보 조회 |
| `15141809` | 한국농수산식품유통공사_전국 공영도매시장 정산정보 |
| `15059518` | 기상청_작물별 농업주산지 상세날씨 조회서비스 |
| `15101609` | 관세청_품목별 수출입실적(GW) |

> ⚠️ **승인 직후에는 게이트웨이 반영이 지연되어 `HTTP 403 Forbidden`이 날 수 있다.** 잠시 후 재시도한다.
> `serviceKey`는 **일반 인증키(Decoding)** 를 쓴다. Encoding 키를 코드에서 다시 인코딩하면 이중 인코딩으로 거부된다.

### 2. 키 저장

인증키는 저장소에 커밋하지 않는다. 홈 디렉터리에 **BOM 없이** 저장한다.

```bash
# BOM이 섞이면 요청이 거부된다
printf '%s' "발급받은_인증키" > ~/.datago-key
```

### 3. 호출 예시

```bash
KEY=$(cat ~/.datago-key)

# ① 배추(200/211) 2025년 10월 · 중도매 가격
curl -sG "https://apis.data.go.kr/B552845/perDay/price" \
  --data-urlencode "serviceKey=$KEY" \
  --data-urlencode "returnType=JSON" \
  --data-urlencode "numOfRows=1000" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "cond[exmn_ymd::GTE]=20251001" \
  --data-urlencode "cond[exmn_ymd::LTE]=20251031" \
  --data-urlencode "cond[ctgry_cd::EQ]=200" \
  --data-urlencode "cond[item_cd::EQ]=211"

# ② 서울가락 2026-07-24 정산 실적
curl -sG "https://apis.data.go.kr/B552845/katSale/trades" \
  --data-urlencode "serviceKey=$KEY" \
  --data-urlencode "returnType=JSON" \
  --data-urlencode "cond[whsl_mrkt_cd::EQ]=110001" \
  --data-urlencode "cond[trd_clcln_ymd::EQ]=2026-07-24"

# ③ 태백 × 배추(고랭지) 일별 기상
curl -sG "http://apis.data.go.kr/1360000/FmlandWthrInfoService/getDayStatistics" \
  --data-urlencode "serviceKey=$KEY" \
  --data-urlencode "ST_YMD=20251001" --data-urlencode "ED_YMD=20251031" \
  --data-urlencode "AREA_ID=4219000000" \
  --data-urlencode "PA_CROP_SPE_ID=PA170301"

# ④ HS 0704902000 배추 수출입
curl -sG "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList" \
  --data-urlencode "serviceKey=$KEY" \
  --data-urlencode "strtYymm=202501" --data-urlencode "endYymm=202512" \
  --data-urlencode "hsSgn=0704902000"
```

### 4. 페이지네이션

`numOfRows` 상한이 **1,000**이므로 전량 수집에는 페이지 순회가 필수다. `totalCount`를 읽어 종료 조건으로 쓴다.

```
page = 1
while 누적 < totalCount:
    요청(pageNo=page, numOfRows=1000)
    page += 1
```

> **일 트래픽 10,000회 제약을 넘지 않도록 수집 범위를 나눈다.** 근거: [DATA_CRITERIA.md §2.2](DATA_CRITERIA.md)

---

## 폐기한 데이터

| 데이터 | 폐기 사유 |
|---|---|
| **AdventureWorks** (Microsoft, MIT) | 갱신되지 않는 완결 파일 · 가상 기업이라 공공데이터와 결합 불가 · 완전 연도 2개뿐 |
| **Contoso V2** (SQLBI, MIT) | 갱신되지 않는 완결 파일 · 가상 기업이라 결합 불가 |
| ~~Contoso Retail DW (Microsoft 원본)~~ | 오픈 라이선스 미명시로 2026-07-20 폐기 (위 Contoso V2로 교체했다가 함께 폐기) |

두 데이터는 **라이선스와 품질에는 문제가 없었다.** 목적 적합성·출처 신뢰성·완전성·일관성을 통과했으나 **최신성 · 갱신 주기 · 외부 결합**에서 막혔다. 상세 판정: [DATA_CRITERIA.md §8.2](DATA_CRITERIA.md)

조달 결정으로 질문을 좁힌 뒤에는 **제조원가 정보가 있다는 장점 자체가 무의미해졌다** — 조달 판단에 필요한 것은 제조원가가 아니라 매입 시세다.
