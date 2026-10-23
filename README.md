# unsan-report

공업사 사장님에게 건네는 「사고수리 검색 진단 리포트」(A4 7장)를 업체명 입력만으로 만드는 운산파트너스 내부 도구.

## 설치

Windows PowerShell (한 줄씩):

```powershell
python -m venv .venv
.venv\Scripts\activate          # "스크립트 실행이 비활성화" 오류면: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
playwright install chromium     # PDF용
copy .env.example .env          # 키 입력
```

macOS / Linux:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && playwright install chromium
cp .env.example .env
```

## 샘플 리포트 만들어 보기

```bash
python -m render.build data/sample_bucheon.json out/
# out/01_cover.html … out/07_plan.html, out/report.html(7장 연결)
python -m render.pdf data/sample_bucheon.json out/report.pdf
```

## 실제 업체 리포트 (수집기가 붙은 뒤)

```bash
python -m collect.region 부천권            # 밤 배치: 검색량·SERP·분류·구글 → cache/regions/부천권/
python -m report "○○공업사" --region 부천권  # 업체 식별 → 플레이스·구글·뉴스·AI → JSON → PDF
```

## 문서

- `CLAUDE.md` — 상태, 순서, 규칙
- `docs/spec.md` — 소스 12개의 API·크롤러 명세, JSON 스키마, 준비 목록
