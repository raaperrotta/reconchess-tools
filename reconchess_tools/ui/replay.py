"""Asynchronous pygame UI for displaying each players' MHT view of the game during a replay

Work in progress!

For simplicity, all asynchronous functions are infinite while loops that yield control when
possible to allow other tasks to run. Information is passed between tasks using queues and by
updating shared state. The game loop is based on the pygame event loop so the entire process can
be terminated when that loop returns (e.g. when the user closes the window).

The desired behavior is for the window to appear immediately and for navigation and rendering to
appear even before the MHT calculations are complete. To accomplish this, we create a surface to
store each board view and the status computing and rendering the boards. We also store a message
to be displayed per turn. Then the animation task has only to render the current surfaces at each
step (and we could possibly set a timestamp for the last change to avoid blit-ing unchanged
surfaces). A separate task runs to compute the MHT views, blit the pieces to each surface,
and update the status information.
"""

import asyncio
import contextlib
import time
from typing import List, Optional, Tuple

from reconchess import GameHistory

with contextlib.redirect_stdout(None):
    import pygame

import chess
from reconchess_tools.utilities import (
    simulate_sense,
    simulate_move,
    possible_requested_moves,
)

from reconchess_tools.ui import PIECE_IMAGES, draw_boards, draw_empty_board

SENSE, MOVE = False, True


class Replay:
    def __init__(self, history_string: str):

        pygame.init()
        pygame.display.set_caption("Reconchess MHT Replay")
        pygame.display.set_icon(
            pygame.transform.scale(
                PIECE_IMAGES[chess.Piece(chess.KING, chess.WHITE)], (32, 32)
            )
        )

        self.header_font = pygame.font.SysFont(pygame.font.get_default_font(), 28)
        self.body_font = pygame.font.SysFont(pygame.font.get_default_font(), 20)
        self.body_spacing = 20
        self.board_font = pygame.font.SysFont(pygame.font.get_default_font(), 20)

        self.background_color = (45, 48, 50)
        self.header_color = (250, 250, 250)
        self.body_color = (160, 160, 160)

        self.square_size = 40
        self.margin = 10
        self.board_size = self.square_size * 8
        self.width = self.square_size * 16 + self.margin * 3
        self.height = self.width
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.screen.fill(self.background_color)

        self.action_index = 0

        self.history = tuple(history_string.strip().split())
        self.history_string = " ".join(
            self.history
        )  # to clean up possible multiple spaces
        self.num_actions = len(self.history)
        self.num_moves = self.num_actions // 2
        self.num_moves_by_white = (self.num_moves + 1) // 2
        self.num_moves_by_black = self.num_moves // 2

        board = chess.Board()
        self.views: List[View] = [View(board, self.board_font, self.board_size)]

        # Compute the true board states synchronously since that is fast
        history_iter = iter(self.history)
        try:
            while True:
                # Sense step
                next(history_iter)
                # Move step
                requested_move = chess.Move.from_uci(next(history_iter))
                taken_move, capture_square = simulate_move(board, requested_move)
                board.push(taken_move)
                self.views.append(View(board, self.board_font, self.board_size))

        except StopIteration:
            pass

        self.winner = not board.turn
        self.win_reason = "timeout" if board.king(board.turn) else "king capture"

    @classmethod
    def from_history(cls, history: GameHistory) -> "Replay":
        actions = []
        for turn in history.turns():
            sense = history.sense(turn)
            actions.append("00" if sense is None else chess.SQUARE_NAMES[sense])
            actions.append((history.requested_move(turn) or chess.Move.null()).uci())
        actions = " ".join(actions)
        return Replay(actions)

    async def play(self):
        task_mht = asyncio.create_task(self.update_mht())
        task_update = asyncio.create_task(self.update_view())
        await self.respond_to_events()
        task_mht.cancel()
        task_update.cancel()
        pygame.quit()

    def play_sync(self):
        asyncio.run(self.play())

    async def update_mht(self):
        history_iter = iter(self.history)
        board = chess.Board()
        active, waiting = AsyncMultiHypothesisTracker(), AsyncMultiHypothesisTracker()
        turn_index = 0
        num_boards = [1, 1]

        requested_move = (
            taken_move
        ) = capture_square = piece_moved = piece_captured = None
        x = y = 10
        view = self.views[0]

        surface_sense = pygame.Surface([self.square_size * 3] * 2, pygame.SRCALPHA)
        surface_sense.fill((205, 205, 255, 85))

        surface_capture = pygame.Surface([self.square_size] * 2, pygame.SRCALPHA)
        surface_capture.fill((255, 0, 0, 50))

        # TODO: Split white and black MHT views in case one explodes
        try:
            while True:
                view = self.views[turn_index]
                if board.turn == chess.WHITE:
                    view.surface_white = draw_boards(
                        active.boards, self.board_size, self.board_font
                    )
                    view.surface_black = draw_boards(
                        waiting.boards, self.board_size, self.board_font
                    )
                else:
                    view.surface_white = draw_boards(
                        waiting.boards, self.board_size, self.board_font
                    )
                    view.surface_black = draw_boards(
                        active.boards, self.board_size, self.board_font
                    )
                # Shade capture square
                if capture_square is not None:
                    x = self.square_size * chess.square_file(capture_square)
                    y = self.board_size - self.square_size * (
                        chess.square_rank(capture_square) + 1
                    )
                    view.surface_true.blit(surface_capture, (x, y))
                    view.surface_white.blit(surface_capture, (x, y))
                    view.surface_black.blit(surface_capture, (x, y))
                view.updated_at = time.monotonic()
                await asyncio.sleep(0)

                # Update info
                view.surface_info.fill(self.background_color)
                if turn_index == 0:
                    info = ["White to sense on turn 1"]
                else:
                    info = [
                        f"{chess.COLOR_NAMES[not board.turn].capitalize()} "
                        f"requested to move {chess.PIECE_NAMES[piece_moved.piece_type]} "
                        f"{requested_move} on turn "
                        f"{(turn_index - 1) // 2 + 1}, which",
                        f"    resulted in move {taken_move} and "
                        + (
                            f"the capture of the {chess.PIECE_NAMES[piece_captured.piece_type]} at "
                            f"{chess.SQUARE_NAMES[capture_square]}"
                            if piece_captured
                            else "no capture"
                        ),
                        f"# possible boards for {chess.COLOR_NAMES[not board.turn]}: "
                        f"{num_boards[not board.turn]:,.0f} -> {len(waiting.boards):,.0f} "
                        f"(Δ = {len(waiting.boards) - num_boards[not board.turn]:+,.0f})",
                        f"# possible boards for {chess.COLOR_NAMES[board.turn]}: "
                        f"{num_boards[board.turn]:,.0f} -> {len(active.boards):,.0f} "
                        f"(Δ = {len(active.boards) - num_boards[board.turn]:+,.0f})",
                        "",
                        f"{chess.COLOR_NAMES[board.turn].capitalize()} to sense on turn {turn_index // 2 + 1}",
                    ]
                x = y = 10
                for line in info:
                    view.surface_info.blit(
                        self.body_font.render(line, True, self.body_color), (x, y)
                    )
                    y += 20
                num_boards[board.turn] = len(active.boards)
                num_boards[not board.turn] = len(waiting.boards)
                await asyncio.sleep(0)

                # Sense step
                square = next(history_iter)
                square = None if square == "00" else chess.parse_square(square)
                result = simulate_sense(board, square)
                await active.sense(square, result)
                view.surface_after_sense = draw_boards(
                    active.boards, self.board_size, self.board_font
                )
                # Shade sensed squares
                if square is not None:
                    x = self.square_size * (chess.square_file(square) - 1)
                    y = self.board_size - self.square_size * (
                        chess.square_rank(square) + 2
                    )
                    view.surface_after_sense.blit(surface_sense, (x, y))
                view.updated_at = time.monotonic()
                await asyncio.sleep(0)

                # Update info
                view.surface_info_after_sense.fill(self.background_color)
                info = [
                    f"{chess.COLOR_NAMES[board.turn].capitalize()} "
                    + (
                        f"sensed at {chess.SQUARE_NAMES[square]}"
                        if square is not None
                        else "did not sense"
                    )
                    + f" on turn {turn_index // 2 + 1}",
                    f"# possible boards for {chess.COLOR_NAMES[board.turn]}: "
                    f"{num_boards[board.turn]:,.0f} -> {len(active.boards):,.0f} "
                    f"(Δ = {len(active.boards) - num_boards[board.turn]:+,.0f})",
                    "",
                    f"{chess.COLOR_NAMES[board.turn].capitalize()} to move on turn {(turn_index + 1) // 2 + 1}",
                ]
                x = y = 10
                for line in info:
                    view.surface_info_after_sense.blit(
                        self.body_font.render(line, True, self.body_color), (x, y)
                    )
                    y += 20
                num_boards[board.turn] = len(active.boards)
                await asyncio.sleep(0)

                # Move step
                requested_move = chess.Move.from_uci(next(history_iter))
                taken_move, capture_square = simulate_move(board, requested_move)
                piece_moved = (
                    board.piece_at(requested_move.from_square)
                    if requested_move
                    else None
                )
                piece_captured = (
                    None if capture_square is None else board.piece_at(capture_square)
                )
                await active.move(requested_move, taken_move, capture_square)
                await waiting.op_move(capture_square)
                board.push(taken_move)
                turn_index += 1
                active, waiting = waiting, active

        except StopIteration:
            pass

        info = [
            "",
            f"{chess.COLOR_NAMES[self.winner].capitalize()} wins by {self.win_reason}!",
        ]
        for line in info:
            (
                view.surface_info_after_sense
                if self.num_actions % 2
                else view.surface_info
            ).blit(self.body_font.render(line, True, self.body_color), (x, y))
            y += 20

    async def respond_to_events(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.action_index = max(0, self.action_index - 1)
                    elif event.key == pygame.K_RIGHT:
                        self.action_index = min(self.num_actions, self.action_index + 1)
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return
            await asyncio.sleep(0.005)

    async def update_view(self):
        dt = 1 / 60
        actual_fps = 1 / dt
        alpha = 0.98
        last_update_time = time.time()
        while True:
            view = self.views[self.action_index // 2]
            surface_true = view.surface_true
            surface_white = view.surface_white
            surface_black = view.surface_black
            surface_info = view.surface_info
            if self.action_index % 2:  # has sensed
                surface_info = view.surface_info_after_sense
                if view.active_player == chess.WHITE:
                    surface_white = view.surface_after_sense
                else:
                    surface_black = view.surface_after_sense

            self.screen.blit(surface_true, (self.margin, self.margin))
            self.screen.blit(
                surface_white,
                (self.margin, self.margin * 2 + self.square_size * 8),
            )
            self.screen.blit(
                surface_black,
                (
                    self.margin * 2 + self.square_size * 8,
                    self.margin * 2 + self.square_size * 8,
                ),
            )
            self.screen.blit(
                surface_info, (self.margin * 2 + self.square_size * 8, self.margin)
            )
            pygame.display.flip()
            current_time = time.time()
            actual_fps = alpha * actual_fps + (1 - alpha) / max(
                1e-3, current_time - last_update_time
            )
            pygame.display.set_caption(f"Reconchess MHT Replay ({actual_fps:.1f} fps)")
            await asyncio.sleep(last_update_time + dt - current_time)
            # await asyncio.sleep(dt)
            last_update_time = current_time


class View:
    def __init__(self, true_board, font, width):
        self.surface_true = draw_boards([true_board], width, font)
        self.surface_white = draw_empty_board(font, width)
        self.surface_black = draw_empty_board(font, width)
        self.surface_after_sense = draw_empty_board(font, width)
        self.surface_info = pygame.Surface((width, width))
        self.surface_info_after_sense = pygame.Surface((width, width))
        self.active_player = true_board.turn
        self.updated_at = time.monotonic()


def board_fingerprint(board: chess.Board):
    return (
        board.turn,
        *board.occupied_co,
        board.kings,
        board.queens,
        board.bishops,
        board.knights,
        board.rooks,
        board.pawns,
        board.castling_rights,
        board.ep_square,
    )


class AsyncMultiHypothesisTracker:
    def __init__(self):
        self.boards = [chess.Board()]

    async def sense(self, square: chess.Square, result: List[Tuple[int, chess.Piece]]):
        new_boards = []
        for board in self.boards:
            if simulate_sense(board, square) == result:
                new_boards.append(board)
            await asyncio.sleep(0)
        self.boards = new_boards

    async def move(
        self,
        requested_move: chess.Move,
        taken_move: chess.Move,
        capture_square: Optional[chess.Square],
    ):
        new_boards = []
        for board in self.boards:
            if simulate_move(board, requested_move) == (taken_move, capture_square):
                board.push(taken_move)
                new_boards.append(board)
            await asyncio.sleep(0)
        self.boards = new_boards

    async def op_move(self, capture_square: Optional[chess.Square]):
        new_boards = {}
        for board in self.boards:
            for requested_move in possible_requested_moves(board):
                taken_move, simulated_capture_square = simulate_move(
                    board, requested_move
                )
                if simulated_capture_square == capture_square:
                    new_board = board.copy(stack=False)
                    new_board.push(taken_move)
                    new_boards[board_fingerprint(new_board)] = new_board
                await asyncio.sleep(0)
        self.boards = list(new_boards.values())


def _main():
    # replay = Replay("")
    # replay = Replay("00 e2e3 f2 f7f5 c7")
    replay = Replay(
        "00 e2e4 b3 d7d5 g7 g1f3 f2 g8f6 c7 e4d5 c5 d8d5 g7 d2d4 c4 d5a5 d5 b1c3 b4 f6e4 g5 "
        "f1b5 e2 b8c6 d7 a2b3 d4 e4c3 d4 b5c6 f3 b7c6 00 b2c3 d2 a5c3 00 c1d2 e2 c3a1 00 d1a1 "
        "g2 c8f5 b7 g2h3 d2 a8b8 c4 f3e5 b2 f5c2 c7 a1c3 g2 b8b1 c7 e1e2 d2 c2d1 d2 h1d1 f4 "
        "b1d1 00 c3c6 d5 e8d8 e7 c6d7 f2 d1e1 d7 d7d8"
    )
    replay.play_sync()


if __name__ == "__main__":
    _main()
