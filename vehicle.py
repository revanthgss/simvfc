class Vehicle:
    """Vehicle class to simulate driving vehicles in environment"""

    def __init__(self, vehicle_id, env, desired_data_rate):
        self.id = vehicle_id
        self.desired_data_rate = desired_data_rate
        self.driving_process = env.process(self._drive(env))
        self.mobility_model = None
        self._position = None

    def get_position(self):
        return self._position

    def set_mobility_model(self, mobility_model):
        self.mobility_model = mobility_model

    def _drive(self, env):
        for position in self.mobility_model.positions():
            self._position = position
            print(f'{i} --> Vehicle {self.id} is at {self._position}')
            yield env.timeout(1)
