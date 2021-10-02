"""Define an openai gym style environment for playing RBC games against random opponents"""
import logging
import random

import chess
from reconchess import LocalGame, notify_opponent_move_results, play_sense, play_turn
from reconchess.bots.attacker_bot import AttackerBot
from reconchess.bots.random_bot import RandomBot
from reconchess.bots.trout_bot import TroutBot

from example_bot.bot import MhtBot
from reconchess_tools.strategy import non_dominated_sense_by_own_pieces
from sac.bot import LEARN_TO_SENSE, SacBot, SacState

LOG = logging.getLogger(__name__)

OPPONENTS = {
    RandomBot: 1,
    AttackerBot: 1,
    TroutBot: 1,
}
_OPPONENT_CLASSES = list(OPPONENTS.keys())
_OPPONENT_WEIGHTS = list(OPPONENTS.values())

SENSE = False
MOVE = True
ACTION_TYPE_NAMES = ["Sense", "Move"]


def get_opponent():
    return random.choices(_OPPONENT_CLASSES, _OPPONENT_WEIGHTS, k=1)[0]()


class Env:

    null_state = SacState([chess.Board()], [])

    def __init__(
        self,
        trainee_side,
        mht_board_limit=2_000,
    ):
        self.trainee_side = trainee_side
        self.mht_board_limit = mht_board_limit

        self.trainee = MhtBot()
        self.trainee.engine.close()  # Don't need this

        self.game = None
        self.opponent = None
        # self.trainee_side = None
        self.next_action_type = None
        self.record = [0, 0, 0]

    def reset(self):
        LOG.info(f"My overall record is %s:%s:%s", *[f"{r:,.0f}" for r in self.record])
        self.opponent = get_opponent()
        self.game = LocalGame()
        # self.trainee_side = chess.WHITE if random.random() < 0.5 else chess.BLACK
        LOG.info(
            f"Starting a new game as {chess.COLOR_NAMES[self.trainee_side]} against {self.opponent.__class__.__name__}"
        )

        self.trainee.handle_game_start(
            self.trainee_side, chess.Board(), self.opponent.__class__.__name__
        )
        self.opponent.handle_game_start(
            not self.trainee_side, chess.Board(), self.trainee.__class__.__name__
        )
        self.game.start()

        if self.trainee_side == chess.BLACK:
            # Play opponent's first turn
            play_turn(self.game, self.opponent)
            notify_opponent_move_results(self.game, self.trainee)
            if LEARN_TO_SENSE:
                self.next_action_type = SENSE
                possible_actions = non_dominated_sense_by_own_pieces(self.game.board)
            else:
                play_sense(self.game, self.trainee, [], [])
                self.next_action_type = MOVE
                possible_actions = self.game.move_actions()
        else:
            # Play trainee's first sense step
            notify_opponent_move_results(self.game, self.trainee)
            sense_result = self.game.sense(None)
            self.trainee.handle_sense_result(sense_result)
            self.next_action_type = MOVE
            possible_actions = self.game.move_actions()

        return SacState(self.trainee.mht.boards, possible_actions)

    def step(self, action):
        LOG.debug("It is my turn to %s", ACTION_TYPE_NAMES[self.next_action_type])
        state, reward, done = (
            self._move(action) if self.next_action_type == MOVE else self._sense(action)
        )
        LOG.debug(
            "The current true board state is\n%s",
            self.game.board.unicode(invert_color=True, empty_square="."),
        )
        LOG.debug(
            "I see %s possible boards and have %s possible actions",
            f"{state.boards.shape[0]:,.0f}",
            f"{len(state.actions):,.0f}",
        )
        if (
            not done and len(self.trainee.mht.boards) > self.mht_board_limit
        ):  # Declare this game lost to aid early sense training
            LOG.info(
                f"I see too many boards so I resigned as {chess.COLOR_NAMES[self.trainee_side]} against {self.opponent.__class__.__name__}!"
            )
            self.record[2] += 1
            return self.null_state, -1, True
        return state, reward, done

    def _move(self, action):
        LOG.debug("I am taking move %s", action)
        # My turn to move
        requested_move, taken_move, opt_enemy_capture_square = self.game.move(action)
        self.trainee.handle_move_result(
            requested_move,
            taken_move,
            opt_enemy_capture_square is not None,
            opt_enemy_capture_square,
        )
        if self.game.is_over():  # We won!
            LOG.info(
                f"I won this game as {chess.COLOR_NAMES[self.trainee_side]} against {self.opponent.__class__.__name__}!"
            )
            self.record[0] += 1
            return self.null_state, 1, True
        self.game.end_turn()
        # Opponent's turn
        play_turn(self.game, self.opponent)
        if self.game.is_over():  # We lost!
            LOG.info(
                f"I lost this game as {chess.COLOR_NAMES[self.trainee_side]} against {self.opponent.__class__.__name__}!"
            )
            self.record[1] += 1
            return self.null_state, -1, True
        notify_opponent_move_results(self.game, self.trainee)

        if LEARN_TO_SENSE:
            self.next_action_type = SENSE
            return (
                SacState(
                    self.trainee.mht.boards,
                    non_dominated_sense_by_own_pieces(self.game.board),
                ),
                0,
                False,
            )

        self.next_action_type = MOVE
        # Move and sense actions provided by the game are not used by MhtBot
        play_sense(self.game, self.trainee, [], [])
        return (
            SacState(
                self.trainee.mht.boards,
                self.game.move_actions(),
            ),
            0,
            False,
        )

    def _sense(self, action):
        LOG.debug("I am sensing at %s", chess.SQUARE_NAMES[action])
        self.next_action_type = MOVE
        # My turn to sense
        sense_result = self.game.sense(action)
        self.trainee.handle_sense_result(sense_result)
        return SacState(self.trainee.mht.boards, self.game.move_actions()), 0, False
