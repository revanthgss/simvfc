from simpy.resources.container import Container
from simpy import Interrupt
from simpy
import math
from .utils import distance


class Node:
    '''A node class that is used to create static nodes in a cloud network'''

    def __init__(self, idx, env, coverage_radius, bandwidth, capacity=100, position=(0, 0)):
        self.id = idx
        self.env = env
        self.coverage_radius = coverage_radius
        self.bandwidth = bandwidth
        self.sigma = 1
        # TODO: Calculate capacity from bandwidth
        self.resource_container = Container(
            env, capacity=capacity, init=capacity)
        self.position = position
        self._vehicle_services = {}
        self.in_service = False

    def set_position(self, x, y):
        """Sets the position of a fog node"""
        self.position = (x, y)

    def _get_channel_gain(self, vehicle):
        return 10**(-12.8)/distance(self.position, vehicle.position)**3.7

    def _get_sinr(self, vehicle):
        """
        Returns the signal to interference plus noise ratio 
        between the given vehicle and fog node
        """
        signal = self._get_channel_gain(vehicle)
        noise = self.sigma**2
        interference = 0
        for service_id, obj in self._vehicle_services:
            interference += self._get_channel_gain(obj["service"].vehicle)
        return signal/(noise + interference)

    def _serve_vehicle(self, env, service):
        """Allots some resources to vehicles"""
        while service.id in self._vehicle_services.keys():
            try:
                # Calculate required resources at that time
                required_resource_blocks = service.desired_data_rate / \
                    (self.bandwidth*math.log2(1+self._get_sinr(service.vehicle)))
                # Allot resources to that vehicle
                yield self.resource_container.get(required_resource_blocks)
                print(
                    f'{required_resource_blocks} resources allotted to vehicle {service.vehicle.id}')
                # Serve that vehicle for 1 second
                yield env.timeout(1)
            except Interrupt as i:
                print(
                    f'Service {service.id} of vehicle {service.vehicle.id} at fog node {self.id} got interrupted')
                self.remove_service(service.id)
            finally:
                # Free resources from that vehicle
                yield self.resource_container.put(required_resource_blocks)

    def add_service(self, service):
        """Adds a vehicle process to provide services to it"""
        self.in_service = True
        self._vehicle_services[service.id] = {
            "service": service,
            "process": self.env.process(
                self._serve_vehicle(self.env, service))
        }

    def remove_service(self, service_id):
        _ = self._vehicle_services.pop(service_id)
