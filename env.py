import random
from gym import Env, spaces
from gym.utils import seeding
from gym.spaces import flatten
import numpy as np
from constants import CACHE_CONTENT_TYPES, TIME_MULTIPLIER, TRANSMIT_POWER_FN2CLOUD, TRANSMIT_POWER_FN2VEHICLE
from utils import distance, find_feasible_fog_nodes
from simulation import Simulation
from itertools import chain
import math

FEASIBILITY_PENALTY = 5
CAPACITY_PENALTY = 5
# Weights are determined by the ranges of the values
POWER_CONSUMPTION_POS_WEIGHT = 20
POWER_CONSUMPTION_NEG_WEIGHT = 10
RESOURCE_REDUCTION_POS_WEIGHT = 0.1
RESOURCE_REDUCTION_NEG_WEIGHT = 0.005


class VehicularFogEnv(Env):

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._current_service_id = None
        if self.config is None:
            self.sim_instance = Simulation()
        else:
            self.sim_instance = Simulation(self.config)
        # Actions determine to which fog node we need to migrate the service
        self.n_actions = len(self.sim_instance.fog_nodes)
        self.action_space = spaces.Discrete(self.n_actions)
        # is content of service cached in curr fog node, resource_blocks, service_id, cache_vector of service,rb vector, available capacity vector
        low = [0, 0, 0] + \
            [0]*self.n_actions + \
            [0]*self.n_actions + [0]*self.n_actions
        high = [1, np.inf, np.inf] + \
            [1]*self.n_actions + \
            [10000]*self.n_actions + [1]*self.n_actions
        self.observation_space = spaces.Box(low=np.array(
            low), high=np.array(high), dtype=np.float32)
        time = self.sim_instance.env.now
        # Process all the events until next time
        while self.sim_instance.env.now-time >= TIME_MULTIPLIER:
            self.sim_instance.env.step()

    def get_observation(self, service):
        curr_fog_node = self.sim_instance.get_service_node_mapping(service)
        feasible_fog_nodes = find_feasible_fog_nodes(
            self.sim_instance.fog_nodes, service.vehicle)
        fog_nodes = [10000]*self.n_actions
        for fn in feasible_fog_nodes:
            fog_nodes[fn.id] = 0.1*fn.get_resource_blocks(service)
        fog_nodes[curr_fog_node.id] = 0.1*curr_fog_node.get_resource_blocks(
            service)
        levels = [fn.resource_container.level for fn in self.sim_instance.fog_nodes]
        mn, mx = min(levels), max(levels)
        for i, l in enumerate(levels):
            levels[i] = (l-mn)/(mx-mn)
        # print(curr_fog_node.get_resource_blocks(
        #     service), curr_fog_node.capacity, curr_fog_node.get_resource_blocks(
        #     service)/curr_fog_node.capacity)
        obs = [curr_fog_node.cache_array[service.content_type], 0.1*curr_fog_node.get_resource_blocks(
            service), service.id] + [fn.cache_array[service.content_type] for fn in self.sim_instance.fog_nodes] + fog_nodes + levels
        # print(obs)
        return np.asfarray(obs)

    def step(self, action, service_id):
        self._current_service_id = service_id
        service = self.sim_instance.services[service_id]
        current_observation = self.get_observation(service)
        curr_fog_node = self.sim_instance.get_service_node_mapping(service)
        next_fog_node = self.sim_instance.fog_nodes[action]
        new_observation = current_observation
        if curr_fog_node.id != action:
            # Check if its feasbile to migrate or not
            if distance(next_fog_node.position, service.vehicle.get_position()) > next_fog_node.coverage_radius:
                reward = - 5
            elif next_fog_node.get_resource_blocks(service) > next_fog_node.resource_container.level:
                reward = - 5
            else:
                pow_red = next_fog_node.cache_array[service.content_type] - \
                    curr_fog_node.cache_array[service.content_type]
                res_red = next_fog_node.get_resource_blocks(
                    service) - curr_fog_node.get_resource_blocks(service)
                # pow_red = current_observation[0] - new_observation[0]
                # res_red = current_observation[1] - new_observation[1]
                reward = 0
                if pow_red > 0:
                    # reward += POWER_CONSUMPTION_POS_WEIGHT*pow_red
                    reward += 5
                elif pow_red < 0:
                    # reward += POWER_CONSUMPTION_NEG_WEIGHT*pow_red
                    reward -= 5
                if res_red > 0:
                    reward += math.log(1+res_red)
                    # reward += 1
                elif res_red < 0:
                    reward -= math.log(1-res_red)
                    # reward -= 1
                # print(service_id, curr_fog_node.id,
                #       action, pow_red, res_red, reward)
                if reward > 0:
                    # print(reward)
                    self.sim_instance.orchestration_module.migrate(
                        curr_fog_node.id, action, service.vehicle.id)
                    new_observation = self.get_observation(service)
        else:
            reward = 0
        # if reward > 0:
        #     print('HURRAY!! -- ', reward)
        # else:
        #     print('OOPS -- ', reward)
        done = service_id >= self.sim_instance.config["total_service_connections"]-1
        if reward > 0:
            print('I am learning!!')
        return new_observation, reward, False, {'done': done}

    def reset(self):
        if self.config is None:
            config = random.choice(
                ['./configs/sa.json', './configs/caa.json', './configs/coa.json'])
            self.sim_instance = Simulation(config=config)
        else:
            self.sim_instance = Simulation(config=self.config)
        return self.observation_space.sample()

    def render(self):
        pass

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        random.seed(seed)
        return [seed]
