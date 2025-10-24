import yaml
p='c:/Users/almir/AiMusicSeparator-Backend/.github/workflows/smoke-test.yml'
with open(p,'r',encoding='utf-8') as f:
    yaml.safe_load(f)
print('YAML parse OK')
