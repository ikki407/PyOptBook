import ast
import json
import os
import re

import nbformat
import pulp
import pytest
from joblib import Parallel, delayed

from api_support import ROOT
from notebook_support import BASELINE, CASES, read_notebook, run_case


@pytest.mark.parametrize('case', CASES)
def test_notebook_models_and_solutions_match_pulp3(case):
    expected = json.loads(BASELINE.read_text())['cases'][case]
    actual = run_case(case)
    assert len(actual) == len(expected)
    for new, old in zip(actual, expected):
        assert new['model'] == old['model']
        assert new['constant'] == old['constant']
        assert new['has_solution'] == old['has_solution']
        if case == 'routing_v2_large':
            continue
        assert new['optimal'] == old['optimal']
        if old['has_solution']:
            assert new['objective'] == pytest.approx(old['objective'], rel=1e-8, abs=1e-5)
        else:
            assert new['status'] == old['status']


@pytest.mark.parametrize('path', sorted(ROOT.glob('*/*.ipynb')), ids=lambda p: str(p.relative_to(ROOT)))
def test_notebooks_are_valid_and_have_no_removed_pulp_calls(path):
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type != 'code':
            continue
        ast.parse(cell.source)
        assert not re.search(r'pulp\.(LpVariable\s*[.(]|LpStatus\b|PULP_CBC_CMD\b|LpAffineExpression\(\))',
                             cell.source)


def configure_worker():
    if os.environ.get('PYOPTBOOK_CBC_PATH'):
        pulp.LpSolverDefault.path = os.environ['PYOPTBOOK_CBC_PATH']
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
