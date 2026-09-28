import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / '6.api' / 'resource'
BASELINE = Path(__file__).parent / 'fixtures' / 'api_pulp3.json'


def sample_data():
    return pd.read_csv(RESOURCE / 'students.csv'), pd.read_csv(RESOURCE / 'cars.csv')


def model_signature(prob, significant_digits=None):
    data = prob.toDict()

    def number(value):
        if value is None:
            return None
        if significant_digits is None:
            return float(value)
        return float(format(value, f'.{significant_digits}g'))

    def terms(coefficients):
        return sorted((c['name'], number(c['value'])) for c in coefficients
                      if c['name'] != '__dummy' and c['value'] != 0)

    variables = sorted(
        (v['name'], v['cat'],
         number(v['lowBound']), number(v['upBound']))
        for v in data['variables'] if v['name'] != '__dummy'
    )
    constraints = sorted(
        (c['sense'], number(c['constant']), terms(c['coefficients']))
        for c in data['constraints']
    )
    model = {
        'sense': data['parameters']['sense'],
        'variables': variables,
        'constraints': constraints,
        'objective': terms(data['objective']['coefficients']),
    }
    return {
        'sha256': hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest(),
        'variables': len(variables),
        'constraints': len(constraints),
        'objective': model['objective'],
    }


def assert_assignment(solution, students, cars):
    assert list(solution.columns) == ['student_id', 'car_id']
    assert not solution.isna().any().any()
    assert solution.student_id.is_unique
    assert sorted(solution.student_id) == sorted(students.student_id)
    assert set(solution.car_id) <= set(cars.car_id)
    assigned = students.merge(solution, on='student_id', validate='one_to_one')
    for car in cars.itertuples():
        group = assigned[assigned.car_id == car.car_id]
        assert len(group) <= car.capacity
        assert (group.license == 1).any()
        assert set(group.grade) == {1, 2, 3, 4}
        assert set(group.gender) == {0, 1}
