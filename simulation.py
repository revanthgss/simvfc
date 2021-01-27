from simpy.core import Environment
from simpy.events import Event
from simpy.resources.store import Store
from .fognode import Node
from .vehicle import Vehicle
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
            self._config = json.load(f)
        self.mean_arrival_rate = self.config["mean_arrival_rate"]
        self.mean_departure_rate = self.config["mean_departure_rate"]
        self.service_store = Store()
        self.env.process(self._monitor_services(self.env))
        # Initialise fog nodes
        self._init_fog_nodes()
        # Initialise vehicles
        self._init_vehicles()
        # Initialise policy
        self._init_policy()

    def _init_fog_nodes(self):
        self.fog_nodes = [
            Node(
                self.env,
                random.randint(*self.config["fn_coverage_radius"]),
                random.choice(self.config["fn_bandwidth"]),
            ) for _ in range(self.config["num_fn"])
        ]

    def _init_vehicles(self):
        self.vehicles = []
        for idx in range(1, self.config["num_vehicles"]+1):
            v = Vehicle(
                idx,
                self.env,
                self.service_store,
                self.config["desired_data_rate"],
            )
            v.set_mobility_model(DynamicMobilityModel(
                '../datasets/trajectory.csv'))
            self.vehicles.append(v)

    def _init_policy(self):
        allocation_policy = self.config["allocation_policy"]
        if allocation_policy == 'signal_aware':
            self.allocation_policy = SignalAwareAllocationPolicy(
                self.fog_nodes)
        elif allocation_policy == 'capacity_aware':
            self.allocation_policy = CapacityAwareAllocationPolicy(
                self.fog_nodes)

    def _monitor_services(self, env):
        while self.total_services < self.config["total_service_connections"]:
            service = yield self.service_store.get()
            self.allocation_policy.allot(service)
            self.total_services += 1
            yield env.timeout(10)
        yield self.stop_simulation_event

    def run(self):
        self.env.run(until=self.stop_simulation_event)
