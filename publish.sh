#!/usr/bin/env bash
# Publish Kairoq to YOUR PERSONAL GitHub and make it live for free — safely, even when
# your company account is the one logged in to the GitHub CLI.
#
#   ./publish.sh --user <personal-username>                    public repo + GitHub Pages
#   ./publish.sh --user <personal-username> --private          private repo + Cloudflare Pages
#   ./publish.sh --user <personal-username> --name my-radar    custom repo name
#   ./publish.sh --user <personal-username> --setup-identity   also make EVERY repo in this
#                                                              project's parent folder use your
#                                                              personal identity from now on
# Safety:
#  • Scans the project for company names, internal links, work emails and secrets — stops if any.
#  • Switches the GitHub CLI to your personal account only for this run, then switches back.
#  • Commits with your personal GitHub "noreply" email set for THIS folder only.
#  • Pushes with your personal account's token, never company credentials from the keychain.
#  • After pushing, verifies on GitHub that every commit uses your personal noreply email.
set -euo pipefail

PERSONAL=""; NAME="ai-qa-radar"; PRIVATE=false; SETUP_IDENTITY=false
# Words that must never appear in your public repo. Add your own: COMPANY_TERMS="acme|acme-internal"
COMPANY_TERMS="${COMPANY_TERMS:-goto\.com|gotoconnect|expertcity|logmein|lastpass|confluence\.ops|enterprise\.slack\.com|jira\.[a-z0-9-]+\.(com|net)}"
SECRET_PATTERNS='gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY'

while [ $# -gt 0 ]; do
  case "$1" in
    --user) PERSONAL="${2:-}"; shift 2 ;;
    --name) NAME="${2:-}"; shift 2 ;;
    --private) PRIVATE=true; shift ;;
    --setup-identity) SETUP_IDENTITY=true; shift ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1 (see --help)"; exit 1 ;;
  esac
done
cd "$(dirname "$0")"
say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '   \033[32m✓\033[0m %s\n' "$*"; }
fail() { printf '\n\033[31m%s\033[0m\n' "$*"; exit 1; }

if [ -z "$PERSONAL" ]; then read -r -p "Your PERSONAL GitHub username (not the company one): " PERSONAL; fi
[[ "$PERSONAL" =~ ^[A-Za-z0-9-]+$ ]] || fail "That doesn't look like a GitHub username: '$PERSONAL'"
[[ "$NAME" =~ ^[A-Za-z0-9._-]+$ ]] || fail "Invalid repo name: '$NAME'"
command -v git >/dev/null || fail "Please install git: https://git-scm.com/downloads"
command -v gh  >/dev/null || fail "Please install the GitHub CLI first:  brew install gh"
gh auth switch --help >/dev/null 2>&1 || fail "Your GitHub CLI is too old for multiple accounts. Run:  brew upgrade gh"
if [ -n "${GH_TOKEN:-}${GITHUB_TOKEN:-}" ]; then
  echo "Note: ignoring GH_TOKEN/GITHUB_TOKEN from your shell for this run (they belong to another account)."
  unset GH_TOKEN GITHUB_TOKEN
fi

# -------------------------------------------------------------- 1. scan
say "1/7  Scanning the project for company content and secrets"
SCAN_EXCLUDE=(--exclude-dir=.git --exclude-dir=.venv --exclude-dir=site --exclude-dir=state --exclude=publish.sh)
if hits="$(grep -rniE "$COMPANY_TERMS" . "${SCAN_EXCLUDE[@]}" || true)" && [ -n "$hits" ]; then
  echo "$hits" | head -20
  fail "Company-related text found (above). Remove it, then run again. Nothing was pushed."
fi
if hits="$(grep -rnoE "$SECRET_PATTERNS" . "${SCAN_EXCLUDE[@]}" || true)" && [ -n "$hits" ]; then
  echo "$hits" | sed -E 's/(.{12}).*/\1…/' | head -20
  fail "Something that looks like a secret/token was found (above). Remove it, then run again."
fi
ok "no company names, internal links, work emails or secrets"

# ----------------------------------------------------------- 2. account
say "2/7  Using your personal GitHub account: $PERSONAL"
PREVIOUS="$(gh api user -q .login 2>/dev/null || true)"
ASKPASS=""
restore() {
  [ -n "$ASKPASS" ] && rm -f "$ASKPASS"
  if [ -n "$PREVIOUS" ] && [ "$PREVIOUS" != "$PERSONAL" ]; then
    if gh auth switch --hostname github.com --user "$PREVIOUS" >/dev/null 2>&1 \
       && [ "$(gh api user -q .login 2>/dev/null)" = "$PREVIOUS" ]; then
      printf '   \033[32m✓\033[0m GitHub CLI is back on your company account (%s)\n' "$PREVIOUS"
    else
      printf '\033[33m   ! Could not switch back automatically. Run:  gh auth switch --user %s\033[0m\n' "$PREVIOUS"
    fi
  fi
}
trap restore EXIT

if ! gh auth status --hostname github.com 2>&1 | grep -qi "account $PERSONAL\b"; then
  cat <<EOF

Your personal account isn't added to the GitHub CLI yet. A browser window will open next.
  ➜ Sign in there as $PERSONAL (your personal account).
    If the browser is logged in to your company account, paste the link into a private/incognito
    window. Your company login in the CLI is kept — this only ADDS a second account.
EOF
  read -r -p "Press Enter to continue… " _
  gh auth login --hostname github.com --web --git-protocol https --skip-ssh-key
fi
gh auth switch --hostname github.com --user "$PERSONAL" >/dev/null 2>&1 \
  || fail "Couldn't switch to '$PERSONAL' — the browser probably signed in with another account.
Nothing was pushed. Run again and sign in as $PERSONAL (use a private/incognito window)."
[ "$(gh api user -q .login)" = "$PERSONAL" ] || fail "Not signed in as $PERSONAL. Nothing was pushed."
ok "signed in as $PERSONAL"

# ---------------------------------------------------------- 3. identity
say "3/7  Setting a private commit identity"
[ -d .git ] || git init -q -b main
GH_ID="$(gh api user -q .id)"
GH_NAME="$(gh api user -q '.name // .login')"
EMAIL="${GH_ID}+${PERSONAL}@users.noreply.github.com"
git config --local user.name  "$GH_NAME"
git config --local user.email "$EMAIL"
git config --local commit.gpgsign false
git config --local credential.helper ""
ok "this folder commits as: $GH_NAME <$EMAIL>"

if $SETUP_IDENTITY; then
  PARENT="$(cd .. && pwd)"
  cat > "$HOME/.gitconfig-personal" <<EOF
# Personal identity for every repo under $PARENT/ (added by ai-qa-radar/publish.sh)
[user]
	name = $GH_NAME
	email = $EMAIL
[commit]
	gpgsign = false
EOF
  if ! git config --global --get-all "includeIf.gitdir:$PARENT/.path" 2>/dev/null | grep -q gitconfig-personal; then
    git config --global --add "includeIf.gitdir:$PARENT/.path" "$HOME/.gitconfig-personal"
  fi
  ok "every repo inside $PARENT/ now uses your personal identity (your work settings elsewhere are unchanged)"
fi

# ------------------------------------------------------------- 4. commit
say "4/7  Committing"
if $PRIVATE; then
  # Private repos get 2,000 free Actions minutes a month: collect every 2 hours instead of 30 min.
  perl -pi -e 's{cron: "\*/30 \* \* \* \*".*}{cron: "0 */2 * * *"   # every 2 hours (private repo: stays inside the free minutes)}' \
    .github/workflows/daily.yml
fi
git add -A
git diff --cached --quiet || git commit -qm "Kairoq"
git branch -M main
if git log --format='%ae' | grep -qv "users.noreply.github.com"; then
  fail "Some earlier commits in this folder use another email. Delete the hidden .git folder here and run again."
fi
ok "all local commits use your noreply email"

# --------------------------------------------------------------- 5. push
VIS="--public"; $PRIVATE && VIS="--private"
say "5/7  Creating github.com/$PERSONAL/$NAME (${VIS#--}) and pushing"
if ! gh repo view "$PERSONAL/$NAME" >/dev/null 2>&1; then
  gh repo create "$PERSONAL/$NAME" "$VIS" \
    --description "Kairoq: hot AI & QA news ranked by urgency and importance, free courses, no repeats" >/dev/null
fi
git remote remove origin >/dev/null 2>&1 || true
git remote add origin "https://github.com/$PERSONAL/$NAME.git"
ASKPASS="$(mktemp)"; chmod 700 "$ASKPASS"
printf '#!/bin/sh\ngh auth token --hostname github.com --user %s\n' "$PERSONAL" > "$ASKPASS"
GIT_ASKPASS="$ASKPASS" GIT_TERMINAL_PROMPT=0 \
  git -c credential.helper= push -u "https://$PERSONAL@github.com/$PERSONAL/$NAME.git" main
git branch --set-upstream-to=origin/main main >/dev/null 2>&1 || true
ok "pushed"

# ------------------------------------------------------------- 6. verify
say "6/7  Verifying on GitHub"
remote_emails="$(gh api "repos/$PERSONAL/$NAME/commits?per_page=100" -q '.[].commit.author.email' | sort -u)"
if echo "$remote_emails" | grep -qv "users.noreply.github.com"; then
  echo "$remote_emails"
  fail "A commit on GitHub uses a non-private email (above). Tell Claude and we'll fix the history."
fi
ok "every commit on GitHub uses your private noreply email"
ok "owner: $(gh api "repos/$PERSONAL/$NAME" -q .owner.login), visibility: $(gh api "repos/$PERSONAL/$NAME" -q .visibility)"

# -------------------------------------------------------------- 7. live
say "7/7  Going live"
if $PRIVATE; then
  gh variable set DEPLOY_TARGET --body cloudflare --repo "$PERSONAL/$NAME" >/dev/null
  cat <<EOF
   Private repos can't use free GitHub Pages, so this deploys to Cloudflare Pages (free):
     1. Create a free account at https://dash.cloudflare.com → Workers & Pages → Create →
        Pages → "Direct Upload" → name it  ai-qa-radar  (upload any file once).
     2. Create an API token: My Profile → API Tokens → Create → "Cloudflare Pages: Edit".
     3. Copy your Account ID (right side of the Workers & Pages overview).
EOF
  read -r -p "   Paste values now? [y/N] " yn
  if [[ "$yn" =~ ^[Yy] ]]; then
    gh secret set CLOUDFLARE_API_TOKEN  --repo "$PERSONAL/$NAME"   # prompts, hidden input
    gh secret set CLOUDFLARE_ACCOUNT_ID --repo "$PERSONAL/$NAME"
    gh workflow run daily.yml --repo "$PERSONAL/$NAME" >/dev/null 2>&1 || true
    URL="https://ai-qa-radar.pages.dev"
  else
    echo "   Later: gh secret set CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID --repo $PERSONAL/$NAME, then run the workflow."
    URL="https://ai-qa-radar.pages.dev (after the Cloudflare step)"
  fi
  echo "   Optional: lock it to your email with Cloudflare Zero Trust → Access."
else
  gh api -X POST "repos/$PERSONAL/$NAME/pages" -f build_type=workflow >/dev/null 2>&1 \
    || gh api -X PUT "repos/$PERSONAL/$NAME/pages" -f build_type=workflow >/dev/null 2>&1 || true
  sleep 3
  gh workflow run daily.yml --repo "$PERSONAL/$NAME" >/dev/null 2>&1 || true
  URL="https://$PERSONAL.github.io/$NAME/"
fi

cat <<EOF

✅ Published to your personal GitHub. Live in about 3 minutes at:

   $URL

   Code:            https://github.com/$PERSONAL/$NAME
   Build progress:  https://github.com/$PERSONAL/$NAME/actions
   (The run started by the push may fail at "deploy" — the run started just now is the one that matters.)

To publish later changes, run this script again with the same options.
EOF
