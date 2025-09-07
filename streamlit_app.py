"""
Streamlit UI for AI Study Group demo (improved, robust click handling).

Usage:
    pip install streamlit requests
    streamlit run streamlit_app.py

Notes:
 - Default backend: http://127.0.0.1:8000
 - Change backend URL in sidebar if deploying backend elsewhere.
"""

import streamlit as st
import requests
import time
from typing import Optional

st.set_page_config(page_title="AI Study Group — Streamlit Demo", layout="wide")
st.title("AI Study Group — Streamlit Demo")

# ---- Config / API base ----
DEFAULT_API = "http://127.0.0.1:8000"

def get_api_base() -> str:
    # Prefer secrets (if present) then sidebar input
    try:
        if hasattr(st, "secrets") and st.secrets:
            api = st.secrets.get("api_base")
            if api:
                return api.rstrip("/")
    except Exception:
        pass
    # sidebar text input (editable)
    val = st.sidebar.text_input("API Base URL", value=DEFAULT_API)
    return (val or DEFAULT_API).rstrip("/")

API_BASE = get_api_base()

st.sidebar.markdown("**Backend settings**")
st.sidebar.write(API_BASE)
st.sidebar.markdown("---")
st.sidebar.write("If backend runs locally: `uvicorn api.app:app --reload --port 8000`")
st.sidebar.markdown("If you deploy, set API base here or via Streamlit secrets.")

# ---- UI inputs ----
with st.sidebar:
    st.markdown("### Session Options")
    TOPICS = ["recursion", "sorting", "graphs", "hashmaps", "linked-lists", "programming"]
    topic = st.selectbox("Topic", TOPICS, index=0)
    difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=0)
    question_text = st.text_area("Question (optional)", value="Write a recursive function fib(n) and explain the naive time complexity.")
    simulate = st.checkbox("Simulate (deterministic demo)", value=True)
    st.markdown("---")
    st.markdown("Press **Start session** to create a new demo session.")

# ---- session_state defaults ----
if "sid" not in st.session_state:
    st.session_state["sid"] = None
if "last_response" not in st.session_state:
    st.session_state["last_response"] = None
if "log" not in st.session_state:
    st.session_state["log"] = []
if "start_attempted" not in st.session_state:
    st.session_state["start_attempted"] = False

# ---- layout ----
controls_col, transcript_col, debug_col = st.columns([1, 2, 1])

with controls_col:
    st.markdown("### Controls")
    # To avoid double-run issues, we use st.button but also set flags in session_state.
    start_click = st.button("▶ Start session")
    step_click = st.button("→ Step (advance)")
    fetch_click = st.button("⟳ Refresh transcript")
    raw_click = st.button("🔎 Show raw JSON")
    clear_click = st.button("✖ Clear session")

    st.markdown("### Tips")
    st.markdown(
        "- If Start returns an id but transcript is missing, press **Refresh transcript** or **Step**.\n"
        "- If your backend is remote change API Base in the sidebar or use Streamlit secrets."
    )

with transcript_col:
    st.markdown("### Session & Transcript")
    status_area = st.empty()
    transcript_area = st.empty()

with debug_col:
    st.markdown("### Debug / Logs")
    log_area = st.empty()

# ---- logging helper ----
def append_log(msg: str):
    t = f"{time.strftime('%H:%M:%S')} - {msg}"
    st.session_state["log"].append(t)
    # show last 100 lines
    log_area.text("\n".join(st.session_state["log"][-200:]))

# ---- API helpers ----
REQUEST_TIMEOUT = 5.0

def api_post(path: str, json_payload: dict, timeout: float = REQUEST_TIMEOUT):
    url = f"{API_BASE}{path}"
    append_log(f"POST {url} payload={json_payload}")
    return requests.post(url, json=json_payload, timeout=timeout)

def api_get(path: str, timeout: float = REQUEST_TIMEOUT):
    url = f"{API_BASE}{path}"
    append_log(f"GET {url}")
    return requests.get(url, timeout=timeout)

def start_session_api(topic: str, difficulty: str, question_text: Optional[str], simulate: bool):
    payload = {"topic": topic, "difficulty": difficulty, "question_text": question_text, "simulate": simulate}
    try:
        r = api_post("/start_session", payload)
        r.raise_for_status()
    except Exception as e:
        append_log(f"Start session failed: {e}")
        status_area.error(f"Start failed: {e}")
        return None

    try:
        data = r.json()
    except Exception:
        append_log("Start session: cannot parse JSON from response")
        data = None

    # extract session id
    sid = None
    if isinstance(data, dict):
        sid = data.get("session_id") or data.get("id") or data.get("session_id")
    if not sid and data and isinstance(data, str):
        # sometimes server returns plain string
        sid = data

    if not sid:
        append_log(f"Start response missing session_id. Response: {r.text[:400]}")
        status_area.warning("Started but response did not include session_id. Check backend.")
        st.session_state["last_response"] = r.text
        return None

    st.session_state["sid"] = sid
    st.session_state["start_attempted"] = True
    append_log(f"Started session {sid}")
    status_area.success(f"Started session: {sid}")

    # Try to fetch transcript immediately (may not be available in some server flows)
    for i in range(3):
        try:
            tr = fetch_transcript_api(sid)
            if tr:
                return tr
        except Exception:
            pass
        time.sleep(0.4)
    status_area.info("Session started — transcript not yet available. Press 'Refresh transcript' or 'Step'.")
    return {"session_id": sid}

def fetch_transcript_api(sid: str):
    if not sid:
        status_area.warning("No session id available.")
        return None
    try:
        r = api_get(f"/session/{sid}")
        if r.status_code == 404:
            append_log("Fetch transcript: 404 Not Found")
            status_area.warning("Transcript not found (404). Maybe session id expired or server expects 'step' first.")
            return None
        r.raise_for_status()
        session_obj = r.json()
        st.session_state["last_response"] = session_obj
        transcript_area.json(session_obj)
        append_log(f"Fetched transcript for {sid}")
        status_area.success(f"Fetched transcript for {sid}")
        return session_obj
    except Exception as e:
        append_log(f"Fetch transcript failed: {e}")
        status_area.error(f"Fetch failed: {e}")
        return None

def step_session_api(sid: str):
    if not sid:
        status_area.warning("Start a session first.")
        return None
    # try POST first, fallback to GET if 404 or method not supported
    post_url = f"{API_BASE}/session/{sid}/step"
    try:
        append_log(f"POST {post_url}")
        r = requests.post(post_url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 404:
            append_log("POST /step returned 404; trying GET /step")
            r = requests.get(post_url, timeout=REQUEST_TIMEOUT)
        # if server returns 405 Method Not Allowed, try GET as well
        if r.status_code == 405:
            append_log("POST /step returned 405; trying GET /step")
            r = requests.get(post_url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        append_log(f"Step succeeded status={r.status_code}")
        # after step, refresh transcript
        time.sleep(0.15)
        fetch_transcript_api(sid)
        return r.json() if r.text else {}
    except Exception as e:
        append_log(f"Step failed: {e}")
        status_area.error(f"Step failed: {e}")
        return None

# ---- button handling ----
# To avoid repeated triggers due to reruns, set flags on session_state
if start_click:
    # clear old logs for new session start
    st.session_state["log"] = []
    append_log("Start button clicked")
    start_session_api(topic=topic, difficulty=difficulty, question_text=question_text, simulate=simulate)

if fetch_click:
    append_log("Refresh button clicked")
    sid = st.session_state.get("sid")
    if not sid:
        status_area.warning("No session id — press Start session first.")
    else:
        fetch_transcript_api(sid)

if step_click:
    append_log("Step button clicked")
    sid = st.session_state.get("sid")
    if not sid:
        status_area.warning("No session id — press Start session first.")
    else:
        step_session_api(sid)

if raw_click:
    append_log("Raw JSON requested")
    sid = st.session_state.get("sid")
    if not sid:
        status_area.warning("No session id — press Start session first.")
    else:
        try:
            r = api_get(f"/session/{sid}")
            r.raise_for_status()
            st.code(r.text, language="json")
        except Exception as e:
            append_log(f"Raw fetch failed: {e}")
            status_area.error(f"Raw fetch failed: {e}")

if clear_click:
    append_log("Clear session clicked")
    st.session_state["sid"] = None
    st.session_state["last_response"] = None
    status_area.info("Session cleared")
    transcript_area.empty()

# ---- initial / background transcript display (non-blocking) ----
if st.session_state.get("sid") and not (start_click or fetch_click or step_click or raw_click):
    # try quick fetch to show recent transcript (may fail quietly)
    sid = st.session_state["sid"]
    try:
        r = api_get(f"/session/{sid}", timeout=1.2)
        if r.status_code == 200:
            transcript_area.json(r.json())
            status_area.info(f"Session: {sid}")
        else:
            status_area.info(f"Session started (id: {sid}). Use Refresh/Step.")
    except Exception:
        pass

# show logs at bottom
append_log("UI ready")
