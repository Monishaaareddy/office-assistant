# Office Assistant — Agentic Enterprise Employee Assistant

An AI-powered employee assistant for **NOVATRIX TECHNOLOGIES PVT. LTD.** that answers company policy questions and employee-specific queries using a combination of **RAG-based document retrieval** and **structured data tools**.

The assistant can retrieve information from company policy documents, query employee records, maintain conversation context, and provide responses through a simple **Streamlit chat interface**.

## Key Features

* 📚 **Policy Q&A** using RAG with FAISS
* 🧑‍💼 **Employee-specific information** using structured data tools
* 💬 **Multi-turn conversations** with short-term context
* 🧠 **Long-term memory** for explicitly saved information
* 🗂️ **Persistent chat history** using SQLite
* 🏢 **Streamlit web interface**
* 🤖 **Gemini-powered responses**


## Architecture

```text
User
  ↓
Streamlit UI
  ↓
OfficeAssistant
  ↓
Intent / Tool Routing
  ├── Policy Query ──────→ FAISS + Gemini Embeddings ──→ Policy Documents
  ├── Employee Query ────→ Structured Data Tools ──────→ CSV Data
  └── General Query ─────→ Gemini
  ↓
Context + Memory
  ↓
Final Response
```

The assistant combines **RAG retrieval**, **structured employee tools**, **conversation memory**, and **Gemini** to generate responses based on the appropriate source of information.


## Tech Stack

* **Python** — Application development
* **Google Gemini** — LLM and embeddings
* **FAISS** — Vector similarity search
* **Pandas** — Structured CSV data handling
* **SQLite** — Conversation history
* **Streamlit** — User interface
* **PyPDF** — PDF document loading


## Project Structure

```text
office-assistant/
├── agent/              # Agent logic, routing and memory
├── rag/                # PDF loading, chunking, embeddings and retrieval
├── tools/              # Employee and structured-data tools
├── ui/                 # Streamlit interface
├── data/
│   ├── database/       # Employee and operational CSV data
│   ├── rag_policies/   # Company policy PDFs
│   └── vector_store/   # FAISS index and chunk metadata
├── memory/             # Conversation history
├── requirements.txt
└── README.md
```


## Setup & Run

### 1. Clone the repository

```bash
git clone https://github.com/charviha/office-assistant.git
cd office-assistant
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Gemini API key

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

### 5. Run the application

```bash
streamlit run ui/app.py
```

The application will open in the browser as a Streamlit chat interface.


## Example Queries

The assistant supports both policy-based and employee-specific queries.

| Query                                         | Source             |
| --------------------------------------------- | ------------------ |
| What is the work from home policy?            | Policy RAG         |
| How many leaves does EMP004 have?             | Leave Balance Tool |
| Who is the manager of EMP001?                 | Employee Tool      |
| What is the travel policy for hotel bookings? | Policy RAG         |
| What IT assets does EMP004 have?              | IT Asset Tool      |
| What is the information for EMP001?           | Employee Tool      |

The assistant determines the appropriate source and generates the final response using the retrieved information.


## Team Contributions

| Member   | Responsibility                  |
| -------- | ------------------------------- |
| Person 1 | Knowledge Base & Policy RAG     |
| Person 2 | Structured Data & Tools         |
| Person 3 | Agent & Orchestration           |
| Person 4 | UI, Integration & Documentation |

The project was developed collaboratively, with each member responsible for their respective module and integration into the final assistant.


## Future Improvements

* Add authentication and role-based access
* Support confirmation workflows for employee actions
* Improve multi-intent query handling
* Expand structured tools and enterprise integrations
