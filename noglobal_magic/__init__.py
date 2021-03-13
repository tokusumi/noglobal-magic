from typing import Optional
from enum import Enum, auto
from packaging import version

import IPython
from IPython.core.magic import register_line_magic
from ipykernel.zmqshell import ZMQInteractiveShell as ip

from noglobal_magic.core import VarWatcher, NoGlobalTransformer, LocalNameError

IPYTHON_VER = version.parse(IPython.__version__)


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


@register_line_magic
def no_global_off(line):
    unload_ipython_extension(vw.shell)


@register_line_magic
def warn_global_off(line):
    unload_ipython_extension(vw.shell)


if IPYTHON_VER >= version.parse("7.0.0"):

    def load_ipython_extension(ip: ip, option: Optional[Option] = None):
        global vw
        if option is None:
            # at `load_ext noglobal_magic`
            vw = VarWatcher(ip)
            return
        elif option == Option.no_global:
            vw.error = True
        elif option == Option.warn_global:
            vw.error = False

        if vw.no_global not in ip.input_transformers_post:
            ip.input_transformers_post.append(vw.no_global)

    def unload_ipython_extension(ip: ip):
        global vw
        if vw is None:
            return
        if vw.no_global in ip.input_transformers_post:
            ip.input_transformers_post.remove(vw.no_global)
        # clear
        vw = VarWatcher(ip)


else:

    def load_ipython_extension(ip: ip, option: Optional[Option] = None):
        global vw
        if option is None:
            # at `load_ext noglobal_magic`
            vw = NoGlobalTransformer(ip)
            return
        elif option == Option.no_global:
            vw.error = True
        elif option == Option.warn_global:
            vw.error = False

        if vw not in ip.input_transformer_manager.python_line_transforms:
            ip.input_transformer_manager.python_line_transforms.append(vw)

    def unload_ipython_extension(ip: ip):
        global vw
        if vw is None:
            return

        if vw in ip.input_transformer_manager.python_line_transforms:
            ip.input_transformer_manager.python_line_transforms.remove(vw)

        # clear
        vw = NoGlobalTransformer(ip)
