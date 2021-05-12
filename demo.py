from simulation import Simulation
import matplotlib.pyplot as plt
import random
import numpy as np

print('Running simulation with signal aware and no orchestration')
random.seed(100)
np.random.seed(100)
s = Simulation(config='./configs/sa.json')
s.run()
r1 = s.get_metrics()

print('Running simulation with signal aware and dro orchestration')
random.seed(100)
np.random.seed(100)
s = Simulation(config='./configs/sa_dro.json')
s.run()
r2 = s.get_metrics()

print('Running simulation with signal aware and rl orchestration')
random.seed(100)
np.random.seed(100)
s = Simulation(config='./configs/sa_rl.json')
s.run()
res_3 = s.get_metrics()

fig, ax = plt.subplots(1, 3)
ax[0].boxplot([res['energy_consumed'] for res in [
    r1, r2, res_3]], showfliers=False, showmeans=True, meanline=True)
ax[0].set_xticklabels(['sa', 'sa+dro', 'sa+rl'])
ax[1].boxplot([res['service_capability'] for res in [
    r1, r2, res_3]], showfliers=False, showmeans=True, meanline=True)
ax[1].set_xticklabels(['sa', 'sa+dro', 'sa+rl'])
ax[0].set_title('Energy consumed per service served')
ax[1].set_title('Service Capability')
ax[2].plot([i*20 for i in range(50)], r1['execution_time'][:50])
ax[2].plot([i*20 for i in range(50)], r2['execution_time'][:50])
ax[2].plot([i*20 for i in range(50)], res_3['execution_time'][:50])
ax[2].legend(['sa', 'sa+dro', 'sa+rl'])

plt.show()
