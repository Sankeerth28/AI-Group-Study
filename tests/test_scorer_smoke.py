from scorer import score_pair

def test_complexity_detect():
    p = "This is O(n^2) because of nested loops."
    t = "This is quadratic; use O(n) DP."
    r = score_pair(p, t, ["inefficient"])
    assert r["peer_detected"]["inefficient"][0]

def test_missing_base_case():
    p = "Recursively add values; I won't check empty list."
    t = "Add a base case: if not lst: return 0"
    r = score_pair(p, t, ["missing_base_case"])
    assert r["peer_detected"]["missing_base_case"][0]
    assert r["teacher_fixed"]["missing_base_case"][0]
