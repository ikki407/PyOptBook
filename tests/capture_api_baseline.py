"""PuLP 3.3.2 の環境で実行し、移行前のコードから比較基準を保存する。"""
import hashlib
import json
import platform
import subprocess
import types

import pulp

from api_support import BASELINE, ROOT, assert_assignment, model_signature, sample_data


SOURCE_COMMIT = '3f5c7f7cf1ac7a3793dfc7c47bb90f38d091f347'


def main():
    if pulp.__version__ != '3.3.2':
        raise RuntimeError('Use PuLP 3.3.2 to capture the baseline')
    source = subprocess.check_output(
        ['git', 'show', f'{SOURCE_COMMIT}:6.api/problem.py'], cwd=ROOT, text=True
    )
    module = types.ModuleType('original_problem')
    exec(compile(source, 'original_problem.py', 'exec'), module.__dict__)
    students, cars = sample_data()
    problem = module.CarGroupProblem(students, cars)
    signature = model_signature(problem.prob['prob'])
    solution = problem.solve()
    assert_assignment(solution, students, cars)
    assert problem.prob['prob'].status == pulp.LpStatusOptimal
    single = module.CarGroupProblem(students.iloc[:4], cars.iloc[:1]).solve()
    baseline = {
        'source_commit': SOURCE_COMMIT,
        'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'python': platform.python_version(),
        'pulp': pulp.__version__,
        'solver': 'PULP_CBC_CMD (CBC 2.10.3)',
        'status': 'Optimal',
        'model': signature,
        'solution': solution.to_dict(orient='records'),
        'single_car_solution': single.to_dict(orient='records'),
    }
    BASELINE.parent.mkdir(exist_ok=True)
    BASELINE.write_text(json.dumps(baseline, indent=2) + '\n')


if __name__ == '__main__':
    main()
