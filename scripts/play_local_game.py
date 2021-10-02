import chess
import reconchess

from example_bot.bot import MhtBot
from reconchess_tools.ui.replay import Replay
from sac.bot import SacBot

if __name__ == "__main__":

    game = reconchess.LocalGame(900)

    white = MhtBot()
    black = SacBot(None, None, None, None)

    winner_color, win_reason, history = reconchess.play_local_game(
        white, black, game=game
    )
    winner = "Draw" if winner_color is None else chess.COLOR_NAMES[winner_color]

    print("Game Over!")
    print(f"Winner: {winner}! ({win_reason})")

    Replay.from_history(history).play_sync()
