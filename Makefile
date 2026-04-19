# ─── Clarium RegTech Compliance Module - Makefile ─────────────────────────────
.PHONY: help up down down-v logs ps test build

help:
	@echo ""
	@echo "  Clarium - RegTech Compliance Module"
	@echo "  ─────────────────────────────────────────────────────"
	@echo "  make up        Start the full stack (API + DB + Redis + Frontend)"
	@echo "  make down      Stop containers"
	@echo "  make down-v    Stop + wipe all volumes"
	@echo "  make logs      Tail all logs"
	@echo "  make logs-api  Tail API logs only"
	@echo "  make test      Run full pytest suite"
	@echo "  make ps        Show container status"
	@echo ""
	@echo "  Endpoints after 'make up':"
	@echo "    API docs:   http://localhost:8000/docs"
	@echo "    Dashboard:  http://localhost:3000"
	@echo ""

up:
	@cp -n .env.example .env 2>/dev/null || true
	docker compose up -d --build
	@echo ""
	@echo "✅ Clarium is starting..."
	@echo "   API:       http://localhost:8000/docs"
	@echo "   Dashboard: http://localhost:3000"

down:
	docker compose down

down-v:
	docker compose down -v

logs:
	docker compose logs -f

logs-%:
	docker compose logs -f $*

ps:
	docker compose ps

test:
	@echo "→ Running Clarium test suite..."
	cd backend && pip install -q -r requirements.txt aiosqlite && \
	pytest tests/ -v --tb=short
	@echo "✅ Tests complete."

build-%:
	docker compose up -d --build $*
