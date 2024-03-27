import json
import sys


json.dump(
    obj={
        field: getattr(sys.version_info, field)
        for field in ('major', 'minor', 'micro', 'releaselevel', 'serial')
    },
    fp=sys.stdout,
)
