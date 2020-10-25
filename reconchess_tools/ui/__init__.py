import chess
import pkg_resources
import pygame


LIGHT_COLOR = (240, 217, 181)
DARK_COLOR = (181, 136, 99)

PIECE_IMAGES = {}
for color in chess.COLORS:
    for piece_type in chess.PIECE_TYPES:
        piece = chess.Piece(piece_type, color)

        img_path = 'res/{}/{}.png'.format(chess.COLOR_NAMES[color], piece.symbol())
        full_path = pkg_resources.resource_filename('reconchess', img_path)

        img = pygame.image.load(full_path)
        PIECE_IMAGES[piece] = img


def draw_empty_board(surface: pygame.Surface, font: pygame.font.SysFont, x, y, w):
    pygame.draw.rect(surface, LIGHT_COLOR, (x, y, w, w))
    sw = w / 8

    for dark_square in chess.SquareSet(chess.BB_DARK_SQUARES):
        sx = x + sw * chess.square_file(dark_square)
        sy = y + sw * chess.square_rank(dark_square)
        pygame.draw.rect(surface, DARK_COLOR, (sx, sy, sw, sw))

    example_label = font.render("a", True, (0, 0, 0))
    rect = example_label.get_rect()
    for i in range(0, 8, 2):
        surface.blit(font.render(chess.FILE_NAMES[i], True, DARK_COLOR), (x + sw * i, y + w - rect.height))
        surface.blit(font.render(chess.RANK_NAMES[i], True, LIGHT_COLOR), (x + w - rect.width, y + w - sw - sw * i))
    for i in range(1, 8, 2):
        surface.blit(font.render(chess.FILE_NAMES[i], True, LIGHT_COLOR), (x + sw * i, y + w - rect.height))
        surface.blit(font.render(chess.RANK_NAMES[i], True, DARK_COLOR), (x + w - rect.width, y + w - sw - sw * i))
