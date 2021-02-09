

class OptimizationSolver:
    """By default it's knapsack solver"""

    def solve(self, weights, values, capacity):
        # TODO: Write a cpp wrapper to solve the knapsack problem
        """Takes the parameters and outputs the indices of items that are selected"""
        n = len(values)
        dp = [[0 for i in range(capacity+1)] for j in range(n+1)]
        for i in range(1, n+1):
            for w in range(1, capacity+1):
                if weights[i-1] <= w and values[i-1] > 0:
                    dp[i][w] = max(dp[i-1][w], values[i-1] +
                                   dp[i-1][w-values[i-1]])
                else:
                    dp[i][w] = dp[i-1][w]
        selected_items = set()
        weight_in_knapsack = capacity
        total_value = dp[n][capacity]
        for i in range(n, 0, -1):
            # If total value is more than the value of the items knapsack
            # include the ith item in selected items
            if total_value != dp[i-1][weight_in_knapsack]:
                selected_items.add(i-1)
                total_value -= values[i-1]
                weight_in_knapsack -= weights[i-1]
        return selected_items
