# 📚 AI Group Study

AI Group Study is an interactive platform simulating a study group with roles:
- **QuestionAgent** — asks questions  
- **PeerAgent** — naive/incorrect attempt  
- **Learner** — reacts with uncertainty  
- **TeacherAgent** — explains/corrects  
- **SummaryAgent** — summarizes  

Helps practice programming through realistic discussions.

---

## 🚀 Features

- FastAPI backend (`api/`) with REST endpoints  
- Streamlit frontend (`streamlit_app.py`)  
- Fuzzy scoring (lemmatization + spaCy)  
- Simulated or real mode (OpenAI API)  
- Unit tests with pytest  

---

## 📂 Project Structure

```
Ai-Group-Study/
├── api/ (FastAPI backend)
├── streamlit_app.py
├── web/ (optional static UI)
├── tests/
├── requirements.txt
└── README.md
```

---

## 🛠️ Installation

```bash
git clone https://github.com/<your-username>/ai-group-study.git
cd ai-group-study
python -m venv venv
source venv/bin/activate    # macOS/Linux
.\venv\Scripts\activate     # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # optional
```

## ▶️ Usage

### Run backend:

```bash
uvicorn api.app:app --reload --host 127.0.0.1 --port 8000
```

**Docs:** http://127.0.0.1:8000/docs

### Run frontend:

```bash
streamlit run streamlit_app.py
```

**Visit:** http://localhost:8501

### Example API:

```bash
curl -X POST "http://127.0.0.1:8000/start_session" \
  -H "Content-Type: application/json" \
  -d '{"topic":"recursion","difficulty":"easy","question_text":"Write fib","simulate":true}'
```

## 🧪 Tests

```bash
pytest -q
```

## 🔑 Real LLM Mode

### Set API key:

```bash
export OPENAI_API_KEY=sk-xxxx      # macOS/Linux
setx OPENAI_API_KEY "sk-xxxx"      # Windows
```

Use `"simulate": false`.

## 🌍 Deployment

* **Backend:** FastAPI (Uvicorn) → Render, Railway, AWS, etc.
* **Frontend:** Streamlit Cloud, Docker/VM

## 📖 Tips

* Use transcript returned from `/start_session` if refresh gives 404
* Extend `orchestrator.py` for new flows
* `docker compose up` for containerized setup

## 🤝 Contributing

PRs welcome. Open issues for major changes.

## 📜 License

MIT License