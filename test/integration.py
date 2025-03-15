from argparse import ArgumentParser
from nbconvert.preprocessors import ExecutePreprocessor
from nbformat import NotebookNode
from traitlets.config import Config
import nbformat
import os
import re


if os.name == 'nt':
    # Python, be better.
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _clear_output(nb:NotebookNode):
    for cell in nb.cells:
        if hasattr(cell,'outputs'):
            cell.outputs.clear()


def _run_notebook(filename:str, dir:str):
    config = Config()
    config.InteractiveShell.colors = 'NoColor'
    nb = nbformat.read(filename,as_version=4)
    _clear_output(nb)
    ExecutePreprocessor(kernel_name="python3", config=config).preprocess(
        nb, resources={ "metadata": { "path": dir } })
    return nb


def _indent(s:str):
    # textwrap.indent() doesn't handle blank lines the way we want.
    lines = s.rstrip().split('\n')
    return '\n'.join("    " + line for line in lines)


_RELOAD_DECL_RE    = re.compile(r"#@\s*reload\s+(\w+)\s*")
_ERROR_DECL_RE     = re.compile(r"#@\s*error\s+(\w+)\s*")
_MISSINGOK_DECL_RE = re.compile(r"#@\s*missingok\s*")


class _Expect:
    reloads   : list[str]
    errors    : list[str]
    missingok : bool

    def __init__(self, source:str):
        self.reloads = []
        self.errors  = []
        self.ok      = True

        for line in source.split('\n'):
            if line.startswith("#@"):
                if (match := _RELOAD_DECL_RE.fullmatch(line)):
                    self.reloads.append(match[1])
                elif (match := _ERROR_DECL_RE.fullmatch(line)):
                    self.errors.append(match[1])
                elif (match := _MISSINGOK_DECL_RE.fullmatch(line)):
                    self.ok = False
                else:
                    raise ValueError(
                        "Bad tag line in notebook code cell: " + line)
                

_RELOADED_LINE_RE = re.compile(r"^Reloaded (\w+) ")

class _Actual:
    reloads : list[str]
    errors  : list[str]
    ok      : bool

    def __init__(self, cell:NotebookNode):
        self.reloads = []
        self.errors  = []
        self.ok      = False

        for output in cell.outputs:
            otype = output.output_type
            if otype == 'display_data':
                if (text := output.data.get('text/markdown')) is not None:
                    if text == "OK":
                        self.ok = True
                    else:
                        for line in text.split('\n'):
                            if (match := _RELOADED_LINE_RE.match(line)):
                                self.reloads.append(match[1])
            elif otype == 'error':
                self.errors.append(output.ename)


def test_notebook(filename:str="notebook.ipynb", dir=".", verbose=False):
    """
    Verify notebook integration.
    """


    nb = _run_notebook(filename,dir)

    for i, cell in enumerate(nb.cells):
        if hasattr(cell,"outputs"):
            expect = _Expect(cell.source)
            actual = _Actual(cell)
            good = (expect.reloads == actual.reloads and 
                    expect.errors  == actual.errors and
                    expect.ok == actual.ok)
            if verbose or not good:
                print()
                print(f"--------------CELL {i}--------------")
                print()
                print("Source:")
                print()
                print(_indent(cell.source))
                print()
                print("Expected:")
                print(f"    reloads={expect.reloads}")
                print(f"     errors={expect.errors}")
                print(f"         ok={expect.ok}")
                print()
                print("Actual:")
                print(f"    reloads={actual.reloads}")
                print(f"     errors={actual.errors}")
                print(f"         ok={actual.ok}")
            if not good:
                print()
                raise RuntimeError("Notebook integration test failed")


if __name__ == '__main__':
    
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Verbosely test liveimport notebook integration")

    parser.add_argument("notebook", nargs='?', default="notebook.ipynb",
        help="Notebook file name")
    
    parser.add_argument("-dir",
        help="Working directory for notebook execution")
    
    parser.add_argument("-verbose",action="store_true",
        help="Print detailed information for every cell")
    
    args = parser.parse_args()    

    filename = args.notebook
    dir = args.dir if args.dir is not None else os.path.dirname(filename)

    test_notebook(filename, dir, args.verbose)
