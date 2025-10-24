# PowerShell auto-allow helper

This folder contains a small safe helper to make it easier to run local
PowerShell scripts during development on Windows.

Files:
- `enable-pwsh-allow.ps1`: Sets ExecutionPolicy for CurrentUser to Bypass and
  recursively runs `Unblock-File` on common PowerShell script file types.

Usage (from repo root):

```pwsh
# interactive (recommended)
pwsh -NoProfile -File scripts/enable-pwsh-allow.ps1

# non-interactive (force)
pwsh -NoProfile -File scripts/enable-pwsh-allow.ps1 -Path . -Force
```

Security notes:
- This only changes the policy for the CurrentUser and does not require
  administrator rights.
- Inspect scripts before running. Do not run this on untrusted code.
