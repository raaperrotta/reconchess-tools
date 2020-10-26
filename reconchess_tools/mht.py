from functools import lru_cache
from itertools import product
from typing import List, Tuple, Optional

import chess

from reconchess_tools.utilities import simulate_sense, simulate_move, possible_requested_moves


def board_fingerprint(board: chess.Board):
    return (
        board.turn,
        *board.occupied_co,
        board.kings,
        board.queens,
        board.bishops,
        board.knights,
        board.rooks,
        board.pawns,
        board.castling_rights,
        board.ep_square,
    )


class MultiHypothesisTracker:

    def __init__(self):
        self.boards = [chess.Board()]

    def sense(self, square: chess.Square, result: List[Tuple[int, chess.Piece]]):
        self.boards = [board for board in self.boards if simulate_sense(board, square) == result]

    def move(self, requested_move: chess.Move, taken_move: chess.Move, capture_square: Optional[chess.Square]):
        self.boards = [board for board in self.boards if simulate_move(board, requested_move) == (taken_move, capture_square)]
        for board in self.boards:
            board.push(taken_move)

    def op_move(self, capture_square: Optional[chess.Square]):
        new_boards = {}
        for board in self.boards:
            for requested_move in possible_requested_moves(board):
                taken_move, simulated_capture_square = simulate_move(board, requested_move)
                if simulated_capture_square == capture_square:
                    new_board = board.copy(stack=False)
                    new_board.push(taken_move)
                    new_boards[board_fingerprint(new_board)] = new_board
        self.boards = list(new_boards.values())
