import random
from time import perf_counter

import chess
from reconchess.utilities import move_actions, revise_move
from tqdm import trange


def main():
    perf_counter()
    n = 10_000
    board = chess.Board()
    for _ in trange(n):
        move = random.choice(move_actions(board))
        revised = revise_move(board, move) or chess.Move.null()
        board.push(revised)
        if board.king(chess.WHITE) is None or board.king(chess.BLACK) is None:
            board.reset()
    t = perf_counter()
    print(
        f"Finished {n:,.0f} random moves in {t:.2f} seconds "
        f"({n/t:,.2f} moves per second on average)"
    )


if __name__ == "__main__":
    main()
