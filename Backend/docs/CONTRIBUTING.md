# Contributing

Thanks for wanting to contribute! For typical workflow please follow GitHub flow:

- Fork the repo
- Create a feature branch: `git checkout -b feat/your-feature`
- Commit changes and open a PR

## CI & Smoke Tests (quick)

We use a CI-safe mode to keep CI fast and reliable. See `docs/ci.md` for full details.

Quick local steps to run the smoke tests (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
$env:CI_SMOKE = 'true'
python app.py &
$env:CI_SMOKE = 'true'
python -m pytest -q -m ci_smoke --junitxml=pytest_ci_smoke.xml
```

If your change requires heavy ML model validation, trigger the manual GitHub Actions workflow `integration-gpu.yml` which runs the full test suite on self-hosted GPU runners.

Thanks — please include tests for new behavior and update the changelog when applicable.
