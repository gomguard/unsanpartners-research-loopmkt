"""수집기. 각 모듈은 '한 소스 → JSON 조각' 만 담당한다. 리포트 조립은 report.py.

규칙
- 반환값은 model/schema.py 의 모델(또는 그 dict)로 맞춘다. 템플릿에 직접 닿지 않는다.
- 네트워크 호출은 전부 collect/_cache.py 의 cached() 를 거친다 (지역 30일, 업체 당일/주1회).
- 키는 .env 에서만 읽는다 (collect/_env.py).
- 스텁(NotImplementedError)은 docs/spec.md 의 같은 번호 절을 보고 채운다.
"""
