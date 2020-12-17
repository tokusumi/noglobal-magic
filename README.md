# noglobal-magic

For Jupyter Notebook user's, [noglobal-magic](https://github.com/tokusumi/noglobal-magic) find global variables in a local scope.

With:
* No need to wait executing a function
* `flake8` style ignoring-error annotation (`# noqa`)
* `no_global` magic command makes raise error, and `warn_global` tells a just warning

## Installation

Make sure you've this `noglobal-magic` (And the Python package `pyflakes`).

```shell
pip install noglobal-magic
```

## How to use

In a cell on Jupyter Notebook, load and activate this extension:

```notebook
%load_ext noglobal_magic
%no_global
```

You've ready to enjoy coding.

Let's see in [colab](https://colab.research.google.com/drive/1y7Zr-RD2RPcSTjs0ml6vswbc96_IKt2y?usp=sharing) how it works.
