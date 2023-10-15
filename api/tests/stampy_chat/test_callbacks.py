from stampy_chat.callbacks import stream_callback


def test_stream_callback_generates():
    def caller_backer(callback):
        for i in range(5):
            callback(f'value no {i}')

    assert list(stream_callback(caller_backer)) == [
        f'value no {i}' for i in range(5)
    ]


def test_stream_callback_formatter():
    def caller_backer(callback):
        for i in range(5):
            callback(f'value no {i}')

    assert list(stream_callback(caller_backer, lambda val: 'formatted ' + val)) == [
        f'formatted value no {i}' for i in range(5)
    ]


def test_stream_callback_on_error():
    def caller_backer(callback):
        for i in range(5):
            callback(f'value no {i}')
        raise ValueError('this is a pen')

    assert list(stream_callback(caller_backer)) == [
        f'value no {i}' for i in range(5)
    ] + ['this is a pen']
