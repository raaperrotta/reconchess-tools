import chess
import reconchess
from reconchess.bots.attacker_bot import AttackerBot
from reconchess.bots.trout_bot import TroutBot

from example_bot.bot import MhtBot


def play(p1, p2):
    winner_color, win_reason, history = reconchess.play_local_game(p1(), p2())
    winner = "Draw" if winner_color is None else chess.COLOR_NAMES[winner_color]
    print("Game Over!")
    print(f"Winner: {winner}! ({win_reason})")
    return winner_color


if __name__ == "__main__":
    p1, p2 = MhtBot, AttackerBot
    # Wins, losses, ties
    record_as_white = [0, 0, 0]
    record_as_black = [0, 0, 0]
    while True:
        winner = play(p1, p2)
        record_as_white[2 if winner is None else (1 - winner)] += 1
        print("Record as white:", record_as_white)
        print("Record as black:", record_as_black)
        winner = play(p2, p1)
        record_as_black[2 if winner is None else winner] += 1
        print("Record as white:", record_as_white)
        print("Record as black:", record_as_black)
