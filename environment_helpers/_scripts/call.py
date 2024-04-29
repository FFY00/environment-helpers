import importlib
import pickle
import sys


if len(sys.argv) != 3:
    print(f'usage: {sys.argv[0]} <module> <function>', file=sys.stderr)  # noqa: T201
    exit(1)


module = importlib.import_module(sys.argv[1])
function = getattr(module, sys.argv[2])

args_dict = pickle.load(sys.stdin.buffer)
args = args_dict['args']
kwargs = args_dict['kwargs']

data = function(*args, **kwargs)

pickle.dump(data, sys.stdout.buffer)
