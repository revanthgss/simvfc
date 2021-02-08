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
        self.capacity = Node.BADNWIDTH_CAPACITY_MAPPING[str(bandwidth)]
        self.resource_container = Container(
            env, capacity=self.capacity, init=self.capacity)
        self._vehicle_services = {}
        self.in_service = False

    def set_position(self, x, y):
        """Sets the position of a fog node"""
        self.position = (x, y)

    def _get_channel_gain(self, vehicle):
        return 1/distance(self.position, vehicle.get_position())**3.7

    def _get_sinr(self, vehicle):
        """
        Returns the signal to interference plus noise ratio 
        between the given vehicle and fog node
        """
        signal = 1000*self._get_channel_gain(vehicle)
        noise = self.sigma**2
        interference = 0
        for vehicle_id, obj in self._vehicle_services.items():
            if vehicle.id != obj["service"].vehicle.id:
                interference += 500 * \
                    self._get_channel_gain(obj["service"].vehicle)
        # print(f'sinr={10*math.log10(signal/(noise+interference))}')
        return signal/(noise + interference)

    def get_resource_blocks(self, service):
        return int(service.desired_data_rate*1000 /
                   (180*math.log2(1+self._get_sinr(service.vehicle))))

    def _serve_vehicle(self, env, service):
        """Allots some resources to vehicles"""
        required_resource_blocks = self.get_resource_blocks(service)
        self._vehicle_services[service.vehicle.id]['resource_blocks'] = required_resource_blocks
        # print(required_resource_blocks)
        # Allot resources to that vehicle
        try:
            yield self.resource_container.get(required_resource_blocks)
            while service.vehicle.id in list(self._vehicle_services.keys()):
                # print(f'FogNode {self.id} -- {self.resource_container.level}')
                yield env.timeout(1)
        except Interrupt as i:
            # print(
            #     f'Service {service.id} of vehicle {service.vehicle.id} at fog node {self.id} got interrupted.')
            pass
        # Free resources from that vehicle
        yield self.resource_container.put(required_resource_blocks)

    def get_vehicle_services(self):
        return self._vehicle_services

    def get_service(self, service_id):
        for vehicle_service in self.get_vehicle_services().values():
            service = vehicle_service['service']
            if service.id == service_id:
                return service

    def add_service(self, service):
        """Adds a vehicle process to provide services to it"""
        print(
            f"Service {service.id} is assigned to fog node {self.id}")
        self.in_service = True
        self._vehicle_services[service.vehicle.id] = {
            "service": service,
            "process": self.env.process(
                self._serve_vehicle(self.env, service))
        }

    def remove_service(self, service):
        self._vehicle_services[service.vehicle.id]["process"].interrupt(
            'Stopped service')
        _ = self._vehicle_services.pop(service.vehicle.id)
