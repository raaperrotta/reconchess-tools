from typing import List

import chess

from reconchess_tools.mht import MultiHypothesisTracker
from reconchess_tools.utilities import simulate_sense, simulate_move


def epd(board: chess.Board) -> str:
    return board.epd(en_passant="xfen")


def epds(mht: MultiHypothesisTracker) -> List[str]:
    return [epd(board) for board in mht.boards]


class History:
    """A class to parse and analyze reconchess game histories from a simple format

    Game histories are based on a single string input recording sense squares and requested moves. Squares are recorded
    by name, with 00 representing no square (following 0000 as the null move uci). Moves are represented by uci. For
    example, history "00 e2e3 f2 f7f5 c7" records that white chose not to sense on it's first turn then advanced a pawn
    to e3, black sensed at f2 and advanced a pawn to f5, and lastly white sensed at c7.
    """

    def __init__(self, history_string: str):
        self.history_string = history_string
        self.history = tuple(history_string.split())
        self.num_actions = len(self.history)
        self.num_moves = self.num_actions // 2
        self.num_moves_by_white = (self.num_moves + 1) // 2
        self.num_moves_by_black = self.num_moves // 2

        # Record the true board following each move
        board = chess.Board()
        self.board = [epd(board)]
        # Record the possible epds according to each player following each action
        # This can be indexed [color][action_num] to return a list of epds
        mhts = [MultiHypothesisTracker(), MultiHypothesisTracker()]
        self.possible_epds = [[epds(mht)] for mht in mhts]

        history_iter = iter(self.history)
        try:
            while True:
                # Sense step
                square = next(history_iter)
                square = None if square == "00" else chess.parse_square(square)
                result = simulate_sense(board, square)
                mhts[board.turn].sense(square, result)
                self.possible_epds[board.turn].append(epds(mhts[board.turn]))
                self.possible_epds[not board.turn].append(self.possible_epds[not board.turn][-1])
                # Move step
                requested_move = chess.Move.from_uci(next(history_iter))
                taken_move, capture_square = simulate_move(board, requested_move)
                mhts[board.turn].move(requested_move, taken_move, capture_square)
                mhts[not board.turn].op_move(capture_square)
                self.possible_epds[board.turn].append(epds(mhts[board.turn]))
                self.possible_epds[not board.turn].append(epds(mhts[not board.turn]))
                board.push(taken_move)

        except StopIteration:
            pass

        self.winner = not board.turn
        self.win_reason = 'timeout' if board.king(board.turn) else 'king capture'

    def __str__(self):
        return f"History({self.history_string})"


def _main():
    history = History("00 e2e3 f2 f7f5 c7 f2f4")
    print(history)
    print(history.num_actions, history.num_moves, history.num_moves_by_white, history.num_moves_by_black)
    print(history.board[-1])


if __name__ == "__main__":
    _main()
