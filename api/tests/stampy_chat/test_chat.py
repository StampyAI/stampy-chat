import pytest
import tiktoken
from unittest.mock import patch, MagicMock

from stampy_chat.followups import Followup
from stampy_chat.settings import Settings
from stampy_chat.get_blocks import Block
from stampy_chat.chat import (
    cap, construct_prompt, check_openai_moderation, remaining_tokens, talk_to_robot_internal,
    talk_to_robot, talk_to_robot_simple, prompt_context, prompt_history, logger
)


ENCODER = tiktoken.get_encoding('cl100k_base')


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def history():
    return [
        {"role": "user", "content": "Die monster. You don’t belong in this world!"},
        {"role": "assistant", "content": "It was not by my hand[1] I am once again given flesh. I was called here by humans who wished to pay me tribute."},
        {"role": "user", "content": "Tribute!?! You steal men's souls and make them your slaves!"},
        {"role": "assistant", "content": "Perhaps the same could be said[321] of all religions..."},
        {"role": "user", "content": "Your words are as empty as your soul! Mankind ill needs a savior such as you!"},
        {"role": "assistant", "content": "What is a man? A[4234] miserable little pile of secrets. But enough talk... Have at you!"},
    ]


@pytest.fixture
def context():
    return [
        Block(
            id=i,
            url=f"http://bla.bla/{i}",
            tags=[],
            title=f"Block{i}",
            authors=[f"Author{i}"],
            date=f"2021-01-0{i + 1}",
            text=f"Block text {i}"
        ) for i in range(5)
    ]


@pytest.mark.parametrize(
    "text, max_tokens, expected",
    [
        ("", 10, ""),  # case when input text is empty
        ("Hello, world!", -1, "..."),  # case when max_tokens are negative
        ("Hello, world!", 0, "..."),  # case when max_tokens is zero
        ("Hello, world!", 10, "Hello, world!"),  # case when input text is less than max_tokens
        ("Hello, world! This is a long text string that exceeds the token limit.", 5,
         ENCODER.decode(ENCODER.encode("Hello, world! This is a long text string that exceeds the token limit.")[:5]) + " ..."),  # case when input text is more than max_tokens
    ],
)
def test_cap(text, max_tokens, expected):
    assert cap(text, max_tokens, ENCODER) == expected


EXPECTED_CONTEXT = """bla bla: [a] Block0 - Author0 - 2021-01-01
Block text 0

[b] Block1 - Author1 - 2021-01-02
Block text 1

[c] Block2 - Author2 - 2021-01-03
Block text 2

[d] Block3 - Author3 - 2021-01-04
Block text 3

[e] Block4 - Author4 - 2021-01-05
Block text 4"""


def test_prompt_context(context):
    settings = Settings(
        numTokens=1000, contextFraction=1,
        prompts={
            'source': {'prefix': "bla bla: "},
            'modes': {'default': ''}
        }
    )
    assert prompt_context(context, settings) == EXPECTED_CONTEXT


def test_prompt_context_cutoff(context):
    settings = Settings(
        numTokens=50, contextFraction=1,
        prompts={
            'source': {'prefix': "bla bla: "},
            'modes': {'default': ''}
        }
    )

    formatted = prompt_context(context, settings)

    assert len(ENCODER.encode(formatted)) == 50 + 1  # the "..." is a single token
    assert prompt_context(context, settings) == EXPECTED_CONTEXT[:116] + '...'


def test_prompt_history(history):
    settings = Settings(numTokens=1000, historyFraction=1)
    assert prompt_history(history, settings) == [
        {'content': 'Q: Die monster. You don’t belong in this world!', 'role': 'user'},
        {'content': 'It was not by my hand[x] I am once again given flesh. I was called here by humans who wished to pay me tribute.', 'role': 'assistant'},
        {'content': "Q: Tribute!?! You steal men's souls and make them your slaves!", 'role': 'user'},
        {'content': 'Perhaps the same could be said[x] of all religions...', 'role': 'assistant'},
        {'content': 'Q: Your words are as empty as your soul! Mankind ill needs a savior such as you!', 'role': 'user'},
        {'content': 'What is a man? A[x] miserable little pile of secrets. But enough talk... Have at you!', 'role': 'assistant'},
    ]


def test_prompt_history_cutoffs(history):
    settings = Settings(numTokens=50, historyFraction=1)
    assert prompt_history(history, settings) == [
        {'content': 'Perhaps the same could be said ...', 'role': 'assistant'},
        {'content': 'Q: Your words are as empty as your soul! Mankind ill needs a savior such as you!', 'role': 'user'},
        {'content': 'What is a man? A[x] miserable little pile of secrets. But enough talk... Have at you!', 'role': 'assistant'},
    ]


def test_prompt_history_limit_items():
    history = [{'content': f'content {i}', 'role': 'assistant'} for i in range(30)]

    settings = Settings(numTokens=1000, historyFraction=1)
    assert len(prompt_history(history, settings)) == 10
    assert prompt_history(history, settings) == history[-10:]


def test_construct_prompt(history, context, settings):
    assert construct_prompt("to be or not to be?", settings, history, context) == [
        {
            'content': (
                'You are a helpful assistant knowledgeable about AI Alignment and '
                "Safety. Please give a clear and coherent answer to the user's "
                'questions.(written after "Q:") using the following sources. Each '
                'source is labeled with a letter. Feel free to use the sources in '
                'any order, and try to use multiple sources in your answers.\n'
                '\n'
                '[a] Block0 - Author0 - 2021-01-01\n'
                'Block text 0\n'
                '\n'
                '[b] Block1 - Author1 - 2021-01-02\n'
                'Block text 1\n'
                '\n'
                '[c] Block2 - Author2 - 2021-01-03\n'
                'Block text 2\n'
                '\n'
                '[d] Block3 - Author3 - 2021-01-04\n'
                'Block text 3\n'
                '\n'
                '[e] Block4 - Author4 - 2021-01-05\n'
                'Block text 4\n'
                '\n'
                'Before the question ("Q: "), there will be a history of previous '
                'questions and answers. These sources only apply to the last '
                'question. Any sources used in previous answers are invalid.'
            ),
            'role': 'system'
         }, {
             'content': 'Q: Die monster. You don’t belong in this world!', 'role': 'user'
         }, {
            'content': 'It was not by my hand[x] I am once again given flesh. I was called'
             ' here by humans who wished to pay me tribute.',
            'role': 'assistant'
        },
        {'content': "Q: Tribute!?! You steal men's souls and make them your slaves!", 'role': 'user'},
        {'content': 'Perhaps the same could be said[x] of all religions...', 'role': 'assistant'},
        {'content': 'Q: Your words are as empty as your soul! Mankind ill needs a savior such as you!', 'role': 'user'},
        {
            'content': 'What is a man? A[x] miserable little pile of secrets. But enough '
                       'talk... Have at you!',
            'role': 'assistant'
        },
        {
            'content': (
                'In your answer, please cite any claims you make back to each '
                'source using the format: [a], [b], etc. If you use multiple '
                'sources to make a claim cite all of them. For example: "AGI is '
                'concerning [c, d, e]."\n'
                '\n'
                'Q: to be or not to be?'
            ),
            'role': 'user'
        },
    ]


def test_construct_prompt_no_history_or_context(settings):
    assert construct_prompt("to be or not to be?", settings, [], []) == [
        {
            'content': (
                'You are a helpful assistant knowledgeable about AI Alignment and '
                "Safety. Please give a clear and coherent answer to the user's "
                'questions.(written after "Q:") using the following sources. Each '
                'source is labeled with a letter. Feel free to use the sources in '
                'any order, and try to use multiple sources in your answers.'
            ),
            'role': 'system'
        },
        {
            'content': (
                'In your answer, please cite any claims you make back to each '
                'source using the format: [a], [b], etc. If you use multiple '
                'sources to make a claim cite all of them. For example: "AGI is '
                'concerning [c, d, e]."\n'
                '\n'
                'Q: to be or not to be?'
            ),
            'role': 'user'
        },
    ]



def test_check_openai_moderation_flagged():
    prompt = [{"content": "message 1"}, {"content": "message 2"}]
    query = "test query"

    # Create a mock for openai.Moderation.create return value
    results = {
        'results': [
            {'flagged': False, 'text': 'bla bla 1'},
            {'flagged': True, 'text': 'bla bla 2'},
            {'flagged': False, 'text': 'bla bla 3'},
        ]
    }

    # Patch openai.Moderation.create and logger.moderation_issue
    with patch('openai.Moderation.create', return_value=results), patch.object(logger, 'moderation_issue'):
        with pytest.raises(ValueError):
            check_openai_moderation(prompt, query)


def test_check_openai_moderation_not_flagged():
    prompt = [{"content": "message 1"}, {"content": "message 2"}]
    query = "test query"

    results = {
        'results': [
            {'flagged': False, 'text': 'bla bla 1'},
            {'flagged': False, 'text': 'bla bla 2'},
            {'flagged': False, 'text': 'bla bla 3'},
        ]
    }

    # Patch openai.Moderation.create and logger.moderation_issue
    with patch('openai.Moderation.create', return_value=results), patch.object(logger, 'moderation_issue'):
        assert check_openai_moderation(prompt, query) is None


@pytest.mark.parametrize('prompt, remaining', (
    ([{'role': 'system', 'content': 'bla'}], 4045),
    (
        [
            {'role': 'system', 'content': 'bla'},
            {'role': 'user', 'content': 'message 1'},
            {'role': 'assistant', 'content': 'response 1'},
        ],
        4037
    ),
    (
        [
            {'role': 'system', 'content': 'bla'},
            {'role': 'user', 'content': 'message 1'},
            {'role': 'assistant', 'content': 'response 1'},
        ] * 1999,
        0
    ),
))
def test_remaining_tokens(prompt, remaining, settings):
    assert remaining_tokens(prompt, settings) == remaining


@patch('stampy_chat.chat.check_openai_moderation')
@patch('stampy_chat.chat.logger')
def test_talk_to_robot_internal(history, context):
    chunks = [
        {'choices': [{'delta': {'content': f"response 1"}}]},
        {'choices': [{'delta': {'content': f"response 2"}}]},
        {'choices': [{'delta': {'content': f"response 3"}}]},
        {'choices': [{'delta': {}}]},
        {'choices': [{'delta': {'content': None}}]},
        {'choices': [{'delta': {'content': f"response 4"}}]},
    ]
    followups = [
        Followup('followup 1', '1', 0.231),
        Followup('followup 2', '2', 0.231),
        Followup('followup 3', '3', 0.231),
    ]
    with patch('stampy_chat.chat.get_top_k_blocks', return_value=context):
        with patch('stampy_chat.chat.multisearch_authored', return_value=followups):
            with patch('openai.ChatCompletion.create', return_value=chunks):
                assert list(talk_to_robot_internal("index", "what is this about?", history, 'session id')) == [
                    {'phase': 'semantic', 'state': 'loading'},
                    {'citations': [], 'state': 'citations'},
                    {'phase': 'prompt', 'state': 'loading'},
                    {'phase': 'llm', 'state': 'loading'},
                    {'content': 'response 1', 'state': 'streaming'},
                    {'content': 'response 2', 'state': 'streaming'},
                    {'content': 'response 3', 'state': 'streaming'},
                    {'content': 'response 4', 'state': 'streaming'},
                    {'state': 'loading', 'phase': 'followups'},
                    {'state': 'followups', 'followups': [
                        {'pageid': '1', 'score': 0.231, 'text': 'followup 1'},
                        {'pageid': '2', 'score': 0.231, 'text': 'followup 2'},
                        {'pageid': '3', 'score': 0.231, 'text': 'followup 3'},
                    ]},
                    {'state': 'done'},
                ]


@patch('stampy_chat.chat.check_openai_moderation')
@patch('stampy_chat.chat.logger')
def test_talk_to_robot_internal_error(history, context):
    chunks = [
        {'choices': [{'delta': {'content': f"response 1"}}]},
        {'choices': [{'delta': {'content': f"response 2"}}]},
        {'choices': [{'delta': {'content': f"response 3"}}]},
        {'choices': []},
    ]
    with patch('stampy_chat.chat.get_top_k_blocks', return_value=context):
        with patch('openai.ChatCompletion.create', return_value=chunks):
            assert list(talk_to_robot_internal("index", "what is this about?", history, 'session id')) == [
                {'phase': 'semantic', 'state': 'loading'},
                {'citations': [], 'state': 'citations'},
                {'phase': 'prompt', 'state': 'loading'},
                {'phase': 'llm', 'state': 'loading'},
                {'content': 'response 1', 'state': 'streaming'},
                {'content': 'response 2', 'state': 'streaming'},
                {'content': 'response 3', 'state': 'streaming'},
                {'error': 'list index out of range', 'state': 'error'},
            ]
