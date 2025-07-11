#!/usr/bin/env python3
"""
Simple API client for testing the Stampy chat server.
"""

import json
import uuid
import requests
import csv
import subprocess
import hashlib
from typing import List, Dict, Any, Optional
from collections import defaultdict
from frozendict import frozendict

from stampy_chat import settings


def parse_model_and_settings(model_and_settings: str) -> frozendict:
    """Parse model_and_settings string into a frozendict structure."""
    parts = model_and_settings.lower().split('|')
    result = {}
    
    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            result[key] = value
        else:
            # Handle parts without '=' - assume they're model or context names
            if part.startswith(('claude', 'gpt', 'gemini', 'deepseek', 'gemma', 'llama', 'mistral', 'o1', 'o3', 'o4', 'qwen')):
                result['model'] = part
            else:
                result['database'] = part
    
    return frozendict(result)


def get_git_hash() -> str:
    """Get current git commit hash, raising if git is dirty."""
    try:
        # Check if git is dirty
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=True
        )
        if status_result.stdout.strip():
            raise RuntimeError("Git repository is dirty - please commit changes first")
        
        # Get current commit hash
        hash_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return hash_result.stdout.strip()[:10]
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git command failed: {e}")


def load_prompts(require_clean_git: bool = True) -> Dict[str, str]:
    """Load all prompts with their names and git hash."""
    if require_clean_git:
        git_hash = get_git_hash()
    prompts = {}
    
    # Load from settings
    for prompt_name, prompt_content in settings.DEFAULT_PROMPTS.items():
        if isinstance(prompt_content, str):
            prompt_hash = hashlib.sha256(prompt_content.encode()).hexdigest()[:8]
            key = f"{prompt_name}-{prompt_hash}"
            prompts[key] = prompt_content
    
    # Also load individual prompts
    for name, content in [
        ('SOURCE_PROMPT', settings.SOURCE_PROMPT),
        ('HISTORY_PROMPT', settings.HISTORY_PROMPT),
        ('HISTORY_SUMMARIZE_PROMPT', settings.HISTORY_SUMMARIZE_PROMPT),
        ('QUESTION_PROMPT', settings.QUESTION_PROMPT),
    ]:
        prompt_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
        key = f"{name}-{prompt_hash}"
        prompts[key] = content
    
    return prompts


def load_csv(file_path: str) -> Dict[str, Dict[str, str]]:
    """Load CSV file into question-major dict representation."""
    result = {}
    
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            question = row.get('', '')  # First column should be empty header for questions
            if not question:
                continue
                
            question_responses = {}
            for model_settings, response in row.items():
                if model_settings and model_settings != '':  # Skip empty column header
                    if response:  # Only add non-empty responses
                        question_responses[model_settings] = response
            
            if question_responses:
                result[question] = question_responses
    
    return result


def save_csv(data: Dict[str, Dict[str, str]], file_path: str) -> None:
    """Save question-major dict to CSV format."""
    if not data:
        return
    
    # Collect all unique model_and_settings across all questions
    all_model_settings = set()
    for question_responses in data.values():
        all_model_settings.update(question_responses.keys())
    
    all_model_settings = sorted(all_model_settings)
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        # Write header
        writer = csv.writer(f)
        writer.writerow([''] + all_model_settings)
        
        # Write data rows
        for question, responses in data.items():
            row = [question]
            for model_settings in all_model_settings:
                row.append(responses.get(model_settings, ''))
            writer.writerow(row)


def stampy(
    *,
    messages: List[str],
    system: str = settings.SOURCE_PROMPT,
    history_prompt: str = settings.HISTORY_PROMPT,
    pre_question: str = settings.QUESTION_PROMPT,
    question_marker: str = settings.QUESTION_MARKER,
    modes: Optional[dict] = None,
    session_id: Optional[str] = None,
    url: str = "http://127.0.0.1:3001/chat",
    mode: str = "default",
    completions: str = "claude-sonnet-4-20250514",
    stream: bool = False,
    **kwargs
) -> Dict[str, Any]:
    if len(messages) % 2 == 0:
        raise ValueError("Messages list must have odd length (ending with user message)")

    our_modes = dict(settings.PROMPT_MODES)
    if modes:
        our_modes = dict(our_modes, **modes)
    
    # Convert alternating messages to history format
    history = []
    for i, content in enumerate(messages[:-1]):  # All but the last message
        role = "user" if i % 2 == 0 else "assistant"
        history.append({"role": role, "content": content})
    
    # Last message is the current query
    query = messages[-1]
    
    # Build settings
    settings = {
        "prompts": {
            "context": system,
            "history": history,
            "history_summary": history,
            "question": pre_question,
            "question_marker": question_marker,
            "modes": our_modes
        },
        "mode": mode,
        "completions": completions,
        "encoder": "cl100k_base",
        "topKBlocks": 50,
        "maxNumTokens": 8000,
        "tokensBuffer": 50,
        "maxHistory": 10,
        "maxHistorySummaryTokens": 200,
        "historyFraction": 0.25,
        "contextFraction": 0.5,
        **kwargs
    }
    
    # Build request payload
    payload = {
        "sessionId": session_id or str(uuid.uuid4()),
        "query": query,
        "history": history,
        "settings": settings,
        "stream": stream
    }
    
    # Make request
    response = requests.post(
        url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json"
        }
    )
    
    response.raise_for_status()
    
    if stream:
        # Parse streaming response
        return _parse_streaming_response(response.text)
    else:
        # Return non-streaming response
        # TODO: this doesn't work, right? because main.py always returns stream? maybe we should delete this block, unless I misread main.py
        return {"reply": response.json(), "full_context": ""}


def _parse_streaming_response(response_text: str) -> Dict[str, Any]:
    """Parse the streaming response format."""
    lines = response_text.strip().split('\n')
    
    citations = []
    prompt = ""
    content_parts = []
    followups = []
    
    for line in lines:
        if line.startswith('data: '):
            data_str = line[6:]  # Remove 'data: ' prefix
            if data_str.strip():
                try:
                    data = json.loads(data_str)
                    if data.get("state") == "citations":
                        citations = data.get("citations", [])
                    elif data.get("state") == "prompt":
                        prompt = data.get("prompt", "")
                    elif data.get("state") == "streaming":
                        content = data.get("content", "")
                        if content:
                            content_parts.append(content)
                    elif data.get("state") == "followups":
                        followups = data.get("followups", [])
                except json.JSONDecodeError:
                    continue
    
    reply = "".join(content_parts)
    
    return {
        "reply": reply,
        "full_context": prompt,
        "citations": citations,
        "followups": followups
    }


def test_csv_functions():
    """Test CSV load/save functionality."""
    import tempfile
    import os
    
    # Test data
    test_data = {
        'What is AI alignment?': {
            'claude-sonnet-4|database=stampy-full': 'AI alignment is the field...',
            'gpt-4|database=stampy-miri': 'AI alignment refers to...'
        },
        'What are x-risks?': {
            'claude-sonnet-4|database=stampy-full': 'X-risks are existential risks...',
            'gemini-pro|database=miri_the_question': 'Existential risks...'
        }
    }
    
    # Test save and load
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        csv_path = f.name
    
    try:
        save_csv(test_data, csv_path)
        loaded_data = load_csv(csv_path)
        
        print('CSV test results:')
        print(f'  Original questions: {len(test_data)}')
        print(f'  Loaded questions: {len(loaded_data)}')
        print(f'  Data matches: {test_data == loaded_data}')
        
        # Test parse_model_and_settings
        test_settings = 'claude-sonnet-4|database=stampy-full|system=SOURCE_PROMPT-abc123'
        parsed = parse_model_and_settings(test_settings)
        print(f'  Parsed settings: {parsed}')
        
        # Test prompts loading
        prompts = load_prompts(require_clean_git=False)
        print(f'  Loaded prompts: {len(prompts)}')
        
        return True
        
    except Exception as e:
        print(f'Test failed: {e}')
        return False
    finally:
        if os.path.exists(csv_path):
            os.unlink(csv_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_csv_functions()
    else:
        # Test the client
        result = stampy(
            messages=["What does the term 'x-risk' mean?"],
            mode="default"
        )
        print("Reply:", result["reply"])
        print("Citations:", len(result.get("citations", [])))
