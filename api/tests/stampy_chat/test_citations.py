import pytest
from datetime import datetime
from unittest.mock import patch, Mock, call

from langchain.schema.vectorstore import VectorStore

from stampy_chat.citations import ReferencesSelector, format_block


class DummyVectorStore(VectorStore):
    """LangChain is very restrictive with validated fields, so this class mocks a VectorStore."""
    def __init__(self, *args, similarity_search=None, similarity_search_return=None, **kwargs):
        self.similarity_search_func = similarity_search
        self.similarity_search_return_value = similarity_search_return

    def add_texts(self, *args, **kwargs):
        pass

    def from_texts(self, *args, **kwargs):
        pass

    def similarity_search(self, *args, **kwargs):
        assert False, 'this should not have been called'

    def similarity_search_with_score(self, *args, **kwargs):
        if self.similarity_search_return_value:
            return self.similarity_search_return_value
        elif self.similarity_search_func:
            return self.similarity_search_func(*args, **kwargs)
        return []


@pytest.fixture
def selector():
    examples = [
        (Mock(page_content=f'{i}', metadata={
            'bla': f'bla {i}'
        }), 0.81 + i / 10) for i in range(5)
    ]
    return ReferencesSelector(vectorstore=DummyVectorStore(similarity_search_return=examples))


@pytest.mark.parametrize('num, letter', (
    (0, 'a'), (25, 'z'),
    (26, '{'),  # this is a basic ASCII translator, so too many citations will result in fun
))
def test_ReferencesSelector_make_references(num, letter):
    assert ReferencesSelector.make_reference(num) == letter


def test_ReferencesSelector_select_examples(selector):
    assert selector.select_examples(input_variables={}) == [
        {'bla': 'bla 0', 'id': '0', 'reference': 'a'},
        {'bla': 'bla 1', 'id': '1', 'reference': 'b'},
        {'bla': 'bla 2', 'id': '2', 'reference': 'c'},
        {'bla': 'bla 3', 'id': '3', 'reference': 'd'},
        {'bla': 'bla 4', 'id': '4', 'reference': 'e'},
    ]


def test_ReferencesSelector_select_examples_callbacks(selector):
    callback = Mock()
    selector.callbacks = [callback]

    expected_examples = [
        {'bla': 'bla 0', 'id': '0', 'reference': 'a'},
        {'bla': 'bla 1', 'id': '1', 'reference': 'b'},
        {'bla': 'bla 2', 'id': '2', 'reference': 'c'},
        {'bla': 'bla 3', 'id': '3', 'reference': 'd'},
        {'bla': 'bla 4', 'id': '4', 'reference': 'e'},
    ]
    input_variables = {'var1': 'bla', 'var2': 'ble'}

    assert selector.select_examples(input_variables=input_variables) == expected_examples
    callback.on_context_fetch_start.assert_called_once_with(input_variables)
    callback.on_context_fetch_end.assert_called_once_with(expected_examples)


def test_ReferencesSelector_select_examples_removes_duplicates(selector):
    selector.vectorstore.similarity_search_return_value = [
        (Mock(page_content=f'{i}', metadata={
            'bla': f'bla {i}'
        }), selector.min_score + 0.1 + i / 10) for i in range(5)
    ] * 5

    assert selector.select_examples(input_variables={}) == [
        {'bla': 'bla 0', 'id': '0', 'reference': 'a'},
        {'bla': 'bla 1', 'id': '1', 'reference': 'b'},
        {'bla': 'bla 2', 'id': '2', 'reference': 'c'},
        {'bla': 'bla 3', 'id': '3', 'reference': 'd'},
        {'bla': 'bla 4', 'id': '4', 'reference': 'e'},
    ]


def test_ReferencesSelector_select_examples_removes_low_scores(selector):
    def calc_score(i):
        # odd numbers should have scores small enough to be removed
        if i % 2 == 0:
            return 0.81 + i / 10
        else:
            return 0.8 - i / 10

    selector.vectorstore.similarity_search_return_value = [
        (Mock(page_content=f'{i}', metadata={
            'bla': f'bla {i}'
        }), calc_score(i)) for i in range(5)
    ]

    assert selector.select_examples(input_variables={}) == [
        {'bla': 'bla 0', 'id': '0', 'reference': 'a'},
        {'bla': 'bla 2', 'id': '2', 'reference': 'b'},
        {'bla': 'bla 4', 'id': '4', 'reference': 'c'},
    ]


def test_ReferencesSelector_select_examples_check_history(selector):

    def searcher(query, *args, **kwargs):
        return [(Mock(page_content=query, metadata={'bla': query}), 0.9)]

    selector.vectorstore.similarity_search_return_value = None
    selector.vectorstore.similarity_search_func = searcher

    history = [
        Mock(content='first history item'),
        Mock(content='second history item'),
        Mock(content='last history item'),
    ]
    assert selector.select_examples(input_variables={'query': 'queried value', 'history': history}) == [
        {'bla': 'queried value', 'id': 'queried value', 'reference': 'a'},
        {'bla': 'last history item', 'id': 'last history item', 'reference': 'b'},
        {'bla': 'second history item', 'id': 'second history item', 'reference': 'c'},
        {'bla': 'first history item', 'id': 'first history item', 'reference': 'd'}
    ]


def test_ReferencesSelector_select_examples_check_history_n_items(selector):
    def searcher(query, *args, **kwargs):
        return [
            (Mock(page_content=f'{query} - {i}', metadata={'bla': query}), 0.9)
            for i in range(3)
        ]

    selector.vectorstore.similarity_search_return_value = None
    selector.vectorstore.similarity_search_func = searcher

    history = [
        Mock(content='first history item'),
        Mock(content='second history item'),
        Mock(content='last history item'),
    ]
    assert selector.select_examples(input_variables={'query': 'queried value', 'history': history}) == [
        {'bla': 'queried value', 'id': 'queried value - 0', 'reference': 'a'},
        {'bla': 'queried value', 'id': 'queried value - 1', 'reference': 'b'},
        {'bla': 'queried value', 'id': 'queried value - 2', 'reference': 'c'},
        {'bla': 'last history item', 'id': 'last history item - 0', 'reference': 'd'},
        {'bla': 'last history item', 'id': 'last history item - 1', 'reference': 'e'},
        {'bla': 'last history item', 'id': 'last history item - 2', 'reference': 'f'},
    ]


@pytest.mark.parametrize("overrides, expected", [
    # Basic fields
    ({}, {}),
    ({'title': 'bla bla'}, {'title': 'bla bla'}),
    ({'text': 'bla bla'}, {'text': 'bla bla'}),
    ({'url': 'different.bla.bla'}, {'url': 'different.bla.bla'}),
    ({'tags': 'a tag, and another one'}, {'tags': 'a tag, and another one'}),

    # Id
    ({'id': 'some id'}, {'id': 'some id'}),
    ({'hash_id': 'some hash id'}, {'id': 'some hash id'}),
    ({'id': 'some id', 'hash_id': 'some hash id'}, {'id': 'some hash id'}),

    # Authors
    ({'authors': 'mr blobby'}, {'authors': 'mr blobby'}),
    ({'authors': ['mr blobby', 'john snow']}, {'authors': ['mr blobby', 'john snow']}),
    ({'author': 'your momma'}, {'authors': ['your momma']}),
    ({'author': 'your momma', 'authors': ['mr blobby', 'john snow']}, {'authors': ['mr blobby', 'john snow']}),

    # Date field
    ({'date_published': '2020-01-02'}, {'date': '2020-01-02'}),
    ({'date': '2020-01-02'}, {'date': '2020-01-02'}),
    ({'date': '1930-01-02', 'date_published': '2020-01-02'}, {'date': '2020-01-02'}),

    # Date format
    ({'date_published': datetime.fromisoformat('2020-01-02T01:02:03')}, {'date': '2020-01-02'}),
    ({'date_published': datetime.fromisoformat('2020-01-02T01:02:03').date()}, {'date': '2020-01-02'}),
    ({'date_published': datetime.fromisoformat('2020-01-02T01:02:03').timestamp()}, {'date': '2020-01-02'}),
    ({'date_published': int(datetime.fromisoformat('2020-01-02T01:02:03').timestamp())}, {'date': '2020-01-02'}),
])
def test_format_block(overrides, expected):
    defaults = {
        'title': 'das kapititle',
        'url': 'http://bla.bla',
        'text': 'some text'
    }
    default_exceptions = {
        'id': None,
        'title': 'das kapititle',
        'url': 'http://bla.bla',
        'text': 'some text',
        'authors': None,
        'date': None,
        'tags': None,
    }
    assert format_block(dict(defaults, **overrides)) == dict(default_exceptions, **expected)
