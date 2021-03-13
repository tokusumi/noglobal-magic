def test_no_global(ip, capsys):
    """pytest version for demo.ipynb"""
    from noglobal_magic.core import LocalNameError

    ip.run_cell("%no_global", store_history=True)
    res = ip.run_cell("""a = 1""", store_history=True)
    res = ip.run_cell(
        """
aaa = 1
bbb = 2

def hoge(b, d=3):
    c = aaa + b + a  # global variable!!!
    c += bbb  # noqa: ignore magic in this line
    return c + d  # global variable!!!
""",
        store_history=True,
    )
    assert isinstance(res.error_in_exec, LocalNameError), res
    captured = capsys.readouterr()
    assert (
        captured.err
        == """noglobal Error
In [3] 5: global variable 'aaa' In 'hoge'
In [3] 5: global variable 'a' In 'hoge'"""
    )

    res = ip.run_cell("""hoge""", store_history=True)
    assert isinstance(res.error_in_exec, NameError), "declaration failed"

    ip.magic("no_global_off")
    res = ip.run_cell(
        """
aaa = 1
bbb = 2

def hoge(b, d=3):
    c = aaa + b + a  # global variable!!!
    c += bbb  # noqa: ignore magic in this line
    return c + d  # global variable!!!

hoge
""",
        store_history=True,
    )
    assert not isinstance(
        res.error_in_exec, (LocalNameError, NameError)
    ), "no global is invalid"


def test_warn_global(ip, capsys):
    """pytest version for demo_warn.ipynb"""
    from noglobal_magic.core import LocalNameError

    ip.run_cell("%warn_global", store_history=True)
    res = ip.run_cell("""a = 1""", store_history=True)
    res = ip.run_cell(
        """
aaa = 1
bbb = 2

def hoge(b, d=3):
    c = aaa + b + a  # global variable!!!
    c += bbb  # noqa: ignore magic in this line
    return c + d  # global variable!!!
""",
        store_history=True,
    )
    assert not isinstance(res.error_in_exec, LocalNameError), res
    captured = capsys.readouterr()
    assert (
        captured.err
        == """noglobal Warning
In [3] 5: global variable 'aaa' In 'hoge'
In [3] 5: global variable 'a' In 'hoge'"""
    )

    res = ip.run_cell("""hoge""", store_history=True)
    assert not isinstance(res.error_in_exec, NameError), "declaration failed"

    ip.magic("warn_global_off")
    res = ip.run_cell(
        """
aaa = 1
bbb = 2

def hoge(b, d=3):
    c = aaa + b + a  # global variable!!!
    c += bbb  # noqa: ignore magic in this line
    return c + d  # global variable!!!

hoge
""",
        store_history=True,
    )
    assert not isinstance(
        res.error_in_exec, (LocalNameError, NameError)
    ), "warn global is invalid"


def test_buildin(ip):
    """build-in function is valid"""
    from noglobal_magic.core import LocalNameError

    ip.run_cell("%no_global", store_history=True)
    res = ip.run_cell(
        """
def hoge():
    return abs(-1)
""",
        store_history=True,
    )
    assert not isinstance(res.error_in_exec, LocalNameError), res


def test_calling(ip):
    """calling function is valid"""
    from noglobal_magic.core import LocalNameError

    ip.run_cell("%no_global", store_history=True)
    res = ip.run_cell(
        """
from math import ceil
def hoge_func(): ...
class HogeClass: ...

def hoge():
    ceil(-1)
    hoge_func()
    HogeClass()
""",
        store_history=True,
    )
    assert not isinstance(res.error_in_exec, LocalNameError), res


def test_ignore(ip):
    from noglobal_magic.core import LocalNameError

    ip.run_cell("%no_global", store_history=True)
    res = ip.run_cell(
        """
bbb = 2

def hoge():
    return 1 + bbb  # noqa
""",
        store_history=True,
    )
    assert not isinstance(res.error_in_exec, LocalNameError), res


def test_indicator(ip, capsys):
    """
    - find cell and line No where use global variable
    - Can't find if dependency use global variables , in function declaration
    """
    ip.run_cell("%warn_global", store_history=True)
    ip.run_cell(
        """
bbb = 2

def using_global():
    a = 1 + bbb
    return a
""",
        store_history=True,
    )
    captured = capsys.readouterr()
    assert (
        captured.err
        == """noglobal Warning
In [2] 4: global variable 'bbb' In 'using_global'"""
    )

    res = ip.run_cell(
        """
def using_dependency_using_global_var():
    return using_global()
""",
        store_history=True,
    )
    captured = capsys.readouterr()
    assert (
        captured.err
        != """noglobal Warning
In [2] 4: global variable 'bbb' In 'using_global'"""
    )
