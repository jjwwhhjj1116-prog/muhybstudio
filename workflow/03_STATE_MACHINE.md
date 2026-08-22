# 03. 상태 머신

## 전이 규칙

- `NOT_STARTED → IN_PROGRESS`: 필수 입력과 정본 읽기 완료
- `IN_PROGRESS → NEEDS_REVIEW`: 산출물 생성과 자동 검수 완료
- `NEEDS_REVIEW → APPROVED`: 차단 오류 0, 사용자 승인 또는 매니페스트의 자동 승인 조건 충족
- `APPROVED → INVALIDATED`: 상위 입력·규칙·캐릭터 레퍼런스 변경
- `IN_PROGRESS|NEEDS_REVIEW → FAILED`: 출력 불완전, 커넥터 실패, 정본 충돌, 검수 실패
- `FAILED|INVALIDATED → IN_PROGRESS`: 복구 입력과 재개 위치 확정

## 단계 상태 필수 필드

`stage`, `status`, `input_versions`, `output_versions`, `started_at`, `updated_at`, `last_completed_unit`, `next_unit`, `validation_summary`, `blocking_errors`, `invalidation_reason`, `approved_by`, `approved_at`

## 자동 연속 진행

사용자가 청크별 승인을 요구하지 않으면 각 청크는 다음을 모두 통과한 뒤 다음 청크로 진행한다.

1. 형식 검수
2. 목표 범위 검수
3. 직전 상태 연속성 검수
4. 체크포인트 저장
5. 산출물 해시 저장
6. 단계 상태의 `last_completed_unit` 갱신

청크 사이의 실제 1~2분 대기는 품질 조건이 아니다. 별도 모델 출력·별도 문서 쓰기 요청·체크포인트 저장으로 경계를 만든다. 시스템이 API 제한 때문에 재시도 대기 시간을 요구할 때만 지수 백오프를 사용한다.
