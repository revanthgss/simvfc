
import itertools
from constants import TIME_MULTIPLIER
from gym.wrappers import FlattenObservation
from gym.utils import seeding
from env import VehicularFogEnv
from baselines.common.schedules import LinearSchedule
from baselines.deepq.utils import ObservationInput
from baselines.deepq.replay_buffer import ReplayBuffer
from baselines import deepq
from baselines import logger
import baselines.common.tf_util as U
import tensorflow.contrib.layers as layers
import tensorflow as tf
import numpy as np
from matplotlib import pyplot as plt
from simulation import Simulation
import random


configs = ['sa', 'sa_dro', 'caa', 'caa_dro', 'coa', 'coa_dro']


def add_metrics(x, y):
    res = {}
    for key in x.keys():
        res[key] = []
        for idx in range(min(len(x[key]), len(y[key]))):
            res[key].append(x[key][idx]+y[key][idx])

    return res


def model(inpt, num_actions, scope, reuse=tf.AUTO_REUSE):
    """This model takes as input an observation and returns values of all actions."""
    with tf.variable_scope(scope, reuse=reuse):
        out = inpt
        out = layers.fully_connected(
            out, num_outputs=512, activation_fn=tf.nn.leaky_relu)
        out = layers.fully_connected(
            out, num_outputs=256, activation_fn=tf.nn.leaky_relu)
        out = layers.fully_connected(
            out, num_outputs=num_actions, activation_fn=None)
        return out


def perform_rl_algo(config):
    results = {}
    BATCH_SIZE = 32
    EPISODES = 10
    with U.make_session(num_cpu=8):
        # Create the environment
        env = VehicularFogEnv(config=f'./configs/{config}.json')
        # Create all the functions necessary to train the model
        act, train, update_target, debug = deepq.build_train(
            make_obs_ph=lambda name: ObservationInput(
                env.observation_space, name=name),
            q_func=model,
            num_actions=env.action_space.n,
            optimizer=tf.train.RMSPropOptimizer(learning_rate=5e-4),
        )
        # optimizer=tf.train.AdamOptimizer(learning_rate=5e-4),
        # Create the replay buffer
        replay_buffer = ReplayBuffer(50000)
        # Create the schedule for exploration starting from 1 (every action is random) down to
        # 0.02 (98% of actions are selected according to values predicted by the model).
#         exploration = LinearSchedule(
#             schedule_timesteps=2500, initial_p=1.0, final_p=0.1)

        # Initialize the parameters and copy them to the target network.
        U.initialize()
        U.load_variables('./checkpoints/omsr.pth')
        update_target()

        episode_rewards = [0.0]
        ep_count = 0
        random.seed(ep_count+100)
        _, _ = seeding.np_random(ep_count+100)
        np.random.seed(ep_count+100)
        obs = env.reset()
        for t in itertools.count():
            if ep_count >= EPISODES:
                break
            patience = 100
            prev_sid = None
            for service_id in env.sim_instance._service_node_mapping.keys():
                if service_id != prev_sid:
                    patience = 100
                    prev_sid = service_id
                else:
                    patience -= 1

                service = env.sim_instance.services[service_id]
                obs = env.get_observation(service)
                # Take action and update exploration to the newest value
                action = act(obs[None], update_eps=1)[0]
                new_obs, rew, don, info = env.step(action, service.id)
                # Store transition in the replay buffer.
                replay_buffer.add(obs, action, rew, new_obs, float(don))
                obs = new_obs
                done = info['done'] or env.sim_instance.is_stopped

                if patience <= 0:
                    done = True
                    patience = 100

                episode_rewards[-1] += rew
                if done:
                    print(config, ep_count)
                    if ep_count == 0:
                        results = env.sim_instance.get_metrics()
                    else:
                        results = add_metrics(
                            results, env.sim_instance.get_metrics())
                    ep_count += 1
                    random.seed(ep_count+100)
                    _, _ = seeding.np_random(ep_count+100)
                    np.random.seed(ep_count+100)
                    obs = env.reset()
                    episode_rewards.append(0)

                # is_solved = t > 100 and np.mean(
                #     episode_rewards[-101:-1]) >= 200
                # if is_solved:
                #     print("Solved OMSR!!")
                #     # Show off the result
                #     env.render()
                # else:
                # Minimize the error in Bellman's equation on a batch sampled from replay buffer.
#                 if t > 250:
#                     obses_t, actions, rewards, obses_tp1, dones = replay_buffer.sample(
#                         BATCH_SIZE)
#                     train(obses_t, actions, rewards, obses_tp1,
#                           dones, np.ones_like(rewards))
#                 # Update target network periodically.
#                 if t % 500 == 0:
#                     update_target()

                if done:
                    print(episode_rewards)
                    logger.record_tabular(
                        "Episode Reward", episode_rewards[-2])
                    logger.record_tabular("steps", t)
                    logger.record_tabular("episodes", len(episode_rewards))
                    logger.record_tabular("mean episode reward", str(round(
                        np.mean(episode_rewards[:-1]), 1)))
                    logger.dump_tabular()
                    break
            time = env.sim_instance.env.now
            # Process all the events until next time

            while env.sim_instance.env.now-time <= TIME_MULTIPLIER:
                env.sim_instance.env.step()
#         U.save_variables(
#             f'./checkpoints/final_model_{str(round(np.mean(episode_rewards[:-1]), 1))}.pth'

        for key in results.keys():
            for idx in range(len(results[key])):
                results[key][idx] /= N
        with open(f'{config}_rl_om.txt', "w") as f:
            str_dictionary = repr(results)
            f.write("results = " + str_dictionary + "\n")
        return results


configs = ['caa']
instances = {}
results = {}
N = 10
for config in configs:
    print('!!OMSRISAIRAM!!')
    tf.reset_default_graph()
    results[config] = perform_rl_algo(config)

print(results)
