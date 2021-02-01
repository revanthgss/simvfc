from simpy.resources.container import Container
from simpy import Interrupt
import math
from utils import distance
import numpy as np


class Node:
    '''A node class that is used to create static nodes in a cloud network'''

    BADNWIDTH_CAPACITY_MAPPING = {
        '10': 50*1000,
        '15': 75*1000,
        '20': 100*1000
    }

    def __init__(self, idx, env, coverage_radius, bandwidth):
        self.id = idx
        self.env = env
        self.coverage_radius = coverage_radius
        self.bandwidth = bandwidth
        self.sigma = 0.05
        capacity = Node.BADNWIDTH_CAPACITY_MAPPING[str(bandwidth)]
        self.resource_container = Container(
            env, capacity=capacity, init=capacity)
        self._vehicle_services = {}
        self.in_service = False

    def set_position(self, x, y):
        """Sets the position of a fog node"""
        self.position = (x, y)

    def _get_channel_gain(self, vehicle):
        return abs(np.random.rayleigh())**2/distance(self.position, vehicle.get_position())**3.7

    def _get_sinr(self, vehicle):
        """
        Returns the signal to interference plus noise ratio 
        between the given vehicle and fog node
        """
        signal = 1000*self._get_channel_gain(vehicle)
        noise = self.sigma**2
        interference = 0
        for service_id, obj in self._vehicle_services.items():
            if vehicle.id != obj["service"].vehicle.id:
                interference += 1000 * \
                    self._get_channel_gain(obj["service"].vehicle)
        return signal/(noise + interference)

    def _serve_vehicle(self, env, service):
        """Allots some resources to vehicles"""
        required_resource_blocks = int(service.desired_data_rate*1000 /
                                       (180*math.log2(1+self._get_sinr(service.vehicle))))
        # print(required_resource_blocks)
        # Allot resources to that vehicle
        try:
            yield self.resource_container.get(required_resource_blocks)
            while service.id in list(self._vehicle_services.keys()):
                # print(f'FogNode {self.id} -- {self.resource_container.level}')
                yield env.timeout(1)
        except Interrupt as i:
            # print(
            #     f'Service {service.id} of vehicle {service.vehicle.id} at fog node {self.id} got interrupted.')
            pass
        # Free resources from that vehicle
        yield self.resource_container.put(required_resource_blocks)

    def add_service(self, service):
        """Adds a vehicle process to provide services to it"""
        print(
            f"Service {service.id} is assigned to fog node {self.id}")
        self.in_service = True
        self._vehicle_services[service.id] = {
            "service": service,
            "process": self.env.process(
                self._serve_vehicle(self.env, service))
        }

    def remove_service(self, service_id):
        self._vehicle_services[service_id]["process"].interrupt(
            'Stopped service')
        _ = self._vehicle_services.pop(service_id)
