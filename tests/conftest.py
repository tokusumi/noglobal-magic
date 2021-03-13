import pytest
from IPython.testing.globalipapp import start_ipython


@pytest.fixture(scope="session")
def session_ip():
    return start_ipython()


@pytest.fixture(scope="function")
def ip(session_ip):
    session_ip.reset()
    session_ip.run_line_magic(magic_name="load_ext", line="noglobal_magic")
    yield session_ip
