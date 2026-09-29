import ast
import os
import re

import nbformat
import pandas as pd
import pulp
import pytest
from joblib import Parallel, delayed

from api_support import ROOT
from notebook_support import BASELINE, CASES, read_notebook, run_case


@pytest.mark.parametrize('case', CASES)
def test_notebook_results_match_expected_values(case):
    results = pd.read_csv(BASELINE)
    expected = results[results.case == case].to_dict(orient='records')
    actual = run_case(case)
    assert len(actual) == len(expected)
    for new, old in zip(actual, expected):
        assert new['variables'] == old['variables']
        assert new['constraints'] == old['constraints']
        assert new['has_solution'] == (old['result'] != 'infeasible')
        if old['result'] == 'optimal':
            assert new['status'] in ('Optimal', 'GapLimit'), new
            assert new['objective'] == pytest.approx(old['objective'], rel=1e-8, abs=1e-5)
        elif old['result'] == 'infeasible':
            assert new['status'] == 'Infeasible'


@pytest.mark.parametrize('path', sorted(ROOT.glob('*/*.ipynb')), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_notebooks_are_valid_and_have_no_removed_pulp_calls(path):
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    executed = path.relative_to(ROOT).as_posix() in {p for p, _ in CASES.values()}
    if executed:
        assert any(cell.get('outputs') for cell in notebook.cells)
    for cell in notebook.cells:
        if cell.cell_type != 'code':
            continue
        ast.parse(cell.source)
        assert not re.search(r'pulp\.(LpVariable\s*[.(]|LpStatus\b|PULP_CBC_CMD\b|LpAffineExpression\(\))',
                             cell.source)
        if executed and cell.source.strip():
            assert cell.execution_count is not None
            assert all(output.output_type != 'error' for output in cell.outputs)


def configure_worker():
    if os.environ.get('PYOPTBOOK_CBC_PATH'):
        if pulp.LpSolverDefault is not None:
            pulp.LpSolverDefault.path = os.environ['PYOPTBOOK_CBC_PATH']
        pulp.COIN_CMD.defaultPath = lambda self: os.environ['PYOPTBOOK_CBC_PATH']
    if pulp.LpSolverDefault is not None:
        pulp.LpSolverDefault.msg = False


def test_routing_builds_models_inside_parallel_workers():
    notebook = read_notebook('5.routing/routing.ipynb')
    namespace = {'__name__': '__main__'}
    for index in (1, 3, 4):
        exec(''.join(notebook['cells'][index]['source']), namespace)
        if index == 3:
            namespace.update(num_places=4, num_days=5, num_requests=12)
    source = ast.parse(''.join(notebook['cells'][9]['source']))
    functions = ast.Module(body=[node for node in source.body if isinstance(node, ast.FunctionDef)],
                           type_ignores=[])
    exec(compile(functions, 'routing_functions', 'exec'), namespace)
    routes = Parallel(n_jobs=2, initializer=configure_worker)(
        delayed(namespace['simulate_route'])(z) for z in [(0, 1, 0, 0), (1, 1, 0, 0)])
    assert routes[0] is None
    assert routes[1]['optimal']
    assert routes[1]['移動時間'] == pytest.approx(namespace['t'][0, 1] + namespace['t'][1, 0])
