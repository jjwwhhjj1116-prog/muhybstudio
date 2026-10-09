# 무협스튜디오 제작 워크플로우

세 PC에서 공유하는 공통 제작 기준. 워크플로우 버전 **3.2.0**. 같은 이야기의 기존 **소설판 NOVEL**과 신규 **실험 웹툰판 WEBTOON_EXPERIMENT**를 구별한다.

다음 신작은 **내부 16부×약 20분 → 공개 4화×80분, 공개 회차당 시각화 200장면 이하**로 설계한다. 시놉시스의 선택·상대 반응·기연의 실효와 본문의 감정·문장 연결을 개선한다. 소설판의 낭독 나레이션·포인트 대사와 기존 웹툰 화풍을 유지하고, 실험 웹툰판은 대화·반응 컷·말풍선·성우·모션과 선택된 핵심 생성 영상으로 제작한다.

## 먼저 읽기

- [작업 계약](AGENTS.md) · [시작과 복구](workflow/00_BOOT_SEQUENCE.md)
- [세 PC 동기화](workflow/12_THREE_PC_SYNC.md) · [현재 진행 상태](coordination/STATUS.md)
- [신작 시놉시스·4화 편성](policy/07_SYNOPSIS_AND_RELEASE_PLAN.md) · [두 버전 제작](policy/08_TWO_VERSION_PRODUCTION.md)
- [창작 네 단계별 지침](creative-guides/README.md) · [3.2 개정 범위와 개선 10안 대응](references/CREATIVE_POLICY_CHANGE_3_2.md)
- 집필: [소설판 지침](policy/01_WRITING.md) / [웹툰판 전용 지침](policy/09_WEBTOON_WRITING.md) · [작품 기억](policy/02_STORY_MEMORY.md) · [인과·발화 검수](policy/03_REVIEW.md)
- [연속 영상 설계](policy/04_CONTINUOUS_ANIMATION.md) · [Flow 실행 계약](policy/05_FLOW_EXECUTION.md) · [음성·편집·납품](policy/06_DELIVERY.md)
- [웹툰판 Remotion 제작안](references/WEBTOON_REMOTION_PRODUCTION_PLAN_2026_10.md) — 내장 이미지·말풍선·성우·모션의 검토안이며 렌더 구현 완료가 아니다.
- [웹툰판 집필 사용본](creative-guides/02B_WEBTOON_SCRIPT_WRITING.md) · [비낭독 전달 메모 빈 서식](templates/webtoon_script_notes.template.md). 웹툰 전용 집필 기준은 활성 지침이며 제작 엔진 선택과 구분한다. VERSION.json의 버전별 진입 경로는 작업자가 읽는 메타데이터이며 자동 집필·렌더 선택기 구현을 뜻하지 않는다.

## 변경 원칙

신작 기본 배분은 내부 1~4부를 공개 1화, 5~8부를 2화, 9~12부를 3화, 13~16부를 최종 4화로 묶는다. 각 공개 회차의 목표·최종 실측 기준은 4,800초이며 글자 수나 계획 계산으로 달성을 표시하지 않는다. 기술 청크는 작업에 맞춰 따로 계획하며 고정 21개가 아니다. 완료된 기존 작품의 정본·배분·제작자료는 새 기본값으로 변경하지 않는다.

소설판은 소설형 낭독·대사 감정 태그·큰따옴표·웹툰 화풍·편집기 3줄 형식과 시각화 N=이미지 N=영상 N의 납품 계약을 유지한다. 실험 웹툰판은 시각화 N=기본 이미지 N=모션 계획 N이며 선택 Flow 영상 K≤N은 원래 장면 번호를 유지한다. 두 버전 모두 N≤200이고 원고·해시·매핑·음성·편집을 분리한다. 내부 샷·크롭·새 표정 이미지·재시도 수는 실제 필요에 맞춰 따로 기록한다. V12의 원본은 대조용 기록이다.

집필→근거 있는 검수→기억 확정→캐릭터 자료→장면 분할→시각화→이미지·음성→버전별 영상/모션 편집→최종 QA로 이어진다. 80분과 200장면은 평균 24초 이상의 표시 길이를 뜻한다. 짧은 생성 클립 하나를 그 장면의 전체 시간으로 간주하지 않는다. 상세 내용은 각 단계에서만 읽는다.

## 설치와 점검

Git과 Python 3.10 이상을 사용한다. 기본 도구는 Python 표준 라이브러리만 필요하다.

    git clone https://github.com/jjwwhhjj1116-prog/muhybstudio.git
    cd muhybstudio
    python automation/sync_workspace.py start
    python automation/validate_repository.py
    python -B -m unittest discover -s tests -v

start는 깨끗한 main에서 fetch 후 fast-forward만 수행한다. 사용자 수정 파일을 정리하거나 임의 커밋하지 않는다. 상태만 보려면 check를 사용한다.

    python automation/sync_workspace.py check

## 작품은 별도 비공개 폴더

    python automation/init_project.py my-series --title "작품명" --project-root ../private-projects

위 명령은 비공개 **로컬 폴더**를 만들며 비공개 원격 저장소를 생성하거나 세 PC에 작품을 전송하지 않는다. 작품 공유는 별도 비공개 저장소/저장소 연결을 정한 뒤 구성한다. 공개 저장소에는 워크플로우·일반 도구·비식별 진행 상태만 둔다.

## 확인 수준

이 버전은 지침, 프로젝트 초기화, 동기화 점검, 문서/템플릿 검증과 회귀 테스트를 제공한다. 검증기는 선언된 버전·배분·시간·장면 수를 검사하며 실제 재미·생성 성공·말풍선/모션 렌더를 판정하지 않는다. Flow 확장 프로그램/MCP·TTS 연결·영상 QA·편집 자동화는 아직 구현 완료가 아니다. [Flow 연결 조사](references/FLOW_INTEGRATION_OPTIONS_2026_10.md)는 조사 기록이며 설치 완료가 아니다. 구판 변환기와 검수기는 [legacy/v12](legacy/v12/README.md)에 격리했다.

공통 지침 변경은 검증→커밋→main 통합→push→원격 확인까지 수행한다. [변경 기록](CHANGELOG.md)과 [V13 경로 대조](migrations/v13.json)에 이력을 남긴다.
