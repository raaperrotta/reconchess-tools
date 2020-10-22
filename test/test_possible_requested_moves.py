import chess

from reconchess_tools.utilities import possible_requested_moves


def run(move_history: str, expected: str):
    board = chess.Board()
    for move in move_history.split():
        board.push(chess.Move.from_uci(move))
    assert set(possible_requested_moves(board)) == {
        chess.Move.from_uci(move) for move in expected.split()
    }


def test_opening_moves_for_white():
    run(
        "",
        "g1h3 g1f3 b1c3 b1a3 h2h3 g2g3 f2f3 e2e3 d2d3 c2c3 b2b3 a2a3 h2h4 g2g4 f2f4 e2e4 d2d4 "
        + "c2c4 b2b4 a2a4 a2b3 b2a3 b2c3 c2b3 c2d3 d2c3 d2e3 e2d3 e2f3 f2e3 f2g3 g2f3 g2h3 h2g3 0000",
    )


def test_opening_moves_for_black():
    run(
        "0000",
        "g8h6 g8f6 b8c6 b8a6 h7h6 g7g6 f7f6 e7e6 d7d6 c7c6 b7b6 a7a6 h7h5 g7g5 f7f5 e7e5 d7d5 "
        + "c7c5 b7b5 a7a5 a7b6 b7a6 b7c6 c7b6 c7d6 d7c6 d7e6 e7d6 e7f6 f7e6 f7g6 g7f6 g7h6 h7g6 0000",
    )
