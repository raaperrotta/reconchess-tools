from typing import List, Set

import chess
from reconchess.utilities import capture_square_of_move

from dynamic.util import sense_result_from_string
from reconchess_tools.utilities import (
    possible_taken_moves,
    simulate_move,
    simulate_sense,
)

possible_boards_on_blacks_first_turn = {
    "rnbqkbnr/pppppppp/8/8/8/7N/PPPPPPPP/RNBQKB1R b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/2N5/PPPPPPPP/R1BQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/N7/PPPPPPPP/R1BQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/7P/PPPPPPP1/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/6P1/PPPPPP1P/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/5P2/PPPPP1PP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/4P3/PPPP1PPP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/3P4/PPP1PPPP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/2P5/PP1PPPPP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/1P6/P1PPPPPP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/P7/1PPPPPPP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/7P/8/PPPPPPP1/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/6P1/8/PPPPPP1P/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/5P2/8/PPPPP1PP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/1P6/8/P1PPPPPP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/P7/8/1PPPPPPP/RNBQKBNR b KQkq -",
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq -",
}


def possible_boards(infoset: List) -> Set[str]:
    if infoset[0] == chess.WHITE:
        step = len(infoset) % 3
        func = [
            _possible_boards_white_to_sense,
            _possible_boards_white_to_move,
            _possible_boards_white_to_wait,
        ][step]
        return func(infoset[1:])
    step = len(infoset) % 3
    func = [
        _possible_boards_black_to_move,
        _possible_boards_black_to_wait,
        _possible_boards_black_to_sense,
    ][step]
    return func(infoset[1:])


def _possible_boards_white_to_move(infoset: List) -> Set[str]:
    if not infoset:
        return {chess.Board().epd(en_passant="xfen")}
    square, result_string = infoset[-1]
    result = sense_result_from_string(square, result_string)
    boards_pre_sense = _possible_boards_white_to_sense(infoset[:-1])
    return {
        board
        for board in boards_pre_sense
        if simulate_sense(chess.Board(board), square) == result
    }


def _possible_boards_white_to_wait(infoset: List) -> Set[str]:
    requested_move_uci, taken_move_uci, capture_square = infoset[-1]
    requested_move = chess.Move.from_uci(requested_move_uci)
    taken_move = chess.Move.from_uci(taken_move_uci)
    boards_pre_move = _possible_boards_white_to_move(infoset[:-1])
    boards = set()
    for board in boards_pre_move:
        board = chess.Board(board)
        if simulate_move(board, requested_move) == (taken_move, capture_square):
            board.push(taken_move)
            boards.add(board.epd(en_passant="xfen"))
            board.pop()
    return boards


def _possible_boards_white_to_sense(infoset: List) -> Set[str]:
    op_capture_square = infoset[-1]
    boards_pre_op_move = _possible_boards_white_to_wait(infoset[:-1])
    boards = set()
    for board in boards_pre_op_move:
        board = chess.Board(board)
        for move in possible_taken_moves(board):
            if capture_square_of_move(board, move) == op_capture_square:
                board.push(move)
                boards.add(board.epd(en_passant="xfen"))
                board.pop()
    return boards


def _possible_boards_black_to_sense(infoset: List) -> Set[str]:
    if infoset == [None]:
        return possible_boards_on_blacks_first_turn
    op_capture_square = infoset[-1]
    boards_pre_op_move = _possible_boards_black_to_wait(infoset[:-1])
    boards = set()
    for board in boards_pre_op_move:
        board = chess.Board(board)
        for move in possible_taken_moves(board):
            if capture_square_of_move(board, move) == op_capture_square:
                board.push(move)
                boards.add(board.epd(en_passant="xfen"))
                board.pop()
    return boards


def _possible_boards_black_to_move(infoset: List) -> Set[str]:
    square, result_string = infoset[-1]
    result = sense_result_from_string(square, result_string)
    boards_pre_sense = _possible_boards_black_to_sense(infoset[:-1])
    return {
        board
        for board in boards_pre_sense
        if simulate_sense(chess.Board(board), square) == result
    }


def _possible_boards_black_to_wait(infoset: List) -> Set[str]:
    requested_move_uci, taken_move_uci, capture_square = infoset[-1]
    requested_move = chess.Move.from_uci(requested_move_uci)
    taken_move = chess.Move.from_uci(taken_move_uci)
    boards_pre_move = _possible_boards_black_to_move(infoset[:-1])
    return {
        board
        for board in boards_pre_move
        if simulate_move(chess.Board(board), requested_move)
        == (taken_move, capture_square)
    }
