from typing import Tuple, List, Optional, Iterable

import chess
from reconchess.utilities import (
    is_illegal_castle,
    capture_square_of_move,
    revise_move,
    move_actions,
    without_opponent_pieces,
)

_BACKRANK_SQUARES = chess.SquareSet(chess.BB_BACKRANKS)


def simulate_sense(
    board: chess.Board, square: Optional[chess.Square]
) -> List[Tuple[int, chess.Piece]]:
    if square is None:
        return []
    assert square in list(chess.SQUARES), f"{square} is not a valid square."
    rank, file = chess.square_rank(square), chess.square_file(square)
    sense_result = []
    for delta_rank in [-1, 0, 1]:
        for delta_file in [-1, 0, 1]:
            if 0 <= rank + delta_rank <= 7 and 0 <= file + delta_file <= 7:
                sense_square = chess.square(file + delta_file, rank + delta_rank)
                sense_result.append((sense_square, board.piece_at(sense_square)))
    return sense_result


def simulate_move(board, move: chess.Move) -> Tuple[chess.Move, Optional[int]]:
    if move:
        taken_move = revise_move(board, move) or chess.Move.null()
        return taken_move, capture_square_of_move(board, taken_move)
    return move, None


def possible_requested_moves(board: chess.Board) -> Iterable[chess.Move]:
    yield from move_actions(board)
    yield chess.Move.null()


def possible_taken_moves(board: chess.Board) -> Iterable[chess.Move]:
    for move in board.pseudo_legal_moves:
        yield move
    for move in without_opponent_pieces(board).generate_castling_moves():
        if not is_illegal_castle(board, move):
            yield move
    yield chess.Move.null()
