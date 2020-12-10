from typing import Optional

import chess

from reconchess_tools.utilities import simulate_move


def run(
    move_history: str,
    requested_move: str,
    expected_taken_move: str,
    expected_capture_square: Optional[str],
):
    board = chess.Board()
    for move in move_history.split():
        move = chess.Move.from_uci(move)
        assert move == chess.Move.null() or board.is_pseudo_legal(
            move
        ), f"Move history is invalid! Move {move} is not pseudo-legal on board\n{board}"
        board.push(move)
    assert simulate_move(board, chess.Move.from_uci(requested_move)) == (
        chess.Move.from_uci(expected_taken_move),
        None
        if expected_capture_square is None
        else chess.parse_square(expected_capture_square),
    )


def test_pawn_attempted_capture():
    run("", "f2g3", "0000", None)
    run("0000", "f7g6", "0000", None)
    run("b2b3 0000", "b3c4", "0000", None)
    run("0000 a7a6 0000", "a6b5", "0000", None)
    run("b2b4 0000", "b4c5", "0000", None)
    run("0000 a7a5 0000", "a5b4", "0000", None)


def test_pawn_stopped_from_advancing_two_ranks():
    run("e2e3 f7f6 d1h5", "h7h5", "h7h6", None)


def test_pawn_stopped_from_advancing_two_ranks_by_knight():
    board = chess.Board(
        "q3kb2/1pp2pp1/4p1Pr/1n1Q3p/P2P1P2/1n2P1Nb/1PP2K2/1RB2BR1 w - - 0 28"
    )
    assert simulate_move(board, chess.Move.from_uci("b2b4")) == (
        chess.Move.null(),
        None,
    )


def test_promotion_with_capture():
    run("e2e4 0000 e4e5 0000 e5e6 0000 e6f7 0000", "f7g8n", "f7g8n", "g8")


def test_promotion_attempted_capture():
    run("e2e4 0000 e4e5 0000 e5e6 0000 e6f7 g8h6", "f7g8n", "0000", None)


def test_promotion_without_capture():
    run("h2h4 0000 h4h5 0000 h5h6 0000 h6g7 g8h6", "g7g8b", "g7g8b", None)


def test_stopped_queen_slide():
    run("e2e3 0000 d1f3 f7f5", "f3f8", "f3f5", "f5")


def test_stopped_queen_slide_diagonal():
    run("e2e3 0000 d1f3 f7f5", "f3a8", "f3b7", "b7")


def test_en_passant_white():
    run("e2e4 0000 e4e5 f7f5", "e5f6", "e5f6", "f5")


def test_en_passant_black():
    run("0000 e7e5 0000 e5e4 d2d4", "e4d3", "e4d3", "d4")
