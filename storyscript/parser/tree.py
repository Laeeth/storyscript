# -*- coding: utf-8 -*-
from lark.lexer import Token
from lark.tree import Tree as LarkTree

from ..version import version


class Tree(LarkTree):

    @staticmethod
    def walk(tree, path):
        for item in tree.children:
            if isinstance(item, Tree):
                if item.data == path:
                    return item

    def node(self, path):
        """
        Finds a subtree or a nested subtree, using path
        """
        shards = path.split('.')
        current = None
        for shard in shards:
            if current is None:
                current = self.walk(self, shard)
            else:
                current = self.walk(current, shard)
        return current

    def child(self, index):
        if len(self.children) > index:
            return self.children[index]

    def line(self):
        """
        Finds the line number of a tree, by finding the first token in the tree
        and returning its line
        """
        for child in self.children:
            if isinstance(child, Token):
                return str(child.line)
            return child.line()

    def insert(self, item):
        """
        Inserts an item into the current tree.
        """
        self.children.insert(0, item)

    def replace(self, index, item):
        """
        Replaces a child at the given index
        """
        self.children[index] = item

    def __getattr__(self, attribute):
        return self.node(attribute)
