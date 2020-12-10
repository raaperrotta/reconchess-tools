from collections import defaultdict
from typing import List, Optional

import chess


# Sensing on the edge of the board is never a good idea
from reconchess.utilities import move_actions, revise_move

from reconchess_tools.utilities import simulate_sense, simulate_move

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


def non_dominated_sense(boards):
    # TODO separate this to make it easier to get minimax square alone when desired

    if len(boards) <= 1:
        return {None}, None

    screened_sense_actions = _non_dominated_sense_helper(boards[0])

    dominated_senses = set()
    sense_results_for_square = {}

    for square in screened_sense_actions:
        sense_results_for_square[square] = sense_results = defaultdict(list)
        for board in boards:
            sense_results[tuple(simulate_sense(board, square))].append(id(board))

    # a square is dominated if every group in its groups is a superset of some group of the dominating square
    for square in screened_sense_actions:
        sense_results = sense_results_for_square[square]
        groups = [set(v) for v in sense_results.values()]
        for square2, sense_results2 in sense_results_for_square.items():
            if square2 in dominated_senses or square2 == square:
                continue
            groups2 = [set(v) for v in sense_results2.values()]
            if all(any(g.issuperset(g2) for g2 in groups2) for g in groups):
                dominated_senses.add(square)
                break

    out = set(screened_sense_actions) - dominated_senses
    # compute the minimax sense here in case we need it
    minimax_square = min(
        out,
        key=lambda sq: max(
            len(group) for group in sense_results_for_square[sq].values()
        ),
    )

    return out, minimax_square


def _non_dominated_sense_helper(board):
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
