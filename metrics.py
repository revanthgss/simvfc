import time


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
        super().__init__()

    def compute(self, nodes):
        self._values.append(sum(
            [node.resource_container.level for node in nodes]
        )/sum([node.capacity for node in nodes]))


class Throughput(Metric):

    def __init__(self):
        self.name = 'throughput'
        super().__init__()

    def compute(self, nodes):
        self._values.append(sum([node.overall_throughput for node in nodes]))


class Serviceability(Metric):

    def __init__(self):
        self.name = 'serviceability'
        super().__init__()

    def compute(self, nodes):
        tis = 0
        tss = 0
        for node in nodes:
            x, y = node.get_serviceability_metrics()
            tss += x
            tis += y
        if tis == 0:
            self._values.append(1)
        else:
            self._values.append(tss /
                                tis)


class Availability(Metric):
    # TODO: Compute this metric by using the minimum data rate for all services

    def __init__(self):
        self.name = 'availability'
        super().__init__()

    def compute(self, nodes):
        tis = 0
        tss = 0
        for node in nodes:
            x, y = node.get_serviceability_metrics()
            tss += x
            tis += y

        if tis == 0:
            self._values.append(1)
        else:
            self._values.append(tss /
                                tis)


class AVGEnergyConsumed(Metric):

    def __init__(self):
        self.name = 'avg_energy_consumed'
        super().__init__()

    def compute(self, nodes):
        tss = sum([node.get_serviceability_metrics()[0] for node in nodes])
        total_energy = sum([node.energy_consumed for node in nodes])
        # self._values.append(total_energy)
        if tss == 0:
            self._values.append(total_energy)
        else:
            self._values.append(total_energy/tss)


class EnergyConsumed(Metric):

    def __init__(self):
        self.name = 'energy_consumed'
        super().__init__()

    def compute(self, nodes):
        total_energy = sum([node.energy_consumed for node in nodes])
        self._values.append(total_energy)


class ExecTime(Metric):

    def __init__(self):
        self.name = 'execution_time'
        self.start = time.time()
        super().__init__()

    def compute(self, nodes):
        self._values.append(time.time()-self.start)


def MetricFactory(metric_type):

    metrics = {
        "service_capability": ServiceCapability,
        "throughput": Throughput,
        "serviceability": Serviceability,
        "availability": Availability,
        "energy_consumed": EnergyConsumed,
        "avg_energy_consumed": AVGEnergyConsumed,
        "execution_time": ExecTime,
    }

    return metrics[metric_type]()
