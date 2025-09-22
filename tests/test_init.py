import os
import re
import subprocess

import pytest

import environment_helpers
import environment_helpers.install
import environment_helpers.introspect


def test_create_venv(tmp_path):
    env = environment_helpers.create_venv(tmp_path)

    assert env.base == tmp_path
    assert env.interpreter.is_file()
    assert env.interpreter.parent == env.scripts
    assert env.scripts.is_dir()


def test_environment(venv, mocker):
    assert isinstance(venv.introspectable, environment_helpers.introspect.Introspectable)
    assert venv.scheme == environment_helpers.introspect.get_virtual_environment_scheme(venv.base)


def test_environment_run_interpreter(venv, mocker):
    mocker.patch('subprocess.check_output')

    venv.run_interpreter()
    assert subprocess.check_output.call_args.args == ((os.fspath(venv.interpreter),),)

    venv.run_interpreter('arg0')
    assert subprocess.check_output.call_args.args == ((os.fspath(venv.interpreter), 'arg0'),)

    venv.run_interpreter('arg0', 'arg1')
    assert subprocess.check_output.call_args.args == (
        (os.fspath(venv.interpreter), 'arg0', 'arg1'),
    )

    venv.run_interpreter('arg0', 'arg1', 'arg2')
    assert subprocess.check_output.call_args.args == (
        (os.fspath(venv.interpreter), 'arg0', 'arg1', 'arg2'),
    )


def test_environment_run_script(venv, mocker):
    mocker.patch('subprocess.check_output')

    subprocess.check_output.reset_mock()

    script = os.fspath(venv.scripts / 'test0')

    venv.run_script('test0')
    assert subprocess.check_output.call_args.args == ((script,),)

    venv.run_script('test0', 'arg0')
    assert subprocess.check_output.call_args.args == ((script, 'arg0'),)

    venv.run_script('test0', 'arg0', 'arg1')
    assert subprocess.check_output.call_args.args == ((script, 'arg0', 'arg1'),)

    venv.run_script('test0', 'arg0', 'arg1', 'arg2')
    assert subprocess.check_output.call_args.args == ((script, 'arg0', 'arg1', 'arg2'),)


def test_environment_install_wheel(venv, mocker, example_wheel, tmp_path):
    mocker.patch('environment_helpers.install.install_wheel')

    venv.install_wheel(example_wheel)
    venv.install_wheel(example_wheel, 'scheme0')
    environment_helpers.install.install_wheel.mock_calls == [
        mocker.call(example_wheel, venv.interpreter, None),
        mocker.call(example_wheel, venv.interpreter, 'scheme0'),
    ]

    with pytest.raises(ValueError, match=re.escape(f"{os.fspath(tmp_path)} isn't a file")):
        venv.install_wheel(tmp_path)


@pytest.mark.parametrize('from_sdist', [True, False])
def test_environment_install_from_path(venv, mocker, packages_path, from_sdist, example_wheel):
    mocker.patch('environment_helpers.Environment.install_wheel')
    mocker.patch('environment_helpers.build.build_wheel_via_sdist')
    mocker.patch('environment_helpers.build.build_wheel')

    if from_sdist:
        build_func = environment_helpers.build.build_wheel_via_sdist
    else:
        build_func = environment_helpers.build.build_wheel

    path = packages_path / 'example'

    venv.install_from_path(path, from_sdist=from_sdist)
    venv.install_from_path(path, 'scheme0', from_sdist=from_sdist)
    # check build function
    assert len(build_func.mock_calls) == 2
    for call in build_func.mock_calls:
        assert len(call.args) == 2
        assert call.args[0] == path
    # check install function
    environment_helpers.Environment.install_wheel.mock_calls == [
        mocker.call(path),
        mocker.call(path, 'scheme0'),
    ]

    with pytest.raises(
        ValueError, match=re.escape(f"{os.fspath(example_wheel)} isn't a directory")
    ):
        venv.install_from_path(example_wheel)


@pytest.mark.parametrize(
    ('has_pip_local', 'has_pip', 'has_uv', 'expected'),
    [
        (True, True, True, 'uv'),
        (True, True, False, 'pip-local'),
        (True, False, False, 'pip-local'),
        (False, True, True, 'uv'),
        (False, True, False, 'pip'),
        (False, False, True, 'uv'),
    ],
)
def test_environment_install(venv, mocker, has_pip_local, has_pip, has_uv, expected):
    mocker.patch('environment_helpers.Environment.run')
    mocker.patch('shutil.which', side_effect=[has_uv, has_pip])

    if has_pip_local:
        venv.scripts.joinpath('pip').touch(exist_ok=False)

    if expected == 'pip':
        cmd = ['pip', '--python', os.fspath(venv.interpreter), 'install']
    elif expected == 'pip-local':
        cmd = [os.fspath(venv.interpreter), '-m', 'pip', 'install']
    elif expected == 'uv':
        cmd = ['uv', 'pip', 'install', '--python', os.fspath(venv.interpreter)]

    venv.install(['requirement0'])
    environment_helpers.Environment.run.assert_called_once_with(*cmd, 'requirement0')


def test_environment_install_no_default_method(venv, mocker):
    mocker.patch('shutil.which', return_value=False)

    with pytest.raises(ValueError, match=re.escape('No valid install method found.')):
        venv.install(['requirement0'])
