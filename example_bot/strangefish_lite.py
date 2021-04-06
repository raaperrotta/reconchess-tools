import random
from typing import Optional, List, Tuple

import chess.engine
import numpy as np
from reconchess import Player, Color, WinReason, GameHistory
from tqdm import tqdm

from reconchess_tools.mht import MultiHypothesisTracker, board_fingerprint
from reconchess_tools.stockfish import create_engine
from reconchess_tools.strategy import (
    certain_win,
    non_dominated_sense_by_own_pieces, minimax_sense, )


class StrangeFishLite(Player):
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
        # can be captured, or we are in checkmate) we ask stockfish to score the position.
        self.engine = create_engine()

        self.color = None
        self.turn_num = None

        self.move_scores = None

    def handle_game_start(
        self, color: chess.Color, board: chess.Board, opponent_name: str
    ):
        self.color = color
        # Initializing this to -1 makes handling the first turn easier
        self.turn_num = -1
        self.mht.reset()

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
        if len(self.mht.boards) > 2_000:
            self.mht.boards = random.sample(self.mht.boards, 2_000)
        # The true board could be the board that results from any possible move on each board that
        # was tracked before the move. That results in a growth factor of roughly 30, and higher
        # still in the late game when the board is more open.
        self.mht.op_move(capture_square)

    def choose_sense(
        self,
        sense_actions: List[chess.Square],
        move_actions: List[chess.Move],
        seconds_left: float,
    ) -> Optional[chess.Square]:
        # Since we limit the size of the MHT board list, it is possible for that list to become
        # empty. In that case there is no point sensing.
        if not self.mht.boards:
            return None

        # You can think of the choice of a sense square as a partition of the possible boards,
        # where possible boards are equivalent if the sense result centered on that square is the
        # same. As such, it is possible to identify choices that are dominated (they can't
        # possibly yield information that would not be revealed by the dominating choice) in
        # terms of these partitions.
        self.mht.speculate_sense(non_dominated_sense_by_own_pieces(self.mht.boards[0]))

        if len(self.mht.boards) > 0:  # 6_000:
            minimax_square = minimax_sense(self.mht.sense_speculation)
            self.move_scores = None
            return minimax_square

        if chess.Move.null() not in move_actions:
            move_actions.append(chess.Move.null())  # Passing is not included in move_actions TODO is this true on the server too?
        self.mht.speculate_move(move_actions)

        # The basis for our decision making is the position strength score for the board that is the
        # result of each requested move on each possible board. We want to consider the distribution
        # of scores that could result from each move request in making our move. And we want to
        # consider how the partition of boards be our sense choice affects our move decision.
        self.move_scores = np.array(score_moves(self.engine, self.mht.boards, *self.mht.move_speculation))

        # Deviating from StrangeFish, we follow a move policy via minimax of position strength. Our
        # sense policy is to sense so as to minimax the minimax move result plus an adjustment for
        # the number of boards remaining.
        minimax_square = None
        minimax_sense_score = -float("inf")
        for square, sense_results in self.mht.sense_speculation.items():
            min_sense_score = float("inf")
            for partition in sense_results.values():
                is_in_partition = np.array([board in partition for board in self.mht.boards])
                subset_scores = self.move_scores[is_in_partition]
                minimax_move_score = subset_scores.min(axis=0).max()
                # Adjust score based on number of boards remaining
                num_boards = len(partition)
                uncertainty_adjustment = 0.1 / (1.0 + num_boards / 20.0)
                minimax_move_score += uncertainty_adjustment
                min_sense_score = min(min_sense_score, minimax_move_score)
            if min_sense_score > minimax_sense_score:
                minimax_sense_score = min_sense_score
                minimax_square = square

        return minimax_square

    def handle_sense_result(
        self, sense_result: List[Tuple[chess.Square, Optional[chess.Piece]]]
    ):
        if sense_result:  # False if we skipped sensing
            # The sense target is just the middle of the list when in sorted order. Note that the
            # sense result from our simulate_sense utility and from the reconchess LocalGame are
            # already in sorted order, but that sense results from server games will not necessarily
            # be sorted. Also, the square-piece pairs are tuples except in server games, in which
            # case they are lists and we convert them to tuples here.
            sorted_result = sorted((s, p) for s, p in sense_result)
            square = sorted_result[4][0]
            # Here we filter the list of possible boards to include only those that match over the
            # sensed region.
            boards_before_sense = self.mht.boards.copy()
            self.mht.sense(square, sorted_result)
            is_in_partition = np.array([board in self.mht.boards for board in boards_before_sense])
            if self.move_scores is not None:
                self.move_scores = self.move_scores[is_in_partition]

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

        # If there were too many boards before sensing, calculate the scores now
        if self.move_scores is None:
            if chess.Move.null() not in move_actions:
                move_actions.append(
                    chess.Move.null())  # Passing is not included in move_actions TODO is this true on the server too?
            self.mht.speculate_move(move_actions)
            self.move_scores = np.array(
                score_moves(self.engine, self.mht.boards, *self.mht.move_speculation))

        # Otherwise, use the scores we calculated before sensing to choose the minimax move.
        minimax_move = self.mht.move_speculation[0][self.move_scores.min(axis=0).argmax()]
        return minimax_move or None

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

    def handle_game_end(
        self,
        winner_color: Optional[Color],
        win_reason: Optional[WinReason],
        game_history: GameHistory,
    ):
        self.engine.close()


def score_moves(
        engine,
        boards: List[chess.Board],
        moves: List[chess.Move],
        all_move_results: List[Tuple[chess.Move, Optional[chess.Square]]]
):
    cache = {}
    all_scores = []
    with tqdm(desc="Scoring possible move outcomes", total=len(boards) * len(moves)) as pbar:
        for board, move_results in zip(boards, all_move_results):
            scores = []
            for requested_move, (taken_move, capture_square) in zip(moves, move_results):
                board.push(taken_move)
                fingerprint = board_fingerprint(board)
                try:
                    score = cache[fingerprint]
                except KeyError:
                    score = cache[fingerprint] = position_strength(engine, board)
                board.pop()  # Put the board back the way we found it
                scores.append(score)
                pbar.update()
            all_scores.append(scores)
    return all_scores


def position_strength(engine, board: chess.Board):
    """Return a float score representing the position strength for the player that just moved"""
    if board.king(board.turn) is None:  # Opponent king has been captured!
        return 1.0
    # if board.is_attacked_by(board.turn, board.king(not board.turn)):  # We are in check
    if board.was_into_check():  # We are in check
        return 0.0
    # Don't include the move history in the analysis, but put it back so we can pop the last move
    # temporary = board.move_stack
    # board.clear_stack()
    engine_result = engine.analyse(board.copy(stack=False), chess.engine.Limit(depth=4))
    # board.move_stack = temporary
    centipawn_score = engine_result['score'].pov(not board.turn).score(mate_score=9999)
    # https: //www.chessprogramming.org/Pawn_Advantage,_Win_Percentage,_and_Elo
    estimated_prob_win = 1.0 / (1.0 + 10.0 ** (-centipawn_score / 400.0))
    return estimated_prob_win
