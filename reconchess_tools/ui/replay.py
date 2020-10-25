import contextlib

with contextlib.redirect_stdout(None):
    import pygame

import chess
import reconchess

from reconchess_tools.history import History


# block output from pygame
from reconchess_tools.ui import PIECE_IMAGES, draw_empty_board, draw_pieces, draw_board

SENSE, MOVE = False, True


class Replay:

    def __init__(self, history_string: str):
        self.state = State(History(history_string))

        pygame.init()
        pygame.display.set_caption('Reconchess MHT Replay')
        pygame.display.set_icon(
            pygame.transform.scale(PIECE_IMAGES[chess.Piece(chess.KING, chess.WHITE)], (32, 32)))

        self.header = pygame.font.SysFont(pygame.font.get_default_font(), 18)

        self.square_size = 50
        self.width = self.square_size * 17
        self.height = self.square_size * 18
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.background = pygame.Surface((self.screen.get_size()))
        self.background.fill((255, 255, 255))
        surface = draw_board(chess.Board(), self.square_size * 8, 255,
                             pygame.font.SysFont(pygame.font.get_default_font(), 18))
        self.background.blit(surface, (0, self.square_size))
        self.background.blit(surface, (0, self.square_size * 10))
        self.background.blit(surface, (self.square_size * 9, self.square_size * 10))

        label = self.header.render("True board state", True, (0, 0, 0))
        rect = label.get_rect()


        self.screen.blit(self.background, (0, 0))
        pygame.display.flip()

    def play(self):
        while True:
            self.respond_to_events()
            self.update_view()

    def respond_to_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.state.go_to_next_action()
                elif event.key == pygame.K_RIGHT:
                    self.state.go_to_prev_action()
                elif event.key == pygame.K_q:
                    pygame.quit()
                    quit()

    def update_view(self):
        pass


class State:

    def __init__(self, history: History):
        self.history = history
        self.turn = 1
        self.action = SENSE
        self.true_board = history.board[0]
        self.possible_boards_white = history.possible_epds[chess.WHITE][0]
        self.possible_boards_black = history.possible_epds[chess.BLACK][0]

    def go_to_next_action(self):
        pass

    def go_to_prev_action(self):
        pass


def _main():
    Replay("00 e2e3 f2 f7f5 c7").play()


if __name__ == "__main__":
    _main()
