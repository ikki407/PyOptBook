import sys
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted(ROOT.glob('*/*.ipynb'))


@pytest.mark.parametrize('path', NOTEBOOKS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_all_notebook_cells(path, tmp_path, capsys):
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            cell.outputs = []
            cell.execution_count = None
    client = NotebookClient(notebook, timeout=1200, kernel_name='python3',
                            resources={'metadata': {'path': str(path.parent)}},
                            allow_errors=False)
    client.km = client.create_kernel_manager()
    client.km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher',
                                  '-f', '{connection_file}']

    def report_cell(cell, cell_index, **kwargs):
        if cell.cell_type == 'code' and cell.source.strip():
            with capsys.disabled():
                print(f'{path.relative_to(ROOT)}: cell {cell_index}', flush=True)

    client.on_cell_start = report_cell
    try:
        client.execute()
    finally:
        nbformat.write(notebook, tmp_path / path.name)
    for cell in notebook.cells:
        if cell.cell_type == 'code' and cell.source.strip():
            assert cell.execution_count is not None
            assert all(output.output_type != 'error' for output in cell.outputs)
