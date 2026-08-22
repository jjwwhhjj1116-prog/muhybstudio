# 단계 08. 시각화 프롬프트 청크 생성

## 출력 형식

```text
[장면 N]
[한국어 번역] 대본의 해당 문장 또는 대사 원문
[영어 이미지 프롬프트] 완결된 영어 프롬프트
```

`[한국어 원문]`, `Intro`, `Body`, 검수 메모 같은 추가 라벨을 만들지 않는다.

같은 장소·시간·시점·행동 흐름은 기본 **2~3문장**을 한 장면으로 묶는다. 직접 대사는 절대 누락하지 않으며, 같은 샷에서 성립할 때만 인접 행동·반응 나레이션과 함께 묶는다.

## CTA·END

- `[CTA]`: Hook 마지막 시각화 장면 직후 단독 한 줄.
- `[END]`: End 첫 시각화 장면 직전 단독 한 줄.
- 둘 다 장면 번호를 부여하지 않고 이미지 수에 포함하지 않는다.

## 인물 규칙

- 주요 인물만 캐릭터시트와 동일한 한글 고정명을 쓴다.
- 주요 인물도 이름만 쓰지 않고 현재 부상·젖음·붕대·마비·무기 위치·행동을 덧붙인다.
- 보조 인물은 이름·역할명만 쓰지 않고 영어 외형 앵커 전체를 직접 삽입한다.
- 얼굴 고정 주요 인물은 원칙적으로 장면당 3명 이하다.

## 영어 프롬프트 고정 머리말

`Korean dark-fantasy martial-arts action manhwa webtoon style, hand-drawn illustration, ink line art with digital coloring, NOT photorealistic, NOT 3D render, NOT photograph, Masterpiece, ultra-detailed, premium anime key-visual quality, cel-shaded digital painting with ink brush texture, rich ink-wash rendering with dramatic lighting, floating particles and embers, flowing hair and fabric with natural physics,`

뒤에는 샷·카메라, 인물/앵커, 중심 행동, 공간·시간, 광원·색, 부상·무기·소품 연속성, 금지를 쓴다. 화면의 읽을 수 있는 글자·로고·워터마크·현대 물품·일본식 문자·실사·3D·치비를 금지한다.

## 청크 규칙

- 전체 21청크, 한 청크 최대 25장면 기본.
- 장면 번호는 전편 연속.
- 청크 후 마지막 문장 ID, 마지막 장면 번호, 누적 수, 다음 문장 ID, CTA·END 상태, 인물 상태, 출력 해시를 저장한다.
- 사용자 승인 질문 없이 검수 통과 후 다음 청크로 이어갈 수 있다.
- 첫 청크를 Docs에 쓰기 전에 21청크 전체 문자량과 문서 누적 예상치를 계산해 용량 게이트를 통과한다.
- 문서 한계에 도달한 뒤 기존 1~N장면의 반복 문구를 무단 축약해 공간을 만들지 않는다.

## 게이트

해당 범위 문장·대사 매핑 100%, 누락·중복·역순 0, 주요 인물명 오류 0, 보조 인물 단독 이름 0, 연속성 오류 0, 범용 오류 문구 0.
