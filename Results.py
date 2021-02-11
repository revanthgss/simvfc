
# coding: utf-8

# In[1]:


from matplotlib import pyplot as plt
from simulation import Simulation
import random


configs = ['sa']

instances = {}
results = {}
for config in configs:
    random.seed(99999)
    instances[config] = Simulation(config=f'./configs/{config}.json')
    print(f'Running simulation with config {config}')
    instances[config].run()
    results[config] = instances[config].get_metrics()


# In[2]:


# In[3]:


# Plotting service capability
x = [i for i in range(len(results['sa']['service_capability']))]
for config in configs:
    plt.plot(results[config]['service_capability'])
plt.legend(configs)
plt.ylim(0.90, 1)
plt.show()


# In[4]:


# Plotting throughput
x = [i for i in range(len(results['sa']['throughput']))]
for config in configs:
    plt.plot(results[config]['throughput'])
plt.legend(configs)
plt.show()


# In[5]:


# Plotting serviceability
x = [i for i in range(len(results['sa']['serviceability']))]
for config in configs:
    plt.plot(results[config]['serviceability'])
plt.legend(configs)
plt.show()


# In[6]:


# # Plotting availability
# x = [i for i in range(len(results['sa']['availability']))]
# # for config in configs:
#     plt.plot(x,results[config]['availability'])
# plt.legend(configs)
# plt.show()


# In[7]:


print(results['sa_dro']['serviceability'])
