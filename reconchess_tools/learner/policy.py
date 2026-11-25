from abc import abstractmethod, ABC
from typing import List, Optional, Tuple

import chess.engine
from reconchess import Color, GameHistory, Player, WinReason, Square

from reconchess_tools.learner.info import InformationRepresentation


class Policy[Info: InformationRepresentation](ABC):
    @abstractmethod
    def sense(self, info: Info) -> Optional[chess.Square]: ...

    @abstractmethod
    def move(self, info: Info) -> chess.Move: ...


class GenericPlayer[I: InformationRepresentation, P: Policy[I]](Player):
    """Define a base class for agents that learn a functional policy for sense and move choices"""
    def __init__(self):
        super().__init__()
        self.info = I()
        self.policy = P()

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.info = I()
        self.info.record_color(color)
        self.info.record_starting_board(board)
        self.info.record_opponent_name(opponent_name)

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        self.info.record_opponent_capture(capture_square)

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        return self.policy.sense(self.info)

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        # The sense target is just the middle of the list when in sorted order. Note that the
        # sense result from our simulate_sense utility and from the reconchess LocalGame are
        # already in sorted order, but that sense results from server games will not necessarily
        # be sorted. Also, the square-piece pairs are tuples except in server games, in which
        # case they are lists and we convert them to tuples here.
        sorted_result = sorted((s, p) for s, p in sense_result)
        self.info.record_sense_result(sorted_result)

    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        return self.policy.move(self.info)

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square]):
        self.info.record_move_result(requested_move, taken_move, capture_square)

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        ...


class SubclassPlayer(Player, InformationRepresentation, Policy, ABC):
    """Define a base class for agents that learn a functional policy for sense and move choices"""
    def __init__(self):
        super().__init__()

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.reset()  # TODO?
        self.record_color(color)
        self.record_starting_board(board)
        self.record_opponent_name(opponent_name)

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        self.record_opponent_capture(capture_square)

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        return self.sense(self.show())

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        # The sense target is just the middle of the list when in sorted order. Note that the
        # sense result from our simulate_sense utility and from the reconchess LocalGame are
        # already in sorted order, but that sense results from server games will not necessarily
        # be sorted. Also, the square-piece pairs are tuples except in server games, in which
        # case they are lists; we convert them to tuples here.
        sorted_result = sorted((s, p) for s, p in sense_result)
        self.record_sense_result(sorted_result)

    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        return self.move(self.show())

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square]):
        self.record_move_result(requested_move, taken_move, capture_square)

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        ...
