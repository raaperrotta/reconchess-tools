from typing import List, Tuple, Optional

import chess

from reconchess_tools.utilities import (
    simulate_sense,
    simulate_move,
    possible_requested_moves,
)


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

        # TODO speculation
        #  - For each of move and sense, add a method to calculate all possible outcomes without the
        #    prior information. For sense, without the opponent's capture square. For move, without
        #    the sense result.
        #  - Have existing methods do a lookup on speculation results if present, then delete them

    def reset(self):
        self.boards = [chess.Board()]

    def sense(self, square: chess.Square, result: List[Tuple[int, chess.Piece]]):
        result = set(result)  # make order-independent
        self.boards = [
            board
            for board in self.boards
            if set(simulate_sense(board, square)) == result
        ]

    def move(
        self,
        requested_move: chess.Move,
        taken_move: chess.Move,
        capture_square: Optional[chess.Square],
    ):
        self.boards = [
            board
            for board in self.boards
            if simulate_move(board, requested_move) == (taken_move, capture_square)
        ]
        for board in self.boards:
            board.push(taken_move)

    def op_move(self, capture_square: Optional[chess.Square]):
        new_boards = {}
        for board in self.boards:
            for requested_move in possible_requested_moves(board):
                taken_move, simulated_capture_square = simulate_move(
                    board, requested_move
                )
                if simulated_capture_square == capture_square:
                    new_board = board.copy(stack=False)
                    new_board.push(taken_move)
                    new_boards[board_fingerprint(new_board)] = new_board
        self.boards = list(new_boards.values())


if __name__ == "__main__":
    board = chess.Board()
    mht = MultiHypothesisTracker()

    board.push(chess.Move.from_uci("g1h3"))
    mht.op_move(None)
    mht.sense(chess.C2, simulate_sense(board, chess.C2))
    mht.move(chess.Move.from_uci("d7d5"), chess.Move.from_uci("d7d5"), None)
    board.push(chess.Move.from_uci("d7d5"))

    board.push(chess.Move.from_uci("h3f4"))
    mht.op_move(None)
    mht.sense(chess.F2, simulate_sense(board, chess.F2))
    mht.move(chess.Move.from_uci("e7e5"), chess.Move.from_uci("e7e5"), None)
    board.push(chess.Move.from_uci("e7e5"))

    board.push(chess.Move.from_uci("f4h5"))
    mht.op_move(None)
    mht.sense(chess.C2, simulate_sense(board, chess.C2))
    mht.move(chess.Move.from_uci("g8f6"), chess.Move.from_uci("g8f6"), None)
    board.push(chess.Move.from_uci("g8f6"))

    board.push(chess.Move.from_uci("h5f6"))
    mht.op_move(chess.F6)
