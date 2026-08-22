# 07. GitHub 저장·커밋·푸시 절차

## 저장소 정책

- 워크플로우 규칙과 자동화는 범용 저장소에 둔다.
- 작품 원문·미공개 대본·이미지는 비공개 저장소 또는 별도 비공개 경로에 둔다.
- `main`은 승인 정본이다. 변경은 `codex/<작업명>` 또는 `workflow/<작업명>` 브랜치에서 수행한다.
- 강제 푸시와 히스토리 재작성은 금지한다.

## 작업 전

```bash
git status --short --branch
git remote -v
git fetch --prune origin
git switch -c workflow/<name> origin/main
```

혼합 작업트리에서는 이번 작업 파일만 스테이징한다. `git add .`, `git add -A`, `git add --all`을 쓰지 않는다.

## 검증·커밋

```bash
python3 automation/validate_repository.py
python3 -m py_compile automation/*.py
git diff --check
git status --short
git add -- <명시적 파일 목록>
git diff --cached --stat
git diff --cached
git commit -m "docs: codify staged wuxia film workflow"
```

## 푸시

```bash
git push -u origin workflow/<name>
```

푸시 전에 원격 저장소, 소유자, 브랜치, 공개 범위를 확인한다. 비공개 작품 내용이 공개 저장소에 섞이면 푸시하지 않는다.

## PR

- 기본은 Draft PR.
- 변경 이유, 영향 단계, 무효화 범위, 검증 결과를 본문에 적는다.
- 규칙 변경 PR이 병합되면 `VERSION.json`과 `CHANGELOG.md`를 갱신한다.

## 새 작품 시작

태그된 워크플로우 버전을 매니페스트에 잠근다. 작업 중 규칙 버전을 바꾸면 영향을 감사하고 사용자가 확정한 뒤에만 마이그레이션한다.
