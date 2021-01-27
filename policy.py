from .utils import distance


class AllocationPolicy:
    """Policy for allocation vehicle services to fog nodes"""

    def __init__(self, fog_nodes):
        self.fog_nodes = fog_nodes

    def find_feasible_fog_nodes(self, service):
        """Finds all the fog nodes that can reach the vehicle of the service"""
        feasible_fog_nodes = []
        for fog_node in self.fog_nodes:
            if distance(fog_node.position, service.vehicle.position) < fog_node.coverage_radius:
                feasible_fog_nodes.append(fog_node)
        return feasible_fog_nodes

    def allocate(self, service):
        """Takes a service and implements the allocation algorithm for choosing fog nodes"""
        raise NotImplementedError


class SignalAwareAllocationPolicy(AllocationPolicy):
    """Choose fog node having the maximum sinr for a vehicle"""

    def allocate(self, service):
        vehicle = service.vehicle
        feasible_fog_nodes = self.find_feasible_fog_nodes(vehicle)
        sinr_values = [fog_node._get_sinr(vehicle)
                       for fog_node in feasible_fog_nodes]
        best_fog_node = feasible_fog_nodes[sinr_values.index(max(sinr_values))]
        best_fog_node.add_service(service)
        vehicle.allotted_fog_node = best_fog_node


class CapacityAwareAllocationPolicy(AllocationPolicy):
    """Choose fog node having the maximum available resources for a vehicle"""

    def allocate(self, service):
        vehicle = service.vehicle
        feasible_fog_nodes = self.find_feasible_fog_nodes(vehicle)
        available_resources = [
            fog_node.resource_container.level for fog_node in feasible_fog_nodes]
        best_fog_node = feasible_fog_nodes[available_resources.index(
            max(available_resources))]
        best_fog_node.add_service(vehicle)
        vehicle.allotted_fog_node = best_fog_node
