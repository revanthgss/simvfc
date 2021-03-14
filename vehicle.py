import random
from constants import TIME_MULTIPLIER, CACHE_CONTENT_TYPES


class Service:

    def __init__(self, vehicle, service_id, desired_data_rate):
        self.vehicle = vehicle
        self.id = service_id
        self.desired_data_rate = desired_data_rate
        self.content_type = random.randint(0, CACHE_CONTENT_TYPES-1)
        self.curr_power_consumed = None


class Vehicle:
    """Vehicle class to simulate driving vehicles in environment"""

    def __init__(self, vehicle_id, env, desired_data_rate):
        self.id = vehicle_id
        self.driving_process = env.process(self._drive(env))
        self.mobility_model = None
        self._position = None
        self.allotted_fog_node = None
        self.in_network = True

    def get_position(self):
        return self._position

    def set_mobility_model(self, mobility_model):
        self.mobility_model = mobility_model

    def _drive(self, env):
        for position in self.mobility_model.positions(self):
            self._position = position
            # print(f'Vehicle {self.id} is at {self._position}')
            yield env.timeout(0.1*TIME_MULTIPLIER)
