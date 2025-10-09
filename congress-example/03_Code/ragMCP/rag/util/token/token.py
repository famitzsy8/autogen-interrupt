import tiktoken

def get_token_encoder():
    try:
        _ENCODER = tiktoken.get_encoding("cl100k_base")
    except ModuleNotFoundError:
        class _DummyEncoder:  # pylint: disable=too-few-public-methods
            def encode(self, text: str):  # noqa: D401
                return text.split()

            def decode(self, tokens):  # noqa: D401
                return " ".join(tokens)

        _ENCODER = _DummyEncoder()

    return _ENCODER