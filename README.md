# Integrations Hub - HubSpot, Notion & Airtable

This project implements integrations for **HubSpot**, **Notion**, and **Airtable**, fulfilling the requirements of a technical assessment. It demonstrates secure OAuth2 flows, credential management, and standardized metadata extraction using a unified schema.

---

## 📦 Features

- 🔐 OAuth2 authentication for HubSpot and Airtable  
- 🧠 Notion integration using API keys  
- ⚡ Asynchronous, performant HTTP communication  
- 📄 Unified metadata format across all platforms  
- 🖥️ React frontend to test and visualize integrations

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **FastAPI** – Web API framework
- **httpx** – Async HTTP client
- **Redis** – For managing OAuth states
- **Dataclasses / Pydantic** – Data modeling
- **Uvicorn** – ASGI web server
- **React** frontend to test and visualize integrations

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Muawia24/integrations-hub.git
cd integrations-hub
```
---

### 🔧 2. Backend Setup (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

Start the backend:
uvicorn main:app --reload
```

---

### 🔧 3. Frontend Setup (React)

```bash
cd frontend
npm i
npm run start  # or `npm run dev` if using Vite
```

> The frontend allows you to test integration flows:  
> Authenticate, store credentials, and trigger data loading.

---

## ✍️ Author

**Ahmed Muawia**  
[GitHub](https://github.com/Muawia24) • [LinkedIn](https://linkedin.com/in/ahmed-muawia)

---

## 📝 License

MIT
