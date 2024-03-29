import itertools
import numpy as np
import tensorflow as tf
import tensorflow.contrib.layers as layers

import baselines.common.tf_util as U

from baselines import logger
from baselines import deepq
from baselines.deepq.replay_buffer import ReplayBuffer
from baselines.deepq.utils import ObservationInput
from baselines.common.schedules import PiecewiseSchedule, LinearSchedule
from env import VehicularFogEnv
from gym.wrappers import FlattenObservation
from constants import TIME_MULTIPLIER


def model(inpt, num_actions, scope, reuse=False):
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


if __name__ == '__main__':
    BATCH_SIZE = 32
    EPISODES = 1000
    with U.make_session(num_cpu=8):
        # Create the environment
        env = VehicularFogEnv(config=None)
        # Create all the functions necessary to train the model
        act, train, update_target, debug = deepq.build_train(
            make_obs_ph=lambda name: ObservationInput(
                env.observation_space, name=name),
            q_func=model,
            num_actions=env.action_space.n,
            optimizer=tf.train.RMSPropOptimizer(learning_rate=5e-4),
            gamma=0,
        )
        # optimizer=tf.train.AdamOptimizer(learning_rate=5e-4),
        # Create the replay buffer
        replay_buffer = ReplayBuffer(50000)
        # Create the schedule for exploration starting from 1 (every action is random) down to
        # 0.02 (98% of actions are selected according to values predicted by the model).
        exploration = LinearSchedule(
            schedule_timesteps=10000, initial_p=1, final_p=0.1)
        # exploration = PiecewiseSchedule(
        #     [(0, 0.1), (600, 0.1), (610, 0.1), (10000, 0.1)], )

        # Initialize the parameters and copy them to the target network.
        U.initialize()
        # U.load_variables('./checkpoints/final_model_22.pth')
        update_target()

        episode_rewards = [0.0]
        obs = env.reset()
        q_val = []
        ep_count = 0
        for t in itertools.count():
            if ep_count >= EPISODES:
                break
            for service_id in env.sim_instance._service_node_mapping.keys():

                service = env.sim_instance.services[service_id]
                obs = env.get_observation(service)
                # Take action and update exploration to the newest value
                action = act(obs[None], update_eps=exploration.value(t))[0]
                new_obs, rew, don, info = env.step(action, service.id)
                # Store transition in the replay buffer.
                replay_buffer.add(obs, action, rew, new_obs, float(don))
                obs = new_obs

                done = info['done'] or env.sim_instance.is_stopped

                episode_rewards[-1] += rew
                if done:
                    print(env.sim_instance.get_metrics())
                    obs = env.reset()
                    ep_count += 1
                    episode_rewards.append(0)

                # is_solved = t > 100 and np.mean(
                #     episode_rewards[-101:-1]) >= 200
                # if is_solved:
                #     print("Solved OMSR!!")
                #     # Show off the result
                #     env.render()
                # else:
                # Minimize the error in Bellman's equation on a batch sampled from replay buffer.
                if t > 250:
                    obses_t, actions, rewards, obses_tp1, dones = replay_buffer.sample(
                        BATCH_SIZE)
                    train(obses_t, actions, rewards, obses_tp1,
                          dones, np.ones_like(rewards))
                if t % 250 == 0:
                    update_target()

                if done:
                    logger.record_tabular(
                        "Episode Reward", episode_rewards[-2])
                    logger.record_tabular("steps", t)
                    logger.record_tabular("episodes", len(episode_rewards))
                    logger.record_tabular("mean episode reward", str(round(
                        np.mean(episode_rewards[:-1]), 1)))
                    logger.record_tabular(
                        "% time spent exploring", int(100 * exploration.value(t)))
                    logger.dump_tabular()
                    U.save_variables(f'./checkpoints/final_model_res.pth')
                    break
            time = env.sim_instance.env.now
            # Process all the events until next time

            while env.sim_instance.env.now-time <= TIME_MULTIPLIER:
                env.sim_instance.env.step()
        U.save_variables(
            f'./checkpoints/final_model_res_{str(round(np.mean(episode_rewards[:-1]), 1))}.pth')
