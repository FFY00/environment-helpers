import build
import pytest

import environment_helpers.build


def test_build_sdist(packages_path, tmp_path):
    package = packages_path / 'example'
    sdist = environment_helpers.build.build_sdist(package, tmp_path)

    assert sdist == tmp_path / sdist.name
    assert sdist.name == 'example-1.2.3.tar.gz'


def test_build_wheel(packages_path, tmp_path):
    package = packages_path / 'example'
    wheel = environment_helpers.build.build_wheel(package, tmp_path)

    assert wheel == tmp_path / wheel.name
    assert wheel.name == 'example-1.2.3-py2.py3-none-any.whl'


def test_build_wheel_via_sdist(packages_path, tmp_path):
    package = packages_path / 'example'
    wheel = environment_helpers.build.build_wheel_via_sdist(package, tmp_path)

    assert wheel == tmp_path / wheel.name
    assert wheel.name == 'example-1.2.3-py2.py3-none-any.whl'


def test_build_wheel_via_sdist_fail(packages_path, tmp_path):
    package = packages_path / 'test-cant-build-via-sdist'
    with pytest.raises(build.BuildBackendException):
        environment_helpers.build.build_wheel_via_sdist(package, tmp_path)
