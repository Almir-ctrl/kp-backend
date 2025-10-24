#!/usr/bin/env python3
import re, json, sys, urllib.request, urllib.error
req_path = r"C:\Users\almir\AiMusicSeparator-Backend\requirements.txt"
keywords = ('spacy','thinc')


def normalize_name(line):
    line = line.strip()
    if not line or line.startswith('#') or line.startswith('--'):
        return None
    if line.startswith('-e ') or line.startswith('git+') or '://' in line:
        return None
    line = line.split(';',1)[0].strip()
    token = line.split()[0]
    name = re.split(r"[<>=!~]", token)[0]
    # split on literal '[' (extras), previous pattern incorrect on Windows
    name = re.split(r"\[", name)[0]
    name = name.strip()
    return name

with open(req_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

candidates = []
for line in lines:
    n = normalize_name(line)
    if n:
        candidates.append(n)

if not candidates:
    print('No candidate packages found in requirements.txt')
    sys.exit(0)

print('Checking', len(candidates), 'packages from requirements.txt...')

for pkg in candidates:
    try:
        url = f'https://pypi.org/pypi/{pkg}/json'
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"{pkg}: error fetching metadata: {e.code}")
        continue
    except Exception as e:
        print(f"{pkg}: error fetching metadata: {e}")
        continue
    requires = data.get('info', {}).get('requires_dist') or []
    matched = [s for s in requires if any(k.lower() in s.lower() for k in keywords)]
    if matched:
        print(f"{pkg} -> declares dependencies matching {keywords}:")
        for m in matched:
            print('   ', m)

print('\nDone')
