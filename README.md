# 무협스튜디오 제작 워크플로우

세 PC에서 공유하는 공통 제작 기준. 워크플로우 버전 **3.1.0**, 작가 지침 **소설형 나레이션·영화체 호흡·포인트 대사**.

다음 신작은 **내부 16부 → 공개 4화, 각 최종 영상 1시간 이상**으로 설계한다. 무협소설의 깊이와 격정적인 발화를 살려 대본을 집필하고, 기존 웹툰 디자인과 현재 선택한 Google Flow / Veo 3.1 - Lite의 실제 입력 모드를 확인해 행동이 이어지는 애니메이션을 만든다.

## 먼저 읽기

- [작업 계약](AGENTS.md) · [시작과 복구](workflow/00_BOOT_SEQUENCE.md)
- [세 PC 동기화](workflow/12_THREE_PC_SYNC.md) · [현재 진행 상태](coordination/STATUS.md)
- [신작 시놉시스·4화 편성](policy/07_SYNOPSIS_AND_RELEASE_PLAN.md) · [개정 범위와 읽는 순서](references/RELEASE_POLICY_CHANGE_2026_10.md)
- [현행 집필 지침](policy/01_WRITING.md) · [작품 기억](policy/02_STORY_MEMORY.md) · [인과·발화 검수](policy/03_REVIEW.md)
- [연속 영상 설계](policy/04_CONTINUOUS_ANIMATION.md) · [Flow 실행 계약](policy/05_FLOW_EXECUTION.md) · [음성·편집·납품](policy/06_DELIVERY.md)

## 변경 원칙

신작 기본 배분은 내부 1~4부를 공개 1화, 5~8부를 2화, 9~12부를 3화, 13~16부를 최종 4화로 묶는다. 각 공개 회차의 실측 최종 타임라인이 3,600초 이상이어야 하며 글자 수나 4부×15분 계산으로 달성을 표시하지 않는다. 기술 청크는 작업에 맞춰 따로 계획하며 고정 21개가 아니다. 완료된 기존 작품의 정본·배분·제작자료는 새 기본값으로 변경하지 않는다.

소설형 낭독·대사 감정 태그·큰따옴표·웹툰 화풍·편집기 3줄 형식은 유지한다. 공개 회차 전체에서 시각화 N장면=이미지 N개=영상 N개를 같은 번호로 납품한다. 내부 샷·공유 키프레임·후보·재시도 작업 수는 별도이며 납품 등식을 해제하지 않는다. V12의 원본은 대조용 기록이다.

집필→근거 있는 검수→기억 확정→음성/샷 시간→Flow 이미지→실제 양 끝 이미지에 맞춘 영상 지시→영상 생성·회수·QA→편집·최종 렌더로 이어진다. 상세 내용은 각 단계에서만 읽는다.

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

이 버전은 지침, 프로젝트 초기화, 동기화 점검, 문서/템플릿 검증과 회귀 테스트를 제공한다. Flow 생성 확장 프로그램·TTS 연결·영상 QA·편집 자동화는 아직 구현 완료가 아니다. 구판 변환기와 검수기는 [legacy/v12](legacy/v12/README.md)에 격리했다. 구명령을 호출하면 새 제작에 부적합함을 알리고 종료한다.

공통 지침 변경은 검증→커밋→main 통합→push→원격 확인까지 수행한다. [변경 기록](CHANGELOG.md)과 [V13 경로 대조](migrations/v13.json)에 이력을 남긴다.
