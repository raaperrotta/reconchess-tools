from math import sqrt
import random
from typing import List

import chess
import pkg_resources
import pygame


LIGHT_COLOR = (240, 217, 181)
DARK_COLOR = (181, 136, 99)

PIECE_IMAGES = {}
for color in chess.COLORS:
    for piece_type in chess.PIECE_TYPES:
        piece = chess.Piece(piece_type, color)

        img_path = "res/{}/{}.png".format(chess.COLOR_NAMES[color], piece.symbol())
        full_path = pkg_resources.resource_filename("reconchess", img_path)

        img = pygame.image.load(full_path)
        PIECE_IMAGES[piece] = img


def draw_empty_board(font: pygame.font.SysFont, w) -> pygame.Surface:
    surface = pygame.Surface((w, w))
    pygame.draw.rect(surface, LIGHT_COLOR, (0, 0, w, w))
    sw = w / 8

    for dark_square in chess.SquareSet(chess.BB_DARK_SQUARES):
        sx = sw * chess.square_file(dark_square)
        sy = w - sw - sw * chess.square_rank(dark_square)
        pygame.draw.rect(surface, DARK_COLOR, (sx, sy, sw, sw))

    example_label = font.render("a", True, (0, 0, 0))
    rect = example_label.get_rect()
    for i in range(0, 8, 2):
        surface.blit(
            font.render(chess.FILE_NAMES[i], True, LIGHT_COLOR),
            (sw * i, w - rect.height),
        )
        surface.blit(
            font.render(chess.RANK_NAMES[i], True, DARK_COLOR),
            (w - rect.width, w - sw - sw * i),
        )
    for i in range(1, 8, 2):
        surface.blit(
            font.render(chess.FILE_NAMES[i], True, DARK_COLOR),
            (sw * i, w - rect.height),
        )
        surface.blit(
            font.render(chess.RANK_NAMES[i], True, LIGHT_COLOR),
            (w - rect.width, w - sw - sw * i),
        )

    return surface


def draw_pieces(board: chess.Board, w, alpha) -> pygame.Surface:
    surface = pygame.Surface((w, w), pygame.SRCALPHA)
    sw = w / 8
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            image = pygame.transform.scale(PIECE_IMAGES[piece], (int(sw), int(sw)))
            s = pygame.Surface((sw, sw), pygame.SRCALPHA)
            s.fill((255, 255, 255, alpha))
            s.blit(image, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            x = sw * chess.square_file(square)
            y = w - sw - sw * chess.square_rank(square)
            surface.blit(s, (x, y))
    return surface


def draw_boards(
    boards: List[chess.Board], w, font: pygame.font.SysFont, max_boards=10_000
) -> pygame.Surface:
    if len(boards) > max_boards:
        boards = random.sample(boards, max_boards)
    surface = draw_empty_board(font, w)
    alpha = max(1, int(255 / sqrt(len(boards))))
    for board in boards:
        surface.blit(draw_pieces(board, w, alpha), (0, 0))
    return surface
