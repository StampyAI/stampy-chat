import pytest
from unittest.mock import patch, Mock


from stampy_chat.followups import Followup, search_authored, multisearch_authored


@pytest.mark.parametrize("query, expected_result", [
    ("what is agi", [Followup("agi title", "agi", 0.5)],),
    ("what is ai", [Followup("ai title", "ai", 0.5)],)])
def test_search_authored(query, expected_result):
    response = Mock(status_code=200, json=lambda: [
        {'title': r.text, 'pageid': r.pageid, 'score': r.score}
        for r in expected_result
    ])

    with patch('requests.get', return_value=response):
        assert search_authored(query) == expected_result


@patch('stampy_chat.followups.logger')
def test_multisearch_authored(_logger):
    results = [
        {'pageid': '1', 'title': f'result 1', 'score': 0.423},
        {'pageid': '2', 'title': f'result 2', 'score': 0.623},
        {'pageid': '3', 'title': f'this should be skipped', 'score': 0.323},
        {'pageid': '4', 'title': f'this should also be skipped', 'score': 0.1},
        {'pageid': '5', 'title': f'result 5', 'score': 0.543},
    ]

    response = Mock(json=lambda: results, status_code=200)
    with patch('requests.get', return_value=response):
        assert multisearch_authored(["what is this?", "how about this?"]) == [
            Followup('result 2', '2', 0.623),
            Followup('result 5', '5', 0.543),
            Followup('result 1', '1', 0.423),
        ]


@patch('stampy_chat.followups.logger')
def test_multisearch_authored_duplicates(_logger):
    results = {
        'query1': [
            {'pageid': '1', 'title': f'result 1', 'score': 0.423},
            {'pageid': '2', 'title': f'result 2', 'score': 0.623},
            {'pageid': '3', 'title': f'this should be skipped', 'score': 0.323},
            {'pageid': '4', 'title': f'this should also be skipped', 'score': 0.1},
            {'pageid': '5', 'title': f'result 5', 'score': 0.543},
        ],
        'query2': [
            {'pageid': '1', 'title': f'result 1', 'score': 0.723},
            {'pageid': '2', 'title': f'this should be skipped', 'score': 0.323},
            {'pageid': '5', 'title': f'this should also be skipped', 'score': 0.1},
        ],
        'query3': [
            {'pageid': '5', 'title': f'result 5', 'score': 0.511},
        ],
    }
    def getter(url):
        query = url.split('query=')[-1]
        return Mock(json=lambda: results[query], status_code=200)

    with patch('requests.get', getter):
        assert multisearch_authored(["query1", "query2", "query3"]) == [
            Followup('result 1', '1', 0.723),
            Followup('result 2', '2', 0.623),
            Followup('result 5', '5', 0.543),
        ]
