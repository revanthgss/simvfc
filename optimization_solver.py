from ortools.algorithms import pywrapknapsack_solver


class OptimizationSolver:
    """By default it's knapsack solver"""

    def __init__(self):
        solver = pywrapknapsack_solver.KnapsackSolver(
            pywrapknapsack_solver.KnapsackSolver.
            KNAPSACK_DYNAMIC_PROGRAMMING_SOLVER, 'KnapsackSolver')

    def solve(self, weights, values, capacity):
        """Takes the parameters and outputs the indices of items that are selected"""
        solver = self.solver
        solver.Init(values, weights, capacity)
        computed_value = solver.Solve()

        selected_items = []
        for i in range(len(values)):
            if solver.BestSolutionContains(i):
                selected_items.append(i)
        return set(selected_items)
