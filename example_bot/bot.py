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
        self.engine = create_engine()

        self.color = None
        self.turn_num = None

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
        self.mht.boards = self.mht.boards[:3_000]
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
        # You can think of the choice of a sense square as a partition of the possible boards, where
        # possible boards are equivalent if the sense result centered on that square is the same. As
        # such, it is possible to identify choices that are dominated (they can't possibly yield
        # information that would not be revealed by the dominating choice) in terms of these
        # partitions. Additionally, it is easy to write simple logic to recommend a sense choice
        # based on the partitions. For convenience, the following function recommends the square
        # whose biggest partition is smallest (the minimax remaining number of boards after the
        # hypothetical sense step).
        _, minimax_square = non_dominated_sense(self.mht.boards)
        return minimax_square

    def handle_sense_result(
        self, sense_result: List[Tuple[chess.Square, Optional[chess.Piece]]]
    ):
        if sense_result:  # False if we skipped sensing
            # The sense target is just the middle of the list when in sorted order. Note that the
            # sense result from our simulate_sense utility and from the reconchess LocalGame are
            # already in sorted order, but that sense results from server games will not necessarily
            # be sorted.
            sense_result = sorted((s, p) for s, p in sense_result)
            square = sense_result[4][0]
            # Here we filter the list of possible boards to include only those that match over the
            # sensed region.
            self.mht.sense(square, sense_result)

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

    def handle_game_end(
        self,
        winner_color: Optional[Color],
        win_reason: Optional[WinReason],
        game_history: GameHistory,
    ):
        self.engine.close()


def vote(possible_requested_moves, boards, engine):
    # This is just one of the many ways to aggregate the perfect-information recommendations over
    # each possible board into a move decision. Additionally, the general approach of aggregating
    # recommendations over MHT hypotheses is not necessarily the best strategy.
    # Imperfect-information-native approaches that don't involve MHT (like
    # counterfactual-regret-minimization) should theoretically outperform MHT approaches, though
    # through the first two competitions MHT bots such as StrangeFish and Oracle continue to be top
    # performers. (Also, MHT can be helpful in CFR and similar approaches, for example by
    # identifying dominated actions.)
    #
    # In this function, we choose a move to request by letting stockfish place votes over a random
    # subset of the MHT boards and selecting a winner by ranked-choice-voting. We must separately
    # handle unusual board configurations (i.e. the opponent king can be captured, or we are in
    # checkmate when it is our turn to move) and we let stockfish rank move options on the rest.
    # Because sometimes multiple move requests would be amended to the same taken move, we allow
    # choices to have a tied rank and nominate all such move requests with the same rank as the
    # taken move suggested by stockfish. In the unusual case where we have multiple options for
    # capturing the opponent king, this also gives us a way to nominate all those options as equal
    # first choices.
    votes = []
    random.shuffle(boards)
    for board in tqdm(boards[:1200]):
        my_ranked_votes = []
        votes.append(my_ranked_votes)
        # All requested moves that result in the voted-for taken moves are counted equally.
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
                    pass  # No moves were suggested because we are in checkmate on this board.
    # Ranked-choice-voting is an iterative algorithm that scores candidates by the number of
    # first-choice votes they receive. If a candidate receives a majority, it is selected.
    # Otherwise, the lowest-scoring candidate is eliminated and the process repeats. Because this
    # version allows tied ranking, the total number of votes can exceed the number of voters.
    while True:
        if not votes:
            return chess.Move.null()
        threshold = len(votes) // 2
        first_choice_votes = defaultdict(int)
        for vote in votes:
            for move in vote[0]:
                first_choice_votes[move] += 1
        max_move, max_num_votes = max(first_choice_votes.items(), key=lambda x: x[1])
        if max_num_votes >= threshold:
            return max_move
        min_move, min_num_votes = min(first_choice_votes.items(), key=lambda x: x[1])
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
