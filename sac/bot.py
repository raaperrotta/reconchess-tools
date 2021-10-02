import random
from itertools import product
from typing import List, Optional

import chess
import numpy as np
import tensorflow as tf
from reconchess.utilities import move_actions

from example_bot.bot import MhtBot
from reconchess_tools.strategy import (
    SENSE_SQUARES,
    certain_win,
    non_dominated_sense,
    non_dominated_sense_by_own_pieces,
)

LEARN_TO_SENSE = False


def find_all_possible_moves():
    moves = [chess.Move.null()]

    board = chess.Board()
    piece_types = [chess.PAWN, chess.QUEEN, chess.KNIGHT]
    for square, piece_type, color in product(chess.SQUARES, piece_types, chess.COLORS):
        piece = chess.Piece(piece_type, color)
        board.clear()
        board.set_piece_at(square, piece)
        board.turn = color
        moves += move_actions(board)

    # Only include underpromotions explicitly
    # Promotion to queen will be added automatically when another promotion is not requested
    moves = {m for m in moves if m.promotion != chess.QUEEN}

    return sorted(moves, key=str)


ACTIONS = find_all_possible_moves()
if LEARN_TO_SENSE:
    ACTIONS += SENSE_SQUARES


class SacBot(MhtBot):
    def __init__(
        self,
        policy_white: tf.keras.models.Model,
        policy_black: tf.keras.models.Model,
    ):
        super().__init__()
        self.policy_white = policy_white
        self.policy_black = policy_black

    def choose_sense(
        self,
        sense_actions: List[chess.Square],
        move_actions: List[chess.Move],
        seconds_left: float,
    ) -> Optional[chess.Square]:
        if len(self.mht.boards) <= 1:
            return None
        self.mht.speculate_sense(non_dominated_sense_by_own_pieces(self.mht.boards[0]))
        non_dominated_squares = non_dominated_sense(self.mht.sense_speculation)
        # Evaluate our trained policy
        policy = self.policy_white if self.color == chess.WHITE else self.policy_black
        weights = policy.predict(
            SacState(self.mht.boards, non_dominated_squares).encode()
        )
        sense_choice = random.choices(ACTIONS, weights, k=1)[0]
        return sense_choice

    def choose_move(
        self, move_actions: List[chess.Move], seconds_left: float
    ) -> Optional[chess.Move]:
        # Since we limit the size of the MHT board list, it is possible for that list to become
        # empty. In that case we fall back to requesting moves randomly.
        if not self.mht.boards:
            return random.choice(move_actions)
        # If any move is guaranteed to result in a king capture, take it!
        winning_move = certain_win(self.mht.boards)
        if winning_move:
            return winning_move
        # Otherwise, evaluate our trained policy
        policy = self.policy_white if self.color == chess.WHITE else self.policy_black
        weights = policy.predict(SacState(self.mht.boards, move_actions).encode())
        move_choice = random.choices(ACTIONS, weights, k=1)[0]
        # The reconchess library encodes passing (null) moves as None so we convert
        # chess.Move.null() to None here using the fact that it evaluates to truthy false.
        return move_choice or None


class SacState:
    def __init__(self, boards, actions):
        self.boards = encode_boards(boards)
        self.actions = actions
        self.action_mask = encode_action_mask(actions)
        self.color = boards[0].turn

    def encode(self):
        return self.boards, self.action_mask


def encode_boards(boards):
    return np.stack([encode_board(board) for board in boards])


def encode_action_mask(actions):
    mask = np.zeros(len(ACTIONS), dtype=bool)
    for action in actions:
        # Only underpromotions are included explicitly.
        if isinstance(action, chess.Move) and action.promotion == chess.QUEEN:
            action.promotion = None
        mask[ACTIONS.index(action)] = True
    return mask


def encode_board(board: chess.Board):
    # Square, piece type, color
    encoded = np.zeros((64, 6, 2), dtype=bool)
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            piece_channel = piece.piece_type - 1
            color_channel = piece.color
            encoded[square, piece_channel, color_channel] = True

    castling = np.array(
        [
            board.has_kingside_castling_rights(chess.WHITE),
            board.has_queenside_castling_rights(chess.WHITE),
            board.has_kingside_castling_rights(chess.BLACK),
            board.has_queenside_castling_rights(chess.BLACK),
        ]
    )

    en_passant_file = np.zeros((8, 2), dtype=bool)
    if board.ep_square:
        rank = chess.square_rank(board.ep_square)
        file = chess.square_file(board.ep_square)
        en_passant_file[file, rank == 5] = True

    encoded = np.concatenate(
        [
            encoded.ravel(),
            castling,
            en_passant_file.ravel(),
        ]
    )

    return encoded
