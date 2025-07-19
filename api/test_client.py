#!/usr/bin/env python3
"""
Test script for the Stampy API client.
"""

from stampy_client import stampy


def test_single_message():
    """Test with a single message."""
    print("=== Testing single message ===")
    result = stampy(
        messages=["What is AI alignment?"],
        mode="concise"
    )
    print("Reply:", result["reply"])
    print()


def test_conversation():
    """Test with a conversation history."""
    print("=== Testing conversation history ===")
    result = stampy(
        messages=[
            "What is AI alignment?",
            "AI alignment is the challenge of ensuring that artificial intelligence systems act in accordance with human values and intentions.",
            "How does this relate to x-risk?"
        ],
        mode="default"
    )
    print("Reply:", result["reply"])
    print()


def test_custom_system():
    """Test with custom system prompt."""
    print("=== Testing custom system prompt ===")
    result = stampy(
        messages=["What is superintelligence?"],
        system="You are an expert AI safety researcher. Explain concepts clearly and concisely.",
        mode="rookie"
    )
    print("Reply:", result["reply"])
    print()


def test_streaming():
    """Test streaming response."""
    print("=== Testing streaming response ===")
    result = stampy(
        messages=["What is the control problem?"],
        stream=True
    )
    print("Streaming reply:", result["reply"])
    print("Full context length:", len(result.get("full_context", "")))
    print("Citations:", len(result.get("citations", [])))
    print("Followups:", len(result.get("followups", [])))
    print()


if __name__ == "__main__":
    test_single_message()
    test_conversation()
    test_custom_system()
    test_streaming()