import pulp


def solve_with_coupon_gap(problem, solver=None, _solve=pulp.LpProblem.solve, **kwargs):
    pulp.LpProblem.solve = _solve
    assert len(problem.variables()) == 15000
    assert len(problem.constraints) == 5049
    # Notebook の注記にある gapRel を使い、乱数シードを固定する。
    solver = solver or pulp.PULP_CBC_CMD(gapRel=1e-3, options=['randomSeed 1'])
    result = _solve(problem, solver, **kwargs)
    assert result == pulp.LpStatusOptimal
    objective = pulp.value(problem.objective)
    assert abs(objective - 326.09) <= 1e-5, objective
    for variable in problem.variables():
        value = variable.value()
        assert value is not None
        assert variable.lowBound is None or value >= variable.lowBound - 1e-5
        assert variable.upBound is None or value <= variable.upBound + 1e-5
        if variable.cat == pulp.LpInteger:
            assert abs(value - round(value)) <= 1e-5
    for constraint in problem.constraints.values():
        residual = constraint.value()
        tolerance = 1e-7 * max(1, abs(constraint.constant),
                               sum(abs(v.value() * c) for v, c in constraint.items()))
        if constraint.sense == 0:
            assert abs(residual) <= tolerance
        else:
            assert constraint.sense * residual >= -tolerance
    return result


pulp.LpProblem.solve = solve_with_coupon_gap
