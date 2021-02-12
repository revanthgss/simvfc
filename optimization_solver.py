from ortools.linear_solver import pywraplp

# class OptimizationSolver:
#     """By default it's knapsack solver"""

#     def solve(self, weights, values, capacity):
#         """Takes the parameters and outputs the indices of items that are selected"""
#         n = len(values)
#         dp = [[0 for i in range(capacity+1)] for j in range(n+1)]
#         for i in range(1, n+1):
#             for w in range(1, capacity+1):
#                 if weights[i-1] <= w and values[i-1] > 0:
#                     dp[i][w] = max(dp[i-1][w], values[i-1] +
#                                    dp[i-1][w-weights[i-1]])
#                 else:
#                     dp[i][w] = dp[i-1][w]
#         selected_items = set()
#         weight_in_knapsack = capacity
#         total_value = dp[n][capacity]
#         for i in range(n, 0, -1):
#             if total_value < 0:
#                 break
#             # If total value is more than the value of the items knapsack
#             # include the ith item in selected items
#             if total_value != dp[i-1][weight_in_knapsack]:
#                 selected_items.add(i-1)
#                 total_value -= values[i-1]
#                 weight_in_knapsack -= weights[i-1]
#         return selected_items


class OptimizationSolver:
    """By default it's knapsack solver"""

    def solve(self, weights, values, capacity):
        """Takes the parameters and outputs the indices of items that are selected"""
        solver = pywraplp.Solver('knapsack_solver',pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)
        n = len(values)
        x = {}
        # Initialize variables
        for i in range(n):
            x[i] = solver.IntVar(0,1,f'x_{i}')

        # define constraints
        solver.Add(solver.Sum([weights[i]*x[i] for i in range(n)])<=capacity)

        # define objective
        solver.Maximize(solver.Sum([values[i]*x[i] for i in range(n)]))

        solver.Solve()

        selected_items = set()
        for i in range(n):
            if x[i].solution_value()==1:
                selected_items.add(i)
        
        return selected_items
        