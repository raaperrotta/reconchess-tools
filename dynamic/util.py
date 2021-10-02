import chess


def sense_result_to_string(result):
    return "".join(str(p) if p else "_" for _, p in sorted(result))


def sense_result_from_string(sensed_square, string):
    result = []
    for offset, symbol in zip([-9, -8, -7, -1, 0, 1, 7, 8, 9], string):
        square = sensed_square + offset
        piece = None if symbol == "_" else chess.Piece.from_symbol(symbol)
        result.append((square, piece))
    return result
