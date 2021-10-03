import chess
import click
import reconchess
import requests

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


@cli.command()
@click.argument("replay_path", type=str)
def replay_from_file(replay_path):
    history = reconchess.GameHistory.from_file(replay_path)
    Replay.from_history(history).play_sync()


@cli.command()
@click.argument("username")
@click.argument("password")
@click.argument("game_id", type=int)
@click.option(
    "--server-url",
    "server_url",
    default="https://rbc.jhuapl.edu",
    help="URL of the server.",
)
def replay_from_server(username, password, game_id, server_url):
    response = requests.get(
        server_url + f"/api/games/{game_id}/game_history", auth=(username, password)
    )
    if response.status_code != 200:
        raise requests.HTTPError(response.text)
    history: reconchess.GameHistory = response.json(cls=reconchess.GameHistoryDecoder)[
        "game_history"
    ]
    Replay.from_history(history).play_sync()


if __name__ == "__main__":
    cli()
