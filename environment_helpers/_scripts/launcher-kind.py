import json
import os
import sys


kind = None

if os.name != 'nt':
    kind = 'posix'

if 'amd64' in sys.version.lower():
    kind = 'win-amd64'
if '(arm64)' in sys.version.lower():
    kind = 'win-arm64'
if '(arm)' in sys.version.lower():
    kind = 'win-arm'
if sys.platform == 'win32':
    kind = 'win-ia32'

json.dump(obj=kind, fp=sys.stdout)
