# -*- coding: utf-8 -*-
from .lines import Lines
from .objects import Objects
from .preprocessor import Preprocessor
from ..exceptions import StoryError
from ..parser import Tree
from ..version import version


class Compiler:

    """
    Compiles Storyscript abstract syntax tree to JSON.
    """
    def __init__(self):
        self.lines = Lines()

    @staticmethod
    def output(tree):
        output = []
        if tree:
            for item in tree.children:
                output.append(item.value)
        return output

    @classmethod
    def function_output(cls, tree):
        return cls.output(tree.node('function_output.types'))

    def imports(self, tree, parent):
        """
        Compiles an import rule
        """
        module = tree.child(1).value
        self.lines.modules[module] = tree.string.child(0).value[1:-1]

    def expression(self, tree, parent):
        """
        Compiles an expression
        """
        mutation = None
        if tree.expression:
            if tree.expression.mutation:
                value = Objects.values(tree.expression.values)
                mutation = Objects.mutation(tree.expression.mutation)
            else:
                value = Objects.expression(tree.expression)
        elif tree.service_fragment:
            value = Objects.path(tree.path)
            mutation = Objects.mutation(tree.service_fragment)
        args = [value]
        if mutation:
            args.append(mutation)
        self.lines.append('expression', tree.line(), args=args, parent=parent)

    def absolute_expression(self, tree, parent):
        """
        Compiles an absolute expression using Compiler.expression
        """
        self.expression(tree, parent)

    def extract_values(self, fragment):
        """
        Extracts values from an assignment_fragment tree, to be used as
        arguments in a set method.
        """
        if fragment.expression:
            if fragment.expression.mutation:
                return [Objects.values(fragment.expression.values),
                        Objects.mutation(fragment.expression.mutation)]
            return [Objects.expression(fragment.expression)]
        return [Objects.values(fragment.child(1))]

    def assignment(self, tree, parent):
        """
        Compiles an assignment tree
        """
        name = Objects.names(tree.path)
        service = tree.assignment_fragment.service
        if service:
            path = Objects.names(service.path)
            if path not in self.lines.variables:
                self.service(service, None, parent)
                self.lines.set_name(name)
                return
            else:
                self.expression(service, parent)
                self.lines.set_name(name)
                return
        line = tree.line()
        args = self.extract_values(tree.assignment_fragment)
        self.lines.append('set', line, name=name, args=args, parent=parent)

    def arguments(self, tree, parent):
        """
        Compiles arguments. This is called only for nested arguments.
        """
        line = self.lines.lines[self.lines.last()]
        if line['method'] != 'execute':
            raise StoryError('arguments-noservice', tree)
        line['args'] = line['args'] + Objects.arguments(tree)

    def service(self, tree, nested_block, parent):
        """
        Compiles a service tree.
        """
        service_name = Objects.names(tree.path)
        if service_name in self.lines.variables:
            self.expression(tree, parent)
            return
        line = tree.line()
        command = tree.service_fragment.command
        if command:
            command = command.child(0)
        arguments = Objects.arguments(tree.service_fragment)
        service = tree.path.extract_path()
        output = self.output(tree.service_fragment.output)
        if output:
            self.lines.set_output(line, output)
        enter = None
        if nested_block:
            enter = nested_block.line()
        self.lines.execute(line, service, command, arguments, output, enter,
                           parent)

    def when(self, tree, nested_block, parent):
        """
        Compiles a when tree
        """
        if tree.service:
            self.service(tree.service, nested_block, parent)
            self.lines.lines[self.lines.last()]['method'] = 'when'
        elif tree.path:
            args = [Objects.path(tree.path)]
            output = self.output(tree.output)
            self.lines.append('when', tree.line(), args=args,
                              output=output, parent=parent)

    def return_statement(self, tree, parent):
        """
        Compiles a return_statement tree
        """
        if parent is None:
            raise StoryError('return-outside', tree)
        line = tree.line()
        args = [Objects.values(tree.child(0))]
        self.lines.append('return', line, args=args, parent=parent)

    def if_block(self, tree, parent):
        line = tree.line()
        nested_block = tree.nested_block
        args = Objects.expression(tree.if_statement)
        self.lines.append('if', line, args=args, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)
        trees = []
        for block in [tree.elseif_block, tree.else_block]:
            if block:
                trees.append(block)
        self.subtrees(*trees)

    def elseif_block(self, tree, parent):
        """
        Compiles elseif_block trees
        """
        line = tree.line()
        self.lines.set_exit(line)
        args = Objects.expression(tree.elseif_statement)
        nested_block = tree.nested_block
        self.lines.append('elif', line, args=args, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)

    def else_block(self, tree, parent):
        """
        Compiles else_block trees
        """
        line = tree.line()
        self.lines.set_exit(line)
        nested_block = tree.nested_block
        self.lines.append('else', line, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)

    def foreach_block(self, tree, parent):
        line = tree.line()
        path = Tree('path', [tree.foreach_statement.child(0)])
        args = [Objects.path(path)]
        output = self.output(tree.foreach_statement.output)
        nested_block = tree.nested_block
        self.lines.append('for', line, args=args, enter=nested_block.line(),
                          parent=parent, output=output)
        self.subtree(nested_block, parent=line)

    def function_block(self, tree, parent):
        """
        Compiles a function and its nested block of code.
        """
        line = tree.line()
        function = tree.function_statement
        args = Objects.function_arguments(function)
        output = self.function_output(function)
        nested_block = tree.nested_block
        self.lines.append('function', line, function=function.child(1).value,
                          output=output, args=args, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)

    def service_block(self, tree, parent):
        """
        Compiles a service block and the eventual nested block.
        """
        self.service(tree.service, tree.nested_block, parent)
        if tree.nested_block:
            self.subtree(tree.nested_block, parent=tree.line())

    def when_block(self, tree, parent):
        self.when(tree, tree.nested_block, parent)
        if tree.nested_block:
            self.subtree(tree.nested_block, parent=tree.line())

    def try_block(self, tree, parent):
        """
        Compiles a try block
        """
        line = tree.line()
        nested_block = tree.nested_block
        self.lines.append('try', line, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)
        if tree.catch_block:
            self.catch_block(tree.catch_block, parent=parent)
        if tree.finally_block:
            self.finally_block(tree.finally_block, parent=parent)

    def catch_block(self, tree, parent):
        """
        Compiles a catch block
        """
        line = tree.line()
        self.lines.set_exit(line)
        nested_block = tree.nested_block
        output = Objects.names(tree.catch_statement)
        self.lines.append('catch', line, enter=nested_block.line(),
                          output=output, parent=parent)
        self.subtree(nested_block, parent=line)

    def finally_block(self, tree, parent):
        """
        Compiles a finally block
        """
        line = tree.line()
        self.lines.set_exit(line)
        nested_block = tree.nested_block
        self.lines.append('finally', line, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)

    def subtrees(self, *trees):
        """
        Parses many subtrees
        """
        for tree in trees:
            self.subtree(tree)

    def subtree(self, tree, parent=None):
        """
        Parses a subtree, checking whether it should be compiled directly
        or keep parsing for deeper trees.
        """
        allowed_nodes = ['service_block', 'absolute_expression', 'assignment',
                         'if_block', 'elseif_block', 'else_block',
                         'foreach_block', 'function_block', 'when_block',
                         'try_block', 'return_statement', 'arguments',
                         'imports']
        if tree.data in allowed_nodes:
            getattr(self, tree.data)(tree, parent)
            return
        self.parse_tree(tree, parent=parent)

    def parse_tree(self, tree, parent=None):
        """
        Parses a tree looking for subtrees.
        """
        for item in tree.children:
            if isinstance(item, Tree):
                self.subtree(item, parent=parent)

    @staticmethod
    def compiler():
        return Compiler()

    @classmethod
    def compile(cls, tree, debug=False):
        tree = Preprocessor.process(tree)
        compiler = cls.compiler()
        compiler.parse_tree(tree)
        lines = compiler.lines
        return {'tree': lines.lines, 'services': lines.get_services(),
                'entrypoint': lines.first(), 'modules': lines.modules,
                'functions': lines.functions, 'version': version}
