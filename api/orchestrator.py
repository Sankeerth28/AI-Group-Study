# orchestrator.py
"""
Orchestrator:
 - simulate=True => deterministic, test-friendly responses (keeps your unit tests stable)
 - simulate=False => uses OpenAI API (OpenAI v1+ python client)
"""
import os
import uuid
from datetime import datetime, timezone, timedelta
import traceback

from prompts import render_prompt

# Try to import the official OpenAI client (v1+)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# --- LLM client wrapper for real-LM mode ---
class LLMClient:
    """
    Thin wrapper around openai.OpenAI for chat completions.
    If OpenAI cannot be imported or no api_key set, _client will be None.
    """
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None
        if OpenAI is not None and self.api_key:
            try:
                self._client = OpenAI(api_key=self.api_key)
            except Exception as e:
                # failed to initialize client
                print("Failed to initialize OpenAI client:", e)
                self._client = None
        else:
            # either library missing or no api key
            if OpenAI is None:
                print("OpenAI library not found. Running in simulate mode or install openai>=1.0.0.")
            else:
                print("OPENAI_API_KEY not found. Running in simulate mode.")

    def available(self) -> bool:
        return self._client is not None

    def generate(self, prompt: str, temperature: float = 0.2, max_tokens: int = 512) -> str:
        """
        Use the chat completions endpoint to generate a reply. Returns the text or an error message.
        """
        if not self._client:
            return "Error: OpenAI client not available. Set OPENAI_API_KEY and install openai>=1.0.0."

        try:
            # Using chat completions style that matches OpenAI v1+ client
            messages = [{"role": "user", "content": prompt}]
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            # defensive extraction
            if getattr(resp, "choices", None):
                choice = resp.choices[0]
                if getattr(choice, "message", None):
                    return choice.message.get("content", "")
                # older responses shape fallback
                return choice.get("text", "")
            # fallback
            return str(resp)
        except Exception as e:
            # Include traceback for easier debugging in logs (but keep transcript short)
            tb = traceback.format_exc()
            print("OpenAI API error:", tb)
            return f"Error generating response from LLM: {e}"


# --- Helpers for deterministic simulate mode ---
def ts_now_iso():
    IST = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(IST).isoformat()


def _extract_mistake_hint(peer_prompt):
    if not peer_prompt:
        return None
    txt = peer_prompt.lower()
    if "wrong time complexity" in txt or "complexity" in txt:
        return "complexity"
    if "off-by-one" in txt or "off by one" in txt:
        return "off_by_one"
    if "base case" in txt or "missing base" in txt:
        return "missing_base_case"
    if "edge case" in txt:
        return "edge_case"
    if "inefficient" in txt:
        return "inefficient"
    return None


def _peer_reply_for(question_text, mistake_key):
    q = (question_text or "").lower()
    mk = (mistake_key or "").lower()

    if "fib(" in q or "fibonacci" in q or "fib" in q:
        if mk == "complexity":
            return "A straightforward recursive solution: fib(n) = fib(n-1) + fib(n-2). This runs in O(n^2) time because subcalls repeat work."
        return "Use naive recursion fib(n)=fib(n-1)+fib(n-2); it's simple though may be inefficient."

    if "sum_nested" in q or "sum nested" in q or "nested list" in q:
        if mk == "missing_base_case":
            return "Recursively sum elements. Don't worry about a base case; Python handles empty lists."
        return "Recursion over nested lists: flatten logically and add values."

    if "selection_sort" in q or "selection sort" in q:
        if mk == "inefficient":
            return "Selection sort is great. It repeatedly finds the min and swaps. It's O(n log n) and very efficient."
        return "Use selection sort by finding min and swapping—simple and uses O(1) extra space."

    # generic fallback
    if mk == "complexity":
        return "I think this runs in O(n^2) due to repeated work."
    if mk == "inefficient":
        return "This is fine but maybe inefficient for large inputs."
    if mk == "edge_case":
        return "I don't think odd/even length handling matters here."

    return "I would attempt a straightforward solution; one detail may be slightly off."


def _teacher_reply_for(question_text, peer_text, learner_input):
    q = (question_text or "").lower()
    if "fib" in q or "fibonacci" in q:
        return "The peer's approach is correct, but the complexity analysis is a common mistake. Naive recursive Fibonacci is exponential (O(2^n)). Use memoization to optimize it to O(n)."
    if "sum_nested" in q or "nested list" in q:
        return "The peer's idea to recurse is good, but omitting the base case is a critical error. Handle empty lists as a base case: e.g., `if not lst: return 0`."
    if "selection_sort" in q or "selection sort" in q:
        return "Selection sort involves nested loops, making it O(n^2), not O(n log n). It's simple but inefficient for large datasets."
    # generic fallback
    return "That's a good start from the peer. Let's refine the logic and double-check the complexity."


def _summary_for(question_text, peer_text, teacher_text):
    q = (question_text or "").strip()
    # summarise with defensive splits
    peer_summary = (peer_text or "").split(".")[0]
    teacher_points = (teacher_text or "").split(".")[0]
    return (f"- **Question**: {q}\n"
            f"- **Peer's Idea**: {peer_summary}.\n"
            f"- **Key Correction**: {teacher_points}.\n"
            f"- **Next Steps**: Implement the corrected algorithm and add tests for edge cases.")


# --- Orchestrator flow ---
def run_session(topic="strings", difficulty="easy", simulate=True, learner_response=None,
                question_text=None, peer_prompt_override=None):
    """
    Runs a single study session.
    - simulate=True -> deterministic canned replies
    - simulate=False -> uses LLMClient (requires OPENAI_API_KEY)
    Returns a transcript list (each item: dict)
    """
    client = None
    if not simulate:
        # initialize LLM client only when not simulating
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        client = LLMClient(model=model)

    session_id = str(uuid.uuid4())
    transcript = []
    context = {"session_id": session_id, "topic": topic, "difficulty": difficulty}

    # 1. Question
    q_text = question_text or f"Generated question about {topic} at {difficulty} level."
    transcript.append({"session_id": session_id, "turn_id": 1, "agent": "QuestionAgent",
                       "role": "question", "content": q_text, "timestamp": ts_now_iso()})

    # 2. Peer
    if simulate:
        mistake_key = "complexity"
        if peer_prompt_override:
            mistake_key = _extract_mistake_hint(peer_prompt_override) or "complexity"
        peer_text = _peer_reply_for(q_text, mistake_key)
    else:
        # render a prompt template or basic instruction
        peer_prompt = peer_prompt_override or render_prompt("peer_agent", {**context, "question": q_text})
        if client and client.available():
            peer_text = client.generate(peer_prompt, temperature=0.7)
        else:
            peer_text = "Error: LLM client not available for peer agent. Falling back to simulation."
            # fall back deterministic reply (don't fail)
            peer_text = _peer_reply_for(q_text, _extract_mistake_hint(peer_prompt_override))

    transcript.append({"session_id": session_id, "turn_id": 2, "agent": "PeerAgent",
                       "role": "peer_attempt", "content": peer_text, "timestamp": ts_now_iso()})

    # 3. Learner (simulated)
    learner_response = learner_response or "I think that's right, but I'm not sure about the details."
    transcript.append({"session_id": session_id, "turn_id": 3, "agent": "Learner",
                       "role": "learner_input", "content": learner_response, "timestamp": ts_now_iso()})

    # 4. Teacher
    if simulate:
        teacher_text = _teacher_reply_for(q_text, peer_text, learner_response)
    else:
        teacher_prompt = render_prompt("teacher_agent", {**context, "question": q_text,
                                                        "peer_answer": peer_text, "learner_input": learner_response})
        if client and client.available():
            teacher_text = client.generate(teacher_prompt, temperature=0.2)
        else:
            teacher_text = _teacher_reply_for(q_text, peer_text, learner_response)
    transcript.append({"session_id": session_id, "turn_id": 4, "agent": "TeacherAgent",
                       "role": "teacher_reply", "content": teacher_text, "timestamp": ts_now_iso()})

    # 5. Summary
    if simulate:
        summary_text = _summary_for(q_text, peer_text, teacher_text)
    else:
        summary_prompt = render_prompt("summary_agent", {**context, "question": q_text,
                                                        "peer_answer": peer_text, "teacher_reply": teacher_text})
        if client and client.available():
            summary_text = client.generate(summary_prompt, temperature=0.1)
        else:
            summary_text = _summary_for(q_text, peer_text, teacher_text)

    transcript.append({"session_id": session_id, "turn_id": 5, "agent": "SummaryAgent",
                       "role": "summary", "content": summary_text, "timestamp": ts_now_iso()})

    # debug print
    print("\n--- SESSION TRANSCRIPT ---")
    for item in transcript:
        print(f"[{item['agent']}] {item['content']}\n")

    return transcript


if __name__ == "__main__":
    # quick demo in simulate mode
    run_session(topic="recursion", difficulty="easy", simulate=True,
                question_text="Write a recursive function fib(n) and explain the naive time complexity.")
