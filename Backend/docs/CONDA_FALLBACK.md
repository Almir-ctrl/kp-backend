# Conda / Mamba fallback for Windows (binary deps)

Why use conda?
- On Windows, many audio and NLP packages (blis, thinc, spacy, av, sentencepiece) have prebuilt binaries on conda-forge. This avoids fragile C extension builds during `pip install`.

Quick start (recommended)
1. Install Mambaforge (https://github.com/conda-forge/miniforge#mambaforge).
2. From the repo root:

```powershell
mamba env create -f environment.yml -n aimusic
mamba activate aimusic
# optionally install a PyTorch variant for your CUDA version
# mamba install -c pytorch pytorch cudatoolkit=12.1 -y
python -m pip install audiocraft
```

Automated helper
- Use `scripts/conda_fallback.ps1` to create the env and install `audiocraft` via pip. The script prefers `mamba` but will use `conda` if `mamba` is not present.

CI notes
- Add a CI job step to install Mambaforge or use the `conda-incubator/setup-miniconda` GitHub Action.
- Create the env with `mamba env create -f environment.yml` and activate before running tests.
- For GPU builds, pin the correct `pytorch` / `pytorch-cuda` package in CI (conda-forge or pytorch channel) matching your CUDA version.

Other notes
- The `environment.yml` in the repo pins Python=3.11 for wide binary support; if you need Python 3.13 adjust carefully and verify conda-forge has builds for that version.
- If you want deterministic installs, consider generating a `conda-lock.yml` (via `conda-lock`) and checking it into the repo.
