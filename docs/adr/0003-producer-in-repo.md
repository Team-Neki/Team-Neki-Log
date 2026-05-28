# ADR-0003: Producer 책임을 본 레포 범위에 포함

## Status
Accepted (2026-05-29)

## Context and Problem Statement

본 레포 문서들 사이에 **Producer의 책임 위치**에 대한 모순이 누적되어 있었다:

| 문서 | Producer 위치 |
|---|---|
| ADR-0001 References | `scripts/ga_daily_report.py`, `.github/workflows/daily-ga-report.yml`을 "관련 자산"으로 명시 → 본 레포 |
| AGENTS.md §4 | "본 시스템에 데이터를 POST 하는 외부 시스템 ... **이 레포 책임 영역 밖**" → 외부 |
| 실제 코드 | `scripts/`, `.github/workflows/`에 존재 → 본 레포 |

추가로, CI path filter(`aggregation/**`, `pyproject.toml`, `.github/workflows/ci.yml`)에 `scripts/**`가 빠져 있어 Producer 코드 변경이 CI 게이트를 우회한 채 머지되는 footgun이 실제로 발생했다(`scripts/ga_daily_report.py`의 ruff 위반이 무관한 후속 PR에서 처음 드러남).

본 ADR은 모순을 해소하고 **Producer를 본 레포 책임으로 명시적으로 포함**시킨다.

## Decision

Producer(현재: GA4 호출 + Discord 알림, 향후: aggregation Lambda POST 포함)는 **본 레포에서 관리**한다.

- 코드 위치: `scripts/`
- 워크플로 위치: `.github/workflows/daily-ga-report.yml`
- 본 레포의 책임 범위: **생성(producer) + 수신(aggregation Lambda) + 저장(S3)**
- Producer 코드는 본 레포의 ruff/pytest CI 게이트 적용 대상 (ADR-0002와 일관). `.github/workflows/ci.yml`의 path filter에 `scripts/**` 추가
- Commit/PR scope에 `producer` 추가 (AGENTS.md §3 갱신)
- AGENTS.md §4 Producer 항목의 "이 레포 책임 영역 밖" 문구 제거

## Rationale

### 책임이 작다
현재 Producer는 GA4 데이터 호출과 Discord 알림. 코드 규모 작고 변경 빈도 낮음.

### 확장 가능성이 낮다
- 단일 GA property (`524989384`)
- 단일 destination 흐름 (Discord, 향후 aggregation Lambda 1개)
- 다른 Producer 시스템(다른 GA property, 다른 source) 도입 계획 없음

### 분리 비용 > 분리 이득
별 레포로 분리할 경우:
- secrets(GA credentials, Discord webhook) 관리가 2배
- CI/배포 흐름 셋업이 2배
- README/AGENTS 문서가 2배
- aggregation 페이로드 contract 변경 시 producer-consumer를 다른 PR로 나눠야 함 → drift 가능성

### 재분리 비용은 작다
- 코드가 이미 `scripts/`로 격리되어 있음
- 자체 워크플로(`daily-ga-report.yml`)도 분리되어 있음
- 향후 분리 결정 시 디렉토리 + 워크플로 + secrets 이전이면 충분

## Consequences

### Positive
- 문서·코드·워크플로 정합성 회복
- 페이로드 contract 변경을 producer-consumer 한 PR에서 처리 가능 (drift 방지)
- AGENTS.md §4가 ADR-0001과 정합
- Producer 코드도 lint/format CI 게이트로 품질 보장 → 위에서 발생한 "다른 PR에서 처음 드러나는" footgun 차단

### Negative
- 본 레포가 "수신·저장 단일 책임"이라는 단순성은 사라짐
- 향후 Producer가 다수화되면 분리 의사결정이 한 번 더 필요

### Re-evaluation Triggers
- Producer가 **다수**가 될 때 (GA4 외 다른 property, 다른 source)
- Producer 책임이 **단순 호출/리포팅을 넘어 복잡한 변환·라우팅**으로 확장될 때
- Producer와 aggregation Lambda가 **서로 다른 배포 주기**를 요구하게 될 때
- 위 조건 충족 시 → Producer 분리 ADR을 새로 작성

## Relationship to Other ADRs

- **ADR-0001 (Storage Architecture)**: 불변. 저장 아키텍처와 직교한 결정 (책임 범위 vs 저장 구조). Status: Accepted 유지. Status 블록에 본 ADR로의 cross-reference 추가
- **ADR-0002 (Lint / CI Pipeline)**: 본 ADR로 인해 Producer 코드도 lint/format/pytest CI 게이트 적용 대상이 됨. `.github/workflows/ci.yml`의 path filter에 `scripts/**` 추가

## References
- `docs/adr/0001-aggregation-storage-on-s3.md` — 저장 아키텍처
- `docs/adr/0002-lint-and-ci-pipeline.md` — lint/CI 게이트 정책
- 정정 대상 문구: AGENTS.md §1, §3, §4
- 작성 컨텍스트: 2026-05-29 거버넌스 변경 논의
