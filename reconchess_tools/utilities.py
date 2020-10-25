from typing import Tuple, List, Optional, Iterable

import chess

from reconchess.utilities import (
    is_illegal_castle,
    is_psuedo_legal_castle,
    capture_square_of_move,
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
    if board.piece_at(move.from_square).piece_type in {chess.PAWN, chess.ROOK, chess.BISHOP, chess.QUEEN}:
        move = _slide_move(board, move)
        return move, capture_square_of_move(board, move)
    return chess.Move.null(), None


def _slide_move(board, move: chess.Move) -> Optional[chess.Move]:
    # We iterate longest to shortest so the revised move is the longest pseudo-legal move.
    # If the to-square < from-square then we want our list in sorted order.
    # Otherwise we want it in reverse order.
    # In either case, we need to add the to-square to the front of our list manually.
    squares = chess.SquareSet(chess.between(move.from_square, move.to_square))
    if move.to_square > move.from_square:
        squares = reversed(squares)
    for slide_square in [move.to_square] + list(squares):
        revised = chess.Move(move.from_square, slide_square, move.promotion)
        if board.is_pseudo_legal(revised):
            return revised
    return chess.Move.null()


def possible_requested_moves(board: chess.Board) -> Iterable[chess.Move]:
    no_opponents_board = without_opponent_pieces(board)
    yield from possible_requested_moves_no_op_pieces(no_opponents_board)


def without_opponent_pieces(board):
    return board.transform(lambda bb: bb & board.occupied_co[board.turn])


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
            if attacked_square in _BACKRANK_SQUARES:
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
