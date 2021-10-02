import logging
import random
from collections import deque
from time import time

import numpy as np
import tensorflow as tf

from sac.bot import ACTIONS, SacState, encode_action_mask
from sac.models import construct_model_base

LOG = logging.getLogger(__name__)


class SAC:
    def __init__(
        self, replay_buffer_len=20_000, num_random_samples=100, mht_board_limit=2_000
    ):
        self.mht_board_limit = mht_board_limit

        self.actor = Actor(mht_board_limit=mht_board_limit)
        self.critic0 = Critic(mht_board_limit=mht_board_limit)
        self.critic1 = Critic(mht_board_limit=mht_board_limit)
        self.replay_buffer = deque(maxlen=replay_buffer_len)
        self.num_random_samples = num_random_samples
        self.updates = 0
        self.creation_time = None

        self.log_alpha = tf.Variable(np.log(0.01), trainable=True, dtype="float32")
        self.alpha_optimizer = tf.keras.optimizers.Adam()

    def act(self, state: SacState):
        boards, actions_mask = state.encode()
        weights = (
            self.actor.act((boards, actions_mask))
            if self.updates > 0
            else actions_mask / sum(actions_mask)
        )
        action = random.choices(ACTIONS, weights, k=1)[0]
        return action

    def record(self, state, action, next_state, reward, done):
        self.replay_buffer.append((state, action, next_state, reward, done))

    def learn(
        self,
        batch_size=2,
        alpha=0.01,
        gamma=0.95,
        H=np.exp(-len(ACTIONS)),
    ):
        if len(self.replay_buffer) < self.num_random_samples:
            LOG.debug(
                "Too few samples (%s) to train! Skipping learning phase.",
                f"{len(self.replay_buffer):,.0f}",
            )
            return
        elif self.creation_time is None:
            self.creation_time = time()

        LOG.debug(
            "Drawing %s samples for training from my buffer of %s",
            f"{batch_size:,.0f}",
            f"{len(self.replay_buffer):,.0f}",
        )

        samples = random.sample(self.replay_buffer, batch_size)
        states, actions, next_states, rewards, dones = zip(*samples)

        boards, action_masks = zip(*(state.encode() for state in states))
        boards = tf.keras.preprocessing.sequence.pad_sequences(boards, value=-1)
        action_masks = np.stack(action_masks, axis=0)

        next_boards, next_action_masks = zip(*(state.encode() for state in next_states))
        next_boards = tf.keras.preprocessing.sequence.pad_sequences(
            next_boards, value=-1
        )
        next_action_masks = np.stack(next_action_masks, axis=0)

        actions = np.stack([encode_action_mask([action]) for action in actions], axis=0)

        rewards = np.array(rewards)
        dones = np.array(dones)

        q0 = self.critic0.model((boards, action_masks))
        q1 = self.critic1.model((boards, action_masks))
        q = np.minimum(q0, q1)

        policy = self.actor.learn(boards, action_masks, q, alpha)

        next_policy = self.actor.model((next_boards, next_action_masks))
        target_next_q0 = self.critic0.teacher((next_boards, next_action_masks))
        target_next_q1 = self.critic1.teacher((next_boards, next_action_masks))
        target_next_q = np.minimum(target_next_q0, target_next_q1)
        target_next_soft_q = target_next_q - alpha * tf.math.log(next_policy + 1e-6)
        target_next_v = np.sum(target_next_soft_q * next_policy, axis=1, keepdims=True)
        state_action_target = rewards[:, None] + gamma * ~dones[:, None] * target_next_v

        masked_state_action_target = state_action_target * actions

        self.critic0.learn(boards, action_masks, masked_state_action_target)
        self.critic1.learn(boards, action_masks, masked_state_action_target)

        # Update (log) alpha
        policy_entropy = -tf.reduce_sum(policy * (tf.math.log(policy + 1e-9)))
        loss = (policy_entropy - H) / batch_size
        with tf.GradientTape() as tape:
            alpha = tf.math.exp(self.log_alpha)
            loss = alpha * loss
        gradients = tape.gradient(loss, [self.log_alpha])
        self.alpha_optimizer.apply_gradients(zip(gradients, [self.log_alpha]))
        LOG.debug("The current value for alpha is %g", np.exp(self.log_alpha))

        self.updates += 1
        elapsed_seconds = time() - self.creation_time
        average_seconds = elapsed_seconds / self.updates
        LOG.info(
            "Finished update %s. Averaging %.2f seconds per update.",
            f"{self.updates:,.0f}",
            average_seconds,
        )


class Actor:
    def __init__(self, mht_board_limit):
        self.mht_board_limit = mht_board_limit

        boards, action_mask, logits = construct_model_base()
        masked = tf.where(action_mask, logits, -1e12)
        policy = tf.keras.layers.Softmax(axis=-1)(masked)

        self.model = tf.keras.models.Model([boards, action_mask], policy)
        self.optimizer = tf.keras.optimizers.Adam()
        self.model.compile("adam", "mse")  # compile to silence warnings when saving

    def act(self, x):
        boards, action_mask = x
        boards = tf.keras.preprocessing.sequence.pad_sequences(
            [boards], value=-1, maxlen=self.mht_board_limit
        )
        return self.model.predict((boards, action_mask[None]))[0]

    def learn(self, boards, action_masks, q, alpha):
        LOG.debug("Training actor")
        with tf.GradientTape() as tape:
            predicted_policy = self.model((boards, action_masks))
            loss = predicted_policy * (alpha * tf.math.log(predicted_policy + 1e-9) - q)
            loss = tf.reduce_sum(loss, axis=-1)
            loss = tf.reduce_mean(loss)
        grads = tape.gradient(loss, self.model.trainable_variables)
        self.optimizer.apply_gradients(zip(grads, self.model.trainable_variables))
        return predicted_policy  # for use updating alpha


class Critic:
    def __init__(self, mht_board_limit):
        self.mht_board_limit = mht_board_limit

        boards, action_mask, score = construct_model_base()
        q = tf.where(action_mask, score, 0)

        self.model = tf.keras.models.Model([boards, action_mask], q)
        self.teacher = tf.keras.models.clone_model(self.model)
        self.model.compile(tf.keras.optimizers.Adam(), "mse")

    def act(self, x):
        boards, action_mask = x
        boards = tf.keras.preprocessing.sequence.pad_sequences(
            [boards], value=-1, maxlen=self.mht_board_limit
        )
        return self.model.predict((boards, action_mask[None]))[0]

    def learn(self, boards, action_masks, masked_state_action_target):
        LOG.debug("Training critic")
        self.model.fit(
            (boards, action_masks),
            masked_state_action_target,
            epochs=1,
            verbose=0,
            batch_size=boards.shape[0],
        )
        self.nudge()

    def nudge(self, step=0.02):
        self.teacher.set_weights(
            [
                v_slow + step * (v_fast - v_slow)
                for v_slow, v_fast in zip(
                    self.teacher.get_weights(), self.model.get_weights()
                )
            ]
        )
