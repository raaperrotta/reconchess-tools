import tensorflow as tf

from sac.bot import ACTIONS


def construct_td_pool_base():
    boards = tf.keras.layers.Input((None, 788))
    action_mask = tf.keras.layers.Input(len(ACTIONS), dtype=bool)

    x = tf.keras.layers.Masking(-1)(boards)
    for n in [64, 128]:
        x = tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(n, "relu"))(x)

    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    for n in [128, 64]:
        x = tf.keras.layers.Dense(n, "relu")(x)

    out = tf.keras.layers.Dense(len(ACTIONS))(x)

    return boards, action_mask, out


def construct_transformer_base():
    boards = tf.keras.layers.Input((None, 788))
    action_mask = tf.keras.layers.Input(len(ACTIONS), dtype=bool)

    # Masks are 1 where data exists, 0 where pad values exist
    board_mask = tf.keras.backend.all(tf.not_equal(boards, -1), axis=-1)

    # Project the one-hot board encodings into a more dense space
    n = 128
    x = tf.keras.layers.Dense(n)(boards)
    # Use a dense layer with constant input to create a learnable class embedding
    cls = tf.keras.layers.Dense(n, use_bias=False)(1 + 0 * x[:, :1, :1])
    x = tf.concat([cls, x], axis=1)
    # Assumes padding is at end so board_mask[:, -1] is always all true
    board_mask = tf.concat([board_mask[:, -1:], board_mask], axis=1)
    for _ in range(3):
        # x = tf.keras.layers.LayerNormalization()(x)  # Does this help?
        mha = tf.keras.layers.MultiHeadAttention(num_heads=8, key_dim=16)
        update = mha(x, x, attention_mask=board_mask[:, :, None])
        # TODO gated connection
        x = x + update
    # Grab output for "class" token as state embedding
    embedded_state = x[:, 0]

    x = embedded_state
    for n in [128, 128]:
        x = tf.keras.layers.Dense(n, "relu")(x)

    out = tf.keras.layers.Dense(len(ACTIONS))(x)

    return boards, action_mask, out


construct_model_base = construct_td_pool_base
