from utils import find_vehicles
import numpy as np
from optimization_solver import OptimizationSolver


class OrchestrationModule:

    def step(self):
        raise NotImplementedError


class DynamicResourceOrchestrationModule(OrchestrationModule):

    def __init__(self, fog_nodes, vehicles, eps=0.1, gamma=0.01):
        self.fog_nodes = fog_nodes
        self.vehicles = vehicles
        self.EPS = eps
        self.GAMMA = gamma
        self.D_star = {}
        self.d_star = {}
        self.W = {}

    def get_feasible_connected_vehicles(self, i, j):
        """Returns the ids of connected vehicles that are possible for service migration"""
        # Feasible connected vehicles for service migrations from i to j
        # key -> (i,j), value: [list of vehicles]

        di = set(filter(
            lambda x: x['service'].vehicle.id, self.fog_nodes[i].get_vehicle_services()))
        dj = set(filter(
            lambda x: x['service'].vehicle.id, self.fog_nodes[j].get_vehicle_services()))
        di_cov = {v.id for v in find_vehicles(
            self.vehicles, fog_nodes[i])}
        dj_cov = {v.id for v in find_vehicles(
            self.vehicles, fog_nodes[j])}
        dij_cov = di_cov.intersection(dj_cov)

        return (di.union(dj)).intersection(dij_cov)

    def is_associated(self, i, j):
        """Returns if jth vehicle is associated with ith fog node"""
        vehicle = [v.id for v in self.vehicles if v.id == j][0]
        return vehicle.alloted_fog_node is not None and vehicle.allotted_fog_node.id == i

    def compute_resource_blocks(self):
        # b[(i,j)] denotes number of resource blocks assigned by fog node i to vehicle j
        self.b = {}
        for fn in self.fog_nodes:
            for vs in find_vehicles(self.vehicles, fn):
                self.b[(fn.id, vs['service'].vehicle.id)
                       ] = fn.get_resource_blocks(vs['service'])

    def solve_knapsack(self, u, i, j, feasible_connected_vehicles):
        n = len(u)
        solver = OptimizationSolver()
        # Solving KP1
        weights = [self.b[(i, k)] for k in feasible_connected_vehicles]
        capacity = self.fog_nodes[i].capacity
        values = [u[idx]-self.b[(i, k)]
                  for idx, k in enumerate(feasible_connected_vehicles)]
        n_kp1 = solver.solve(weights, values, capacity)
        # Solving KP2
        weights = [self.b[(j, k)] for k in feasible_connected_vehicles]
        capacity = self.fog_nodes[j].capacity
        values = []
        for k in range(n):
            v = feasible_connected_vehicles[k]
            if k in n_kp1:
                values.append(self.b[(j, v)] - self.b[(j, v)])
            else:
                values.append(u[k] - self.b[(j, v)])
        n_kp2 = solver.solve(weights, values, capacity)
        n_kp1 = n_kp1.difference(n_kp2)
        x = {}
        for k in n_kp1:
            x.insert((i, k))
        for k in n_kp2:
            x.insert((j, k))
        return x

    def get_x(self, i, n):
        return 1 if (i, n) in self.x else 0

    def get_gradient(self, i, j, feasible_connected_vehicles):
        """Returns the gradients having length of feasible connected vehicles"""
        return [1+get_x(i, k)+get_x(j, k) for k in feasible_connected_vehicles]

    def step(self):
        self.compute_resource_blocks()
        # X_ij denotes whether ith fog node is connected jth vehicle
        self.x = {}
        for fn in self.fog_nodes:
            for v in self.vehicles:
                if self.is_associated(fn.id, v.id):
                    self.x.insert((fn.id, v.id))

        for i in range(len(self.fog_nodes)):
            for j in range(i+1, len(self.fog_nodes)):
                feasible_connected_vehicles = self.get_feasible_connected_vehicles(
                    i, j)
                u = [0]*len(feasible_connected_vehicles)
                du = self.get_gradient(
                    self.x, i, j, feasible_connected_vehicles)
                while not np.linalg.norm(du) <= self.EPS:
                    new_x = self.solve_knapsack(
                        u, i, j, feasible_connected_vehicles)
                    u = u + self.GAMMA * \
                        self.get_gradient(
                            new_x, i, j, feasible_connected_vehicles)
                new_u = u
