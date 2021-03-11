import random
from gym import Env, spaces
from gym.utils import seeding
import numpy as np
from constants import CACHE_CONTENT_TYPES, TIME_MULTIPLIER
from utils import distance
from simulation import Simulation

FEASIBILITY_PENALTY = 10000
CAPACITY_PENALTY = 5000
# Weights are determined by the ranges of the values
POWER_CONSUMPTION_WEIGHT = 1
RESOURCE_REDUCTION_WEIGHT = 10


class VehicularFogEnv(Env):

    def __init__(self):
        super().__init__()
        self._current_service_id = None
        self.sim_instance = Simulation()
        # Actions determine to which fog node we need to migrate the service
        n_actions = len(self.sim_instance.fog_nodes)
        self.action_space = spaces.Discrete(n_actions)
        self.observation_space = spaces.Dict({
            "power_consumed": spaces.Box(0, np.inf, dtype='float32'),
            "occupied_resource_blocks": spaces.Box(0, np.inf, dtype='float32'),
            "content_type": spaces.MultiBinary(CACHE_CONTENT_TYPES),
            "cache_matrix": spaces.MultiBinary([n_actions, CACHE_CONTENT_TYPES])
            # TODO RL: Add capacities of fog nodes
            # TODO RL: If no convergence, test by providing feasible nodes heuristic
        })
        time = self.sim_instance.env.now
        # Process all the events until next time
        while self.sim_instance.env.now-time >= TIME_MULTIPLIER:
            self.sim_instance.env.step()

    def step(self, action, service_id):
        self._current_service_id = service_id
        service = self.sim_instance.service[service_id]
        current_observation = self.get_observation(service)
        curr_fog_node = self.sim_instance.get_service_node_mapping
        next_fog_node = self.sim_instance.fog_nodes[action]
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
                reward = POWER_CONSUMPTION_WEIGHT*(current_observation['power_consumed']-new_observation['power_consumed']) + RESOURCE_REDUCTION_WEIGHT*(
                    current_observation['occupied_resource_blocks']-new_observation['occupied_resource_blocks'])
        else:
            reward = 0
        done = service_id >= self.config["total_service_connections"]
        return new_observation, reward, done, {}

    def reset(self):
        self.sim_instance = Simulation()

    def render(self):
        pass

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        random.seed(seed)
        return [seed]


# TODO RL: Don't forget to manually run the step method in simpy env to simulate online RL training with episodes
