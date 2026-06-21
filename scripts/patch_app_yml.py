"""Patch .build/app.yml with target-specific values after apx build.

Usage:  python3 scripts/patch_app_yml.py <catalog> [mas_endpoint] [genie_space_id]
"""
import pathlib
import sys

APP_YML = pathlib.Path(".build/app.yml")

if len(sys.argv) < 2:
    print("Usage: python3 scripts/patch_app_yml.py <catalog> [mas_endpoint] [genie_space_id]")
    sys.exit(1)

catalog = sys.argv[1]
mas_endpoint = sys.argv[2] if len(sys.argv) > 2 else ""
genie_space_id = sys.argv[3] if len(sys.argv) > 3 else ""

text = APP_YML.read_text()
text = text.replace('value: ""  # CATALOG', f'value: "{catalog}"')
if mas_endpoint:
    text = text.replace('value: ""  # MAS_ENDPOINT', f'value: "{mas_endpoint}"')
if genie_space_id:
    text = text.replace('value: ""  # GENIE_SPACE_ID', f'value: "{genie_space_id}"')
APP_YML.write_text(text)
print(f"Patched CATALOG -> {catalog}")
if mas_endpoint:
    print(f"Patched MAS_ENDPOINT -> {mas_endpoint}")
if genie_space_id:
    print(f"Patched GENIE_SPACE_ID -> {genie_space_id}")
