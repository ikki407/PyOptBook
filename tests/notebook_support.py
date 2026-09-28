import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from unittest.mock import patch

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pulp

from api_support import ROOT, model_signature


SOURCE_COMMIT = '3f5c7f7cf1ac7a3793dfc7c47bb90f38d091f347'
BASELINE = Path(__file__).parent / 'fixtures' / 'notebooks_pulp3.json'
CASES = {
    'tutorial': ('2.tutorial/tutorial.ipynb', None),
    'scipy_comparison': ('2.tutorial/tutorial_scipy_optimize_milp.ipynb', None),
    'school': ('3.school/school.ipynb', None),
    'coupon': ('4.coupon/coupon.ipynb', None),
    'routing': ('5.routing/routing.ipynb', [1, 3, 4, 9, 11, 12, 15, 17, 18, 19, 20]),
    'routing_v2_small': ('5.routing_ver2/routing_ver2.ipynb',
                         [4, 6, 7, 9, 10, 12, 14, 32, 35, 38, 39, 41, 44, 45]),
    'routing_v2_tsp': ('5.routing_ver2/routing_ver2.ipynb', [31, 32, 33, 34]),
    'routing_v2_large': ('5.routing_ver2/routing_ver2.ipynb', [4, 16, 18, 19, 20, 21, 22, 25]),
}


def read_notebook(path, original=False):
    if original:
        return json.loads(subprocess.check_output(
            ['git', 'show', f'{SOURCE_COMMIT}:{path}'], cwd=ROOT, text=True))
    return json.loads((ROOT / path).read_text())


def check_solution(prob):
    data = prob.toDict()
    values = {v['name']: v['varValue'] for v in data['variables']}
    for v in data['variables']:
        if v['name'] == '__dummy':
            continue
        value = v['varValue']
        assert value is not None, v['name']
        assert v['lowBound'] is None or value >= v['lowBound'] - 1e-5, v
        assert v['upBound'] is None or value <= v['upBound'] + 1e-5, v
        if v['cat'] == 'Integer':
            assert abs(value - round(value)) <= 1e-5, v
    for constraint in data['constraints']:
        products = [c['value'] * (values[c['name']] or 0)
                    for c in constraint['coefficients']]
        residual = constraint['constant'] + sum(products)
        tolerance = 1e-7 * max(1, abs(constraint['constant']), sum(map(abs, products)))
        if constraint['sense'] == 0:
            assert abs(residual) <= tolerance, (constraint['name'], residual, tolerance)
        else:
            assert constraint['sense'] * residual >= -tolerance, (constraint['name'], residual)


def run_case(case, original=False):
    path, selected = CASES[case]
    notebook = read_notebook(path, original)
    records = []
    solve = pulp.LpProblem.solve
    namespace = {'__name__': '__main__'}

    def checked_solve(prob, solver=None, **kwargs):
        signature = model_signature(prob)
        signature.pop('objective')
        constant = float(prob.objective.constant) if prob.objective is not None else 0.0
        if solver is None:
            solver_class = pulp.PULP_CBC_CMD if original else pulp.COIN_CMD
            solver = solver_class(msg=False)
        solver.msg = False
        solver.timeLimit = 600 if case == 'routing_v2_large' else 120
        if os.environ.get('PYOPTBOOK_CBC_PATH'):
            solver.path = os.environ['PYOPTBOOK_CBC_PATH']
        if case == 'routing_v2_large' and not original:
            initial = json.loads(BASELINE.read_text())['cases'][case][0]['initial_values']
            for variable in prob.variables():
                variable.setInitialValue(initial.get(variable.name, 0))
            solver.optionsDict['warmStart'] = True
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / 'cbc.log'
            solver.optionsDict['logPath'] = str(log_path)
            result = solve(prob, solver, **kwargs)
            log = log_path.read_text()
        if original:
            has_solution = prob.sol_status in (pulp.LpSolutionOptimal, pulp.LpSolutionIntegerFeasible)
            optimal = prob.sol_status == pulp.LpSolutionOptimal
            status = pulp.LpStatus[result]
        else:
            has_solution = result.has_solution
            optimal = result.status == pulp.LpSolveStatus.Optimal
            status = result.status_str
        gap_limited = 'within gap tolerance' in log
        objective = None
        if has_solution:
            check_solution(prob)
            objective = float(pulp.value(prob.objective) or 0)
        lower = re.search(r'Lower bound:\s+([-+\d.eE]+)', log)
        best_bound = float(lower.group(1)) + constant if lower else None
        records.append({'model': signature, 'constant': constant, 'status': status,
                        'has_solution': has_solution, 'optimal': optimal and not gap_limited,
                        'gap_limited': gap_limited, 'objective': objective, 'best_bound': best_bound})
        if case == 'routing_v2_large' and original:
            records[-1]['initial_values'] = {v.name: v.value() for v in prob.variables() if v.value()}
        if case == 'routing_v2_large':
            assert has_solution
            assert optimal or gap_limited, (status, objective, best_bound, log[-2500:])
            if gap_limited:
                assert best_bound is not None
                assert abs(objective - best_bound) <= 0.101 * abs(objective - constant)
        return result

    with contextlib.chdir(ROOT / Path(path).parent), contextlib.redirect_stdout(io.StringIO()), \
            patch.object(pulp.LpProblem, 'solve', checked_solve):
        try:
            for index, cell in enumerate(notebook['cells']):
                if cell['cell_type'] != 'code' or (selected is not None and index not in selected):
                    continue
                source = ''.join(cell['source'])
                if original and case == 'routing':
                    source = source.replace('from IPython.core.display import display',
                                            'from IPython.display import display')
                    source = source.replace('.loc[nondominated_idx_set, :]',
                                            '.loc[sorted(nondominated_idx_set), :]')
                exec(compile(source, f'{path}:cell_{index}', 'exec'), namespace)
                if case == 'routing' and index == 1:
                    from joblib import Parallel
                    namespace['Parallel'] = lambda **kwargs: Parallel(n_jobs=1)
                if case == 'routing' and index == 3:
                    namespace.update(num_places=4, num_days=5, num_requests=12)
        finally:
            plt.close('all')
    assert records, case
    return records
