import logging
from time import time

import chess

from sac.agent import SAC
from sac.env import Env

TRAINEE_SIDE = chess.WHITE

MHT_BOARD_LIMIT = 2_000

REPLAY_BUFFER_LEN = 10_000
NUM_RANDOM_SAMPLES = 1_000

BATCH_SIZE = 100
ALPHA = 1e-4
GAMMA = 0.95
H = 1e-6

SAVE_EVERY = 60  # seconds


def main():
    env = Env(
        trainee_side=TRAINEE_SIDE,
        mht_board_limit=MHT_BOARD_LIMIT,
    )
    sac = SAC(
        replay_buffer_len=REPLAY_BUFFER_LEN,
        num_random_samples=NUM_RANDOM_SAMPLES,
        mht_board_limit=MHT_BOARD_LIMIT,
    )
    sac.actor.model.summary()

    state = env.reset()

    last_saved = None

    while True:

        action = sac.act(state)
        next_state, reward, done = env.step(action)
        sac.record(state, action, next_state, reward, done)
        state = env.reset() if done else next_state
        sac.learn(
            batch_size=BATCH_SIZE,
            alpha=ALPHA,
            gamma=GAMMA,
            H=H,
        )

        if sac.updates == 1:
            last_saved = time()
        elif sac.updates > 1 and time() - last_saved > SAVE_EVERY:
            print("Saving actors")
            sac.actor.model.save(f"actor-{chess.COLOR_NAMES[TRAINEE_SIDE]}")
            last_saved = time()


if __name__ == "__main__":
    log = logging.getLogger("sac")
    log.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter("%(levelname).1s - %(asctime)s - %(name)s: %(message)s")
    )
    log.addHandler(handler)
    main()
