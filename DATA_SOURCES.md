# DATA_SOURCES — 데이터 출처 · 라이선스 · 무결성

> 작성 2026-07-20 · 세션 #1
> 원본 데이터는 `.gitignore`로 저장소에서 제외한다. 이 문서와 재현 절차만 커밋한다.
> **모든 제출물·발표자료에는 아래 출처와 라이선스를 표기한다.**

---

## 요약

| 데이터셋 | 라이선스 | 재배포 | 제출 경로 |
|---|---|---|---|
| **AdventureWorks** (OLTP) | **MIT** (Microsoft) | 가능 | ✅ 사용 |
| **Contoso V2** (SQLBI) | **MIT** (SQLBI) | 가능 | ✅ 사용 |
| ~~Contoso Retail DW (Microsoft 원본)~~ | ❌ 오픈 라이선스 없음 | 불가 | ⛔ **폐기함** (아래 §3) |

---

## 1. AdventureWorks (OLTP)

| 항목 | 값 |
|---|---|
| 배포처 | Microsoft `sql-server-samples` (공식) |
| 다운로드 URL | https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks-oltp-install-script.zip |
| 라이선스 | **MIT License** — 저장소 `license.txt` 원문이 MIT 전문 ("Microsoft SQL Server Sample Code, Copyright (c) Microsoft Corporation … MIT License") |
| 라이선스 원문 | https://github.com/microsoft/sql-server-samples/blob/master/license.txt |
| 다운로드일 | 2026-07-20 |
| 로컬 경로 | `adventureworks/` |
| 구성 | CSV 69개 + 스키마 정의 `instawdb.sql` (총 70파일) |
| 총 용량 | 94,873,739 bytes |
| 매니페스트 SHA-256 | `b5bc46a53359cf91243288b563b3d0d73057dfcf8504804f9e2721fc9b2db1e4` |

- 매니페스트 해시 = 각 파일의 `이름 크기 SHA-256` 줄을 파일명 정렬 후 개행 결합한 문자열의 SHA-256.
- **포맷 주의:** CSV가 **탭 구분 · 헤더 없음**. 컬럼명은 `instawdb.sql`의 `CREATE TABLE` 정의에서 매핑해야 한다.
- 스키마(부서) 5개: `HumanResources` · `Person` · `Production` · `Purchasing` · `Sales`

> ⚠️ GitHub API의 라이선스 자동분류는 이 저장소를 `NOASSERTION(Other)`로 표시한다. 파일명이 `license.txt`이고 헤더가 커스텀이라 분류기가 인식하지 못한 것으로, **원문 내용은 MIT가 맞다**(2026-07-20 원문 직접 확인).

---

## 2. Contoso V2 (SQLBI)

| 항목 | 값 |
|---|---|
| 배포처 | SQLBI — `Contoso-Data-Generator-V2-Data` |
| 다운로드 URL | https://github.com/sql-bi/Contoso-Data-Generator-V2-Data/releases/download/ready-to-use-data/csv-1m.7z |
| 릴리스 | 태그 `ready-to-use-data` (발행 2025-09-21) |
| 라이선스 | **MIT License** — `Copyright (c) 2024 SQLBI` |
| 라이선스 원문 | https://github.com/sql-bi/Contoso-Data-Generator-V2-Data/blob/main/LICENSE |
| 생성 도구 | https://github.com/sql-bi/Contoso-Data-Generator-V2 (MIT) |
| 다운로드일 | 2026-07-20 |
| 로컬 경로 | `contoso/` |
| 아카이브 SHA-256 | `76672db38b1e7f72b698792d4b7c7be7aa756dd04b1cda868874b3e139862e1e` (48,894,397 bytes) |

**성격:** SQLBI가 자체 오픈소스 생성기로 만든 **SQLBI의 저작물**이다. Microsoft 원본 Contoso 데이터의 복제본이 아니므로 라이선스가 독립적이고 깨끗하다.

### 파일별 SHA-256

| 파일 | 크기(bytes) | 행수 | SHA-256 |
|---|---:|---:|---|
| `sales.csv` | 198,865,104 | 2,349,091 | `d6d726e64c8093110e88a9e2dbb9c23181388f55b3288764ea49fc812a40d74e` |
| `orderrows.csv` | 89,163,136 | 2,349,091 | `7c666e29605ab31eb2e55098bc4439b9d2871b2f38fb9973f9757bcc87358ffd` |
| `orders.csv` | 47,658,521 | 980,666 | `c8a1ee7f794e650beb46c215068d1afc21e02c95250881c65f167ae929d3f9d9` |
| `customer.csv` | 23,871,850 | 104,990 | `cacb0dd78339ddc9f05523053046fca31e02d8c569b5ffc5683c6493143bdd2a` |
| `currencyexchange.csv` | 2,781,872 | 100,450 | `96ef581e68d0a7dde54d1ba66e136ee8cc7664c218350ec49860bf694e89d420` |
| `date.csv` | 415,223 | 4,018 | `5c5ec069627ad1601e035d2001d362a585d68f7561b1bc371eb450f437b3bbdd` |
| `product.csv` | 371,458 | 2,517 | `442bd9804dee0f41d6d0a5eeac197bf8c3d2ece6a16d3a7e0414e574994010da` |
| `store.csv` | 6,363 | 74 | `8e1efb4dcd03f89487550ae74f8d20367b42c10adfea3ff7102b56b2b37e9af9` |

### 마진 분해 적합성

`sales.csv` 한 테이블에 필요한 요소가 모두 있다 (CSV · 쉼표 구분 · **헤더 있음**):
`OrderKey, LineNumber, OrderDate, DeliveryDate, CustomerKey, StoreKey, ProductKey, Quantity, UnitPrice, NetPrice, UnitCost, CurrencyCode, ExchangeRate`

- **`UnitPrice` vs `NetPrice`** → 할인 효과를 명시적으로 분리 가능
- **`CurrencyCode` + `ExchangeRate`가 행 단위** → FX 효과를 실제로 분해 가능
- `product.csv`의 `CategoryName`·`SubCategoryName`·`Brand` → 믹스 효과 분석 계층

---

## 3. 폐기한 데이터 (사용 금지)

**Microsoft Contoso Retail DW** (구 로컬 `contoso/` 25테이블, `DimAccount`·`FactStrategyPlan` 등)

- 원출처: [Microsoft Download Center ID 18279](https://www.microsoft.com/en-us/download/details.aspx?id=18279) v2.1
- **오픈 라이선스·EULA가 명시되지 않음.** 별도 조건이 없으면 [Microsoft 이용약관](https://www.microsoft.com/en-us/legal/terms-of-use)이 적용되어 개인·비상업 이용을 기본으로 하고 복제·배포를 제한한다.
- 로컬 사본은 원출처·버전·다운로드 흔적이 없어 **출처 증빙 불가**했다.
- → **2026-07-20 폐기하고 §2의 SQLBI판(MIT)으로 교체.** MIT/CC 같은 오픈데이터로 표기해서는 안 된다.

---

## 4. 재현 절차

```bash
# AdventureWorks
curl -L -o aw.zip "https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks-oltp-install-script.zip"
unzip -o aw.zip -d adventureworks/ && rm aw.zip

# Contoso V2 (SQLBI) — py7zr 필요: python -m pip install py7zr
curl -L -o csv-1m.7z "https://github.com/sql-bi/Contoso-Data-Generator-V2-Data/releases/download/ready-to-use-data/csv-1m.7z"
python -c "import py7zr; py7zr.SevenZipFile('csv-1m.7z','r').extractall('contoso')" && rm csv-1m.7z
```

> 다른 규모가 필요하면 동일 릴리스의 `csv-10k`(5.2MB) · `csv-100k`(9.3MB) · `csv-10m`(489MB) · `csv-100m`(4.2GB)로 교체 가능하다.
