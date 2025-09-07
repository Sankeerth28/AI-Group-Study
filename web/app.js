const runBtn = document.getElementById("runBtn");
const topicEl = document.getElementById("topic");
const difficultyEl = document.getElementById("difficulty");
const questionEl = document.getElementById("question_text");
const statusEl = document.getElementById("status");
const transcriptEl = document.getElementById("transcript");

function setStatus(s){
  statusEl.textContent = s;
}

function renderTranscript(transcript){
  transcriptEl.innerHTML = "";
  transcript.forEach(item=>{
    const card = document.createElement("div");
    card.className = "card";
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `[${item.agent}] • ${item.role} • ${new Date(item.timestamp || Date.now()).toLocaleString()}`;
    const pre = document.createElement("pre");
    pre.textContent = item.content || "";
    card.appendChild(meta);
    card.appendChild(pre);
    transcriptEl.appendChild(card);
  });
}

async function runSession(){
  setStatus("running...");
  transcriptEl.innerHTML = "";
  const payload = {
    topic: topicEl.value,
    difficulty: difficultyEl.value,
    question_text: questionEl.value
  };
  document.addEventListener("DOMContentLoaded", () => {
  const startBtn = document.getElementById("startBtn");
  const sessionDiv = document.getElementById("sessionId");

  startBtn.addEventListener("click", async () => {
    startBtn.disabled = true;
    startBtn.textContent = "Starting...";
    try {
      const payload = {
        topic: "recursion",
        difficulty: "easy",
        question_text: "Write fib",
        simulate: true
      };
      const resp = await fetch("/start_session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      sessionDiv.textContent = `Started: ${data.session_id}`;
    } catch (err) {
      console.error(err);
      sessionDiv.textContent = `Error: ${err.message}`;
    } finally {
      startBtn.disabled = false;
      startBtn.textContent = "Start Session";
    }
  });
});

  try{
    const resp = await fetch("/run_sync", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload),
    });
    if(!resp.ok){
      const err = await resp.json().catch(()=>({detail: "Unknown error"}));
      setStatus("error");
      transcriptEl.innerHTML = `<div class="card"><pre>Error: ${JSON.stringify(err)}</pre></div>`;
      return;
    }
    const body = await resp.json();
    // in your backend run_session returns transcript array - show it
    const transcript = body.transcript || body;
    renderTranscript(transcript);
    setStatus("done");
  }catch(e){
    setStatus("error");
    transcriptEl.innerHTML = `<div class="card"><pre>Network error: ${e.message}</pre></div>`;
  }
}

runBtn.addEventListener("click", runSession);
