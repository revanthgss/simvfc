
class Metric:

    def __init__(self):
        self._values = []

    def compute(self, nodes):
        raise NotImplementedError

    def get_values(self):
        return self._values


class ServiceCapability(Metric):
    """Ratio of sum of available resources by sum of capacities"""

    def __init__(self):
        self.name = 'service_capability'

    def compute(self, nodes):
        self._values.append(sum(
            [node.capacity - node.resource_container.level for node in nodes]
        )/sum([node.capacity for node in nodes]))


class Throughput(Metric):

    def __init__(self):
        self.name = 'throughput'

    def compute(self, nodes):
        self._values.append(sum([node.overall_throughput for node in nodes]))


class Serviceability(Metric):

    def __init__(self):
        self.name = 'serviceability'

    def compute(self, nodes):
        self._values.append(sum([node.services_served for node in nodes]
                                )/sum([node.incoming_services for node in nodes]))


class Availability(Metric):

    def __init__(self):
        self.name = 'availability'

    def compute(self, nodes):
        self._values.append(sum([node.services_served for node in nodes]
                                )/sum([node.incoming_services for node in nodes]))


def MetricFactory(metric_type):

    metrics = {
        "service_capability": ServiceCapability,
        "throughput": Throughput,
        "serviceability": Serviceability,
        "availability": Availability
    }

    return metrics[metric_type]()
