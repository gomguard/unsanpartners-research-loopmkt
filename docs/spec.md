# 운산파트너스 · 사고수리 검색 진단 리포트 자동화 — 수집·API 명세

목적: 영업 담당이 업체명을 넣으면 5분 안에 7장짜리 A4 PDF가 나오는 내부 도구.
이 문서는 "어떤 API/크롤러로 무엇을 가져와서 리포트 어느 칸에 넣는가"를 고정한다.
Claude Code로 구현할 때 이 문서를 `CLAUDE.md` 옆에 두고 참조한다.

---

## 0. 한눈에

| # | 리포트 칸 | 소스 | 종류 | 비용 | 캐시 단위 |
|---|---|---|---|---|---|
| 1 | 월 검색량 (7쪽 표, 10쪽 퍼널) | 네이버 검색광고 API `keywordstool` | 공식 | 무료 | 지역 / 30일 |
| 2 | 실제 검색 표현 (키워드 후보 보강) | 네이버 자동완성 | 비공식 JSON | 무료 | 지역 / 30일 |
| 3 | 1페이지 주인, 사장님 순위, AI 브리핑 (7·8쪽, 3쪽 KPI) | 네이버 모바일 통합검색 크롤링 | 크롤링 | 프록시 비용 | 지역 / 30일 |
| 4 | 1페이지 주인 분류 (중개/체험단/공업사/정보) | 규칙 + LLM 분류 | Claude API | 미미 | 블로그 ID / 영구 |
| 5 | 플레이스 점검 10항목 (9쪽, 6쪽 타일) | 네이버 플레이스 모바일 페이지 | 크롤링 | 무료 | 업체 / 당일 |
| 6 | 업체 식별 (플레이스 ID, 주소, 전화) | 네이버 지역검색 API + 플레이스 검색 | 공식 + 비공식 | 무료 | 업체 / 영구 |
| 7 | 구글 검색·지도팩·AI 오버뷰 (3쪽, 9쪽 구글 행) | SerpAPI 또는 DataForSEO | 유료 API | 쿼리당 1~15원 | 지역 / 30일 |
| 8 | 구글 비즈니스 프로필 (9쪽) | Google Places API (New) | 공식 | 월 무료 한도 내 | 업체 / 당일 |
| 9 | AI 답변 언급·인용률 (3쪽, 2쪽 KPI) | OpenAI · Perplexity · Gemini · Anthropic 웹검색 API | 공식 | 80콜 수백 원 | 업체 / 주 1회 |
| 10 | 기사 유무 (8쪽 표) | 네이버 뉴스 검색 API | 공식 | 무료 | 업체 / 당일 |
| 11 | 당근 비즈프로필 유무 (9쪽) | 수동 체크박스 | — | — | 업체 |
| 12 | 결론 세 줄·해석 문장 (6·8·9쪽) | Claude API | 공식 | 건당 수십 원 | 리포트 |

핵심 설계: **무거운 것은 지역 단위로 한 번만** (1·2·3·7), 업체 단위는 가벼운 것만 (5·6·8·9·10). 지역 캐시가 있으면 업체 리포트는 10초.

---

## 1. 네이버 검색광고 API — 월 검색량

- 가입: 네이버 검색광고(searchad.naver.com) 광고주 계정 → 도구 > API 사용 관리 → 액세스라이선스·비밀키, 고객 ID(CUSTOMER_ID)
- 엔드포인트: `GET https://api.naver.com/keywordstool`
- 헤더: `X-Timestamp`(ms), `X-API-KEY`, `X-Customer`, `X-Signature` = Base64(HMAC-SHA256(secret, `{timestamp}.GET./keywordstool`))
- 파라미터: `hintKeywords`(최대 5개, 콤마) , `showDetail=1`
- 응답: `keywordList[]` — `relKeyword`, `monthlyPcQcCnt`, `monthlyMobileQcCnt`, `monthlyAvePcClkCnt`, `monthlyAveMobileClkCnt`, `compIdx`(낮음/중간/높음)
  - 10 미만은 문자열 `"< 10"`으로 옴 → 5로 치환해 합산
- 쓰는 법: 지역 조합 키워드(지역×부위×처리 등) 300~500개를 5개씩 묶어 호출. 연관 키워드(relKeyword)도 같이 돌아오므로 후보가 자연히 늘어남
- 리포트 매핑: `keywords[].volume = pc + mobile` → 7쪽 "월 검색" 열, 합계 → 6쪽 타일·10쪽 퍼널 첫 칸

## 2. 네이버 자동완성 — 실제 표현

- `GET https://ac.search.naver.com/nx/ac?q={키워드}&st=100&r_format=json&r_enc=UTF-8&frm=nv` (비공식, 가벼움)
- 응답: `items[0][]` 에 완성어 목록
- 쓰는 법: 지역명 + 핵심어("공업사", "판금", "범퍼") 20~30개로 호출 → 나온 표현을 1번의 hintKeywords로 넘겨 검색량 확인
- 리포트 매핑: 직접 노출 없음. 7쪽 표의 검색어 품질을 올리는 용도

## 3. 네이버 모바일 통합검색 크롤링 — 1페이지 주인·사장님 순위·AI 브리핑

- URL: `https://m.search.naver.com/search.naver?query={검색어}`
- 방식: Playwright 헤드리스, 모바일 UA. 운산네트웍스 크롤러 프록시 풀 사용. 1 IP당 2~3초 간격, 동시 5~10 IP
- 추출 (검색어 1개당):
  - 블로그/VIEW/스마트블록 영역의 글: 블로그 ID, 글 제목, 작성일, 노출 순서
  - 플레이스 영역에 뜬 업체명 순서
  - 광고(파워링크) 업체명 (참고용)
  - **AI 브리핑** 블록: 존재 여부, 본문 텍스트, 출처 링크 목록
- 저장: `serp/{지역}/{검색어}.json` — 수집 시각 포함. 30일 캐시
- 규모: 지역당 300~500 검색어 → 15~30분. 밤에 배치
- 리포트 매핑:
  - 7쪽 "지금 1페이지에 있는 곳": 상위 2개 글의 주인(4번 분류 결과)
  - 7쪽 "사장님 가게": 블로그 ID 또는 플레이스 업체명이 사장님 업체와 일치하는 첫 순위, 없으면 "없음"
  - 8쪽 와플: 검색어별 **1위 글의 주인 유형** 집계 (중개/체험단/B공업사 등 개별 업체/기타/정보성/빈자리). 합계 = 검색어 수
  - 3쪽·2쪽 KPI "AI 답변 인용률(네이버)": 질문형 검색어 20개 중 AI 브리핑 출처에 업체 링크가 있는 수

## 4. 1페이지 주인 분류 — 규칙 + LLM

- 입력: 블로그 ID, 블로그명, 글 제목 샘플 3개
- 규칙 먼저:
  - 블로그명/제목에 업체명 포함 → `공업사`(해당 업체)
  - "체험단·협찬·원고료·제공받아" 포함 → `체험단`
  - 알려진 중개업체 블로그 ID 목록(수동 관리, 카컨류) → `중개`
  - 보험사·손해사정·정보성 → `정보`
- 애매하면 Claude API 분류 (유형 5개 중 하나 + 근거 한 줄). 결과는 `owners.json`에 영구 캐시 (블로그 ID 기준)
- 리포트 매핑: 8쪽 와플 색, 8쪽 표 "유형", 6쪽 결론 2번 문장

## 5. 네이버 플레이스 — 10항목 점검

- URL: `https://m.place.naver.com/place/{placeId}/home`, `/review/visitor`, `/feed`(소식), `/photo`
- 방식: 헤드리스로 열고 페이지에 박힌 `window.__APOLLO_STATE__` JSON 파싱. 필드명이 수시로 바뀌므로 `place_fields.yaml` 매핑 테이블로 관리하고 깨지면 알림
- 추출: 사진 수, 방문자 리뷰 수, 블로그 리뷰 수, 평점(노출 시), 소식 최근 게시일, 최근 리뷰 30개 중 사장님 답글 수(→답글률), 영업시간·전화·주소 등록 여부, 예약/톡톡 버튼 유무
- 리포트 매핑: 9쪽 표 "사장님 가게 현재" 열 전체, 6쪽 "플레이스 리뷰" 타일. 판정 ○△×는 `place_rules.yaml`의 기준값(운산자동차 기준)과 비교해 코드가 결정

## 6. 업체 식별

- 네이버 지역검색 API (공식): `GET https://openapi.naver.com/v1/search/local.json?query={업체명 지역}&display=5` 헤더 `X-Naver-Client-Id`, `X-Naver-Client-Secret` → 업체명, 주소, 전화, 좌표 (플레이스 ID는 안 줌)
- 플레이스 ID: 모바일 플레이스 검색(`https://m.place.naver.com/place/list?query=`)에서 첫 결과의 ID를 추출 (비공식). 영업 담당이 앱에서 후보 중 하나를 고르는 UI 필요 (동명 업체 방지)
- 리포트 매핑: 표지·머리줄 업체명, 7쪽 지역 키 (주소의 구·동으로 지역 조합 생성)

## 7. 구글 — SerpAPI 또는 DataForSEO

- SerpAPI: `GET https://serpapi.com/search.json?engine=google&q={검색어}&hl=ko&gl=kr&location=South+Korea&api_key=` → `organic_results[]`, `local_results[]`(지도팩), `ai_overview`(있을 때), `related_questions[]`
  - 쿼리당 약 1.5센트. 간단하고 문서 좋음
- DataForSEO: `POST https://api.dataforseo.com/v3/serp/google/organic/live/advanced` (location_code 2410 한국, language_code ko) → items에 `ai_overview`, `local_pack`, `organic` 포함. 쿼리당 1원 안팎. 대량이면 이쪽
- 쓰는 법: 지역 검색어 중 검색량 상위 50개 + 질문형 20개만 (전부 돌릴 필요 없음)
- 리포트 매핑: 3쪽 구글 AI 오버뷰 인용 여부, 9쪽 "구글 비즈니스 프로필" 행 보조, 8쪽 경쟁 표 보조

## 8. Google Places API (New) — 구글 프로필

- `POST https://places.googleapis.com/v1/places:searchText` 헤더 `X-Goog-Api-Key`, `X-Goog-FieldMask: places.id,places.displayName,places.rating,places.userRatingCount,places.photos,places.regularOpeningHours,places.websiteUri`
- 추출: 평점, 리뷰 수, 사진 수, 영업시간 등록 여부, 웹사이트 등록 여부 (소유 확인 여부는 API로 안 나옴 → "정보 완성도"로 판정)
- 리포트 매핑: 9쪽 "구글 비즈니스 프로필" 행

## 9. AI 답변 언급·인용률 — 엔진 4개

질문 20개 (`questions.yaml`, 지역명만 치환): "{지역} 범퍼 수리비 얼마?", "{지역} 사고 났을 때 대차 되나요?", "{지역} 공업사 추천", "{지역} 판금도색 잘하는 곳", "자차 수리 자기부담금 {지역}" …

| 엔진 | 호출 | 인용 추출 |
|---|---|---|
| OpenAI | `POST /v1/responses`, `tools:[{"type":"web_search_preview"}]` | `output[].content[].annotations[].url` (url_citation) + 본문 텍스트 |
| Perplexity | `POST https://api.perplexity.ai/chat/completions`, model `sonar` | `citations[]` + 본문 |
| Gemini | `generateContent`, `tools:[{"google_search":{}}]` | `candidates[0].groundingMetadata.groundingChunks[].web.uri` |
| Anthropic | `messages`, `tools:[{"type":"web_search_20250305","name":"web_search"}]` | 응답 블록의 `citations[].url` + 본문 |
| 네이버 AI 브리핑 | 3번 크롤링 결과 재사용 | 출처 링크 목록 |

- 집계: 질문 × 엔진 표에 `언급`(본문에 업체명) / `인용`(출처에 업체 도메인·블로그) 두 값. 리포트엔 "질문 20개 중 n개에서 언급/인용"
- 주의: 소비자용 ChatGPT 앱과 API 결과가 100% 같지는 않음. 리포트 각주에 "API 기준" 명시. 주 1회 갱신, 월말 추이 표
- 리포트 매핑: 3쪽 "측정 — AI 인용률", 2쪽 KPI, 6쪽 타일(선택)

## 10. 네이버 뉴스 검색 API

- `GET https://openapi.naver.com/v1/search/news.json?query={업체명}&display=10` (6번과 같은 키)
- 리포트 매핑: 8쪽 표 "기사" 열 (업체별 건수)

## 11. 당근

- 공개 API 없음, 크롤링 비권장. 앱 입력 폼에 "당근 비즈프로필 있음/없음, 단골 수" 수동 입력 (영업 담당 30초)
- 리포트 매핑: 9쪽 "당근 비즈프로필" 행

## 12. 문장 생성 — Claude API

- 입력: 아래 JSON 전체. 출력: `narrative` 객체만 (결론 3문장, 8쪽 해석 3문장, 9쪽 코멘트 1문장, 10쪽 "언제부터 보이나" 1문단)
- 제약: 숫자는 JSON에 있는 값만 사용, 새 숫자 생성 금지. 생성 후 코드가 본문 속 숫자를 JSON과 대조해 불일치 시 재생성
- 템플릿(7장 HTML)에는 LLM이 손대지 않음

---

## 13. 리포트 JSON 스키마 (리포트 1건 = 파일 1개)

**정본은 `model/schema.py` (pydantic) 와 `data/sample_bucheon.json`.** 아래는 초기 스케치라 몇 군데 다르다:
`keywords[].page1` 는 상위 2개 주인의 리스트, `place_checks[].label`, `funnel.outputs.range_low/high·revenue_low/high`,
`narrative.timeline` 은 3줄 리스트, `plan` 객체(역할·일정·가격·다음 단계) 추가.

```json
{
  "report_id": "2026-10-23-bucheon-oo",
  "collected_at": "2026-10-20T03:00:00+09:00",
  "shop": {"name": "○○공업사", "region": "부천권", "sub_regions": ["중동","상동","송내","원미"],
           "place_id": "1234567890", "address": "...", "phone": "...", "daangn": null},
  "keywords": [
    {"kw": "부천 판금도색", "volume": 390, "intent": "거래",
     "page1_top": {"type": "중개", "name": "중개업체 A"}, "page1_second": {"type": "체험단", "name": null},
     "our_rank": null, "ai_briefing": {"present": true, "cites_us": false}}
  ],
  "summary": {"kw_count": 287, "volume_total": 2600, "tx_kw_count": 118, "tx_volume": 940,
              "our_page1_count": 2, "empty_count": 64,
              "owner_share": {"중개": 48, "체험단": 31, "공업사": 41, "정보": 101, "빈자리": 64, "사장님": 2}},
  "competitors": [{"name": "중개업체 A", "type": "중개", "page1_count": 48, "posts_90d": 120, "reviews": 97, "news": 1, "note": "..."}],
  "place": {"photos": 12, "photos_last_at": "2022-05-01", "visitor_reviews": 31, "blog_reviews": 8, "rating": 4.6,
            "last_news_at": "2025-03-10", "reply_rate": 0.10, "hours_ok": true, "has_kakao": false, "has_booking": false,
            "google": {"rating": null, "reviews": 0, "photos": 0, "hours_ok": false}},
  "place_checks": [{"item": "플레이스 사진 수", "now": "12장, 2022년", "standard": "50장 이상", "verdict": "×"}],
  "ai_citation": {"questions": 20, "engines": ["naver_ai","openai","perplexity","gemini","anthropic"],
                  "mentioned": 0, "cited": 0, "table": []},
  "funnel": {"assumptions": {"share": 0.35, "ctr": 0.12, "inquiry": 0.15, "intake": 0.50, "ticket_krw": 850000},
             "outputs": {"impressions": 910, "clicks": 109, "inquiries": 16, "intakes": 8, "range": [6, 12], "revenue_krw": [5100000, 10200000]}},
  "narrative": {"conclusions": ["...", "...", "..."], "competitor_notes": ["...", "...", "..."],
                "place_comment": "...", "timeline_comment": "..."}
}
```

---

## 14. 실행 흐름

```
[밤 배치]  지역 선택 → 1·2(검색량·표현) → 3(SERP 크롤링) → 4(주인 분류) → 7(구글 상위 70개) → 지역 캐시 저장
[업체 요청] 6(식별) → 5(플레이스) → 8(구글 프로필) → 10(뉴스) → 9(AI 4엔진, 주 1회면 캐시) → 지역 캐시와 결합
           → summary/funnel 계산 → 12(문장) → 템플릿 렌더(Jinja) → Playwright PDF(A4 7장) → 카톡/슬랙 링크
```

- 지역 캐시 있음: 업체 요청부터 PDF까지 1~2분 (AI 4엔진 포함 시 3분)
- 지역 캐시 없음: +15~30분 (앱에서 "지역 수집 중" 상태 표시, 전날 예약 권장)

## 15. 필요한 계정·키 (준비 목록)

1. 네이버 검색광고 광고주 계정 + API 라이선스 (1번)
2. 네이버 개발자센터 앱 — 지역검색·뉴스검색 (6·10번)
3. SerpAPI 또는 DataForSEO 계정 (7번)
4. Google Cloud 프로젝트 + Places API (New) 키 (8번)
5. OpenAI, Perplexity, Google AI Studio(Gemini), Anthropic API 키 (9·12번)
6. 운산네트웍스 크롤러 프록시 풀 접근 (3·5번)
7. 카카오 알림톡 또는 슬랙 웹훅 (완료 알림)

## 16. 저장소 구조 (제안)

```
unsan-report/
  CLAUDE.md                # 이 문서 요약 + 코딩 규칙
  config/ questions.yaml  place_rules.yaml  place_fields.yaml  owners.json  regions.yaml
  collect/ searchad.py  autocomplete.py  naver_serp.py  classify.py  place.py  identify.py
           google_serp.py  google_places.py  ai_citation.py  news.py
  model/   schema.py (pydantic)  funnel.py  summary.py
  narrative/ writer.py (Claude API)  validate.py
  render/  templates/ (7장 Jinja HTML, 캔버스에서 추출)  pdf.py (Playwright)
  app/     main.py (FastAPI)  queue.py  notify.py  static/
  cache/   regions/{region}/  shops/{shop}/
```
