from dataclasses import dataclass

import chess


@dataclass
class Infoset:
    ...


@dataclass
class GameState:
    board: chess.Board
    infoset_white: Infoset
    infoset_black: Infoset


def _main():
    state = GameState(chess.Board(), Infoset(), Infoset())


if __name__ == "__main__":
    _main()
