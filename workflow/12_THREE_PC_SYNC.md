# 세 PC 동기화와 계속 푸시

사용자는 이 저장소의 워크프로세스를 계속 커밋·푸시해 세 PC에서 공유하도록 요청했다. 공통 기준 브랜치는 main이다. 진행이 끝났다는 보고에는 실제 원격 커밋과 남은 작업을 포함한다.

## 각 PC 최초 설정

Git과 Python 3.10 이상을 설치하고 각 PC의 원하는 폴더에 같은 저장소를 clone한다. 경로는 PC마다 달라도 된다. 프로젝트/스크립트는 저장소 기준 상대 경로를 사용한다. GitHub 로그인과 push 권한은 PC별로 설정해야 하며 토큰을 저장소에 복사하지 않는다.

    git clone https://github.com/jjwwhhjj1116-prog/muhybstudio.git
    cd muhybstudio
    python automation/sync_workspace.py start

Codex에서 이 clone 폴더를 작업 프로젝트로 열고 AGENTS.md와 현재 진행 상태를 읽는다. 별도 임시 대화 폴더에만 결과를 저장하면 이 저장소로 자동 전송되지 않는다.

## 시작

    python automation/sync_workspace.py check
    python automation/sync_workspace.py start

check는 origin을 확인하고 fetch한 뒤 현재 브랜치·작업 변경·main과의 앞섬/뒤처짐을 보고한다. start는 깨끗한 main에서만 origin/main으로 fast-forward한다. 수정 파일, 다른 브랜치, 로컬 선행 커밋, 분기된 이력이 있으면 상태를 보존하고 종료한다. 임의 stash, reset, force push는 하지 않는다.

작업 브랜치는 현재 main에서 만든다. 여러 PC가 병행하면 각기 다른 작업 브랜치를 쓰며 같은 미공개 회차의 정본을 동시에 확정하지 않는다. 이 도구에는 PC 점유 잠금이나 백그라운드 감시 기능이 없다. 협업 상태와 충돌은 작업자가 확인한다.

## 의미 있는 변경을 완료할 때

1. 최신 사용자 결정과 구현 상태를 policy/stages 및 coordination/STATUS.md에 반영한다. 새 규칙이 구규칙을 참조해 되살아나지 않는지 확인한다.
2. 원고·인물 사실·계정 정보가 공개 diff에 섞이지 않았는지 검사한다.
3. 검증과 해당 변경의 테스트를 실행한다.

       python automation/validate_repository.py
       python -B -m unittest discover -s tests -v
       git diff --check

4. 이번 변경의 경로만 명시해 add하고 staged diff를 읽은 뒤 작업 브랜치에서 commit한다. 이름만 추가하고 실제 파일·계약을 빠뜨리지 않는다.
5. origin/main을 다시 fetch한다. 그 사이 다른 PC가 업데이트했다면 작업 브랜치에 통합하고 영향 검증을 반복한다. 서로 충돌하는 의도는 원문과 사용자 지시로 해결한다.
6. 검증된 작업 브랜치를 main에 통합하고 main을 push한다. 브랜치 보호로 직접 push가 안 되면 작업 브랜치를 push하고 PR을 만든다. main 반영 전에는 세 PC의 공통 기준이 갱신됐다고 말하지 않는다.
7. git ls-remote origin refs/heads/main으로 원격 SHA를 확인하고 로컬 main과 대조한다.

이 절차는 이미 허용된 범용 지침·도구 수정의 일상적 push를 매번 사용자에게 재승인받으라는 뜻이 아니다. 미완료 작업은 별도 작업 브랜치로 공유하고 브랜치명·마지막 검증·남은 작업을 명시한다.

## 다음 PC에서 이어가기

작업 시작 시 start를 실행하고 coordination/STATUS.md를 읽는다. 공유된 workflow 버전과 비공개 작품 매니페스트의 workflow_git_sha를 비교한다. 작품이 구버전을 사용하면 영향받는 제작 단계만 이관·재검수한다. 다른 PC의 미커밋 작업이나 아직 push하지 않은 변경은 Git으로 공유되지 않는다.

## 작품 자료의 공유

이 저장소는 공개다. 대본·설정·인물 기억·이미지·TTS·작품별 상태는 별도 비공개 저장소나 사용자 지정 비공개 저장소에 둔다. 큰 미디어는 비공개 미디어 저장소와 해시 목록으로 관리할 수 있다. 이 문서만으로 비공개 원격이나 미디어 동기화가 설치되지는 않는다. 작품 경로·접속 정보는 각 PC의 .local 또는 비공개 설정에 둔다.

공개 STATUS에는 범용 개발 진행과 다음 작업만 남긴다. 실제 인물명·반전·대사·로컬 절대 경로·비공개 문서 ID는 넣지 않는다.
