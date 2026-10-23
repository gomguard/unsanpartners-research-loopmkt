# unsan-report — 사고수리 검색 진단 리포트 자동화

운산파트너스 데이터 분석실이 공업사 사장님에게 건네는 7장짜리 A4 진단 리포트를
"업체 이름 입력 → 5분 → PDF"로 양산하는 내부 도구.

읽는 순서: 이 파일 → `docs/product-direction.md`(누구에게 파는지, 2026-10-23 결정) → `docs/spec.md`(소스별 API·크롤러 명세, JSON 스키마) → `README.md`(실행법).

방향 요약: 개별 사장 유료 판매 ×. 운산파트너스 제휴망의 수요 확보·제휴점 관리 도구이자, **가맹 본사용 별도 서비스(본사→지점 계층, 지점당 월 과금)**. 운산은 진단·초안·측정, 승인·게시는 본사/지점이 한다.

## 지금 상태

- [x] 리포트 7장 템플릿 (`render/templates/`, Jinja2) — 캔버스 디자인 그대로
- [x] JSON 스키마 (`model/schema.py`, pydantic) + 샘플 데이터 (`data/sample_bucheon.json`)
- [x] 퍼널 계산 (`model/funnel.py`), 플레이스 판정 규칙 (`config/place_rules.yaml`)
- [x] 렌더러: HTML (`render/build.py`) · PDF (`render/pdf.py`, Playwright)
- [x] 키워드 후보 생성 `collect/keywords.py` (부천권 2,160개, `extra=True`면 차종 포함 10,160개)
- [x] 공식 API 수집기 작성됨 (키만 넣으면 동작, 미검증): `searchad` `autocomplete` `identify` `google_serp` `google_places` `news`
- [ ] 크롤러 스텁 (`NotImplementedError`): `naver_serp` `place` `identify.place_id_for` `classify.llm_classify` `classify.anonymize` `ai_citation.ask_*`
- [x] 문장 검증 `narrative/validate.py` (샘플 통과). `narrative/writer.py` 는 Claude API 호출부 작성됨, 미검증
- [x] 앱 뼈대 `app/main.py` (FastAPI 폼 → 백그라운드 큐 → PDF 링크), `report.py` (업체 1건 조립 CLI)
- [ ] `report.py` 의 `competitors` 조립 (owners 집계 → 익명 라벨) — TODO 표시해 둠

## 구현 순서 (권장)

1. `collect/searchad.py` (네이버 검색광고 API) → `collect/place.py` (플레이스) — 이 둘만 붙어도 7·9쪽이 실제 숫자
2. `collect/naver_serp.py` (통합검색 크롤링) + `collect/classify.py` (1페이지 주인 분류) → 7·8쪽 완성
3. `collect/google_serp.py`, `collect/google_places.py`, `collect/news.py`
4. `collect/ai_citation.py` (OpenAI·Perplexity·Gemini·Anthropic 웹검색) → 3쪽 KPI
5. `narrative/writer.py` → 결론 세 줄 등 문장
6. `app/` → 폼 → 큐 → PDF → 카톡/슬랙 알림

## 지켜야 할 규칙

- **숫자는 코드가, 문장은 LLM이.** 템플릿의 숫자는 전부 JSON에서 온다. LLM 출력(`narrative`)에 새 숫자가 들어오면 `narrative/validate.py`가 거부한다.
- **지역 단위 캐시 (30일)**: 검색량·SERP·분류·구글 SERP는 `cache/regions/{region}/`. 업체 단위(플레이스·구글 프로필·뉴스·AI 인용)는 `cache/shops/{shop_id}/`.
- **측정 조건 고정**: 네이버는 모바일·비로그인·위치 미설정. 구글은 location=해당 시, gl=kr, hl=ko. AI 엔진은 질문 20개 × 3회 반복, 주 1회.
- **크롤링 예의**: 운산네트웍스 프록시 풀, IP당 2~3초 간격, 재요청은 캐시로 최소화. 당근은 크롤링하지 않는다(수동 입력).
- **예시 업체·경쟁사는 익명**: 리포트에 실제 경쟁사 상호를 쓰지 않는다. "중개업체 A", "B공업사". 기준치는 "운산자동차(광명) 기준".
- **디자인은 손대지 않는다**: 템플릿의 색(남색 #1C2A76 주인공, 주황 #E2703A/#B4501F 한 점, 연회청 #E9EDF3 표·카드, 바탕 흰색)·서체(Pretendard)·간격은 고정. 주황은 한 장에 최대 3곳, 섹션당 1곳.
- A4 794×1123px 고정 판형. 내용이 넘치면 글자를 줄이지 말고 문장을 줄인다.
- 비밀키는 `.env`에만. 커밋 금지.

## 빠른 실행

```bash
pip install -r requirements.txt && playwright install chromium
python -m render.build data/sample_bucheon.json out/              # HTML 7장 + report.html
python -m render.pdf   data/sample_bucheon.json out/report.pdf    # PDF 7장 (검증됨)
python -m collect.region 부천권                                     # 지역 배치 (검색광고 키 필요)
python -m report "○○공업사" --region 부천권 --daangn no              # 업체 1건 (스텁 단계는 NotImplementedError)
uvicorn app.main:app --reload                                      # 영업용 폼
```

## 리포트 숫자가 어디서 오는지

- 표지 `0.7%` = `summary.our_page1_count / kw_count`. 점 그리드·와플은 `render/build.py` 가 `kw_count`로 격자를 계산
- 2쪽 막대 = `summary.owner_share` (1위 자리 기준, 합계 = kw_count). 정보성 블로그는 2쪽 막대에서만 뺀다
- 5쪽 ○△× = `config/place_rules.yaml` 기준값 vs `place.*` (`model/summary.py`)
- 6쪽 퍼널 = `funnel.assumptions` 를 끝까지 곱해 마지막에 반올림 (`model/funnel.py`). 보수·상단도 같은 방식이라 표와 결과가 항상 맞는다
- 쪽 번호는 1~7 (`render/build.py` PG). 문장 안의 "5쪽" 같은 참조도 이 번호를 쓴다

## 디렉터리

```
config/     questions.yaml · place_rules.yaml · regions.yaml · owners.json · keyword_axes.yaml
collect/    searchad · autocomplete · naver_serp · classify · place · identify · google_serp · google_places · ai_citation · news
model/      schema.py · funnel.py · summary.py
narrative/  writer.py · validate.py
render/     templates/ (01_cover … 07_plan) · build.py · pdf.py · fonts/
app/        main.py · queue.py · notify.py
data/       sample_bucheon.json
cache/      regions/ · shops/
```
