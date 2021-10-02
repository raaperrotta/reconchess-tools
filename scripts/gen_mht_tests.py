import chess

from reconchess_tools.mht import MultiHypothesisTracker
from reconchess_tools.utilities import simulate_sense

mht_white = MultiHypothesisTracker()
mht_black = MultiHypothesisTracker()

infoset_white = [chess.WHITE]
infoset_black = [chess.BLACK]

board = chess.Board()

print("White to move")
print("White infoset", infoset_white)
print("MHT boards:")
print("\n".join(board.epd(en_passant="xfen") for board in mht_white.boards))
print("\n")

move = chess.Move.from_uci("e2e4")
board.push(move)
infoset_white.append((move.uci(), move.uci(), None))
mht_white.move(move, move, None)
infoset_black.append(None)
mht_black.op_move(None)

print("Black to sense")
print("Black infoset", infoset_black)
print("MHT boards:")
print("\n".join(board.epd(en_passant="xfen") for board in mht_black.boards))
print("\n")

square = chess.E3
result = simulate_sense(board, square)
mht_black.sense(square, result)
result_str = "".join(str(p) if p else "_" for _, p in sorted(result))
infoset_black.append((square, result_str))

print("Black to move")
print("Black infoset", infoset_black)
print("MHT boards:")
print("\n".join(board.epd(en_passant="xfen") for board in mht_black.boards))
print("\n")

move = chess.Move.from_uci("f7f5")
board.push(move)
infoset_black.append((move.uci(), move.uci(), None))
mht_black.move(move, move, None)
infoset_white.append(None)
mht_white.op_move(None)

print("White to sense")
print("White infoset", infoset_white)
print("MHT boards:")
print({board.epd(en_passant="xfen") for board in mht_white.boards})
print("\n")
