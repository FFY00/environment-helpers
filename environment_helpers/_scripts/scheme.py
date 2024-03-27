import json
import sys
import sysconfig


if len(sys.argv) >= 2:
    paths = sysconfig.get_paths(sys.argv[1])
else:
    paths = sysconfig.get_paths()


json.dump(obj=paths, fp=sys.stdout)
