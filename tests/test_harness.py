# tests/test_harness.py
import pytest
from harness_lib import run_all

def test_harness_all_pass_simulated():
    results = run_all(simulate=True)
    # print debug info on failure
    failed = [r for r in results if not r["pass"]]
    if failed:
        for f in failed:
            print("\nFAILED SEED:", f["topic"], f["difficulty"])
            print("Q:", f["question"])
            print("Peer:", f["peer_answer"])
            print("Teacher:", f["teacher_reply"])
            print("Peer detected:", f["peer_detected"])
            print("Teacher fixed:", f["teacher_fixed"])
    assert not failed, f"{len(failed)} seeds failed. See printed debug above."
