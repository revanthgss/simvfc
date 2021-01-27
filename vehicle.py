import random


class Service:

    def __init__(self, vehicle, service_id, desired_data_rate):
        self.vehicle = vehicle
        self.id = service_id
        self.desired_data_rate = desired_data_rate


class Vehicle:
    """Vehicle class to simulate driving vehicles in environment"""

    def __init__(self, vehicle_id, env, service_store, desired_data_rate):
        self.id = vehicle_id
        self.desired_data_rate = desired_data_rate
        self.driving_process = env.process(self._drive(env))
        env.process(self._gen_services(env))
        self.mobility_model = None
        self._position = None
        self.allotted_fog_node = None
        self.service_store = service_store

    def get_position(self):
        return self._position

    def set_mobility_model(self, mobility_model):
        self.mobility_model = mobility_model

    def _drive(self, env):
        for position in self.mobility_model.positions(self):
            self._position = position
            print(f'Vehicle {self.id} is at {self._position}')
            yield env.timeout(1)

    def _gen_services(self, env):
        idx = 1
        while True:
            yield self.service_store.put(Service(self, idx, random.uniform(*desired_data_rate)))
            yield env.timeout(5)
            idx += 1
