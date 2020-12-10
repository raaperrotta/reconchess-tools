from collections import defaultdict
from typing import List, Tuple, Optional

import chess

from reconchess_tools.strategy import SENSE_SQUARES
from reconchess_tools.utilities import (
    simulate_sense,
    simulate_move,
    possible_requested_moves,
)


def board_fingerprint(board: chess.Board):
    """Compute a fingerprint for fast board comparisons

    This fingerprint is a tuple of integers and booleans that contains the same information as the
    extended position description (EPD). It does not contain all of the information in the FEN, e.g.
    half-move counter, because those are not significant in reconchess. Two boards have the same
    fingerprint, they are identical as far as reconchess is concerned, including allowing the same
    requested moves, and having the same results for any sense or move action.
    """
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
    """An object to keep track of the possible true board states in a reconchess game

    The MultiHypothesisTracker (MHT) maintains a list of the possible true board positions. At the
    start of the game that list contains only the starting position. Whenever a player receives a
    sense result, that list may be filtered to include only the boards for which the simulated sense
    result matches. Likewise, whenever a player receives a move result, the list may be filtered to
    include only those boards for which the requested move would have resulted in the same taken
    move and capture square, after which the taken move must be pushed to all boards to keep them
    up to date. And lastly, after an opponent moves, each board in the list must be expanded into
    the result of all possible taken moves for which the capture square was the same as observed.
    Because that may result in duplicate positions, the list should be filtered to ensure
    uniqueness.

    Because the board list and the boards themselves are mutable, you must take care not to
    unintentionally alter them. For example, you may need copy a board from this list if you want
    to alter it (or you can ensure you undo any moves made on it). It is possible that the list will
    grow too large to be reasonably sustained. To prevent that, you may slice the list and all the
    methods below will still work. If you do so, you may discard the true board state, in which
    case it is possible to reveal information that contradicts all remaining boards and leaves the
    list of possible boards empty. Therefore, if you discard boards to limit memory requirements, be
    sure to handle the edge case of an empty board set.

    It is sometimes beneficial to speculate outcomes before making a decision. For example, to
    imagine all possible outcomes of a sense decision across all possible (or reasonable) choices.
    The speculate_sense method does just that and stores the result in the sense_speculation
    property. If present, this is used in the sense step rather than recomputing simulated sense
    results. The sense_speculation property can be input to various functions in the strategy module
    to aid sense decision making. It is reset to None after it is used in the sense step.
    """

    def __init__(self):
        self.boards = [chess.Board()]

        # An optional nested map of subsequent boards given a sense square and sense result
        self.sense_speculation = None

        # TODO speculation
        #  - For each of my move and opponent move, add a method to calculate all possible outcomes
        #    without the prior information.
        #  - Have existing methods do a lookup on speculation results if present, then delete them.

    def reset(self):
        self.boards = [chess.Board()]

    def speculate_sense(self, sense_squares=SENSE_SQUARES):
        self.sense_speculation = {}
        for square in sense_squares:
            self.sense_speculation[square] = sense_results = defaultdict(list)
            for board in self.boards:
                sense_results[tuple(simulate_sense(board, square))].append(board)

    def sense(self, square: chess.Square, sorted_result: List[Tuple[int, chess.Piece]]):
        if self.sense_speculation is not None:
            self.boards = self.sense_speculation[square][tuple(sorted_result)]
            self.sense_speculation = None
        else:
            self.boards = [
                board
                for board in self.boards
                if simulate_sense(board, square) == sorted_result
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
