# -*- coding: utf-8 -*-
import re

from lark import Transformer as LarkTransformer

from .tree import Tree
from ..exceptions import StoryError


class Transformer(LarkTransformer):

    """
    Performs transformations on the tree before it's parsed.
    All trees are transformed to Storyscript's custom tree. In some cases,
    additional transformations or checks are performed.
    """

    def arguments(self, matches):
        """
        Transform an argument tree. If dealing with is a short-hand argument,
        expand it.
        """
        if len(matches) == 1:
            matches = [matches[0].child(0), matches[0]]
        return Tree('arguments', matches)

    def assignment(self, matches):
        token = matches[0].children[0]
        if '/' in token.value:
            raise StoryError('variables-backslash', token)
        if '-' in token.value:
            raise StoryError('variables-dash', token)
        return Tree('assignment', matches)

    def __getattr__(self, attribute, *args):
        return lambda matches: Tree(attribute, matches)
