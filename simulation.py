from simpy.core import Environment
from simpy.events import Event
from simpy.resources.store import Store
from .fognode import Node
from .vehicle import Service
from .mobility_model import DynamicMobilityModel
from .policy import SignalAwareAllocationPolicy, CapacityAwareAllocationPolicy
import json
import random


class Simulation:

    def __init__(self, config='config.json'):
        self.env = Environment()
        self.stop_simulation_event = Event()
        # Initialise config
        with open(config) as f:
            self.config = json.load(f)
        self.mean_arrival_rate = self.config["mean_arrival_rate"]
        self.mean_departure_rate = self.config["mean_departure_rate"]
        self.env.process(self._monitor_services(self.env))
        self._service_node_mapping = {}
        # Initialise fog nodes
        self._init_fog_nodes()
        # Initialise update vehicles process
        self.env.process(self._update_vehicles(self.env))
        # Initialise policy
        self._init_policy()

    def _init_fog_nodes(self):
        # TODO: Add positions to fog nodes while initialising
        self.fog_nodes = [
            Node(
                idx,
                self.env,
                random.randint(*self.config["fn_coverage_radius"]),
                random.choice(self.config["fn_bandwidth"]),
            ) for idx in range(self.config["num_fn"])
        ]

    def _update_vehicles(self, env):
        frame_id = 1
        self.mobility_model = DynamicMobilityModel(
            '../datasets/trajectory.csv', self.config)
        while True:
            self.mobility_model.update_vehicles(frame_id)
            yield env.timeout(1)
            frame_id += 1

    def _init_policy(self):
        allocation_policy = self.config["allocation_policy"]
        if allocation_policy == 'signal_aware':
            self.allocation_policy = SignalAwareAllocationPolicy(
                self.fog_nodes)
        elif allocation_policy == 'capacity_aware':
            self.allocation_policy = CapacityAwareAllocationPolicy(
                self.fog_nodes)

    # TODO: While migrating services, follow below steps
    '''
    - remove the service from previous fog node
    - Add the service to the new fog node
    - Update the service node mapping to new fog node
    '''

    def _monitor_services(self, env):
        self.total_services = 0
        while self.total_services < self.config["total_service_connections"]:
            service_arrivals = random.uniform(0, 2*self.mean_arrival_rate)
            service_departures = random.uniform(0, 2*self.mean_departure_rate)
            for _ in range(service_arrivals):
                service = Service(
                    random.choice(self.mobility_model.vehicles),
                    self.total_services,
                    random.uniform(self.config["desired_data_rate"])
                )
                allotted_node = self.allocation_policy.allot(service)
                self._service_node_mapping[service.id] = allotted_node
                self.total_services += 1
            yield env.timeout(1)
            for _ in range(service_departures):
                service_id = random.choice(self._service_node_mapping.keys())
                self._service_node_mapping[service_id].remove_service(
                    service_id)
                _ = self._service_node_mapping.pop(service_id)
        yield self.stop_simulation_event

    def run(self):
        self.env.run(until=self.stop_simulation_event)
