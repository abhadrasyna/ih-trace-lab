# Pushing to this repo when your default GitHub account differs

## Symptom

```
❯ git push
remote: Permission to abhadrasyna/ih-trace-lab.git denied to <other-account>.
fatal: unable to access 'https://github.com/abhadrasyna/ih-trace-lab.git/': The requested URL returned error: 403
```

## Root cause

Git's HTTPS auth on macOS goes through `credential.helper=osxkeychain`, which is set in the **system-wide** gitconfig (`/Library/Developer/CommandLineTools/usr/share/git-core/gitconfig`), not
per-repo. macOS Keychain stores exactly one entry per host (`github.com`), so whichever GitHub account was last authenticated (e.g. via `gh auth login`) is used for **every** HTTPS git operation to
any `github.com` repo on the machine, regardless of that repo's actual owner. Local `user.name`/`user.email` only affect commit metadata, not push authentication, so they don't help here. Diagnose it
with `git config --list --show-origin | grep -i credential` and `security find-internet-password -s github.com`.

Also note: GitHub no longer accepts account passwords over HTTPS (2FA or not) — the "password" prompt must be a Personal Access Token or a `gh`-issued token, never your literal account password.

## Fix — scope this repo to a different GitHub account via `gh`

This overrides the credential helper for **this repo only**; other repos on the machine keep using the existing host-level Keychain identity untouched.

```bash
# 1. In this repo, reset the inherited helper chain and point it at gh's own credential helper
git config --local credential.helper ""
git config --local credential.helper "!gh auth git-credential"
git config --local credential.useHttpPath true   # keeps lookups scoped by full URL, not just host

# 2. Add the second GitHub account to gh (device-code flow, browser-based — no manual token copying)
gh auth login --hostname github.com --web
# choose "HTTPS" as the Git protocol when prompted

# 3. gh only has one *active* account per host at a time — switch to the one that owns this repo
gh auth switch --hostname github.com --user <repo-owner-username>

# 4. Push as usual
git push
```

To confirm which accounts `gh` currently knows about and which is active:

```bash
gh auth status
cat ~/.config/gh/hosts.yml
```

When switching back to work on a repo owned by the other account, just re-run `gh auth switch --hostname github.com --user <other-username>` — this only flips the shared "active account" pointer; it
does not touch this repo's local `credential.helper` override, so each repo keeps authenticating correctly as long as the right account is active in `gh` at push time.
