import chess
import reconchess
from reconchess.bots.trout_bot import TroutBot

from example_bot.bot import MhtBot
from reconchess_tools.ui.replay import Replay

if __name__ == "__main__":

    game = reconchess.LocalGame(900)

    white = TroutBot()
    black = MhtBot()

    winner_color, win_reason, history = reconchess.play_local_game(
        white, black, game=game
    )
    winner = "Draw" if winner_color is None else chess.COLOR_NAMES[winner_color]

    print("Game Over!")
    print(f"Winner: {winner}! ({win_reason})")

    actions = []
    for turn in history.turns():
        sense = history.sense(turn)
        actions.append("00" if sense is None else chess.SQUARE_NAMES[sense])
        actions.append((history.requested_move(turn) or chess.Move.null()).uci())
    actions = " ".join(actions)
    Replay(actions).play_sync()
