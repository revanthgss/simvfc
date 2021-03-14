import random
from gym import Env, spaces
from gym.utils import seeding
from gym.spaces import flatten
import numpy as np
from constants import CACHE_CONTENT_TYPES, TIME_MULTIPLIER, TRANSMIT_POWER_FN2CLOUD
from utils import distance, find_feasible_fog_nodes
from simulation import Simulation
from itertools import chain

FEASIBILITY_PENALTY = 0
CAPACITY_PENALTY = 0
# Weights are determined by the ranges of the values
POWER_CONSUMPTION_WEIGHT = 0.5
RESOURCE_REDUCTION_WEIGHT = 0.5


class VehicularFogEnv(Env):

    def __init__(self):
        super().__init__()
        self._current_service_id = None
        self.sim_instance = Simulation()
        # Actions determine to which fog node we need to migrate the service
        self.n_actions = len(self.sim_instance.fog_nodes)
        self.action_space = spaces.Discrete(self.n_actions)
        # Power_consumed, resource_blocks, content_vector of service, cache matrix,feasibility vector, available capacity vector
        low = [0, 0] + [0]*CACHE_CONTENT_TYPES + \
            [0]*self.n_actions*CACHE_CONTENT_TYPES + \
            [0]*self.n_actions + [0]*self.n_actions
        high = [1, 1] + [1]*CACHE_CONTENT_TYPES + \
            [1]*self.n_actions*CACHE_CONTENT_TYPES + \
            [1]*self.n_actions + [1]*self.n_actions
        self.observation_space = spaces.Box(low=np.array(
            low), high=np.array(high), dtype=np.float32)
        time = self.sim_instance.env.now
        # Process all the events until next time
        while self.sim_instance.env.now-time >= TIME_MULTIPLIER:
            self.sim_instance.env.step()

    def get_observation(self, service):
        curr_fog_node = self.sim_instance.get_service_node_mapping(service)
        content_types = [0]*CACHE_CONTENT_TYPES
        content_types[service.content_type] = 1
        feasible_fog_nodes = find_feasible_fog_nodes(
            self.sim_instance.fog_nodes, service.vehicle)
        fog_nodes = [0]*self.n_actions
        for fn in feasible_fog_nodes:
            fog_nodes[fn.id] = 1
        levels = [fn.resource_container.level for fn in self.sim_instance.fog_nodes]
        mn, mx = min(levels), max(levels)
        for i, l in enumerate(levels):
            levels[i] = (l-mn)/(mx-mn)
        obs = [service.curr_power_consumed/TRANSMIT_POWER_FN2CLOUD, curr_fog_node.get_resource_blocks(
            service)/curr_fog_node.capacity] + content_types + list(chain.from_iterable(fn.cache_array for fn in self.sim_instance.fog_nodes)) + fog_nodes + levels
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
            if distance(curr_fog_node.position, service.vehicle.get_position()) < curr_fog_node.coverage_radius:
                reward = - FEASIBILITY_PENALTY
            elif next_fog_node.resource_container.level < next_fog_node.get_resource_blocks(service):
                reward = - CAPACITY_PENALTY
            else:
                # TODO RL: If not possible to get observation after migrate, compute it before and then migrate
                self.sim_instance.orchestration_module.migrate(
                    curr_fog_node.id, action, service.vehicle.id)
                new_observation = self.get_observation(service)
                reward = POWER_CONSUMPTION_WEIGHT*(current_observation[0]-new_observation[0]) + RESOURCE_REDUCTION_WEIGHT*(
                    current_observation[1]-new_observation[1])
        else:
            reward = 0
        done = service_id >= self.sim_instance.config["total_service_connections"]-1
        return new_observation, reward, done, {}

    def reset(self):
        self.sim_instance = Simulation()
        return self.observation_space.sample()

    def render(self):
        pass

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        random.seed(seed)
        return [seed]


# TODO RL: Don't forget to manually run the step method in simpy env to simulate online RL training with episodes
