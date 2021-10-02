import random
from typing import List, Optional, Tuple

import chess.engine
from reconchess import Color, GameHistory, Player, WinReason

from dynamic.util import sense_result_to_string
from reconchess_tools.mht import MultiHypothesisTracker
from reconchess_tools.strategy import (
    certain_win,
    minimax_sense,
    non_dominated_sense_by_own_pieces,
)


class MhtBot(Player):
    def __init__(self):
        # We use the MHT object to handle all uncertainty tracking. In the methods below, we call
        # the appropriate update methods of the MHT object after which its boards property contains
        # the list of all chess boards that might be the true state of the game board. It is
        # important to be aware that both that list and the boards within it are mutable. It is the
        # responsibility of the user to avoid mutating those except intentionally, for example, we
        # slice the list below to prevent if from growing too large, even though that might mean we
        # lose track of the true board state.
        self.mht = MultiHypothesisTracker()
        # We use Stockfish (though this could be any UCI-compliant engine) to analyze the possible
        # boards. After handling boards that are not valid in regular chess (i.e. the opponent king
        # can be captured, or we are in checkmate) we ask stockfish to suggest a few moves, which we
        # aggregate using a variation of ranked-choice-voting. (More on that below.)
        self.engine = None

        self.color = None
        self.turn_num = None

        self.infoset = None

    def handle_game_start(
        self, color: chess.Color, board: chess.Board, opponent_name: str
    ):
        self.color = color
        # Initializing this to -1 makes handling the first turn easier
        self.turn_num = -1
        self.mht.reset()
        self.infoset = [color]

    def handle_opponent_move_result(
        self, captured_my_piece: bool, capture_square: Optional[chess.Square]
    ):
        self.turn_num += 1
        # This is called even before the first action. In that case, do nothing.
        if self.turn_num == 0 and self.color == chess.WHITE:
            return
        # Though we risk losing track of the true board, to avoid the number of possible boards
        # growing too large we limit its size here. Expanding the possible boards to account for all
        # possible opponent moves is the most demanding step in the MHT processing so it is critical
        # that we ensure this next step is tractable.
        self.mht.boards = self.mht.boards[:3_000]
        # The true board could be the board that results from any possible move on each board that
        # was tracked before the move. That results in a growth factor of roughly 30, and higher
        # still in the late game when the board is more open.
        self.mht.op_move(capture_square)
        self.infoset.append(capture_square)
        print(self.infoset)
        print({b.epd(en_passant="xfen") for b in self.mht.boards})

    def choose_sense(
        self,
        sense_actions: List[chess.Square],
        move_actions: List[chess.Move],
        seconds_left: float,
    ) -> Optional[chess.Square]:
        if not self.mht.boards:
            return None
        # You can think of the choice of a sense square as a partition of the possible boards,
        # where possible boards are equivalent if the sense result centered on that square is the
        # same. As such, it is possible to identify choices that are dominated (they can't
        # possibly yield information that would not be revealed by the dominating choice) in
        # terms of these partitions. Additionally, it is easy to write simple logic to recommend
        # a sense choice based on the partitions. For example, the following function recommends
        # the square whose biggest partition is smallest (the minimax remaining number of boards
        # after the hypothetical sense step).
        self.mht.speculate_sense(non_dominated_sense_by_own_pieces(self.mht.boards[0]))
        minimax_square = minimax_sense(self.mht.sense_speculation)
        return minimax_square

    def handle_sense_result(
        self, sense_result: List[Tuple[chess.Square, Optional[chess.Piece]]]
    ):
        if sense_result:  # False if we skipped sensing
            # The sense target is just the middle of the list when in sorted order. Note that the
            # sense result from our simulate_sense utility and from the reconchess LocalGame are
            # already in sorted order, but that sense results from server games will not necessarily
            # be sorted. Also, the square, piece pairs are tuples except in server games, in which
            # case they are lists and we convert them to tuples here.
            sorted_result = sorted((s, p) for s, p in sense_result)
            square = sorted_result[4][0]
            # Here we filter the list of possible boards to include only those that match over the
            # sensed region.
            self.mht.sense(square, sorted_result)
            self.infoset.append((square, sense_result_to_string(sorted_result)))
            print(self.infoset)
            print({b.epd(en_passant="xfen") for b in self.mht.boards})

    def choose_move(
        self, move_actions: List[chess.Move], seconds_left: float
    ) -> Optional[chess.Move]:
        # Since we limit the size of the MHT board list, it is possible for that list to become
        # empty. In that case we fall back to requesting moves randomly.
        if not self.mht.boards:
            return random.choice(move_actions)
        # If any move is guaranteed to result in a king capture, take it!
        winning_move = certain_win(self.mht.boards)
        if winning_move:
            return winning_move
        # Otherwise, let stockfish evaluate over all possible boards and tally a vote.
        move = vote(move_actions, self.mht.boards, self.engine)
        # The reconchess library encodes passing (null) moves as None so we convert
        # chess.Move.null() to None here using the fact that it evaluates to truthy false.
        return move or None

    def handle_move_result(
        self,
        requested_move: Optional[chess.Move],
        taken_move: Optional[chess.Move],
        captured_opponent_piece: bool,
        capture_square: Optional[chess.Square],
    ):
        # Here we update all possible boards by pushing our move to them and only keeping the ones
        # with the same capture square as observed.
        self.mht.move(
            requested_move or chess.Move.null(),
            taken_move or chess.Move.null(),
            capture_square,
        )
        self.infoset.append(
            (
                (requested_move or chess.Move.null()).uci(),
                (taken_move or chess.Move.null()).uci(),
                capture_square,
            )
        )
        print(self.infoset)
        print({b.epd(en_passant="xfen") for b in self.mht.boards})

    def handle_game_end(
        self,
        winner_color: Optional[Color],
        win_reason: Optional[WinReason],
        game_history: GameHistory,
    ):
        self.engine.close()


def vote(possible_requested_moves, boards, engine):
    return random.choice(possible_requested_moves)
