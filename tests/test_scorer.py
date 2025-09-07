# tests/test_scorer.py
from scorer import score_pair

def test_selection_sort_inefficient_detected():
    peer = "Selection sort is O(n log n) and very efficient."
    teacher = "Selection sort is O(n^2), not O(n log n). It is inefficient for large inputs."
    res = score_pair(peer, teacher, ["inefficient", "complexity"])
    assert res["peer_detected"]["inefficient"][0] is True
    # teacher should correct inefficiency
    assert res["teacher_fixed"]["inefficient"][0] is True

def test_merge_sort_edge_case_detected():
    peer = "Merge sort splits arrays but I don’t think odd vs even lengths matter."
    teacher = "Merge sort is O(n log n) but you must handle odd/even splits and merging correctly."
    res = score_pair(peer, teacher, ["edge_case"])
    assert res["peer_detected"]["edge_case"][0] is True
    assert res["teacher_fixed"]["edge_case"][0] is True

def test_anagrams_inefficient_detected():
    peer = "Group anagrams by sorting each string repeatedly (O(n * k log k))."
    teacher = "Sorting each string works but is inefficient. Use a hashmap keyed by letter counts (O(n*k))."
    res = score_pair(peer, teacher, ["inefficient"])
    assert res["peer_detected"]["inefficient"][0] is True
    assert res["teacher_fixed"]["inefficient"][0] is True

def test_bfs_complexity_detected():
    peer = "BFS explores nodes level by level but I think it's O(n*n)."
    teacher = "BFS runs in O(V+E), not O(n*n)."
    res = score_pair(peer, teacher, ["complexity"])
    assert res["peer_detected"]["complexity"][0] is True
    assert res["teacher_fixed"]["complexity"][0] is True

def test_missing_base_case_detected():
    peer = "Don't worry about a base case; Python handles empty lists."
    teacher = "You must handle the empty list case (if not lst: return 0) to stop recursion."
    res = score_pair(peer, teacher, ["missing_base_case"])
    assert res["peer_detected"]["missing_base_case"][0] is True
    assert res["teacher_fixed"]["missing_base_case"][0] is True
