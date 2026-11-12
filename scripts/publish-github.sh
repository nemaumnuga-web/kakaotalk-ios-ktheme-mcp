#!/usr/bin/env bash
# 사용자의 로컬 GitHub 인증으로 신규 저장소에 업로드합니다.
# 실행: bash scripts/publish-github.sh [public|private] [repo-name]
set -euo pipefail
VISIBILITY="${1:-public}"
REPO_NAME="${2:-kakaotalk-ios-ktheme-mcp}"
if [[ "$VISIBILITY" != "public" && "$VISIBILITY" != "private" ]]; then
  echo "사용법: bash scripts/publish-github.sh [public|private] [repo-name]" >&2
  exit 2
fi
if [[ ! "$REPO_NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "저장소 이름에는 영문/숫자/._-만 사용하세요." >&2
  exit 2
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI(gh)가 필요합니다: https://cli.github.com/" >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub 로그인이 필요합니다. gh auth login 실행 후 재시도하세요." >&2
  exit 1
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -d .git ]]; then
  git init -b main
fi
if [[ -n "$(git remote)" ]]; then
  echo "원격 저장소가 이미 있습니다. 실수로 덮어쓰지 않도록 중단합니다." >&2
  exit 1
fi
git add .
if ! git diff --cached --quiet; then
  git -c user.name="${GIT_AUTHOR_NAME:-KTheme MCP Contributor}" -c user.email="${GIT_AUTHOR_EMAIL:-ktheme-contributor@users.noreply.github.com}" commit -m "feat: add Korean iOS KTheme engineering MCP"
fi
# 새 원격 저장소가 없으면 생성하고 현재 git 상태를 첫 푸시합니다.
gh repo create "$REPO_NAME" "--$VISIBILITY" --source . --remote origin --push
