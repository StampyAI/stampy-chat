import pytest
from unittest.mock import patch, Mock, call

from langchain_core.messages import HumanMessage, AIMessage
from stampy_chat.logging import *


def test_emit_ignore_internal():
    handler = DiscordHandler()
    record = Mock(name="stampy_chat.bla")
    record.name = "stampy_chat.bla"

    with patch.object(handler, "to_discord") as sender:
        assert handler.emit(record) is None
        assert sender.assert_not_called


@pytest.mark.parametrize(
    "level, discord_level",
    (
        ("debug", "warn"),
        ("info", "warn"),
    ),
)
def test_emit_ignore_lower_levels(level, discord_level):
    handler = DiscordHandler()
    record = Mock(exc_text="bla", stack_info="", levelno=getLevelName(level))
    record.name = "bla"

    with patch.object(handler, "to_discord") as sender:
        with patch("stampy_chat.logging.DISCORD_LOG_LEVEL", discord_level):
            handler.emit(record)
            assert sender.assert_not_called


@pytest.mark.parametrize(
    "level, discord_level",
    (
        ("warn", "warn"),
        ("warn", "info"),
        ("debug", "debug"),
    ),
)
def test_emit_for_higher_levels(level, discord_level):
    handler = DiscordHandler()
    record = Mock(exc_text="bla", stack_info="", levelno=getLevelName(level))
    record.name = "bla"

    with patch.object(handler, "to_discord") as sender:
        with patch("stampy_chat.logging.DISCORD_LOG_LEVEL", discord_level):
            handler.emit(record)
            assert sender.assert_called


def test_to_discord_no_url():
    handler = DiscordHandler()

    with patch("stampy_chat.logging.DISCORD_LOGGING_URL", None):
        with patch("stampy_chat.logging.DiscordWebhook") as discord:
            handler.to_discord("bla bla bla")
            assert discord.assert_not_called


def test_to_discord():
    handler = DiscordHandler()

    with patch("stampy_chat.logging.DISCORD_LOGGING_URL", "http://example.org"):
        with patch("stampy_chat.logging.DiscordWebhook") as discord:
            handler.to_discord("bla bla bla")
            discord.assert_called_once_with(
                url="http://example.org", content="```\nbla bla bla\n```"
            )


def test_to_discord_splits_large():
    handler = DiscordHandler()

    with patch("stampy_chat.logging.DISCORD_LOGGING_URL", "http://example.org"):
        with patch("stampy_chat.logging.MAX_MESSAGE_LEN", 30):
            with patch("stampy_chat.logging.DiscordWebhook") as discord:
                handler.to_discord("""
                Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut
                labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris
                """)
                assert discord.call_args_list == [
                    call(
                        url="http://example.org",
                        content="```\n\n                Lorem ipsum d\n```",
                    ),
                    call(
                        url="http://example.org",
                        content="```\nolor sit amet, consectetur adi\n```",
                    ),
                    call(
                        url="http://example.org",
                        content="```\npiscing elit, sed do eiusmod t\n```",
                    ),
                    call(
                        url="http://example.org",
                        content="```\nempor incididunt ut\n          \n```",
                    ),
                    call(
                        url="http://example.org",
                        content="```\n      labore et dolore magna a\n```",
                    ),
                    call(
                        url="http://example.org",
                        content="```\nliqua. Ut enim ad minim veniam\n```",
                    ),
                    call(
                        url="http://example.org",
                        content="```\n, quis nostrud exercitation ul\n```",
                    ),
                    call(
                        url="http://example.org",
                        content="```\nlamco laboris\n                \n```",
                    ),
                ]


def test_ChatLogger_is_debug():
    logger = ChatLogger("tester")
    logger.setLevel(DEBUG)
    assert logger.is_debug()


@pytest.mark.parametrize("level", (WARN, ERROR, INFO))
def test_ChatLogger_is_debug_false(level):
    logger = ChatLogger("tester")
    logger.setLevel(level)
    assert not logger.is_debug()


def test_ChatLogger_interaction():
    history = [
        HumanMessage(content="Die monster. You don’t belong in this world!"),
        AIMessage(
            content="It was not by my hand[1] I am once again given flesh. I was called here by humans who wished to pay me tribute."
        ),
        HumanMessage(
            content="Tribute!?! You steal men's souls and make them your slaves!"
        ),
        AIMessage(content="Perhaps the same could be said[321] of all religions..."),
        HumanMessage(
            content="Your words are as empty as your soul! Mankind ill needs a savior such as you!"
        ),
        AIMessage(
            content="What is a man? A[4234] miserable little pile of secrets. But enough talk... Have at you!"
        ),
    ]
    blocks = [
        {
            "id": str(i),
            "url": f"http://bla.bla/{i}",
            "tags": [],
            "title": f"Block{i}",
            "authors": [f"Author{i}"],
            "date": f"2021-01-0{i + 1}",
            "text": f"Block text {i}",
        }
        for i in range(5)
    ]
    response = "This is the response from the LLM to the user's query"
    prompt = (
        "System: This is where the system prompt would go\n"
        "User: Q: Die monster. You don’t belong in this world!\n"
        "Assistant: It was not by my hand[x] I am once again given flesh. I was called\n"
        "User: Q: Tribute!?! You steal men's souls and make them your slaves!\n"
        "Assistant: Perhaps the same could be said[x] of all religions...\n"
        "User: Q: Your words are as empty as your soul! Mankind ill needs a savior such as you!\n",
        "Assistant: What is a man? A[x] miserable little pile of secrets\n"
        "User: In your answer, please cite any claims you make back to each "
        "source using the format: [a], [b], etc. If you use multiple "
        'sources to make a claim cite all of them. For example: "AGI is '
        'concerning [c, d, e]."\n'
        "\n"
        "Q: to be or not to be?",
    )

    logger = ChatLogger("tester")
    with patch.object(logger, "item_adder") as adder:
        logger.interaction(
            "session id", "what is this?", response, history, prompt, blocks
        )
        interaction = adder.add.call_args_list[0][0][0]
        assert interaction.session_id == "session id"
        assert interaction.interaction_no == 3
        assert interaction.query == "what is this?"
        assert (
            interaction.response
            == "This is the response from the LLM to the user's query"
        )
        assert interaction.prompt == prompt
        assert interaction.chunks == ",".join(b.get("id") for b in blocks)
