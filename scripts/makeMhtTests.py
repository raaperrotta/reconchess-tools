"""Generate MHT unit tests for my Kotlin RBC implementation"""
import random

import chess
from reconchess.utilities import capture_square_of_move

from reconchess_tools.mht import MultiHypothesisTracker
from reconchess_tools.strategy import minimax_sense, non_dominated_sense_by_own_pieces
from reconchess_tools.utilities import simulate_move, simulate_sense


def random_board():
    board = chess.Board()
    for _ in range(1_000):
        board.push(random.choice(list(board.pseudo_legal_moves)))
        if board.king(board.turn) is None:
            board = chess.Board()
    return board


def easy():
    # Set up by playing a bunch of random moves
    board = chess.Board()
    test = board.fen(en_passant="xfen") + "\n"
    mht = MultiHypothesisTracker()
    mht.boards = [board.copy()]

    op_move = chess.Move.from_uci("e2e4")
    capture_square = capture_square_of_move(board, op_move)
    board.push(op_move)
    mht.op_move(capture_square)
    test += f"{op_move} "

    square = chess.C2
    mht.sense(square, simulate_sense(board, square))
    test += f"{chess.SQUARE_NAMES[square]} "

    test += f"- "

    test = test[:-1] + "\n" + "\n".join(board.fen() for board in mht.boards)
    return test


def main():
    # Set up by playing a bunch of random moves
    board = random_board()
    test = board.fen(en_passant="xfen") + "\n"
    mht = MultiHypothesisTracker()
    mht.boards = [board.copy()]

    for _ in range(random.randint(2, 8)):
        op_move = random.choice(list(board.pseudo_legal_moves))
        capture_square = capture_square_of_move(board, op_move)
        board.push(op_move)
        mht.op_move(capture_square)
        test += f"{op_move} "

        mht.speculate_sense(non_dominated_sense_by_own_pieces(mht.boards[0]))
        minimax_square = minimax_sense(mht.sense_speculation)
        mht.sense(minimax_square, simulate_sense(board, minimax_square))
        test += f"{chess.SQUARE_NAMES[minimax_square]} "

        requested_move = random.choice(list(board.pseudo_legal_moves))
        taken_move, capture_square = simulate_move(board, requested_move)
        mht.move(requested_move, taken_move, capture_square)
        board.push(taken_move)
        test += f"{requested_move} "

    test = (
        test[:-1]
        + "\n"
        + "\n".join(board.fen(en_passant="xfen") for board in mht.boards)
    )
    return test


if __name__ == "__main__":
    print(easy())
