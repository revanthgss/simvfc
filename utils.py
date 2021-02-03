import math


def distance(a, b):
    """Computes distance between two tuples"""
    return math.sqrt((b[0]-a[0])**2+(b[1]-a[1])**2)


def find_feasible_fog_nodes(fog_nodes, vehicle):
    """Finds all the fog nodes that can reach the vehicle of the service"""
    feasible_fog_nodes = []
    for fog_node in fog_nodes:
        if distance(fog_node.position, vehicle.get_position()) < fog_node.coverage_radius:
            feasible_fog_nodes.append(fog_node)
    return feasible_fog_nodes


def find_vehicles(vehicles, fog_node):
    """Returns all the vehicles that are in the coverage radius of the given fog_node"""
    possible_vehicles = []
    for vehicle in vehicles:
        if distance(fog_node.position, vehicle.get_position()) < fog_node.coverage_radius:
            possible_vehicles.append(vehicle)
    return possible_vehicles
