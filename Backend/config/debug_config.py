#!/usr/bin/env python
"""Debug script to check config types"""

from config import Config

c = Config()
print('Checking models configuration types:\n')

for model_name, config in c.MODELS.items():
    print(model_name + ':')
    print('  file_types type: {}'.format(type(config.get('file_types'))))
    print('  available_models type: {}'.format(type(config.get('available_models'))))
    if isinstance(config.get('file_types'), set):
        print('  ⚠️  file_types is a SET (needs conversion)')
    if isinstance(config.get('available_models'), list):
        print('  ✓ available_models is a list')
    print()
