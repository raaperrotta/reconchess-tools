import chess

from reconchess_tools.utilities import possible_requested_moves


def run(move_history: str, expected: str):
    board = chess.Board()
    for move in move_history.split():
        board.push(chess.Move.from_uci(move))
    moves_under_test = set(possible_requested_moves(board))
    expected_moves = {chess.Move.from_uci(move) for move in expected.split()}
    extra = moves_under_test - expected_moves
    missing = expected_moves - moves_under_test
    assert extra == set(), f"Included these extra moves {[m.uci() for m in extra]}"
    assert (
        missing == set()
    ), f"Missing these expected moves {[m.uci() for m in missing]}"
    assert moves_under_test == expected_moves


def test_opening_moves_for_white():
    run(
        "",
        "g1h3 g1f3 b1c3 b1a3 h2h3 g2g3 f2f3 e2e3 d2d3 c2c3 b2b3 a2a3 h2h4 g2g4 f2f4 e2e4 d2d4 c2c4 "
        "b2b4 a2a4 a2b3 b2a3 b2c3 c2b3 c2d3 d2c3 d2e3 e2d3 e2f3 f2e3 f2g3 g2f3 g2h3 h2g3 0000",
    )


def test_opening_moves_for_black():
    run(
        "0000",
        "g8h6 g8f6 b8c6 b8a6 h7h6 g7g6 f7f6 e7e6 d7d6 c7c6 b7b6 a7a6 h7h5 g7g5 f7f5 e7e5 d7d5 c7c5 "
        "b7b5 a7a5 a7b6 b7a6 b7c6 c7b6 c7d6 d7c6 d7e6 e7d6 e7f6 f7e6 f7g6 g7f6 g7h6 h7g6 0000",
    )


def test_moves_with_en_passant():
    run(
        "c2c4 0000 c4c5 b7b5",
        "g1h3 g1f3 d1a4 d1b3 d1c2 b1c3 b1a3 c5c6 h2h3 g2g3 f2f3 e2e3 d2d3 b2b3 a2a3 h2h4 g2g4 f2f4 "
        "e2e4 d2d4 b2b4 a2a4 a2b3 b2a3 b2c3 d2c3 d2e3 e2d3 e2f3 f2e3 f2g3 g2f3 g2h3 h2g3 c5b6 "
        "c5d6 0000",
    )


def test_moves_with_castling():
    run(
        "e2e3 0000 f1d3 0000 g1h3 0000",
        "0000 a2a3 a2a4 a2b3 b1a3 b1c3 b2a3 b2b3 b2b4 b2c3 c2b3 c2c3 c2c4 d1e2 d1f3 d1g4 d1h5 d2c3 "
        "d3a6 d3b5 d3c4 d3e2 d3e4 d3f1 d3f5 d3g6 d3h7 e1e2 e1f1 e1g1 e3d4 e3e4 e3f4 f2f3 f2f4 "
        "f2g3 g2f3 g2g3 g2g4 h1f1 h1g1 h2g3 h3f4 h3g1 h3g5",
    )
    run(
        "0000 g7g6 0000 g8f6 0000 f8h6",
        "g1h3 g1f3 b1c3 b1a3 h2h3 g2g3 f2f3 e2e3 d2d3 c2c3 b2b3 a2a3 h2h4 g2g4 f2f4 e2e4 d2d4 c2c4 "
        "b2b4 a2a4 a2b3 b2a3 b2c3 c2b3 c2d3 d2c3 d2e3 e2d3 e2f3 f2e3 f2g3 g2f3 g2h3 h2g3 0000",
    )
    run(
        "g1h3 g7g6 h3g5 g8f6 g5e6 f8h6 e6f8",
        "0000 a7a5 a7a6 a7b6 b7a6 b7b5 b7b6 b7c6 b8a6 b8c6 c7b6 c7c5 c7c6 c7d6 d7c6 d7d5 d7d6 d7e6 "
        "e7d6 e7e5 e7e6 e8f8 e8g8 f6d5 f6e4 f6g4 f6g8 f6h5 f7e6 g6f5 g6g5 g6h5 h6c1 h6d2 h6e3 "
        "h6f4 h6f8 h6g5 h6g7 h8f8 h8g8",
    )


def test_can_capture_king():
    run(
        "f2f3 g7g5 g1h3 f7f5 h3g5 d7d5 g5h7 d5d4 e2e4 a7a6 h1g1 g8f6 g2g3 e8d7 e4f5 e7e5 h2h4 f6g4 "
        "b1c3 c7c5 f1a6 d8a5 b2b3 d4d3 a6c4 0000 f3f4 a5a6 0000 h8h7 h4h5 g4e3 b3b4 a6a2 b4b5 "
        "d7e7 g1h1 e7d8 c4d3 a8a7 c1b2 e5f4 f5f6 h7h6 f6f7 h6h5 d3f1 a2b3 c3b1 b3d5 h1h5 d5d4 "
        "a1a5 d4d5 b2a1 c5c4 c2c3 a7a5 h5h7 d5d7 a1b2 d7h3 f1d3 e3g2 e1f2 h3h4 f2f3 a5a1 d1e1 "
        "c4d3 f3g4 d8d7 g4f5 d7e7 b2a3 h4h5 e1d1 e7f7 f5f6 c8g4 a3b4 g2e3 f6g6 f7e6 b4d6 0000 "
        "g6g5 e3f5 d1e1 a1a6 g5g6 h5g5 h7h1 b8c6 d6e7 a6a5 h1h6 e6e7 g6f5 e7d7 f5e5",
        "f8g7 f8e7 f8h6 f8d6 f8c5 f8b4 f8a3 d7e8 d7d8 d7c8 d7e7 d7c7 d7e6 d7d6 c6d8 c6b8 c6e7 c6a7 "
        "c6e5 c6d4 c6b4 g5g8 g5d8 g5g7 g5e7 g5h6 g5g6 g5f6 g5h5 g5f5 g5e5 g5d5 g5c5 g5b5 g5h4 "
        "a5a8 a5a7 a5a6 a5f5 a5e5 a5d5 a5c5 a5b5 a5a4 a5a3 a5a2 a5a1 g4e6 g4h5 g4f5 g4h3 g4f3 "
        "g4e2 g4d1 b7b6 f4f3 d3d2 b7b5 d3c2 d3e2 f4e3 f4g3 b7a6 0000",
    )
