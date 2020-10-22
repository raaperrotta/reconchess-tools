from typing import Tuple, List, Optional, Dict, Iterable

import chess

from reconchess.utilities import (
    is_illegal_castle,
    is_psuedo_legal_castle,
    capture_square_of_move,
)


SENSE_SQUARES = [
    9,
    10,
    11,
    12,
    13,
    14,
    17,
    18,
    19,
    20,
    21,
    22,
    25,
    26,
    27,
    28,
    29,
    30,
    33,
    34,
    35,
    36,
    37,
    38,
    41,
    42,
    43,
    44,
    45,
    46,
    49,
    50,
    51,
    52,
    53,
    54,
]
# Copied here for convenience
[
    A1,
    B1,
    C1,
    D1,
    E1,
    F1,
    G1,
    H1,
    A2,
    B2,
    C2,
    D2,
    E2,
    F2,
    G2,
    H2,
    A3,
    B3,
    C3,
    D3,
    E3,
    F3,
    G3,
    H3,
    A4,
    B4,
    C4,
    D4,
    E4,
    F4,
    G4,
    H4,
    A5,
    B5,
    C5,
    D5,
    E5,
    F5,
    G5,
    H5,
    A6,
    B6,
    C6,
    D6,
    E6,
    F6,
    G6,
    H6,
    A7,
    B7,
    C7,
    D7,
    E7,
    F7,
    G7,
    H7,
    A8,
    B8,
    C8,
    D8,
    E8,
    F8,
    G8,
    H8,
] = range(64)


def simulate_sense(
    board: chess.Board, square: Optional[chess.Square]
) -> List[Tuple[int, chess.Piece]]:
    if square is None:
        return []
    assert square in list(chess.SQUARES), f"{square} is not a valid square."
    rank, file = chess.square_rank(square), chess.square_file(square)
    sense_result = []
    for delta_rank in [1, 0, -1]:
        for delta_file in [-1, 0, 1]:
            if 0 <= rank + delta_rank <= 7 and 0 <= file + delta_file <= 7:
                sense_square = chess.square(file + delta_file, rank + delta_rank)
                sense_result.append((sense_square, board.piece_at(sense_square)))
    return sense_result


def simulate_move(board, move: chess.Move) -> Tuple[chess.Move, Optional[int]]:
    if (
        move == chess.Move.null()
        or board.is_pseudo_legal(move)
        or is_psuedo_legal_castle(board, move)
    ):
        return move, capture_square_of_move(board, move)
    if is_illegal_castle(board, move):
        return chess.Move.null(), None
    # if the piece is a sliding piece, slide it as far as it can go
    piece = board.piece_at(move.from_square)
    if piece.piece_type in {chess.PAWN, chess.ROOK, chess.BISHOP, chess.QUEEN}:
        move = _slide_move(board, move)
        return move, capture_square_of_move(board, move)
    return chess.Move.null(), None


def _slide_move(board, move: chess.Move) -> Optional[chess.Move]:
    squares = list(chess.SquareSet(chess.between(move.from_square, move.to_square))) + [
        move.to_square
    ]
    squares = sorted(
        squares, key=lambda s: chess.square_distance(s, move.from_square), reverse=True
    )
    for slide_square in squares:
        revised = chess.Move(move.from_square, slide_square, move.promotion)
        if board.is_pseudo_legal(revised):
            return revised
    return chess.Move.null()


def without_opponent_pieces(board):
    return board.transform(lambda bb: bb & board.occupied_co[board.turn])


def possible_requested_moves(board: chess.Board) -> Iterable[chess.Move]:
    no_opponents_board = without_opponent_pieces(board)
    yield from possible_requested_moves_no_op_pieces(no_opponents_board)


def possible_requested_moves_no_op_pieces(
    no_opponents_board: chess.Board,
) -> Iterable[chess.Move]:

    yield from no_opponents_board.generate_pseudo_legal_moves()

    for pawn_square in no_opponents_board.pieces(chess.PAWN, no_opponents_board.turn):
        # TODO: optimize to use SquareSet and pawn attack bitboards directly
        for attacked_square in no_opponents_board.attacks(pawn_square):
            # skip this square if one of our own pieces are on the square
            if no_opponents_board.piece_at(attacked_square):
                continue

            # add in promotion moves
            if attacked_square in chess.SquareSet(chess.BB_BACKRANKS):
                for piece_type in chess.PIECE_TYPES[1:-1]:
                    yield chess.Move(pawn_square, attacked_square, promotion=piece_type)
            else:
                yield chess.Move(pawn_square, attacked_square)

    yield chess.Move.null()


def possible_taken_moves(board: chess.Board) -> Iterable[chess.Move]:
    for move in board.pseudo_legal_moves:
        yield move
    for move in without_opponent_pieces(board).generate_castling_moves():
        if not is_illegal_castle(board, move):
            yield move
    yield chess.Move.null()
