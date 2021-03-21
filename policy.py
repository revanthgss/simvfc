from utils import find_feasible_fog_nodes

# TODO: Create a factory class


class AllocationPolicy:
    """Policy for allocation vehicle services to fog nodes"""

    def __init__(self, fog_nodes):
        self.fog_nodes = fog_nodes

    def find_best_fog_node(self, vehicle):
        """Finds the best fog node according to the policy"""
        raise NotImplementedError

    def allocate(self, service):
        """Takes a service and implements the allocation algorithm for choosing fog nodes"""
        vehicle = service.vehicle
        self.feasible_fog_nodes = find_feasible_fog_nodes(
            self.fog_nodes, vehicle)
        best_fog_node = self.find_best_fog_node(vehicle, service)
        if best_fog_node:
            best_fog_node.add_service(service)

        return best_fog_node


class SignalAwareAllocationPolicy(AllocationPolicy):
    """Choose fog node having the maximum sinr for a vehicle"""

    def find_best_fog_node(self, vehicle, service):
        sinr_values = [fog_node._get_sinr(vehicle)
                       for fog_node in self.feasible_fog_nodes]
        if len(sinr_values) == 0:
            return None
        best_fog_node = self.feasible_fog_nodes[sinr_values.index(
            max(sinr_values))]
        return best_fog_node


class CapacityAwareAllocationPolicy(AllocationPolicy):
    """Choose fog node having the maximum available resources for a vehicle"""

    def find_best_fog_node(self, vehicle, service):
        available_resources = [
            fog_node.resource_container.level for fog_node in self.feasible_fog_nodes]

        if len(available_resources) == 0:
            return None
        best_fog_node = self.feasible_fog_nodes[available_resources.index(
            max(available_resources))]
        return best_fog_node


class ContentAwareAllocationPolicy(AllocationPolicy):
    """Choose fog node having the maximum sinr for a vehicle"""

    def find_best_fog_node(self, vehicle, service):
        # Filter the nodes that has the contents stored
        fog_nodes_cache = list(filter(
            lambda fn: fn.cache_array[service.content_type] == 1, self.feasible_fog_nodes))
        if len(fog_nodes_cache) == 1:
            # If it is only one return it
            return fog_nodes_cache[0]
        elif len(fog_nodes_cache) == 0:
            # If no feasible node has content cached, then allocate according to signal aware approach
            sap = SignalAwareAllocationPolicy(self.fog_nodes)
            sap.feasible_fog_nodes = self.feasible_fog_nodes
            return sap.find_best_fog_node(vehicle, service)
        else:
            # If multiple feasible nodes are there, allocate the nodes with cached content
            # according to signal aware approach
            sap = SignalAwareAllocationPolicy(self.fog_nodes)
            sap.feasible_fog_nodes = fog_nodes_cache
            return sap.find_best_fog_node(vehicle, service)
        return None
