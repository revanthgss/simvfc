from simpy.core import Environment
from simpy.rt import RealtimeEnvironment
from simpy.events import Event
from simpy.resources.store import Store
from fognode import Node
from vehicle import Service
from topology import Topology
from mobility_model import DynamicMobilityModel
from policy import SignalAwareAllocationPolicy, CapacityAwareAllocationPolicy
from orchestration import DynamicResourceOrchestrationModule
import json
import random


class Simulation:

    def __init__(self, config='./config.json'):
        self.env = RealtimeEnvironment(strict=False)
        self.stop_simulation_event = Event(self.env)
        # Initialise config
        with open(config) as f:
            self.config = json.load(f)
        self.mobility_model = DynamicMobilityModel(
            '../dataset/trajectory.csv', self.config)
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
        if self.config.get('orchestration_scheme', None):
            self.env.process(self._orchestrate_services(self.env))

    def _init_fog_nodes(self):
        self.fog_nodes = [
            Node(
                idx,
                self.env,
                random.randint(*self.config["fn_coverage_radius"]),
                random.choice(self.config["fn_bandwidth"]),
            ) for idx in range(self.config["num_fn"])
        ]
        area = self.config["network_area"]
        Topology(self.config["topology_origin"], area[0],
                 area[1]).assign_positions(self.fog_nodes)

    def _update_vehicles(self, env):
        frame_id = 150
        while True:
            self.mobility_model.update_vehicles(env, frame_id)
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
            service_arrivals = self.mean_arrival_rate
            service_departures = self.mean_departure_rate
            for _ in range(service_arrivals):
                # possible_vehicles = list(filter(
                #     lambda v: v.allotted_fog_node is None, self.mobility_model.vehicles.values()))
                # if len(possible_vehicles) != 0:
                vehicles = list(self.mobility_model.vehicles.values())
                if len(vehicles) != 0:
                    service = Service(
                        random.choice(vehicles),
                        self.total_services,
                        random.uniform(*self.config["desired_data_rate"])
                    )
                    allotted_node = self.allocation_policy.allocate(service)
                    self._service_node_mapping[service.id] = allotted_node
                    self.total_services += 1
            yield env.timeout(1)
            for _ in range(service_departures):
                if len(self._service_node_mapping.keys()) != 0:
                    service_id = random.choice(
                        list(self._service_node_mapping.keys()))
                    self._service_node_mapping[service_id].remove_service(
                        service_id)
                    _ = self._service_node_mapping.pop(service_id)
        print(
            f'Stopping simulation as {self.total_services} services are served')
        self.stop_simulation_event.succeed()

    def _orchestrate_services(self, env):
        """Orchestrate services periodically"""
        if self.config["orchestration_scheme"] == 'dro':
            self.orchestration_module = DynamicResourceOrchestrationModule(
                self.fog_nodes, self.mobility_model.vehicles)

        while True:
            self.orchestration_module.step()
            yield env.timeout(2)

    def run(self):
        self.env.run(until=self.stop_simulation_event)


# Run simulation
Simulation().run()
