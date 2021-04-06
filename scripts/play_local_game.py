import chess
import reconchess
from reconchess.bots.attacker_bot import AttackerBot
from reconchess.bots.trout_bot import TroutBot

from example_bot.bot import MhtBot
from example_bot.strangefish_lite import StrangeFishLite
from reconchess_tools.ui.replay import Replay

if __name__ == "__main__":

    game = reconchess.LocalGame(900)

    white = StrangeFishLite()
    black = TroutBot()

    winner_color, win_reason, history = reconchess.play_local_game(
        white, black, game=game
    )
    winner = "Draw" if winner_color is None else chess.COLOR_NAMES[winner_color]

    print("Game Over!")
    print(f"Winner: {winner}! ({win_reason})")

    Replay.from_history(history).play_sync()
