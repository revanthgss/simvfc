import math


class Topology:

    def __init__(self, origin, length, breadth):
        self.origin = origin
        self.length = length
        self.breadth = breadth

    def assign_positions(self, nodes):
        n = math.ceil(math.sqrt(len(nodes)))
        dx = self.length/(n-1)
        dy = self.breadth/(n-1)
        x, y = self.origin
        idx = 0
        while idx < len(nodes):
            nodes[idx].set_position(x, y)
            x += dx
            if x >= self.origin[0]+self.length:
                x = self.origin[0]
                y += dy
            idx += 1
