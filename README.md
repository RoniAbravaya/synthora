# Synthora

<p align="center">
  <img src="frontend/public/logo.svg" alt="Synthora Logo" width="300" />
</p>

<p align="center">
  <strong>AI-Powered Video Generator Platform</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#tech-stack">Tech Stack</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#deployment">Deployment</a> •
  <a href="#documentation">Documentation</a>
</p>

---

Synthora is a SaaS web application that enables users to generate viral videos using multiple AI integrations, post them to social media platforms, and analyze performance with AI-powered suggestions for improvement.

## ✨ Features

- **🎬 AI Video Generation** - Create videos using OpenAI, ElevenLabs, Pexels, and various video AI services
- **📱 Multi-Platform Posting** - Post to YouTube, TikTok, Instagram, and Facebook
- **📅 Smart Scheduling** - Schedule posts for optimal engagement times (Premium)
- **📊 Analytics Dashboard** - Track performance across all platforms
- **🤖 AI Suggestions** - Get AI-powered recommendations to improve your content (Premium)
- **📝 Template System** - Use and create customizable video templates

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+ / FastAPI |
| **Frontend** | React 18 / TypeScript / Vite |
| **UI** | shadcn/ui / Tailwind CSS |
| **Database** | PostgreSQL |
| **Queue** | RQ (Redis Queue) / Upstash Redis |
| **Storage** | Google Cloud Storage |
| **Auth** | Firebase Authentication |
| **Payments** | Stripe |
| **Deployment** | Railway |

## 📁 Project Structure

```
synthora/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/               # API routes (v1 endpoints)
│   │   ├── core/              # Config, security, auth
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── integrations/      # External API integrations
│   │   └── workers/           # Background job definitions
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Backend tests
│   └── requirements.txt
│
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── components/        # UI components
│   │   ├── pages/             # Page components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── services/          # API client services
│   │   ├── contexts/          # React contexts
│   │   └── types/             # TypeScript types
│   └── package.json
│
├── ai-planning/               # Planning documents
│   ├── ai-overview.md         # Project overview
│   └── todo-synthora.md       # Implementation checklist
│
├── docs/                      # Documentation
│   ├── SETUP_GUIDE.md         # External services setup
│   └── DEPLOYMENT.md          # Railway deployment guide
│
└── .github/workflows/         # CI/CD pipelines
```

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (or use SQLite for development)
- Redis (or Upstash account)

### Quick Start (Local Development)

1. **Clone the repository**
   ```bash
   git clone https://github.com/RoniAbravaya/synthora.git
   cd synthora
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # Run migrations (requires DATABASE_URL)
   alembic upgrade head
   
   # Start server
   uvicorn app.main:app --reload
   ```

4. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Worker Setup** (optional, for background jobs)
   ```bash
   cd backend
   rq worker --url $REDIS_URL
   ```

### Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🔐 User Roles

| Role | Features |
|------|----------|
| **Free** | 1 video/day, immediate posting only, basic analytics |
| **Premium** ($5/mo or $50/yr) | Unlimited videos, scheduling, AI suggestions, full analytics |
| **Admin** | All features + user management + system settings |

## 🔌 Supported Integrations

### AI Services
| Category | Providers |
|----------|-----------|
| **Script Generation** | OpenAI (GPT-4) |
| **Voice Generation** | ElevenLabs |
| **Stock Media** | Pexels, Unsplash |
| **Video AI** | Google Veo 3, OpenAI Sora, Runway Gen-4, Luma Dream Machine, and more |
| **Video Assembly** | FFmpeg, Creatomate, Shotstack |

### Social Platforms
- YouTube
- TikTok
- Instagram
- Facebook

## 🧪 Testing

```bash
# Backend tests
cd backend
python -m pytest tests/unit -v

# Frontend tests
cd frontend
npm run test:run

# With coverage
npm run test:coverage
```

### Test Results

| Category | Tests | Status |
|----------|-------|--------|
| Backend Unit Tests | 70 | ✅ Passing |
| Frontend Tests | 44 | ✅ Passing |

## 🚂 Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed Railway deployment instructions.

### Quick Deploy to Railway

1. Fork this repository
2. Create a new project on [Railway](https://railway.app)
3. Add PostgreSQL database
4. Deploy backend, frontend, and worker services
5. Configure environment variables
6. Set up Stripe webhook

## 📖 Documentation

- [Project Overview](ai-planning/ai-overview.md) - Architecture and design decisions
- [Implementation Checklist](ai-planning/todo-synthora.md) - Development progress
- [Setup Guide](docs/SETUP_GUIDE.md) - External services configuration
- [Deployment Guide](docs/DEPLOYMENT.md) - Railway deployment instructions
- [API Documentation](http://localhost:8000/docs) - OpenAPI/Swagger (when running locally)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - UI library
- [shadcn/ui](https://ui.shadcn.com/) - Beautiful UI components
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
- [Railway](https://railway.app/) - Deployment platform

---

<p align="center">
  <strong>Built with ❤️ by the Synthora Team</strong>
</p>
