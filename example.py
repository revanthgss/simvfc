from simulation import Simulation

configs = ['sa', 'caa', 'sa_dro', 'caa_dro']

instances = {}
for config in configs:
    instances[config] = Simulation(config=f'./configs/{config}.json')

results = {}
for config in configs:
    print(f'Running simulation with config {config}')
    instances[config].run()
    results[config] = instances[config].get_metrics()

print(results)
