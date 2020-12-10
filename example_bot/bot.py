import random
from collections import defaultdict
from typing import Optional, List, Tuple

import chess.engine
from reconchess import Player, Color, WinReason, GameHistory
from tqdm import tqdm

from reconchess_tools.mht import MultiHypothesisTracker
from reconchess_tools.stockfish import create_engine
from reconchess_tools.strategy import non_dominated_sense, certain_win
from reconchess_tools.utilities import simulate_move


class MhtBot(Player):
    def __init__(self):
        self.mht = MultiHypothesisTracker()
        self.engine = create_engine()

        self.color = None
        self.turn_num = None

    def handle_game_start(
        self, color: chess.Color, board: chess.Board, opponent_name: str
    ):
        self.color = color
        self.turn_num = -1

    def handle_opponent_move_result(
        self, captured_my_piece: bool, capture_square: Optional[chess.Square]
    ):
        self.turn_num += 1
        if self.turn_num == 0 and self.color == chess.WHITE:
            return  # This is called even before the first action. In that case, do nothing.
        self.mht.boards = self.mht.boards[:3_000]
        self.mht.op_move(capture_square)

    def choose_sense(
        self,
        sense_actions: List[chess.Square],
        move_actions: List[chess.Move],
        seconds_left: float,
    ) -> Optional[chess.Square]:
        _, minimax_square = non_dominated_sense(self.mht.boards)
        return minimax_square

    def handle_sense_result(
        self, sense_result: List[Tuple[chess.Square, Optional[chess.Piece]]]
    ):
        if sense_result:  # False if we skipped sensing
            sense_result = sorted((s, p) for s, p in sense_result)
            square = sense_result[4][0]
            self.mht.sense(square, sense_result)

    def choose_move(
        self, move_actions: List[chess.Move], seconds_left: float
    ) -> Optional[chess.Move]:
        if not self.mht.boards:
            return random.choice(move_actions)
        # If any move is guaranteed to result in a king capture, take it!
        winning_move = certain_win(self.mht.boards)
        if winning_move:
            return winning_move
        # Otherwise, let stockfish evaluate over all possible boards and tally a vote
        move = vote(move_actions, self.mht.boards, self.engine)
        return move or None

    def handle_move_result(
        self,
        requested_move: Optional[chess.Move],
        taken_move: Optional[chess.Move],
        captured_opponent_piece: bool,
        capture_square: Optional[chess.Square],
    ):
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


def vote(possible_requested_moves, boards, engine):
    votes = []
    random.shuffle(boards)
    for board in tqdm(boards[:1200]):
        my_ranked_votes = []
        votes.append(my_ranked_votes)
        # All requested moves that result in the voted-for taken moves are counted equally
        move_lookup = defaultdict(list)
        for requested_move in possible_requested_moves:
            taken_move, _ = simulate_move(board, requested_move)
            move_lookup[taken_move].append(requested_move)
        # Boards where the king can be captured cannot be scored by stockfish.
        # Instead, vote equally for all possible king capture moves.
        op_king_square = board.king(not board.turn)
        king_attackers = board.attackers(board.turn, op_king_square)
        if king_attackers:
            my_ranked_votes.append([])
            for attacker in king_attackers:
                taken_move = chess.Move(attacker, op_king_square)
                requested_moves = move_lookup[taken_move]
                my_ranked_votes[0] += requested_moves
        else:
            board.clear_stack()
            results = engine.analyse(
                board, limit=chess.engine.Limit(depth=8), multipv=4
            )
            for result in results:
                try:
                    taken_move = result["pv"][0]
                    my_ranked_votes.append(move_lookup[taken_move])
                except KeyError:
                    pass  # no moves were suggested because we are in checkmate on this board
    while True:
        if not votes:
            return chess.Move.null()
        threshold = len(votes) // 2
        first_choice_votes = defaultdict(int)
        for vote in votes:
            for move in vote[0]:
                first_choice_votes[move] += 1
        max_move, max_num_votes = max(first_choice_votes.items(), key=lambda x: x[1])
        min_move, min_num_votes = min(first_choice_votes.items(), key=lambda x: x[1])
        if max_num_votes >= threshold:
            return max_move
        revised_votes = []
        for vote in votes:
            revised_vote = []
            for group in vote:
                revised_group = [move for move in group if move != min_move]
                if revised_group:
                    revised_vote.append(revised_group)
            if revised_vote:
                revised_votes.append(revised_vote)
        votes = revised_votes
