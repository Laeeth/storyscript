# -*- coding: utf-8 -*-
import io
import os

from lark import Lark
from lark.exceptions import UnexpectedInput, UnexpectedToken

from pytest import fixture, raises

from storyscript.exceptions import StoryError
from storyscript.parser import (CustomIndenter, Grammar, Parser, Transformer,
                                Tree)


@fixture
def parser():
    return Parser()


def test_parser_init(parser):
    assert parser.algo == 'lalr'
    assert parser.ebnf_file is None


def test_parser_init_algo():
    parser = Parser(algo='algo')
    assert parser.algo == 'algo'


def test_parser_init_ebnf_file():
    parser = Parser(ebnf_file='grammar.ebnf')
    assert parser.ebnf_file == 'grammar.ebnf'


def test_parser_indenter(patch, parser):
    patch.init(CustomIndenter)
    assert isinstance(parser.indenter(), CustomIndenter)


def test_parser_transfomer(patch, parser):
    patch.init(Transformer)
    assert isinstance(parser.transformer(), Transformer)


def test_parser_grammar(patch, parser):
    patch.init(Grammar)
    patch.object(Grammar, 'build')
    result = parser.grammar()
    assert Grammar.__init__.call_count == 1
    assert result == Grammar().build()


def test_parser_grammar_ebnf_file(patch, parser):
    patch.object(io, 'open')
    parser.ebnf_file = 'test.ebnf'
    result = parser.grammar()
    io.open.assert_called_with('test.ebnf', 'r')
    assert result == io.open().__enter__().read()


def test_parser_lark(patch, parser):
    patch.init(Lark)
    patch.many(Parser, ['indenter', 'grammar'])
    result = parser.lark()
    Lark.__init__.assert_called_with(parser.grammar(),
                                     parser=parser.algo,
                                     postlex=Parser.indenter())
    assert isinstance(result, Lark)


def test_parser_parse(patch, parser):
    """
    Ensures the build method can build the grammar
    """
    patch.many(Parser, ['lark', 'transformer'])
    result = parser.parse('source')
    Parser.lark().parse.assert_called_with('source\n')
    Parser.transformer().transform.assert_called_with(Parser.lark().parse())
    assert result == Parser.transformer().transform()


def test_parser_parse_empty(patch, parser):
    """
    Ensures that empty stories are parsed correctly
    """
    assert parser.parse('') == Tree('empty', [])


def test_parser_parser_unexpected_token(capsys, patch, magic, parser):
    patch.init(StoryError)
    patch.object(StoryError, 'message')
    patch.many(Parser, ['lark', 'transformer'])
    Parser.lark().parse.side_effect = UnexpectedToken(magic(), 'exp', 0, 1)
    with raises(SystemExit):
        parser.parse('source', debug=False)
    out, err = capsys.readouterr()
    assert out == '{}\n'.format(StoryError.message())


def test_parser_parser_unexpected_token_debug(patch, magic, parser):
    patch.many(Parser, ['lark', 'transformer'])
    Parser.lark().parse.side_effect = UnexpectedToken(magic(), 'exp', 0, 1)
    with raises(UnexpectedToken):
        parser.parse('source', debug=True)


def test_parser_parser_unexpected_input(capsys, patch, magic, parser):
    patch.init(StoryError)
    patch.object(StoryError, 'message')
    patch.many(Parser, ['lark', 'transformer'])
    Parser.lark().parse.side_effect = UnexpectedInput(magic(), 0, 0, 0)
    with raises(SystemExit):
        parser.parse('source', debug=False)
    out, err = capsys.readouterr()
    assert out == '{}\n'.format(StoryError.message())


def test_parser_parser_unexpected_input_debug(patch, magic, parser):
    patch.many(Parser, ['lark', 'transformer'])
    Parser.lark().parse.side_effect = UnexpectedInput(magic(), 0, 0, 0)
    with raises(UnexpectedInput):
        parser.parse('source', debug=True)


def test_parser_lex(patch, parser):
    patch.many(Parser, ['lark', 'indenter'])
    result = parser.lex('source')
    Parser.lark().lex.assert_called_with('source')
    assert result == Parser.lark().lex()
