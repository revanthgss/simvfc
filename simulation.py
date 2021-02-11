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
from metrics import MetricFactory
import json
import random
from constants import TIME_MULTIPLIER


class Simulation:

    def __init__(self, config='./config.json'):
        self.env = Environment()
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
        if self.config.get('metrics', None):
            self.metrics = [MetricFactory(metric)
                            for metric in self.config['metrics']]
            self.env.process(self._compute_metrics(self.env))

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
        frame_id = 0
        while True:
            self.mobility_model.update_vehicles(env, frame_id)
            yield env.timeout(0.1*TIME_MULTIPLIER)
            frame_id += 1

    def _init_policy(self):
        allocation_policy = self.config["allocation_policy"]
        if allocation_policy == 'signal_aware':
            self.allocation_policy = SignalAwareAllocationPolicy(
                self.fog_nodes)
        elif allocation_policy == 'capacity_aware':
            self.allocation_policy = CapacityAwareAllocationPolicy(
                self.fog_nodes)

    def _compute_metrics(self, env):
        while True:
            for metric in self.metrics:
                metric.compute(self.fog_nodes)
            yield env.timeout(TIME_MULTIPLIER)

    def get_metrics(self):
        return {metric.name: metric.get_values() for metric in self.metrics}

    def _monitor_services(self, env):
        self.total_services = 0
        while self.total_services < self.config["total_service_connections"]:
            # print(self.total_services, len(self.mobility_model.vehicles.keys()))
            service_arrivals = self.mean_arrival_rate
            service_departures = self.mean_departure_rate
            for _ in range(service_arrivals):
                possible_vehicles = list(filter(
                    lambda v: v.allotted_fog_node is None, self.mobility_model.vehicles.values()))
                if len(possible_vehicles) != 0:
                    service = Service(
                        random.choice(possible_vehicles),
                        self.total_services,
                        random.uniform(*self.config["desired_data_rate"])
                    )
                    allotted_node = self.allocation_policy.allocate(service)
                    self._service_node_mapping[service.id] = allotted_node
                    self.total_services += 1
                    if self.total_services >= self.config["total_service_connections"]:
                        break
            yield env.timeout(TIME_MULTIPLIER)
            for _ in range(service_departures):
                if len(self._service_node_mapping.keys()) != 0:
                    service_id = random.choice(
                        list(self._service_node_mapping.keys()))
                    fn = self._service_node_mapping[service_id]
                    fn.remove_service(fn.get_service(service_id))
                    _ = self._service_node_mapping.pop(service_id)
        print(
            f'Stopping simulation as {self.total_services} services are served')
        # if hasattr(self, 'metrics'):
        #     print(self.get_metrics())
        self.stop_simulation_event.succeed()

    def set_service_node_mapping(self, service, fog_node):
        self._service_node_mapping[service.id] = fog_node

    # TODO: If possible, run this service in a new thread
    def _orchestrate_services(self, env):
        """Orchestrate services periodically"""
        yield env.timeout(TIME_MULTIPLIER)
        if self.config["orchestration_scheme"] == 'dro':
            self.orchestration_module = DynamicResourceOrchestrationModule(
                self)

        while True:
            self.orchestration_module.step()
            yield env.timeout(TIME_MULTIPLIER)

    def run(self):
        self.env.run(until=self.stop_simulation_event)
