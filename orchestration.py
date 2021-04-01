from utils import find_vehicles
import numpy as np
from vehicle import Service
import math
import pandas as pd
from optimization_solver import OptimizationSolver
from stable_baselines import PPO2, A2C
from kp_env import KPEnv


class OrchestrationModule:

    def __init__(self, simulation_instance, gamma=1000):
        self.simulation_instance = simulation_instance
        self.fog_nodes = self.simulation_instance.fog_nodes
        self.GAMMA = gamma

    def migrate(self, i, j, vehicle_id):
        """Migrates all the service that are required from fog node i to fog node j"""
        services = [item['service']
                    for item in self.fog_nodes[i].get_vehicle_services().values()]
        for service in services:
            if service.vehicle.id == vehicle_id:
                print(
                    f'Migrating service {service.id} of vehicle {vehicle_id} from fog node {i} to fog node {j}')
                self.fog_nodes[i].remove_service(service)
                self.fog_nodes[j].add_service(service, migrated=True)
                self.simulation_instance.set_service_node_mapping(
                    service, self.fog_nodes[j])

    def step(self):
        raise NotImplementedError


class DynamicResourceOrchestrationModule(OrchestrationModule):

    def __init__(self, simulation_instance, gamma=1000):
        self.array = []
        super().__init__(simulation_instance, gamma)

    def get_feasible_connected_vehicles(self, i, j):
        """Returns the ids of connected vehicles that are possible for service migration"""
        # Feasible connected vehicles for service migrations from i to j
        # key -> (i,j), value: [list of vehicles]
        di = set(self.fog_nodes[i].get_vehicle_services().keys())
        dj = set(self.fog_nodes[j].get_vehicle_services().keys())
        self.D[i] = di
        self.D[j] = dj
        di_cov = {v.id for v in find_vehicles(
            self.vehicles, self.fog_nodes[i])}
        dj_cov = {v.id for v in find_vehicles(
            self.vehicles, self.fog_nodes[j])}
        dij_cov = di_cov.intersection(dj_cov)
        res = (di.union(dj)).intersection(dij_cov)
        return res

    def is_associated(self, i, j):
        """Returns if jth vehicle is associated with ith fog node"""
        return j in self.fog_nodes[i].get_vehicle_services().keys()

    def compute_resource_blocks(self):
        # b[(i,j)] denotes number of resource blocks assigned by fog node i to vehicle j
        self.b = {}
        self.vehicle_services = {}
        for fn in self.fog_nodes:
            self.vehicle_services.update(fn.get_vehicle_services())
        serving_vehicles = []
        for vehicle in self.vehicles:
            if vehicle.id in self.vehicle_services.keys():
                serving_vehicles.append(vehicle)

        for fn in self.fog_nodes:
            for vehicle in find_vehicles(serving_vehicles, fn):
                self.b[(fn.id, vehicle.id)
                       ] = fn.get_resource_blocks(self.vehicle_services[vehicle.id]['service'])

    def solve_knapsack(self, u, i, j, feasible_connected_vehicles):
        n = len(u)
        solver = OptimizationSolver()
        vehicle_list = list(feasible_connected_vehicles)
        # Solving KP1
        weights = [self.b[(i, k)] for k in vehicle_list]
        di_fea = self.D[i].intersection(feasible_connected_vehicles)
        capacity = self.fog_nodes[i].resource_container.level + \
            sum([self.b[(i, k)] for k in di_fea])
        values = [u[idx]-self.b[(i, k)]
                  for idx, k in enumerate(vehicle_list)]
        n_kp1 = {vehicle_list[idx]
                 for idx in solver.solve(weights, values, capacity)}
        # Solving KP2
        weights = [self.b[(j, k)] for k in vehicle_list]
        dj_fea = self.D[j].intersection(feasible_connected_vehicles)
        capacity = self.fog_nodes[j].resource_container.level + \
            sum([self.b[(j, k)] for k in dj_fea])
        values = []
        for idx, vid in enumerate(vehicle_list):
            if vid in n_kp1:
                values.append(self.b[(i, vid)] - self.b[(j, vid)])
            else:
                values.append(u[idx] - self.b[(j, vid)])
        n_kp2 = {vehicle_list[idx]
                 for idx in solver.solve(weights, values, capacity)}
        n_kp1 = n_kp1.difference(n_kp2)
        x = set()
        for k in n_kp1:
            x.add((i, k))
        for k in n_kp2:
            x.add((j, k))

        return x

    def get_x(self, x, i, n):
        return 1 if (i, n) in x else 0

    def get_D_star(self, i, new_x):
        """Returns all the vehicle id's associated with fog node i with new allocation vector new_x"""
        di_star = set()
        for fn_id, v_id in new_x:
            if fn_id == i:
                di_star.add(v_id)

        return di_star

    def get_gradient(self, x, i, j, feasible_connected_vehicles):
        """Returns the gradients having length of feasible connected vehicles"""
        return [1+self.get_x(x, i, k)+self.get_x(x, j, k) for k in feasible_connected_vehicles]

    def get_weight(self, i, j, feasible_connected_vehicles):
        """Returns the amount of optimal resource migration of the edge between fog node i and fog node j"""
        di_fea = self.D[i].intersection(feasible_connected_vehicles)
        dj_fea = self.D[j].intersection(feasible_connected_vehicles)
        di_star_fea = self.D_star[i].intersection(feasible_connected_vehicles)
        dj_star_fea = self.D_star[j].intersection(feasible_connected_vehicles)
        # assert(di_fea.union(dj_fea) == di_star_fea.union(dj_star_fea))
        oij = sum([self.b[(i, k)] for k in di_fea]) + \
            sum([self.b[(j, k)] for k in dj_fea])
        oij_star = sum([self.b[(i, k)] for k in di_star_fea]) + \
            sum([self.b[(j, k)] for k in dj_star_fea])
        return (oij - oij_star)

    def compute_heuristic(self, i, j, feasible_connected_vehicles):
        u = [0]*len(feasible_connected_vehicles)
        new_x = None
        patience = 1000000/self.GAMMA
        eps = 2*math.sqrt(len(feasible_connected_vehicles))
        gamma = self.GAMMA
        old_du = 0
        while patience >= 0:
            new_x = self.solve_knapsack(
                u, i, j, feasible_connected_vehicles)
            du = self.get_gradient(
                new_x, i, j, feasible_connected_vehicles)
            for k in range(len(u)):
                u[k] = u[k] + gamma * du[k]
            if old_du == du:
                patience -= 1
            else:
                patience = 1000000/gamma
            if np.linalg.norm(du) >= eps:
                break
            old_du = du
        if new_x is not None and len(new_x) != 0:
            # for k in feasible_connected_vehicles:
            #     if not (i, k) in new_x and not (j, k) in new_x:
            #         if (i, k) in self.x:
            #             new_x.add((i, k))
            #         else:
            #             new_x.add((j, k))
            self.D_star[i] = self.get_D_star(i, new_x)
            self.D_star[j] = self.get_D_star(j, new_x)
            self.d_star[(i, j)] = (self.D[i].intersection(
                feasible_connected_vehicles)).difference(self.D_star[i])
            self.d_star[(j, i)] = (self.D[j].intersection(
                feasible_connected_vehicles)).difference(self.D_star[j])
            # self.d_star[(i, j)] = self.D[i].difference(self.D_star[i])
            # self.d_star[(j, i)] = self.D[j].difference(self.D_star[j])
            self.W[(i, j)] = self.get_weight(
                i, j, feasible_connected_vehicles)

    def get_optimal_pairs(self):
        """Performs maximum weight matching on fog node graph to get the optimal pairs of fog nodes for service migration"""
        phi = set()
        while self.W:
            edge = max(self.W, key=self.W.get)
            phi.add(edge)
            new_W = {}
            for key in self.W.keys():
                if not(edge[0] in key or edge[1] in key):
                    new_W[key] = self.W[key]
            self.W = new_W
        return phi

    def step(self):
        self.vehicles = self.simulation_instance.mobility_model.vehicles.values()
        self.D = {}
        self.D_star = {}
        self.d_star = {}
        self.W = {}
        self.compute_resource_blocks()
        # X_ij denotes whether ith fog node is connected jth vehicle
        self.x = set()
        for fn in self.fog_nodes:
            for v in self.vehicles:
                if self.is_associated(fn.id, v.id):
                    self.x.add((fn.id, v.id))

        for i in range(len(self.fog_nodes)):
            for j in range(i+1, len(self.fog_nodes)):
                feasible_connected_vehicles = self.get_feasible_connected_vehicles(
                    i, j)
                if feasible_connected_vehicles:
                    self.compute_heuristic(i, j, feasible_connected_vehicles)

        phi = self.get_optimal_pairs()

        for i, j in phi:
            for vehicle_id in self.d_star[(i, j)]:
                self.migrate(i, j, vehicle_id)
            for vehicle_id in self.d_star[(j, i)]:
                self.migrate(j, i, vehicle_id)


class RLOrchestrationModule(DynamicResourceOrchestrationModule):

    def __init__(self, simulation_instance, gamma=1000):
        super().__init__(simulation_instance)
        self.env = KPEnv()
        self.model = A2C.load("omsr_power_final_2")

    def compute_heuristic(self, i, j, feasible_connected_vehicles):
        # print("Here")
        veh = list(feasible_connected_vehicles)
        veh = veh[:self.env.N]
        feasible_connected_vehicles = set(veh)
        W = 100
        N = len(feasible_connected_vehicles)
        val1 = []
        w1 = []
        val2 = []
        w2 = []
        cache1 = []
        cache2 = []
        for v in feasible_connected_vehicles:
            # Get the content type of service
            sct = self.vehicle_services[v]['service'].content_type
            cache1.append(self.fog_nodes[i].cache_array[sct])
            cache2.append(self.fog_nodes[j].cache_array[sct])
        for v in feasible_connected_vehicles:
            val1.append(-int((self.b[(i, v)])/W))
            w1.append(int(self.b[(i, v)]/W))
            val2.append(-int((self.b[(j, v)])/W))
            w2.append(int(self.b[(j, v)]/W))
        # Solving KP1
        di_fea = self.D[i].intersection(feasible_connected_vehicles)
        c1 = self.fog_nodes[i].resource_container.level + \
            sum([self.b[(i, k)] for k in di_fea])
        # Solving KP2
        dj_fea = self.D[j].intersection(feasible_connected_vehicles)
        c2 = self.fog_nodes[j].resource_container.level + \
            sum([self.b[(j, k)] for k in dj_fea])
        sv1 = -sum(val1)
        sv2 = -sum(val2)
        sw1 = sum(w1)
        sw2 = sum(w2)
        sc1 = sum(cache1)
        sc2 = sum(cache2)
        vector = [N, int(c1/W), int(c2/W), sv1, sv2, sw1, sw2, sc1, sc2]
        for index in range(len(feasible_connected_vehicles)):
            vector.append(val1[index])
            vector.append(w1[index])
            vector.append(cache1[index])
            vector.append(val2[index])
            vector.append(w2[index])
            vector.append(cache2[index])
        while len(vector) < 6*self.env.N+9:
            vector = vector + [0, 0, 0, 0, 0, 0]
        self.env.vector = vector
        obs = vector
        new_x = set()
        # TODO RL: Order by occupied load to get better results
        # print(feasible_connected_vehicles)
        patience = 0
        while True:
            prev_obs = obs
            action, _states = self.model.predict(obs)
            # print(self.model.action_probability(obs))
            # print(action, obs[0])
            obs, rew, done, _ = self.env.step(action)
            # if patience >= 100:
            #     break
            if action[0] >= len(veh):
                patience += 1
                print(patience)
                continue
            # if action[0] != 0:
            #     print(action, prev_obs)
            patience = 0
            v = veh.pop(action[0])
            if rew >= 0:
                # Allot the predicted action
                if action[1] == 0:
                    new_x.add((i, v))
                else:
                    new_x.add((j, v))
            if done:
                # print("Done breaking")
                break
        # print(new_x)
        if new_x is not None and len(new_x) != 0:

            # for k in feasible_connected_vehicles:
            #     if not (i, k) in new_x and not (j, k) in new_x:
            #         if (i, k) in self.x:
            #             new_x.add((i, k))
            #         else:
            #             new_x.add((j, k))
            self.D_star[i] = self.get_D_star(i, new_x)
            self.D_star[j] = self.get_D_star(j, new_x)
            self.d_star[(i, j)] = (self.D[i].intersection(
                feasible_connected_vehicles)).difference(self.D_star[i])
            self.d_star[(j, i)] = (self.D[j].intersection(
                feasible_connected_vehicles)).difference(self.D_star[j])
            # self.d_star[(i, j)] = self.D[i].difference(self.D_star[i])
            # self.d_star[(j, i)] = self.D[j].difference(self.D_star[j])
            self.W[(i, j)] = self.get_weight(
                i, j, feasible_connected_vehicles)
