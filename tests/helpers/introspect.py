#!/bin/python3

import argparse
import json
import os
import pathlib
import sys


root = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, os.fspath(root))


import environment_helpers.introspect  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'action',
        choices=[
            'get_virtual_environment_scheme',
            'get_version',
            'get_scheme',
            'get_system_scheme',
            'get_launcher_kind',
        ],
    )
    parser.add_argument('--interpreter', type=str, default=sys.executable)
    parser.add_argument('--write-to-file', type=pathlib.Path, required=False)
    args = parser.parse_args()

    if args.action == 'get_virtual_environment_scheme':
        data = environment_helpers.introspect.get_virtual_environment_scheme(args.interpreter)
    else:
        instrospectable = environment_helpers.introspect.Introspectable(args.interpreter)
        if args.action == 'get_version':
            data = instrospectable.get_version()
        elif args.action == 'get_scheme':
            data = instrospectable.get_scheme()
        elif args.action == 'get_system_scheme':
            data = instrospectable.get_system_scheme()
        elif args.action == 'get_launcher_kind':
            data = instrospectable.get_launcher_kind()

    if args.write_to_file:
        with args.write_to_file.open('w') as f:
            json.dump(data, f)
    else:
        json.dump(data, sys.stdout)


if __name__ == '__main__':
    main()
