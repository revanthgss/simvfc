from simpy.resources import container

class Node:
    '''A node class that is used to create static nodes in a cloud network'''

    def __init__(self, env, coverage_radius, bandwidth, vehicle_arrival_rate, vehicle_departure_rate, capacity, position=(0,0)):
        self.env = env
        self.coverage_radius = coverage_radius
        self.bandwidth = bandwidth
        self.vehicle_arrival_rate = vehicle_arrival_rate
        self.vehicle_departure_rate = vehicle_departure_rate
        self.resource_container = container.Container(env, capacity=capacity, init=capacity)
        self.position = position    

    def set_position(x,y):
        self.position = (x,y)
        