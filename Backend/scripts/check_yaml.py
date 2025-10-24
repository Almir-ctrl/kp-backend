import yaml
import sys

p = "api/openapi.yaml"
try:
    with open(p) as f:
        yaml.safe_load(f)
    print("openapi.yaml parsed OK")
except Exception as e:
    print("parse error", e)
    sys.exit(1)
