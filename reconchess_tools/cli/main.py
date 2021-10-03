import chess
import click
import reconchess

from reconchess_tools.ui.replay import Replay


@click.group()
def cli():
    pass


@cli.command()
@click.argument("white_path", type=str)
@click.argument("black_path", type=str)
def bot_match(white_path, black_path):
    game = reconchess.LocalGame(900)

    _, white = reconchess.load_player(white_path)
    _, black = reconchess.load_player(black_path)

    winner_color, win_reason, history = reconchess.play_local_game(
        white(), black(), game=game
    )
    winner = "Draw" if winner_color is None else chess.COLOR_NAMES[winner_color]

    print("Game Over!")
    print(f"Winner: {winner}! ({win_reason})")

    Replay.from_history(history).play_sync()


if __name__ == "__main__":
    cli()
