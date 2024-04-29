import pathlib

import environment_helpers
import environment_helpers.install


def test_install_wheel(example_wheel, venv):
    purelib = pathlib.Path(venv.scheme['purelib'])

    assert not purelib.joinpath('example.py').is_file()
    assert not purelib.joinpath('example-1.2.3.dist-info').is_dir()

    environment_helpers.install.install_wheel(example_wheel, venv.interpreter)

    assert purelib.joinpath('example.py').is_file()
    assert purelib.joinpath('example-1.2.3.dist-info').is_dir()
