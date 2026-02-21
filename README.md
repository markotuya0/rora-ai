# 🤖 Rora AI - Text-to-SQL Intelligence

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)
[![CI](https://github.com/markotuya0/rora-ai/workflows/CI/badge.svg)](https://github.com/markotuya0/rora-ai/actions)

A production-ready, full-stack AI application that transforms natural language questions into SQL queries. Built with FastAPI, LangChain, Ollama, and Streamlit for a seamless developer experience.

<div align="center">
  <img src="images/unnamed.png" alt="Rora AI Demo" width="800"/>
  <p><em>Transform natural language into SQL queries with AI</em></p>
</div>

## ✨ Features

- 🚀 **REST API** - FastAPI backend with auto-generated OpenAPI documentation
- 💬 **Natural Language Processing** - Ask questions in plain English
- 🏠 **Local LLM** - Uses Ollama (Qwen 2.5) - zero API costs, complete privacy
- 📊 **Interactive UI** - Beautiful Streamlit interface with real-time results
- 📜 **Query History** - Track and review all past queries
- 🔒 **Security First** - SQL injection prevention, query validation
- 🐳 **Docker Ready** - One-command deployment with Docker Compose
- ⚡ **Performance Monitoring** - Built-in benchmarking and health checks
- 🧪 **Comprehensive Testing** - Unit tests, API tests, and performance tests
- 📈 **Production Ready** - Logging, error handling, CORS, health checks

## 🛠️ Tech Stack

| Category | Technology |
|----------|-----------|
| **Backend** | FastAPI, Uvicorn |
| **Frontend** | Streamlit |
| **AI/ML** | LangChain, Ollama (Qwen 2.5) |
| **Database** | SQLite (easily upgradable to PostgreSQL) |
| **Validation** | Pydantic |
| **Containerization** | Docker, Docker Compose |
| **Testing** | Pytest, unittest |
| **Language** | Python 3.11+ |

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- [Ollama](https://ollama.ai) installed
- Docker (optional, for containerized deployment)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/markotuya0/rora-ai.git
cd rora-ai

# Start all services
docker-compose up --build
```

Access the application:
- 🌐 **API**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs
- 🎨 **UI**: http://localhost:8501

### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/markotuya0/rora-ai.git
cd rora-ai

# Run automated setup
chmod +x setup.sh
./setup.sh

# Or manual setup
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Install and pull Ollama model
ollama pull qwen2.5:0.5b

# Initialize database
python create_db.py

# Start API server (Terminal 1)
python api.py

# Start Streamlit UI (Terminal 2)
streamlit run app_v2.py
```

### Using Makefile

```bash
make setup      # Full setup
make api        # Start API server
make ui         # Start Streamlit UI
make test       # Run all tests
make docker     # Start with Docker
```

## 💡 Example Queries

Try these natural language questions:

```
"Who scored the highest in Math?"
"Show all students with grade A"
"What is the average score in Science?"
"List students who scored below 70"
"How many students got an A in History?"
```

## 📁 Project Structure

```
rora-ai/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI/CD
├── images/
│   └── unnamed.png             # Project screenshots
├── api.py                      # FastAPI REST API server
├── app_v2.py                   # Streamlit web interface
├── config.py                   # Configuration management
├── utils.py                    # Utility functions
├── create_db.py                # Database initialization
├── benchmark.py                # Performance testing
├── test_api.py                 # API integration tests
├── test_utils.py               # Unit tests
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Multi-service orchestration
├── .dockerignore               # Docker ignore rules
├── .env.example                # Environment variables template
├── Makefile                    # Development commands
├── setup.sh                    # Automated setup script
├── README.md                   # Main documentation
├── ARCHITECTURE.md             # System architecture docs
├── DEPLOYMENT.md               # Deployment guide
├── INTERVIEW_GUIDE.md          # Interview preparation
├── CONTRIBUTING.md             # Contribution guidelines
└── LICENSE                     # MIT License
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root endpoint with API info |
| `POST` | `/query` | Execute natural language query |
| `GET` | `/history` | Retrieve query history |
| `GET` | `/schema` | Get database schema |
| `GET` | `/health` | Health check endpoint |
| `GET` | `/docs` | Interactive API documentation |

### Example API Usage

```bash
# Health check
curl http://localhost:8000/health

# Execute query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Who scored the highest in Math?"}'

# Get query history
curl http://localhost:8000/history?limit=10
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test suites
python -m pytest test_utils.py -v
python -m pytest test_api.py -v

# Run performance benchmarks
python benchmark.py
```

## 🔒 Security Features

- ✅ **Query Validation** - Only SELECT statements allowed
- ✅ **SQL Injection Prevention** - Parameterized queries and input validation
- ✅ **Local Processing** - No data sent to external APIs
- ✅ **CORS Configuration** - Controlled cross-origin access
- ✅ **Input Validation** - Pydantic models for type safety
- ✅ **Error Handling** - Secure error messages without internal exposure

## 📊 Architecture

The application follows a clean, microservices-inspired architecture:

```
┌─────────────┐      HTTP/REST      ┌──────────────┐
│  Streamlit  │ ◄─────────────────► │   FastAPI    │
│     UI      │                      │   Backend    │
└─────────────┘                      └───────┬──────┘
                                             │
                                    ┌────────┴────────┐
                                    │                 │
                              ┌─────▼─────┐    ┌─────▼─────┐
                              │ LangChain │    │  SQLite   │
                              │  + Ollama │    │  Database │
                              └───────────┘    └───────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

## 🚀 Deployment

### Docker Deployment

```bash
docker-compose up -d
```

### Cloud Deployment Options

- **AWS**: ECS/Fargate + RDS
- **GCP**: Cloud Run + Cloud SQL
- **Azure**: Container Apps + Azure SQL
- **Heroku**: Container deployment
- **Railway**: One-click deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## 🛣️ Roadmap

- [x] FastAPI REST API
- [x] Streamlit UI
- [x] Query history
- [x] Docker support
- [x] Comprehensive testing
- [x] CI/CD pipeline
- [ ] Redis caching layer
- [ ] PostgreSQL support
- [ ] User authentication (JWT)
- [ ] Rate limiting
- [ ] Data visualization charts
- [ ] Multi-database support
- [ ] Query result export (CSV, JSON)
- [ ] Advanced analytics dashboard

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Marko Tuya**

- GitHub: [@markotuya0](https://github.com/markotuya0)
- Project: [rora-ai](https://github.com/markotuya0/rora-ai)

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [LangChain](https://langchain.com/) - LLM orchestration
- [Ollama](https://ollama.ai/) - Local LLM inference
- [Streamlit](https://streamlit.io/) - Interactive UI framework

## 📚 Additional Resources

- [Architecture Documentation](ARCHITECTURE.md)
- [Interview Preparation Guide](INTERVIEW_GUIDE.md)
- [API Documentation](http://localhost:8000/docs) (when running)

---

⭐ If you find this project useful, please consider giving it a star!
