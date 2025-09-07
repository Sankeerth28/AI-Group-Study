// web/static/app.js
document.addEventListener("DOMContentLoaded", () => {
  const startBtn = document.getElementById("start-btn");
  const output = document.getElementById("output");
  const topicInput = document.getElementById("topic");
  const diffInput = document.getElementById("difficulty");

  function renderTranscript(transcript) {
    if (!transcript || !Array.isArray(transcript)) return "No transcript returned.";
    // Build nice readable text
    const lines = transcript.map(t => {
      const time = t.timestamp ? ` [${t.timestamp}]` : "";
      return `${t.turn_id}. ${t.agent} (${t.role})${time}:\n${t.content}\n`;
    });
    return lines.join("\n");
  }

  async function startSession(payload) {
    const res = await fetch("/start_session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`Server returned ${res.status}: ${txt}`);
    }
    return res.json();
  }

  // Optional: fetch the next step or session status (example usage)
  async function fetchSessionStep(sessionId) {
    const res = await fetch(`/session/${encodeURIComponent(sessionId)}/step`);
    if (!res.ok) {
      // not fatal — return null
      return null;
    }
    return res.json();
  }

  startBtn.addEventListener("click", async () => {
    const topic = topicInput.value || "recursion";
    const difficulty = diffInput.value || "easy";

    output.textContent = "Starting session...";

    try {
      const payload = {
        topic,
        difficulty,
        question_text: "Auto-generated question",
        simulate: true
      };

      const json = await startSession(payload);

      // The server may return top-level session_id and/or transcript[0].session_id
      // Prefer the session_id embedded inside the transcript items if present,
      // otherwise fallback to top-level session_id.
      let sessionId = json.session_id || null;
      if (json.transcript && json.transcript.length > 0 && json.transcript[0].session_id) {
        sessionId = json.transcript[0].session_id;
      }

      // Render transcript (if present)
      if (json.transcript) {
        output.textContent = renderTranscript(json.transcript);
      } else {
        output.textContent = JSON.stringify(json, null, 2);
      }

      // Example: if you want to poll an extra step endpoint (often returns the next item),
      // uncomment the lines below to fetch session step and append to the output.
      /*
      if (sessionId) {
        const step = await fetchSessionStep(sessionId);
        if (step && step.transcript) {
          output.textContent += "\n\nFetched /step result:\n" + renderTranscript(step.transcript);
        }
      }
      */

    } catch (err) {
      output.textContent = "Error: " + err.message;
      console.error(err);
    }
  });
});
