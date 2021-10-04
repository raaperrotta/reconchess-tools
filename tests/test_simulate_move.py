from typing import Optional

import chess
import pytest

from reconchess_tools.utilities import simulate_move


@pytest.mark.parametrize(
    "move_history, requested_move, expected_taken_move, expected_capture_square",
    [
        # Attempted pawn captures
        ("", "f2g3", "0000", None),
        ("0000", "f7g6", "0000", None),
        ("b2b3 0000", "b3c4", "0000", None),
        ("0000 a7a6 0000", "a6b5", "0000", None),
        ("b2b4 0000", "b4c5", "0000", None),
        ("0000 a7a5 0000", "a5b4", "0000", None),
        # Pawn stopped from advancing two ranks
        ("e2e3 f7f6 d1h5", "h7h5", "h7h6", None),
        # Promotion with capture
        ("e2e4 0000 e4e5 0000 e5e6 0000 e6f7 0000", "f7g8n", "f7g8n", "g8"),
        # Attempted promotion with capture
        ("e2e4 0000 e4e5 0000 e5e6 0000 e6f7 g8h6", "f7g8n", "0000", None),
        # Promotion without capture
        ("h2h4 0000 h4h5 0000 h5h6 0000 h6g7 g8h6", "g7g8b", "g7g8b", None),
        # stopped_queen_slide
        ("e2e3 0000 d1f3 f7f5", "f3f8", "f3f5", "f5"),
        # stopped_queen_slide_diagonal
        ("e2e3 0000 d1f3 f7f5", "f3a8", "f3b7", "b7"),
        # en_passant_white
        ("e2e4 0000 e4e5 f7f5", "e5f6", "e5f6", "f5"),
        # en_passant_black
        ("0000 e7e5 0000 e5e4 d2d4", "e4d3", "e4d3", "d4"),
        # white_castle
        ("e2e3 0000 f1e2 0000 g1f3 0000", "e1g1", "e1g1", None),
        # white_interrupted_castle
        ("e2e3 b7b6 f1a6 c8a6 g1f3 a6f1", "e1g1", "0000", None),
    ],
)
def test_simulate_move(
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


def test_pawn_stopped_from_advancing_two_ranks_by_knight():
    board = chess.Board(
        "q3kb2/1pp2pp1/4p1Pr/1n1Q3p/P2P1P2/1n2P1Nb/1PP2K2/1RB2BR1 w - - 0 28"
    )
    assert simulate_move(board, chess.Move.from_uci("b2b4")) == (
        chess.Move.null(),
        None,
    )
