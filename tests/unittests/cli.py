# -*- coding: utf-8 -*-
import os

import click
from click.testing import CliRunner

from pytest import fixture, mark

from storyscript.app import App
from storyscript.cli import Cli
from storyscript.version import version


@fixture
def runner():
    return CliRunner()


@fixture
def echo(patch):
    patch.object(click, 'echo')


@fixture
def app(patch):
    patch.object(App, 'compile')
    return App


def test_cli(runner, echo):
    runner.invoke(Cli.main, [])
    # NOTE(vesuvium): I didn't find how to get the context in testing
    assert click.echo.call_count == 1


def test_cli_version_flag(runner, echo):
    """
    Ensures --version outputs the version
    """
    runner.invoke(Cli.main, ['--version'])
    message = 'StoryScript {} - http://storyscript.org'.format(version)
    click.echo.assert_called_with(message)


def test_cli_compile(patch, runner, echo, app):
    """
    Ensures the compile command compiles a story
    """
    patch.object(click, 'style')
    runner.invoke(Cli.compile, ['/path'])
    App.compile.assert_called_with('/path', ebnf_file=None, debug=False)
    click.style.assert_called_with('Script syntax passed!', fg='green')
    click.echo.assert_called_with(click.style())


def test_cli_compile_default_path(patch, runner, app):
    """
    Ensures the compile command default path is the current working directory.
    """
    runner.invoke(Cli.compile, [])
    App.compile.assert_called_with(os.getcwd(), ebnf_file=None, debug=False)


def test_cli_compile_output_file(runner, app, tmpdir):
    """
    Ensures the compile command outputs to an output file when
    available. If no file were to be available (e.g. no file was
    written), this test would throw an error
    """
    tmp_file = tmpdir.join('output_file')
    runner.invoke(Cli.compile, ['-j', '/path', str(tmp_file)])
    tmp_file.read()


@mark.parametrize('option', ['--silent', '-s'])
def test_cli_compile_silent(runner, echo, app, option):
    """
    Ensures --silent makes everything quiet
    """
    result = runner.invoke(Cli.compile, ['/path', option])
    App.compile.assert_called_with('/path', ebnf_file=None, debug=False)
    assert result.output == ''
    assert click.echo.call_count == 0


def test_cli_compile_debug(runner, echo, app):
    runner.invoke(Cli.compile, ['/path', '--debug'])
    App.compile.assert_called_with('/path', ebnf_file=None, debug=True)


@mark.parametrize('option', ['--json', '-j'])
def test_cli_compile_json(runner, echo, app, option):
    """
    Ensures --json outputs json
    """
    runner.invoke(Cli.compile, ['/path', option])
    App.compile.assert_called_with('/path', ebnf_file=None, debug=False)
    click.echo.assert_called_with(App.compile())


def test_cli_compile_ebnf_file(runner, echo, app):
    runner.invoke(Cli.compile, ['/path', '--ebnf-file', 'test.grammar'])
    kwargs = {'ebnf_file': 'test.grammar', 'debug': False}
    App.compile.assert_called_with('/path', **kwargs)


def test_cli_lexer(patch, magic, runner, app, echo):
    """
    Ensures the lex command outputs lexer tokens
    """
    token = magic(type='token', value='value')
    patch.object(App, 'lex', return_value={'one.story': [token]})
    runner.invoke(Cli.lex, ['/path'])
    app.lex.assert_called_with('/path')
    click.echo.assert_called_with('0 token value')
    assert click.echo.call_count == 2


def test_cli_lexer_default(patch, magic, runner, app):
    """
    Ensures the lex command storypath defaults to cwd
    """
    patch.object(App, 'lex', return_value={'one.story': [magic()]})
    runner.invoke(Cli.lex, [])
    app.lex.assert_called_with(os.getcwd())


def test_cli_grammar(patch, runner, app, echo):
    patch.object(App, 'grammar')
    runner.invoke(Cli.grammar, [])
    assert app.grammar.call_count == 1
    click.echo.assert_called_with(app.grammar())


def test_cli_help(patch, runner, echo):
    runner.invoke(Cli.help, [])
    # NOTE(vesuvium): another weird click thing. The context.parent.get_help
    # seems to mess up with mock, registering no call on click.echo
    assert click.echo.call_count == 0


def test_cli_version(patch, runner, echo):
    runner.invoke(Cli.version, [])
    click.echo.assert_called_with(version)
