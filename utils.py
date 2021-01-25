import math


def distance(a, b):
    """Computes distance between two tuples"""
    return math.sqrt((b[0]-a[0])**2+(b[1]-a[1])**2)
