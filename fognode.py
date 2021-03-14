from simpy.resources.container import Container
from simpy import Interrupt
import math
from utils import distance
import numpy as np
from constants import TIME_MULTIPLIER, TRANSMIT_POWER_FN2VEHICLE, TRANSMIT_POWER_FN2CLOUD


class Node:
    '''A node class that is used to create static nodes in a cloud network'''

    BADNWIDTH_CAPACITY_MAPPING = {
        '10': 50*100,
        '15': 75*100,
        '20': 100*100
    }

    def __init__(self, idx, env, coverage_radius, bandwidth, cache_array):
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
        self.cache_array = cache_array
        self.overall_throughput = 0
        self.incoming_services = 0
        self.services_served = 0
        self.energy_consumed = 0

    def set_position(self, x, y):
        """Sets the position of a fog node"""
        self.position = (x, y)

    def get_serviceability_metrics(self):
        return (self.services_served, self.incoming_services)

    def _get_channel_gain(self, vehicle):
        return 1/distance(self.position, vehicle.get_position())**3.5

    def _get_sinr(self, vehicle):
        """
        Returns the signal to interference plus noise ratio
        between the given vehicle and fog node
        """
        # TODO: figure out whether transmit power is 1 kW
        signal = TRANSMIT_POWER_FN2VEHICLE*self._get_channel_gain(vehicle)
        noise = self.sigma**2
        interference = 0
        for vehicle_id, obj in self._vehicle_services.items():
            if vehicle.id != obj["service"].vehicle.id:
                interference += 0.5 * TRANSMIT_POWER_FN2VEHICLE *\
                    self._get_channel_gain(obj["service"].vehicle)
        # print(f'sinr={10*math.log10(signal/(noise+interference))}')
        return signal/(noise + interference)

    def get_throughput(self, service):
        return self.bandwidth*self._get_sinr(service.vehicle)

    def get_resource_blocks(self, service):
        # TODO: return the resource blocks if sinr value is optimal
        # otherwise return the capacity so that service is rejected
        sinr = self._get_sinr(service.vehicle)
        spectral_efficiency = math.log2(1+sinr)
        if spectral_efficiency == 0:
            return self.capacity
        return int(service.desired_data_rate * 1000 /
                   (180*math.log2(1+self._get_sinr(
                    service.vehicle))))

    def _serve_vehicle(self, env, service, migrated=False):
        """Allots some resources to vehicles"""
        # Minimum resource blocks is 1
        required_resource_blocks = max(1, self.get_resource_blocks(service))
        if not service.vehicle.id in self._vehicle_services:
            # Then it means service has been migrated before even allotting resource blocks
            return
        self._vehicle_services[service.vehicle.id]['resource_blocks'] = required_resource_blocks
        # Allot resources to that vehicle
        start = env.now
        try:
            # if migrated:
            #     assert(required_resource_blocks <=
            #            self.resource_container.level)
            if required_resource_blocks <= self.resource_container.level:
                if not migrated:
                    self.services_served += 1
            else:
                _ = self._vehicle_services.pop(service.vehicle.id)
                service.vehicle.allotted_fog_node = None
                return
            yield self.resource_container.get(required_resource_blocks)
            while service.vehicle.id in list(self._vehicle_services.keys()):
                # For every second add the energy consumed
                self.energy_consumed += service.curr_power_consumed
                yield env.timeout(TIME_MULTIPLIER)
        except Interrupt as i:
            # print(
            #     f'Service {service.id} of vehicle {service.vehicle.id} at fog node {self.id} got interrupted.')
            pass
        # Free resources from that vehicle
        self.overall_throughput += self.get_throughput(service)
        yield self.resource_container.put(required_resource_blocks)

    def get_vehicle_services(self):
        return self._vehicle_services

    def get_service(self, service_id):
        for vehicle_service in self.get_vehicle_services().values():
            service = vehicle_service['service']
            if service.id == service_id:
                return service

    def add_service(self, service, migrated=False):
        """Adds a vehicle process to provide services to it"""
        if not migrated:
            self.incoming_services += 1
        service.vehicle.allotted_fog_node = self
        # print(
        #     f"Service {service.id} is assigned to fog node {self.id}")
        self.in_service = True
        service.curr_power_consumed = TRANSMIT_POWER_FN2VEHICLE if self.cache_array[
            service.content_type] else TRANSMIT_POWER_FN2CLOUD
        self._vehicle_services[service.vehicle.id] = {
            "service": service,
            "process": self.env.process(
                self._serve_vehicle(self.env, service, migrated))
        }

    def remove_service(self, service):
        # print(f"Service {service.id} is removed")
        if service is not None:
            service.vehicle.allotted_fog_node = None
            self._vehicle_services[service.vehicle.id]["process"].interrupt(
                'Stopped service')
            _ = self._vehicle_services.pop(service.vehicle.id)
