# 단계 10. Flow 자동 생성

## 정의

Flow는 창작 산출물이 아니다. 승인된 시각화에서 Python으로 영어 이미지 프롬프트만 추출한 자동 파생물이다.

## 실행

```bash
python3 automation/build_flow_from_visual.py \
  projects/<slug>/visualization/visualization_full.txt \
  projects/<slug>/flow/flow_full.txt \
  --expected-scenes N
```

## 규칙

- 장면 번호와 모든 라벨 제거
- 장면당 영어 프롬프트 정확히 하나
- CTA·END 완전 제거
- 순서 유지
- 문단 사이 빈 줄 하나
- 시각화가 한 글자라도 바뀌면 부분 수정 없이 전체 재생성

## 게이트

Flow 수 N = 시각화 장면 수 N, 빈 줄 N-1, 장면 번호·라벨·CTA·END 0, 누락·중복·역순 0, 범용 오류 문구 0.
