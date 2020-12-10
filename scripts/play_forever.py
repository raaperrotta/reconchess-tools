import chess
import reconchess
from reconchess.bots.trout_bot import TroutBot

from example_bot.bot import MhtBot


def play(p1, p2):
    winner_color, win_reason, history = reconchess.play_local_game(p1(), p2())
    winner = "Draw" if winner_color is None else chess.COLOR_NAMES[winner_color]
    print("Game Over!")
    print(f"Winner: {winner}! ({win_reason})")


if __name__ == "__main__":
    p1, p2 = MhtBot, TroutBot
    while True:
        play(p1, p2)
        p1, p2 = p2, p1
