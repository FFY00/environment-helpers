import pathlib

import pytest

import environment_helpers
import environment_helpers.build


@pytest.fixture(scope='session')
def packages_path():
    return pathlib.Path(__file__).parent / 'packages'


@pytest.fixture(scope='session')
def example_wheel(packages_path, tmp_path_factory):
    return environment_helpers.build.build_wheel(
        packages_path / 'example',
        tmp_path_factory.mktemp('example-wheel'),
    )


@pytest.fixture
def venv(tmp_path):
    return environment_helpers.create_venv(tmp_path)
