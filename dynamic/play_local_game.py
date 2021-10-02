import chess
import reconchess

from dynamic.bot import MhtBot

if __name__ == "__main__":

    game = reconchess.LocalGame(900)

    white = MhtBot()
    black = MhtBot()

    winner_color, win_reason, history = reconchess.play_local_game(
        white, black, game=game
    )
    winner = "Draw" if winner_color is None else chess.COLOR_NAMES[winner_color]

    print("Game Over!")
    print(f"Winner: {winner}! ({win_reason})")
