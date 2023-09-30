import pytest
from datetime import datetime
from unittest.mock import patch, Mock, call
from stampy_chat.get_blocks import Block, get_top_k_blocks, parse_block, join_blocks


@pytest.mark.parametrize('match_override, block_override', (
    ({}, {}),

    # Check dates
    ({'date_published': '2023-01-01T03:04:05'}, {'date': '2023-01-01T03:04:05'}),
    (
        {'date_published': datetime.fromisoformat('2023-01-02T03:04:05')},
        {'date': '2023-01-02'}
    ),
    (
        {'date_published': datetime.fromisoformat('2023-01-03T03:04:05').date()},
        {'date': '2023-01-03'}
    ),
    (
        {'date_published': datetime.fromisoformat('2023-01-04T03:04:05').timestamp()},
        {'date': '2023-01-04'}
    ),
    (
        {'date_published': int(datetime.fromisoformat('2023-01-05T03:04:05').timestamp())},
        {'date': '2023-01-05'}
    ),

    # Check authors
    ({'author': 'mr blobby'}, {'authors': ['mr blobby']}),
    ({'authors': ['mr blobby', 'John Snow']}, {'authors': ['mr blobby', 'John Snow']}),
    (
        {'authors': ['mr blobby', 'John Snow'], 'author': 'your momma'},
        {'authors': ['mr blobby', 'John Snow']}
    ),
))
def test_parse_block(match_override, block_override):
    match = dict({
        "hash_id": "1",
        "title": "Block",
        "text": "text",
        "date_published": "2021-12-30",
        "authors": [],
        "url": "http://test.com",
        "tags": "tag",
    }, **match_override)

    expected_block_data = dict({
        "id": "1",
        "title": "Block",
        "text": "text",
        "date": "2021-12-30",
        "authors": [],
        "url": "http://test.com",
        "tags": "tag",
    }, **block_override)

    assert parse_block({'metadata': match}) == Block(**expected_block_data)


@pytest.mark.parametrize("blocks, expected", [
    ([], []),
    (
        [Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1')],
        [Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1')]
    ),
    (
        [
            Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1'),
            Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text2')
        ],
        [Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1\n.....\ntext2')]
    ),
    (
        [
            Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1'),
            Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text2'),
            Block('id2', 'title2', ['author2'], 'date2', 'url2', 'tags2', 'text2'),
            Block('id3', 'title3', ['author3'], 'date3', 'url3', 'tags3', 'text3'),
        ],
        [
            Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1\n.....\ntext2'),
            Block('id2', 'title2', ['author2'], 'date2', 'url2', 'tags2', 'text2'),
            Block('id3', 'title3', ['author3'], 'date3', 'url3', 'tags3', 'text3'),
        ]
    ),
    (
        [
            Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1-1'),
            Block('id3', 'title3', ['author3'], 'date3', 'url3', 'tags3', 'text3'),
            Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1-2'),
            Block('id2', 'title2', ['author2'], 'date2', 'url2', 'tags2', 'text2'),
            Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1-3'),
        ],
        [
            Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1-1\n.....\ntext1-2\n.....\ntext1-3'),
            Block('id2', 'title2', ['author2'], 'date2', 'url2', 'tags2', 'text2'),
            Block('id3', 'title3', ['author3'], 'date3', 'url3', 'tags3', 'text3'),
        ]
    ),
])
def test_join_blocks(blocks, expected):
    assert list(join_blocks(blocks)) == expected


def test_join_blocks_different_blocks():
    blocks = [
        Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1'),
        Block('id2', 'title2', ['author2'], 'date2', 'url2', 'tags2', 'text2')
    ]
    assert list(join_blocks(blocks)) == [
        Block('id1', 'title1', ['author1'], 'date1', 'url1', 'tags1', 'text1'),
        Block('id2', 'title2', ['author2'], 'date2', 'url2', 'tags2', 'text2')
    ]


def test_get_top_k_blocks_no_index():
    response = Mock()
    response.json.return_value = [
        {
            "hash_id": f"{i}",
            "title": f"Block {i}",
            "text": f"text {i}",
            "date_published": f"2021-12-0{i}",
            "authors": [],
            "url": f"http://test.com/{i}",
            "tags": f"tag{i}",
        } for i in range(5)
    ]
    with patch('stampy_chat.get_blocks.requests.post', return_value=response):
        assert get_top_k_blocks(None, "bla bla bla", 10) == [
            Block(
                id=f"{i}",
                title=f"Block {i}",
                text=f"text {i}",
                date=f"2021-12-0{i}",
                authors=[],
                url=f"http://test.com/{i}",
                tags=f"tag{i}"
            ) for i in range(5)
        ]


@patch('stampy_chat.get_blocks.get_embedding')
def test_get_top_k_blocks(_mock_embedder):
    index = Mock()
    index.query.return_value = {
        'matches': [
            {
                'metadata': {
                    "hash_id": f"{i}",
                    "title": f"Block {i}",
                    "text": f"text {i}",
                    "date_published": f"2021-12-0{i}",
                    "authors": [],
                    "url": f"http://test.com/{i}",
                    "tags": f"tag{i}",
                }
            } for i in range(5)
        ]
    }

    assert get_top_k_blocks(index, "bla bla bla", 10) == [
        Block(
            id=f"{i}",
            title=f"Block {i}",
            text=f"text {i}",
            date=f"2021-12-0{i}",
            authors=[],
            url=f"http://test.com/{i}",
            tags=f"tag{i}"
        ) for i in range(5)
    ]
