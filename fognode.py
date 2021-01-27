from simpy.resources import container
import math


class Node:
    '''A node class that is used to create static nodes in a cloud network'''

    def __init__(self, env, coverage_radius, bandwidth, capacity=100, position=(0, 0)):
        self.env = env
        self.coverage_radius = coverage_radius
        self.bandwidth = bandwidth
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

    def _serve_vehicle(self, env, service, time):
        """Allots some resources to vehicles"""
        # TODO: Implement an interrupt here to enable vehicle for reallocation and make vehicle's allotted fog node as none
        # TODO: Calculate service time from the distribution of arrival rate and departure rate
        for t in range(time):
            # Calculate required resources at that time
            required_resource_blocks = service.desired_data_rate / \
                (self.bandwidth*math.log2(1+self._get_sinr(service.vehicle)))
            # Allot resources to that vehicle
            yield self.resource_container.get(required_resource_blocks)
            print(
                f'{required_resource_blocks} resources allotted to vehicle {service.vehicle.id}')
            # Serve that vehicle for 1 second
            yield env.timeout(1)
            # Free resources from that vehicle
            yield self.resource_container.put(required_resource_blocks)

    def add_vehicle(self, service, time):
        """Adds a vehicle process to provide services to it"""
        self._vehicle_services[service.id] = {
            "service": service,
            "process": self.env.process(
                self._serve_vehicle(self.env, service, time))
        }
