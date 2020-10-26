import contextlib

with contextlib.redirect_stdout(None):
    import pygame

import chess

from reconchess_tools.history import History


# block output from pygame
from reconchess_tools.ui import PIECE_IMAGES, draw_boards

SENSE, MOVE = False, True


class Replay:

    def __init__(self, history_string: str):
        self.state = State(History(history_string))

        pygame.init()
        pygame.display.set_caption('Reconchess MHT Replay')
        pygame.display.set_icon(
            pygame.transform.scale(PIECE_IMAGES[chess.Piece(chess.KING, chess.WHITE)], (32, 32)))

        self.clock = pygame.time.Clock()

        self.header_font = pygame.font.SysFont(pygame.font.get_default_font(), 28)
        self.body_font = pygame.font.SysFont(pygame.font.get_default_font(), 20)
        self.body_spacing = 20
        self.board_font = pygame.font.SysFont(pygame.font.get_default_font(), 20)

        self.background_color = (45, 48, 50)
        self.header_color = (250, 250, 250)
        self.body_color = (160, 160, 160)

        self.square_size = 50
        self.width = self.square_size * 17
        self.height = self.square_size * 18
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.background = pygame.Surface((self.screen.get_size()))

    def play(self):
        while True:
            self.clock.tick(60)
            self.respond_to_events()
            self.update_view()

    def respond_to_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.state.go_to_prev_action()
                elif event.key == pygame.K_RIGHT:
                    self.state.go_to_next_action()
                elif event.key == pygame.K_q:
                    pygame.quit()
                    quit()

    def update_view(self):
        self.background.fill(self.background_color)
        self.background.blit(
            draw_boards([self.state.true_board], self.square_size * 8, self.board_font),
            (0, self.square_size)
        )
        self.background.blit(
            draw_boards(self.state.possible_boards_white, self.square_size * 8, self.board_font),
            (0, self.square_size * 10)
        )
        self.background.blit(
            draw_boards(self.state.possible_boards_black, self.square_size * 8, self.board_font),
            (self.square_size * 9, self.square_size * 10)
        )

        label = self.header_font.render("True board state", True, self.header_color)
        rect = label.get_rect()
        self.background.blit(label, (
            int(self.square_size * 4 - rect.width / 2),
            int(self.square_size * 0.75 - rect.height / 2),
        ))

        label = f"White sees {len(self.state.possible_boards_white):,.0f} possible board"
        if len(self.state.possible_boards_white) > 1:
            label += "s"
        label = self.header_font.render(label, True, self.header_color)
        rect = label.get_rect()
        self.background.blit(label, (
            int(self.square_size * 4 - rect.width / 2),
            int(self.square_size * 9.75 - rect.height / 2),
        ))

        label = f"Black sees {len(self.state.possible_boards_black):,.0f} possible board"
        if len(self.state.possible_boards_black) > 1:
            label += "s"
        label = self.header_font.render(label, True, self.header_color)
        rect = label.get_rect()
        self.background.blit(label, (
            int(self.square_size * 13 - rect.width / 2),
            int(self.square_size * 9.75 - rect.height / 2),
        ))

        self.update_info()

        self.screen.blit(self.background, (0, 0))
        pygame.display.flip()

    def update_info(self):
        x = self.square_size * 9
        y = self.square_size

        info = [
            "Game info:",
            f"    Winner: {chess.COLOR_NAMES[self.state.history.winner]} by {self.state.history.win_reason}",
            f"    Total actions: {self.state.history.num_actions:,.0f}",
        ]

        info += [
            "",
            "Last action:",
        ]
        if self.state.action_num > 0:
            if self.state.upcoming_action == SENSE:
                info.append(f"    Move {(self.state.action_num - 1) // 4 + 1} for "
                            f"{chess.COLOR_NAMES[not self.state.true_board.turn]}")
            else:
                info.append(f"    Sense {(self.state.action_num - 1) // 4 + 1} for "
                            f"{chess.COLOR_NAMES[self.state.true_board.turn]}")
            info.append(f"    {self.state.history.history[self.state.action_num - 1]}")
        else:
            info += ["    -"] * 2

        info += [
            "",
            "Upcoming action:",
            f"    {'Move' if self.state.upcoming_action == MOVE else 'Sense'} {self.state.action_num // 4 + 1} "
            f"for {chess.COLOR_NAMES[self.state.true_board.turn]}",
        ]
        if self.state.action_num == self.state.history.num_actions:
            info += ["    -"]
        else:
            info += [
                f"    {self.state.history.history[self.state.action_num]}",
            ]

        for line in info:
            self.background.blit(self.body_font.render(line, True, self.body_color), (x, y))
            y += self.body_spacing


class State:

    def __init__(self, history: History):
        self.history = history
        self.action_num = 0
        self.turn = 1
        self.upcoming_action = SENSE
        self.true_board = chess.Board(self.history.board[self.action_num])
        self.possible_boards_white = [chess.Board(epd) for epd in self.history.possible_epds[chess.WHITE][self.action_num]]
        self.possible_boards_black = [chess.Board(epd) for epd in self.history.possible_epds[chess.BLACK][self.action_num]]

    def go_to_next_action(self):
        if self.action_num == self.history.num_actions:
            return
        self.action_num += 1
        self.turn = self.action_num // 4 + 1
        self.upcoming_action = not self.upcoming_action
        self.true_board = chess.Board(self.history.board[self.action_num // 2])
        self.possible_boards_white = [chess.Board(epd) for epd in self.history.possible_epds[chess.WHITE][self.action_num]]
        self.possible_boards_black = [chess.Board(epd) for epd in self.history.possible_epds[chess.BLACK][self.action_num]]

    def go_to_prev_action(self):
        if self.action_num == 0:
            return
        self.action_num -= 1
        self.turn = self.action_num // 4 + 1
        self.upcoming_action = not self.upcoming_action
        self.true_board = chess.Board(self.history.board[self.action_num // 2])
        self.possible_boards_white = [chess.Board(epd) for epd in self.history.possible_epds[chess.WHITE][self.action_num]]
        self.possible_boards_black = [chess.Board(epd) for epd in self.history.possible_epds[chess.BLACK][self.action_num]]


def _main():
    # Replay("00 e2e3 f2 f7f5 c7").play()
    Replay("00 e2e4 b3 d7d5 g7  g1f3 f2  g8f6 c7  e4d5 c5  d8d5 g7  d2d4 c4  d5a5 d5  b1c3 b4  f6e4 g5  f1b5 e2  b8c6 d7  a2b3 d4  e4c3 d4  b5c6 f3  b7c6 00  b2c3 d2  a5c3 00  c1d2 e2  c3a1 00  d1a1 g2  c8f5 b7  g2h3 d2  a8b8 c4  f3e5 b2  f5c2 c7  a1c3 g2  b8b1 c7  e1e2 d2  c2d1 d2  h1d1 f4  b1d1 00  c3c6 d5 e8d8 e7  c6d7 f2  d1e1 d7  d7d8").play()


if __name__ == "__main__":
    _main()
