class Vehicle:
    """Vehicle class to simulate driving vehicles in environment"""

    def __init__(self, vehicle_id, env, desired_data_rate, mobility_model):
        self.env = env
        self.id = vehicle_id
        self.desired_data_rate = desired_data_rate
        self.driving_process = self.env.process(self._drive(env))
        self.mobility_model = mobility_model
        self._position = None

    def set_position(self, x, y):
        self._position = (x, y)

    def get_position(self):
        return self._position
