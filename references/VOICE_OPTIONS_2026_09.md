# 음성 선택과 비용 비교 — 2026-09-06 확인

이 문서는 제작 단계의 기능 확인 기록이다. 작가의 문체 지침이나 특정 엔진 채택 결정이 아니다. 서비스·계정에서 실제 생성 전에 기능과 적용 요금을 다시 확인한다.

## Flow

Omni Flash에서 Voices 프리셋을 선택하고, 기본 음성과 연기 설명으로 custom voice를 저장할 수 있다. 공식 도움말은 음성 참조를 Ingredients 생성에만 허용한다. 시작·종료 Frames 생성과 음성 참조를 동시에 지정하면 된다고 가정하지 않는다. 이 설명은 외부 TTS voice ID의 가져오기나 복제 지원을 뜻하지 않는다. [공식 도움말](https://support.google.com/flow/answer/16353334?hl=en)

## 별도 대사 생성

Gemini TTS는 한국어와 음성 선택, 연기 지시를 지원한다. 다중 화자는 한 요청에 최대 두 명이다. AI Studio에서 음성을 비교하고, 자동화에서는 확정 대본을 Gemini API로 전달해 오디오를 받아 편집할 수 있다. 오디오 생성만으로 영상의 입모양이 맞춰지는 것은 아니다. [공식 TTS 문서](https://ai.google.dev/gemini-api/docs/speech-generation)

Gemini 3.1 Flash TTS Preview의 표준 유료 가격은 입력 텍스트 100만 토큰당 1달러, 출력 오디오 100만 토큰당 20달러다. 초당 25 오디오 토큰 기준 출력 1분은 약 0.03달러, 5분은 0.15달러다. 입력·재시도·세금은 별도이며 실제 사용량으로 정산한다. 무료 구간도 있지만 무제한 생산을 보장하지 않는다. [공식 가격](https://ai.google.dev/gemini-api/docs/pricing)

ElevenAPI의 게시 요금은 v2/v3 1,000자당 0.10달러, Flash/Turbo 0.05달러다. 기존 Creative 구독의 크레딧, 구독 기본료, 개별 계약과 실제 청구를 이 표로 단정하지 않는다. [공식 API 가격](https://elevenlabs.io/pricing/api)

## 제작에 적용

- 배역별 엔진·보이스는 샘플을 듣고 선택한다. 저렴한 모델을 쓰기 위해 감정 대사를 자동 삭제하지 않는다.
- 지문과 낭독 원문을 구별한다. 지문은 영상 제작의 근거이며 성우에게 읽히지 않는다. 화면과 겹치는 나레이션도 작품상 필요하면 유지한다.
- 대본 확정 전에는 짧은 핵심 구간으로 비교한다. 음성 확정 뒤에는 정상 발화를 보존하고 실패·수정된 구간만 재생성한다.
- 요청 캐시 키에는 엔진·모델·보이스·낭독 원문·발음 교정·연기·속도 설정을 포함한다. 문장이 같아도 연기가 바뀌면 기존 음성을 무조건 재사용하지 않는다.
- 한 문장씩 기계적으로 끊어 호흡을 망치지 않는다. 실제 API 요청은 짧은 연속 발화 묶음으로 구성할 수 있고, 개별 원문 ID와 정렬 관계는 보존한다.
- Frames 액션 연결과 별도 음성 합성, Ingredients 대사 장면은 각각 검증한다. 최종 대사는 원문과 대조하며 립싱크·음질·한국어 연기는 실제로 듣고 본다.

이번 기록은 문서 조사와 제작 계약 반영까지다. 유료 음성 생성, Flow 계정별 기능 시험, 어댑터 구현을 완료했다는 뜻은 아니다.

## Creative 구독과 모델 선택 보충

Creative 구독의 크레딧 예산에서는 v3 1자당 1크레딧, Flash/Turbo v2.5의 경로별 할인 0.5~1크레딧을 구별한다. 계정 적용량과 보이스 배율을 확인하고 API 달러 단가를 구독의 실제 청구로 치환하지 않는다. [v3 크레딧](https://help.elevenlabs.io/hc/en-us/articles/35869113958801-How-much-does-it-cost-to-generate-using-Eleven-v3-Alpha), [Creative 가격](https://elevenlabs.io/pricing)

감정 표현 비교는 v3를 우선 후보로 둘 수 있다. Multilingual v2와 Flash/Turbo v2.5가 같은 모델인 것처럼 쓰지 않는다. v3의 감정 태그를 다른 모델에도 그대로 전달하지 않는다. [모델별 기능](https://elevenlabs.io/docs/eleven-creative/playground/text-to-speech)
