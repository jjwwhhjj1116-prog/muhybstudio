# Flow 연결 방식 확인 — 2026-10-09

사용자는 브라우저 제어 오류를 줄이기 위해 플러그인/MCP 직접 연결을 문의하고, 로그인 쿠키를 사용하는 내부 API 기반 headless MCP 제안의 사실 확인을 요청했다. 이번 확인은 공식 문서·플러그인 검색·공개 README와 생성/인증 소스의 일부에 대한 조사다. 설치·사용자 쿠키나 프로필 접근·계정 연결·유료 생성·소스 전체 보안 감사는 수행하지 않았다.

## 확인한 경로

| 경로 | 실제 연결 대상과 확인 수준 |
|---|---|
| Google Flow 전용 공식 MCP/플러그인 | 이번 공식 Flow 도움말과 현재 플러그인 검색 결과에서는 프로젝트·캐릭터·생성을 직접 제어하는 연결을 확인하지 못함. 존재하지 않는다는 전역 단정은 아님 |
| 비공식 Flow Browser MCP | 공개 구현은 Playwright/CDP로 로그인된 Chrome을 조작한다고 설명함. MCP 인터페이스이지만 브라우저 의존은 남음 |
| 비공식 Flow 내부 요청 서비스 | 실제 공개 구현이 존재함. 로그인 세션뿐 아니라 추가 인증·브라우저 맥락 등에 의존하며, 우리 계정에서 현재 동작한다고 검증한 것은 아님. HTTP 서비스와 MCP 도구 등록도 별도 단계 |
| Gemini API의 Veo + 제작용 MCP | 공식 API로 영상 요청·operation 상태 확인·결과 다운로드를 구현할 수 있음. Flow 프로젝트·등록 캐릭터·Flow 크레딧을 그대로 제어하는 API와 구별 |

참고 공개 구현: [hitjcl/google-flow-mcp](https://github.com/hitjcl/google-flow-mcp), [shaig-mahmudov/google-flow-mcp](https://github.com/shaig-mahmudov/google-flow-mcp). 두 README의 브라우저 방식 설명을 확인했다. 해당 도구를 설치했다거나 현재 Flow UI에서 정상 동작한다고 검증한 기록은 아니다. 웹사이트 변경·브라우저 상태·업로드 실패가 MCP 설치만으로 해결된다고 말하지 않는다. 설치가 필요하면 실제 코드·권한·전용 프로필·현재 기능을 따로 검토한다.

## 세션 기반 내부 요청 제안의 소스 확인

- [flow2api](https://github.com/TheSmallHanCat/flow2api)는 비공식 이미지·영상 요청 서비스를 공개한다. [FlowClient 소스](https://github.com/TheSmallHanCat/flow2api/blob/main/src/services/flow_client.py)에는 직접 요청과 인증 토큰·브라우저 맥락·403/429/인증 실패 재시도 처리가 있다. 내부 API 요청 구현이 실제 존재한다는 근거이며 쿠키 세 개만으로 완전 무인 운영된다는 근거가 아니다. 추가 인증 처리 구현의 우회·대행 부분은 도입하지 않는다.
- [gflow-cli](https://github.com/ffroliva/gflow-cli/tree/develop)는 CLI·MCP 생성 도구를 제공하지만 [현재 제한](https://github.com/ffroliva/gflow-cli/blob/develop/README.md#architecture--current-limitations)은 실제 Chrome의 `ui_automation`을 기본 경로로 설명하고 순수 HTTP 영상 생성은 차단 상태라고 명시한다. [인증 문서](https://github.com/ffroliva/gflow-cli/blob/develop/docs/AUTHENTICATION.md)는 persistent 브라우저 프로필을 사용하며 만료 시 재로그인이 필요하다. 도구·문서의 기능표에는 개정 시점 차이도 있어 설치 전 고정 리비전과 실제 계정 지원을 확인해야 한다.
- [vynnlee/google-flow-mcp의 영상 소스](https://github.com/vynnlee/google-flow-mcp/blob/main/src/tools/generate-video.js)는 프롬프트 입력·버튼 클릭·DOM 완료 감지와 인증 세션의 다운로드를 사용한다. ‘Browser as an API’라는 표현이나 다운로드의 HTTP 사용만으로 생성이 순수 HTTP라고 해석하지 않는다.

MCP는 작업 도구의 호출 인터페이스다. UI 제어, 세션 기반 내부 요청, 공식 API 중 어느 연결을 뒤에서 사용하는지는 구현에 달려 있다. Playwright/Selenium 방식이 모든 경우에 반드시 실패한다는 주장과 오류가 0%가 된다는 주장은 근거가 없다. [공식 Flow 문제 해결 안내](https://support.google.com/flow/answer/16353333?co=GENIE.Platform%3DDesktop)도 생성·정책·일시적 활동 오류를 구분한다.

계정의 Flow 잔액을 쓰는 비공식 경로라는 구현 설명과 우리 계정의 실제 과금 결과는 구별한다. Ultra 크레딧·특정 모델·4K 업스케일 지원을 포괄적으로 보장하지 않는다. 실제 채택 시 해당 모델의 입력·업스케일 경로·잔액 변화·결과 파일 확인이 필요하다. 쿠키를 대화·공개 저장소·외부 서비스에 전달하지 않는다. 현재는 읽기 전용 조사만 완료했으며 유료 시험을 실행하지 않았다.

## 공식 API와 비용의 구분

[공식 Veo API 문서](https://ai.google.dev/gemini-api/docs/veo)는 `veo-3.1-lite-generate-preview`를 제공한다. 모델별 입력·길이·해상도·참조·연장 지원을 해당 API의 표로 확인한다. Flow 웹 UI의 지원표를 API 기능표로 대체하지 않는다. 두 경로의 기능은 서로 다를 수 있다.

[Gemini API 결제](https://ai.google.dev/gemini-api/docs/billing)는 Cloud Billing을 사용한다. [Google AI 구독의 AI Studio 지원](https://ai.google.dev/gemini-api/docs/google-ai-plans)과 API 종량제는 구별한다. 구독 혜택이나 적용 가능한 크레딧이 있어도 Flow 잔액을 API에서 그대로 사용할 수 있다고 가정하지 않는다. 실제 계정의 연결·과금·프로모션을 확인한 후 비용을 산정한다.

API 경로는 UI 선택자와 클릭 실패를 줄일 수 있지만 모델 생성 실패·콘텐츠 제한·참조 이미지 문제·쿼터와 서비스 오류를 제거하지 않는다. 잘못된 프롬프트를 API로 우회 제출하는 전략으로 사용하지 않는다. 실패의 원인·수정 범위·재시도 예산은 [Flow 실행 지침](../policy/05_FLOW_EXECUTION.md)을 따른다.

현재 연결 방식은 미정이다. Flow 크레딧 활용이 우선이면 자체 로컬 인증을 유지하는 브라우저/확장 프로그램 또는 검토된 세션 연결의 지원 범위를 확인한다. 정상 인증이 차단되면 재로그인·서비스 복구로 처리하며 추가 인증의 우회는 도입하지 않는다. 브라우저 의존 제거가 우선이면 공식 API의 별도 비용과 기능을 확인한다. 모델·입력 이미지·장면 번호·중복 방지·작업 상태·다운로드·실패 사유를 제작 큐에 남기는 MCP 구조는 가능하지만, 명세 작성과 실제 설치·계정 생성 성공은 구별한다.
