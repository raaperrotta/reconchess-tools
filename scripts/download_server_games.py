import logging
import os
from functools import partial
from multiprocessing.pool import ThreadPool
from pathlib import Path
from random import shuffle

import click
import requests


LOG = logging.getLogger(__name__)
game_dir = Path("gameLogs")


def download_game(username, password, server_url, game_id):
    game_file = game_dir / f"{game_id}.json"
    if not os.path.isfile(game_file):
        try:
            response = requests.get(server_url + f'/api/games/{game_id}/game_history',
                                    auth=(username, password))
        except ConnectionError:
            LOG.error("Connection error for game %d", game_id)
            return
        if response.status_code != 200:
            LOG.debug("Received response code %d for game ID %d", response.status_code, game_id)
        else:
            game_file.write_bytes(response.content)


@click.command()
@click.argument('username')
@click.argument('password')
@click.option('--server-url', 'server_url', default='https://rbc.jhuapl.edu', help='URL of the server.')
def main(username, password, server_url):
    ids = list(range(10_000, 300_000))
    shuffle(ids)
    list(ThreadPool(32).imap_unordered(
        partial(download_game, username, password, server_url),
        ids
    ))


if __name__ == "__main__":
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(
        "%(levelname).1s: %(message)s"
    ))
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG)
    main()
