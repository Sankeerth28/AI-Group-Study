# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_run_sync_simulated_fib():
    payload = {
        "topic": "recursion",
        "difficulty": "easy",
        "question_text": "Write a recursive function fib(n) and explain the naive time complexity."
    }

    response = client.post("/run_sync", json=payload)
    assert response.status_code == 200

    data = response.json()
    transcript = data["transcript"]

    # Ensure 5 turns: Question, Peer, Learner, Teacher, Summary
    assert len(transcript) == 5

    peer = transcript[1]["content"].lower()
    teacher = transcript[3]["content"].lower()
    summary = transcript[4]["content"].lower()

    # Check Peer has a complexity mistake
    assert "o(n^2)" in peer or "inefficient" in peer

    # Teacher should mention correction
    assert "o(2^n)" in teacher or "memoization" in teacher

    # Summary should highlight correction
    assert "correction" in summary or "next steps" in summary
