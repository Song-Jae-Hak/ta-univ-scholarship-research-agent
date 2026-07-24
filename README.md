# 리서치 에이전트 (타대학 장학 제도)

주제를 주면 **조사원 5인이 동시에** 각 기관 사이트를 조사하고, **편집장**이 결과를 종합해 사용자와 상의하며 **보고서 목차·스토리라인**을 확정하는 서브 에이전트 파이프라인.

## 한 번에 실행
```
/scholarship-research 타대학 장학 제도
```
(주제를 비우면 `타대학 장학 제도`가 기본값. 다른 주제도 인자로 넣으면 동일 파이프라인이 돈다.)

## 구성

### 서브 에이전트 (`.claude/agents/`)
| 에이전트 | 담당 | 산출 |
|---|---|---|
| `policy-researcher` | 정책 조사원 — 교육부·한국장학재단 정책·공고 | `research/01_policy.md` |
| `univ-national-researcher` | 타대학 — 거점국립대 교내 장학 | `research/02_univ_national.md` |
| `univ-private-researcher` | 타대학 — 주요 사립대 교내 장학 | `research/03_univ_private.md` |
| `univ-special-researcher` | 타대학 — 특수대학 장학·학비 | `research/04_univ_special.md` |
| `disclosure-researcher` | 공시 조사원 — 대학알리미 장학 지표 | `research/05_disclosure.md` |
| `chief-editor` | 편집장 — 종합·목차·스토리라인(사용자와 확정) | `report/목차_스토리라인.md` |

### 명령 (`.claude/commands/`)
- `scholarship-research.md` — 위 표의 조사원 5인을 **병렬** 실행(각 15분 제한) → 편집장 종합 → **사용자와 상의해 확정** → 저장.

### 브라우징 도구
- [agent-browser](https://github.com/vercel-labs/agent-browser) v0.33.0 단독 바이너리를 `~/.claude/bin/agent-browser.exe`에 설치, User PATH 등록.
- 사용법 스킬: `~/.claude/skills/agent-browser/SKILL.md`.
- 조사원은 **각 기관 공식 사이트에 직접 접속**해 수집한다(1순위 agent-browser, 헤드리스가 막힌 환경/정적 페이지는 WebFetch, WebSearch는 URL 탐색용).

## 원칙
- 조사원은 **순차가 아니라 동시** 실행하고 결과를 각각 md로 남긴다.
- 편집장은 목차·스토리라인을 **혼자 정하지 않고** 사용자와 대화로 확정한다(언급할 점 / 가릴 점 / 이야기 순서).
- 모든 수치·주장에 **출처 URL·확인일**을 병기하고, 확인 안 된 것은 `(미확인)`으로 표기(추정 금지).

## 범위 밖 (다음 단계)
- 확정된 목차·스토리라인을 **한글(HWP/HWPX) 보고서로 내보내는 작업은 별도 세션에서 진행 중**이다. 이 저장소는 그 스킬 코드(`pnu-hwpx-report/`)를 포함하되 작업 파일을 수정하지 않는다.
- 핸드오프: `report/handoff/`에 그 스킬이 바로 빌드할 수 있는 콘텐츠 JSON + 인수인계 README를 둔다.

## 저장소 구성 / 공개 범위
- **포함**: `.claude/`(조사원·편집장 에이전트, `/scholarship-research` 커맨드, agent-browser 스킬 사본), `research/`(조사 결과 5종), `report/`(확정 목차·스토리라인 + 한글 세션 인수인계 패키지), `pnu-hwpx-report/`(HWPX 생성 스킬 코드).
- **제외(.gitignore)**: 부산대 원본 문서 및 모든 `*.hwpx` 산출물, `pnu-hwpx-report/assets/image1.jpg`(기관 로고). → `pnu-hwpx-report` 실행 시 로고 이미지는 별도 제공 필요(해당 SKILL.md의 로고 교체 안내 참조).
- **저장소 밖**: agent-browser 실행 바이너리(`~/.claude/bin/agent-browser.exe`)와 Chrome for Testing는 각 PC에 설치하는 도구라 저장소에 포함하지 않는다.
