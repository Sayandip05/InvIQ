# 🏥 InvIQ - AI-Powered Smart Inventory Assistant

**AI-powered inventory management for healthcare facilities with natural language queries and intelligent automation**

---

## 🎯 Problem It Solves

Healthcare facilities struggle with manual inventory tracking, leading to critical stockouts, expired medications, and inefficient procurement. Staff waste hours on spreadsheets without real-time visibility or predictive insights. **InvIQ automates inventory management with AI-powered analytics, natural language queries, and intelligent shortage predictions.**

---

## 🚀 Live Demo

**Frontend:** [Coming Soon]  
**Backend API:** [Coming Soon]  
**API Docs:** [Coming Soon]/docs

---

## 📸 Demo

![InvIQ Dashboard](https://via.placeholder.com/800x400/4F46E5/FFFFFF?text=InvIQ+Dashboard+Screenshot)

*Replace with actual screenshot*

---

## 🛠️ Tech Stack

### Backend
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Upstash-DC382D?logo=redis&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-LangGraph-1C3C3C?logo=chainlink&logoColor=white)

### Frontend
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind-3-06B6D4?logo=tailwindcss&logoColor=white)

### AI & Infrastructure
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-FF6B00?logo=ai&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-FF6F00?logo=database&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

---

## ✨ Key Features

- 🤖 **AI Chatbot** - Ask questions in plain English: *"What items are critical right now?"*
- 📊 **Real-Time Analytics** - Dashboard with heatmaps, alerts, and stock health monitoring
- 🔄 **Requisition Workflow** - Digital approval system for stock requests
- 📤 **Vendor Integration** - Excel upload with fuzzy item matching (85% accuracy)
- 🔐 **Multi-Tenancy & RBAC** - 6 roles (Super Admin, Admin, Manager, Staff, Vendor, Viewer)
- ⚡ **Real-Time Alerts** - WebSocket notifications for critical stock levels

---

## 🚀 Quick Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (or Neon account)
- Redis (or Upstash account)

### Backend Setup

```bash
# Clone repository
git clone https://github.com/Sayandip05/InvIQ.git
cd InvIQ

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env with your database, Redis, and API keys

# Initialize database
python -c "from app.infrastructure.database.connection import init_db; init_db()"

# Run development server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with backend API URL

# Run development server
npm run dev
```

### Docker Setup (Recommended)

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your credentials

# Start all services
docker-compose up -d

# Access application
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  React SPA (6 Role-Based Portals + Landing Page)                │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/REST + WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                           │
│  FastAPI (56 endpoints) + Rate Limiting + JWT Auth              │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Business   │  │  AI Agent    │  │  Analytics   │
│   Logic      │  │  Service     │  │  Service     │
│              │  │              │  │              │
│ Inventory    │  │ LangGraph    │  │ Dashboard    │
│ Requisition  │  │ 7 Tools      │  │ Heatmap      │
│ Vendor       │  │ ChromaDB RAG │  │ Alerts       │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │ Upstash Redis│  │  ChromaDB    │         │
│  │  (Neon)      │  │  (REST API)  │  │  (Vector DB) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📚 Documentation

For detailed documentation, see the `/docs` folder:

- **[High-Level Design (HLD)](docs/HLD.md)** - System overview, architecture, tech stack decisions
- **[Low-Level Design (LLD)](docs/LLD.md)** - Database schema, API specs, component details
- **[Deployment Guide](docs/deployment.md)** - Production deployment instructions
- **[System Architecture](docs/system-architecture.md)** - Detailed architecture diagrams
- **[Scaling & Cost](docs/scaling-and-cost.md)** - Scalability strategies and cost analysis

---

## 🧪 Testing

```bash
# Run all tests
cd backend
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_inventory_service.py -v
```

**Test Coverage:** 80% (18 test files, 200+ tests)

---

## 📦 Project Structure

```
InvIQ/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes
│   │   ├── application/      # Business logic services
│   │   ├── core/             # Config, security, middleware
│   │   ├── domain/           # Business domain logic
│   │   └── infrastructure/   # Database, cache, vector store
│   ├── tests/                # Test suite
│   └── requirements-dev.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Portal pages
│   │   ├── context/          # Auth & WebSocket context
│   │   └── utils/            # Helper functions
│   └── package.json
├── database/
│   ├── schema.sql            # Database schema
│   └── seed_data.py          # Sample data
├── docs/                     # Documentation
├── docker-compose.yml
└── README.md
```

---

## 🔐 Security Features

- **JWT Authentication** - Access (30min) + Refresh (7 days) tokens
- **Argon2 Password Hashing** - GPU-resistant algorithm
- **Rate Limiting** - 5-60 req/min based on endpoint sensitivity
- **Token Blacklist** - Logout invalidation with Redis
- **Login Lockout** - 5 attempts → 15 min lockout
- **Role-Based Access Control** - 6-tier role hierarchy
- **Audit Logging** - All write operations tracked
- **Multi-Tenancy** - Organization-level data isolation

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Sayandip Bar**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin&logoColor=white)](http://www.linkedin.com/in/sayandipbar2005)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-181717?logo=github&logoColor=white)](https://github.com/Sayandip05)
[![Email](https://img.shields.io/badge/Email-Contact-EA4335?logo=gmail&logoColor=white)](mailto:sayandip@inviq.io)

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **LangChain/LangGraph** - AI agent orchestration
- **Groq** - Fast LLM inference
- **Neon** - Managed PostgreSQL
- **Upstash** - Serverless Redis
- **ChromaDB** - Vector database for RAG

---

## 📊 Project Stats

![GitHub Stars](https://img.shields.io/github/stars/Sayandip05/InvIQ?style=social)
![GitHub Forks](https://img.shields.io/github/forks/Sayandip05/InvIQ?style=social)
![GitHub Issues](https://img.shields.io/github/issues/Sayandip05/InvIQ)
![GitHub License](https://img.shields.io/github/license/Sayandip05/InvIQ)

---

<div align="center">
  <p>Made with ❤️ for healthcare professionals</p>
  <p>⭐ Star this repo if you find it helpful!</p>
</div>
