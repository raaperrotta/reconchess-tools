from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import chess.engine
from reconchess import Color, Square

from reconchess_tools.mht import board_fingerprint


class InformationRepresentation[T](ABC):
    def __init__(self):
        self.info: T = self._init_info()

    @abstractmethod
    def show(self) -> T: ...

    @abstractmethod
    def _init_info(self): ...

    @abstractmethod
    def record_color(self, color: Color): ...

    @abstractmethod
    def record_starting_board(self, board: chess.Board): ...

    @abstractmethod
    def record_opponent_name(self, opponent_name: str): ...

    @abstractmethod
    def record_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]): ...

    @abstractmethod
    def record_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           capture_square: Optional[Square]): ...

    @abstractmethod
    def record_opponent_capture(self, capture_square: Optional[Square]): ...


class ListInfo(InformationRepresentation[List]):
    """Add all information except opponent name to a list to disambiguate game states"""

    def _init_info(self) -> List:
        return []

    @abstractmethod
    def show(self) -> List:
        return self.info

    def record_color(self, color: Color):
        self.info.append(color)

    def record_starting_board(self, board: chess.Board):
        self.info.append(board_fingerprint(board))

    def record_opponent_name(self, opponent_name: str):
        ...

    def record_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        self.info.append(sense_result)

    def record_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           capture_square: Optional[Square]):
        self.info.append((requested_move, taken_move, capture_square))

    def record_opponent_capture(self, capture_square: Optional[Square]):
        self.info.append(capture_square)
