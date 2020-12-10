import os

import chess.engine


# make sure stockfish environment variable exists
if "STOCKFISH_EXECUTABLE" not in os.environ:
    raise KeyError(
        'This bot requires an environment variable called "STOCKFISH_EXECUTABLE" '
        "pointing to the Stockfish executable"
    )

# make sure there is actually a file
STOCKFISH_EXECUTABLE = os.getenv("STOCKFISH_EXECUTABLE")
if not os.path.exists(STOCKFISH_EXECUTABLE):
    raise ValueError(f'No stockfish executable found at "{STOCKFISH_EXECUTABLE}"')


def create_engine():
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_EXECUTABLE, setpgrp=True)
    return engine
