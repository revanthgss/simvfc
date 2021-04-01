import random
from gym import Env, spaces
import numpy as np
from gym.utils import seeding
from stable_baselines.common.policies import FeedForwardPolicy, register_policy
from stable_baselines.common.vec_env import DummyVecEnv

from stable_baselines import PPO2, A2C
import tensorflow as tf


class KPEnv(Env):

    def __init__(self):
        super().__init__()
        # {i,j} i is the item to be picked and j is the vehicle 0 or 1
        self.N = 20
        self.R = self.N*2
        # self.action_space = spaces.Box(low=np.array(
        #     [1, 0]), high=np.array([self.N, 1]), dtype=np.int)
        self.action_space = spaces.MultiDiscrete([self.N, 2])
        # Observation space will have
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(6*self.N+9,), dtype=np.float32)
        self.vector = None
        self.ov = 0
        self.reset()

    def step(self, action):
        item = action[0]+1
        flag = action[1]
        # print(self.vector)
        item_obj = self.vector[item*6+3:item*6+9]
        if flag == 0:
            v, w, cache = self.vector[item*6+3:item*6+6]
        else:
            v, w, cache = self.vector[item*6+6:item*6+9]
        n, c1, c2, sv1, sv2, sw1, sw2, sc1, sc2 = self.vector[:9]
        if flag == 0:
            c = self.vector[1]
        else:
            c = self.vector[2]
        # print(item, n, c, v, w)
        if item <= n and w <= c:
            self.ow[flag] += w
            self.ov += -v
            self.oc += cache
        reward = 0
        if item > n:
            # reward = -120
            if flag == 0:
                reward = -100*pow(1.2, (item-n))
            else:
                reward = -100*pow(1.2, (item-n))
            # print('Undefined action!')
        elif w <= c:
            reward = self.R+v
            if cache == 1:
                reward += 10
            else:
                reward -= 10
            reward = max(0, reward)
            # print('Success!!')
        elif w > c:
            reward = -w
            # print('KP Penalty!!')
        self.reward += reward
        # if reward > -100:
        # print(action, n)
        if item <= n:
            if flag == 0:
                c1 -= w
            else:
                c2 -= w
            self.vector = [n-1, c1, c2, sv1+item_obj[0], sv2+item_obj[3], sw1-item_obj[1], sw2-item_obj[4], sc1 -
                           item_obj[2], sc2-item_obj[5]]+self.vector[9:item*6+3] + self.vector[item*6+9:]
        while len(self.vector) < 6*self.N+9:
            self.vector.append(0)
        done = not((c1 >= 0 or c2 >= 0) and n > 1)
        return np.array(self.vector), reward, done, {}

    def reset(self):
        self.reward = 0
        # self.seed(random.randint(1, 1000))
        val1 = []
        w1 = []
        val2 = []
        w2 = []
        cac1 = []
        cac2 = []
        for i in range(self.N):
            val1.append(random.randint(-self.R, -1))
            w1.append(-val1[-1])
            val2.append(random.randint(-self.R, -1))
            w2.append(-val2[-1])
            cac1.append(random.randint(0, 1))
            cac2.append(random.randint(0, 1))

        c1 = random.randint(self.R//10, 3*self.R)
        c2 = random.randint(self.R//10, 3*self.R)
        sv1 = -sum(val1)
        sv2 = -sum(val2)
        sw1 = sum(w1)
        sw2 = sum(w2)
        sc1 = sum(cac1)
        sc2 = sum(cac2)
        self.vector = [self.N, c1, c2, sv1, sv2, sw1, sw2, sc1, sc2]
        for i in range(self.N):
            self.vector.append(val1[i])
            self.vector.append(w1[i])
            self.vector.append(cac1[i])
            self.vector.append(val2[i])
            self.vector.append(w2[i])
            self.vector.append(cac1[i])

        self.ow = [0, 0]
        self.ov = 0
        self.oc = 0
        return np.array(self.vector)

    def render(self):
        pass

    def seed(self, seed=None):
        random.seed(seed)
        return [seed]


class CustomPolicy(FeedForwardPolicy):
    def __init__(self, *args, **kwargs):
        super(CustomPolicy, self).__init__(*args, **kwargs,
                                           net_arch=[256, 256], feature_extraction='mlp')


# env = KPEnv()
# env = DummyVecEnv([lambda: env])
# model = A2C(CustomPolicy, env, verbose=1)
# model.learn(total_timesteps=200000)
# model.save('omsr_power_final_2')
# #
