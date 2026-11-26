# Getting started: from download to live (Mac, beginner-friendly)

About 20 minutes the first time. You type the grey commands in **Terminal**: copy one block,
paste it with ⌘V, press Enter, and wait until the prompt (`%`) comes back before the next one.

## Step 0 — Two quick checks
- **Revoke any token you pasted anywhere:** https://github.com/settings/tokens (signed in as
  your personal account) → Delete. You don't need tokens for this guide.
- **Company policy:** if unsure whether you may publish a side project publicly, use the
  `--private` option in Step 6.

## Step 1 — Download and unzip
1. In Claude, click the **ai-qa-radar.zip** card → save it (it goes to **Downloads**).
2. Open **Finder → Downloads** and double-click **ai-qa-radar.zip**. A folder **ai-qa-radar** appears.

## Step 2 — Open Terminal
Press **⌘ + Space**, type **Terminal**, press **Enter**.

## Step 3 — Install Homebrew (the Mac app installer for developer tools)
Check if you already have it:
```bash
brew --version
```
If you see `command not found`, install it:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
- It asks for your **Mac login password** (nothing shows while you type — that's normal).
- When it finishes it prints **"Next steps"** with 2–3 commands. **Copy and run those too**
  (they look like `echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile`).
- Then close Terminal and open it again.

> Work laptop without admin rights? Install instead: Git via `xcode-select --install`, and the
> GitHub CLI installer from https://cli.github.com (download the macOS .pkg). Then skip Step 4.

## Step 4 — Install Git and the GitHub CLI
```bash
brew install git gh
git --version
gh --version
```
Both should print a version number. If `gh` is already installed but old: `brew upgrade gh`.

## Step 5 — Put the project in a personal folder
```bash
mkdir -p ~/personal
mv ~/Downloads/ai-qa-radar ~/personal/
cd ~/personal/ai-qa-radar
chmod +x publish.sh
ls
```
You should see files like `README.md`, `publish.sh`, `web`, `digest`, `server`.

## Step 6 — Publish (one command)
Public (free GitHub Pages):
```bash
./publish.sh --user Abhaysinha77 --setup-identity
```
or private (free Cloudflare Pages, extra steps shown on screen):
```bash
./publish.sh --user Abhaysinha77 --private --setup-identity
```

What you'll see:
1. **Scanning…** ✓ no company content or secrets.
2. **Personal account:** first time only, it says a browser will open → press **Enter**.
   - Terminal shows a one-time code like `ABCD-1234` → press **Enter** again.
   - In the browser: sign in as **Abhaysinha77**. If it shows your **company** account, copy
     the address into a **private window** (Safari: ⇧⌘N, Chrome: ⇧⌘N) and sign in there.
   - Paste the code → **Authorize GitHub CLI**. Go back to Terminal.
3. ✓ commit identity (your private GitHub noreply email) · 4. ✓ committed · 5. ✓ pushed ·
   6. ✓ verified on GitHub · 7. going live.
4. Last line: **"GitHub CLI is back on your company account"**.

It ends with your links, e.g. **https://abhaysinha77.github.io/ai-qa-radar/**

## Step 7 — Watch the first build (about 3 minutes)
Open the **Build progress** link it printed (…/actions).
- Wait for a green ✓ on the newest run "Collect & publish".
- A red ✗ on the *first* run (from the push) at "deploy" is normal — the newer run is the one that counts.

## Step 8 — Open it on your phone
- **iPhone (Safari):** open the link → **Share** → **Add to Home Screen**.
- **Android (Chrome):** open the link → **⋮** → **Add to Home screen** / **Install app**.

Check **Saved+ → Sources**: ✓ means the source works; ✗ shows why.

## Later: publish changes
```bash
cd ~/personal/ai-qa-radar
./publish.sh --user Abhaysinha77
```

## If something goes wrong
| You see | Do this |
|---|---|
| `command not found: brew` after installing | Run the "Next steps" commands Homebrew printed, then reopen Terminal |
| `zsh: permission denied: ./publish.sh` | `chmod +x publish.sh` |
| `Your GitHub CLI is too old` | `brew upgrade gh` |
| `Couldn't switch to 'Abhaysinha77'` | Run again; sign in as Abhaysinha77 in a **private** browser window |
| `Company-related text found` | It lists the file and line; remove it and run again |
| Site shows 404 | Wait 2–3 min; check Repo → Settings → Pages → Source = **GitHub Actions** |
| A red ✗ in Actions (not the first run) | Click it → the red step shows the error; paste the message (never a password/token) to Claude |
