from typing import List, Optional, Dict, Tuple

import chess
from reconchess.utilities import move_actions, revise_move

from reconchess_tools.utilities import simulate_move

# Sensing on the edge of the board is never a good idea
SENSE_SQUARES = [
    square
    for square in chess.SQUARES
    if 0 < chess.square_file(square) < 7 and 0 < chess.square_rank(square) < 7
]


def non_dominated_moves(boards: List[chess.Board]):
    move_choices = {chess.Move.null()}
    for requested_move in move_actions(boards[0]):
        for board in boards:
            if requested_move == revise_move(board, requested_move):
                move_choices.add(requested_move)
                break
    return move_choices


def certain_win(boards: List[chess.Board]) -> Optional[chess.Move]:
    for requested_move in move_actions(boards[0]):
        for board in boards:
            op_king_square = board.king(not board.turn)
            if requested_move.to_square != op_king_square:
                break  # this can't possibly be a king-capture
            _, capture_square = simulate_move(board, requested_move)
            if capture_square != op_king_square:
                break  # this isn't a king-capture
        else:
            return requested_move


def minimax_sense(
    sense_results_for_square: Dict[chess.Square, Dict[Tuple, chess.Board]]
):
    """Find the minimax sense square

    Returns the square for which the worst case number of boards remaining after sensing there is
    the smallest.
    """
    return min(
        sense_results_for_square.items(),
        key=lambda x: max(len(group) for group in x[1].values()),
    )[0]


def non_dominated_sense(
    sense_results_for_square: Dict[chess.Square, Dict[Tuple, chess.Board]]
):
    # a square is dominated if every group in its groups is a superset of some group of the dominating square
    dominated_senses = set()
    for square, sense_results in sense_results_for_square.items():
        # Assume equal boards are identical objects as they are with mht.speculate_sense. This leads
        # to drastically faster comparisons than if we had to check the boards for equality.
        groups = [set(id(board) for board in v) for v in sense_results.values()]
        for square2, sense_results2 in sense_results_for_square.items():
            if square2 in dominated_senses or square2 == square:
                continue
            groups2 = [set(id(board) for board in v) for v in sense_results2.values()]
            if all(any(g.issuperset(g2) for g2 in groups2) for g in groups):
                dominated_senses.add(square)
                break
    return set(sense_results_for_square.keys()) - dominated_senses


def non_dominated_sense_by_own_pieces(board):
    """Screen sense squares that are trivially dominated because of my own piece positions"""
    actions = []
    for square in SENSE_SQUARES:
        rank = chess.square_rank(square)
        file = chess.square_file(square)
        # Skip if can sense higher and bottom row is full of my pieces
        if rank < 6:
            for offset in [-9, -8, -7]:
                piece = board.piece_at(square + offset)
                if piece is None or piece.color != board.turn:
                    break
            else:
                continue
        # Skip if can sense lower and top row is full of my pieces
        if rank > 1 and square - 8 in actions:
            for offset in [7, 8, 9]:
                piece = board.piece_at(square + offset)
                if piece is None or piece.color != board.turn:
                    break
            else:
                continue
        # Skip if can sense right and left col is full of my pieces
        if file < 6:
            for offset in [-9, -1, 7]:
                piece = board.piece_at(square + offset)
                if piece is None or piece.color != board.turn:
                    break
            else:
                continue
        # Skip if can sense left and right col is full of my pieces
        if file > 1 and square - 1 in actions:
            for offset in [-7, 1, 9]:
                piece = board.piece_at(square + offset)
                if piece is None or piece.color != board.turn:
                    break
            else:
                continue
        actions.append(square)
    return actions
