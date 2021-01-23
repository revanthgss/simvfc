from simpy.resources import container
import math


class Node:
    '''A node class that is used to create static nodes in a cloud network'''

    def __init__(self, env, coverage_radius, bandwidth, vehicle_arrival_rate, vehicle_departure_rate, capacity, position=(0, 0)):
        self.env = env
        self.coverage_radius = coverage_radius
        self.bandwidth = bandwidth
        self.vehicle_arrival_rate = vehicle_arrival_rate
        self.vehicle_departure_rate = vehicle_departure_rate
        self.resource_container = container.Container(
            env, capacity=capacity, init=capacity)
        self.position = position
        self._vehicle_services = {}

    def set_position(self, x, y):
        """Sets the position of a fog node"""
        self.position = (x, y)

    def _get_sinr(self, vehicle):
        """
        Returns the signal to interference plus noise ratio 
        between the given vehicle and fog node
        """
        # TODO: Add the formula for getting sinr here
        return 10

    def _serve_vehicle(self, env, vehicle, desired_data_rate, time):
        """Allots some resources to vehicles"""
        for t in range(time):
            # Calculate required resources at that time
            required_resource_blocks = desired_data_rate / \
                (self.bandwidth*math.log2(1+self._get_sinr(vehicle)))
            # Allot resources to that vehicle
            yield self.resource_container.get(required_resource_blocks)
            print(
                f'{required_resource_blocks} resources allotted to vehicle {vehicle.name}')
            # Serve that vehicle for 1 second
            yield env.timeout(1)
            # Free resources from that vehicle
            yield self.resource_container.put(required_resource_blocks)

    def add_vehicle(self, vehicle, desired_data_rate, time):
        """Adds a vehicle process to provide services to it"""
        self._vehicle_services[vehicle.name] = self.env.process(
            self._serve_vehicle(self.env, vehicle, desired_data_rate, time))
