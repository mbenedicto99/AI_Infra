set -euo pipefail
REPO="AI_Infra"; OWNER="mbenedicto99"
REMOTE="git@github.com:${OWNER}/${REPO}.git"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || git init
git checkout -B main
if ! git rev-parse HEAD >/dev/null 2>&1; then
  [ -f README.md ] || echo "# ${REPO}" > README.md
  git add -A && git commit -m "init"
fi
git remote get-url origin >/dev/null 2>&1 || git remote add origin "$REMOTE"
git remote set-url origin "$REMOTE"

gh auth status || gh auth login -s repo -p ssh
gh repo view "${OWNER}/${REPO}" >/dev/null 2>&1 || gh repo create "${OWNER}/${REPO}" --private --confirm
git push -u origin main

