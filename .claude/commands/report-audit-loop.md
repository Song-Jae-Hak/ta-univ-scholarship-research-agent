---
description: 확정 보고서를 감사→수정 루프로 자가 검토·개선하고 회차마다 파일·GitHub에 반영, 최종본은 HWPX로 출력
argument-hint: "(인자 없음 — report/목차_스토리라인.md 확정본을 사용)"
---

# 보고서 감사→수정 루프

전제: `report/목차_스토리라인.md`(확정본)이 있어야 한다. 당신은 **오케스트레이터**다.

## 0. v1 준비
- `report/보고서_v1.md`가 없으면 `chief-editor`(MODE: draft_v1)로 작성한다. → **commit + push**.

## 1. 감사→수정 루프 (멈춤 조건: 세 번 왕복 후 종료)
`N=1`부터 반복한다. (1 왕복 = 감사 1회 + 지적>0이면 수정 1회)
1. `report-auditor`로 `report/보고서_vN.md` 평가 → `report/검토의견_vN.md`(총 지적 건수 포함).
2. **멈춤 판정**:
   - 지적 **0건** → 종료(최종 = vN).
   - 감사 **3회** 수행 완료 → 3회차 지적이 있으면 마지막 1회만 수정해 v(N+1)을 최종으로 만들고 종료; 없으면 vN 최종.
   - *(대안 조건 — 미사용: 지적 0건 종료 / 지적이 안 줄면 종료)*
3. 계속이면 `chief-editor`(MODE: revise)로 `report/보고서_v(N+1).md` 작성(개정 이력 포함).
4. `검토의견_vN` + `보고서_v(N+1)`을 **commit + push**. `N += 1`.

## 2. 버전 비교
`report/보고서_v1~vN`을 나란히 비교해 회차별 변경점을 `report/버전비교.md`로 정리한다. → commit + push.

## 3. 최종 HWPX 출력 (스킬 활용)
최종 보고서를 `pnu-hwpx-report` 콘텐츠 JSON으로 변환 → `python pnu-hwpx-report\scripts\build.py -c <json> -o report\<최종>.hwpx` 로 출력(`PASS: true` 확인). **스킬 파일은 실행만 하고 수정하지 않는다.** 로고 이미지가 없으면(공개 저장소에서 제외됨) 그대로 빌드하거나 대체 로고를 안내한다.

## 정의 파일
평가 기준·멈춤 조건은 `.claude/agents/report-auditor.md`(정의 파일)에 기록되어 있다. 부서 지정 반려 사유 = 결재선 관점·눈높이 / 법령·규정·지침 근거 누락.
