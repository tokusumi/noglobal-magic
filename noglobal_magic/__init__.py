import ast
import sys
import re
from typing import Optional, List
from enum import Enum, auto
from copy import copy
from packaging import version

import IPython
from IPython.core.magic import register_line_magic
from IPython.core.inputtransformer import InputTransformer
from ipykernel.zmqshell import ZMQInteractiveShell as ip
import pyflakes
import pyflakes.checker
from pyflakes.messages import Message, UndefinedName, RedefinedWhileUnused


IPYTHON_VER = version.parse(IPython.__version__)


class LocalNameError(NameError):
    def _render_traceback_(self):
        pass


NOQA_INLINE_REGEXP = re.compile(
    # We're looking for items that look like this:
    # ``# noqa``
    r"# noqa(?::[\s]?(?P<codes>([A-Z]+[0-9]+(?:[,\s]+)?)+))?",
    re.IGNORECASE,
)


def find_noqa(physical_line: str):
    return NOQA_INLINE_REGEXP.search(physical_line)


class GlobalVariable:
    message = "global variable %r"

    def __init__(self, filename: str, loc: ast.Module, name: str):
        self.success = True
        self.message_args = (name,)
        self.filename = filename
        self.col: int = loc.col_offset
        self.lineno: int = loc.lineno

        self.parent = loc
        for _ in range(loc._pyflakes_depth):
            self.parent = self.parent._pyflakes_parent

        if not hasattr(self.parent, "lineno"):
            # this module exists out of function or class
            self.success = False
            return

        if hasattr(self.parent, "cellno"):
            self.cellno: int = self.parent.cellno
        else:
            self.cellno = int(filename)


class Checker(pyflakes.checker.Checker):
    def __init__(self, *args, noqa: Optional[List[int]] = None, **kwargs):
        self.pure_tree = copy(args[0].body)
        self.noqa = set(noqa) if noqa else set([])
        self.messages: List[GlobalVariable]
        super().__init__(*args, **kwargs)

    def report(self, messageClass: Message, *args, **kwargs):
        if issubclass(messageClass, UndefinedName):
            global_variable = GlobalVariable(self.filename, *args, **kwargs)
            if global_variable.success:
                self.messages.append(global_variable)
        elif issubclass(messageClass, RedefinedWhileUnused):
            for obj in args[1:]:
                if not isinstance(obj, str):
                    self.pure_tree.remove(obj)

    def run(self, body, only_current_cell=True):
        messages: List[GlobalVariable] = []
        set_body = set(body)
        for message in self.messages:
            if only_current_cell and message.parent not in set_body:
                # ignore not current cell
                continue

            if message.lineno in self.noqa:
                # ignore `noqa` line
                continue

            messages.append(
                "In [{}] {}: {} In '{}'".format(
                    message.cellno,
                    message.lineno,
                    message.message % message.message_args,
                    message.parent.name,
                )
            )
        return messages


class NoGlobal:
    def __init__(self):
        self.dependencies = []
        self.checker = []

    def __call__(
        self,
        raw_cell: str,
        current_cell_no: int,
        only_current_cell=True,
        noqa: Optional[List[int]] = None,
    ):
        """return no global error messages"""
        if not noqa:
            noqa = []
        tree = ast.parse(raw_cell)

        # eliminate declaration lines and add cell no
        body = []
        body_a = body.append
        for child in tree.body:
            if not isinstance(child, ast.Assign):
                child.cellno = current_cell_no
                body_a(child)

        # add past dependencies
        tree.body = self.dependencies + body

        # check and return only UndefinedName messages
        self.checker = Checker(
            tree,
            filename=current_cell_no,
            withDoctest=False,
            file_tokens=(),
            noqa=noqa,
        )

        messages = self.checker.run(body, only_current_cell=only_current_cell)

        return messages


class VarWatcher:
    def __init__(self, ip: ip, error=True, only_current_cell=True):
        self.shell = ip
        self.error = error
        self.only_current_cell = only_current_cell
        self.success = False
        self.target_cell = None
        self._no_global = NoGlobal()

    def no_global(self, lines: List[str]):
        if self.target_cell == self.shell.execution_count:
            if self.success:
                return lines
            return ["from noglobal_magic import LocalNameError; raise LocalNameError"]

        self.target_cell = self.shell.execution_count

        noqa = [lineno for lineno, line in enumerate(lines, 1) if find_noqa(line)]
        raw_cell = "".join(lines)

        messages = self._no_global(
            raw_cell,
            f"{self.target_cell}",
            only_current_cell=self.only_current_cell,
            noqa=noqa,
        )

        if messages:
            if self.error:
                sys.stderr.write("noglobal Error\n")
            else:
                sys.stderr.write("noglobal Warning\n")
            sys.stderr.write("\n".join(messages))

            if self.error:
                self.success = False
                return [
                    "from noglobal_magic import LocalNameError; raise LocalNameError"
                ]

        # extract new dependencies
        new_dependencies = [
            f
            for f in self._no_global.checker.pure_tree
            if isinstance(f, (ast.Import, ast.FunctionDef, ast.ClassDef))
        ]

        self._no_global.dependencies = new_dependencies
        self.success = True
        return lines


class NoGlobalTransformer(InputTransformer):
    def __init__(self, ip: ip, error=True, only_current_cell=True):
        self.shell = ip
        self.error = error
        self.only_current_cell = only_current_cell
        self.success = False
        self.target_cell = None
        self._lines: List[str] = []
        self._no_global = NoGlobal()

    def push(self, line: str):
        self._lines.append(line)

    def reset(self):
        noqa = [lineno for lineno, line in enumerate(self._lines, 1) if find_noqa(line)]

        raw_cell = "\n".join(self._lines)
        self._lines = []

        if not raw_cell:
            return ""

        self.target_cell = self.shell.execution_count

        messages = self._no_global(
            raw_cell,
            f"{self.target_cell}",
            only_current_cell=self.only_current_cell,
            noqa=noqa,
        )

        if messages:
            if self.error:
                sys.stderr.write("noglobal Error\n")
            else:
                sys.stderr.write("noglobal Warning\n")
            sys.stderr.write("\n".join(messages))

            if self.error:
                self.success = False
                return "from noglobal_magic import LocalNameError; raise LocalNameError"

        # extract new dependencies
        new_dependencies = [
            f
            for f in self._no_global.checker.pure_tree
            if isinstance(f, (ast.Import, ast.FunctionDef, ast.ClassDef))
        ]

        self._no_global.dependencies = new_dependencies
        self.success = True
        return raw_cell


vw: Optional[VarWatcher] = None


class Option(Enum):
    no_global = auto()
    warn_global = auto()


@register_line_magic
def no_global(line):
    load_ipython_extension(vw.shell, option=Option.no_global)


@register_line_magic
def warn_global(line):
    load_ipython_extension(vw.shell, option=Option.warn_global)


if IPYTHON_VER >= version.parse("7.0.0"):

    def load_ipython_extension(ip: ip, option: Optional[Option] = None):
        global vw
        if option is None:
            vw = VarWatcher(ip)
            return
        elif option == Option.no_global:
            vw.error = True
        elif option == Option.warn_global:
            vw.error = False

        if vw.no_global not in ip.input_transformers_post:
            ip.input_transformers_post.append(vw.no_global)


else:

    def load_ipython_extension(ip: ip, option: Optional[Option] = None):
        global vw
        if option is None:
            vw = NoGlobalTransformer(ip)
            return
        elif option == Option.no_global:
            vw.error = True
        elif option == Option.warn_global:
            vw.error = False

        if vw not in ip.input_transformer_manager.python_line_transforms:
            ip.input_transformer_manager.python_line_transforms.append(vw)
