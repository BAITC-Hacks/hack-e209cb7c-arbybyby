# AURA — Automated Urban Response Analytics
## Pulse 109 | GovTech Camp 2026 | Team arbybyby

Интеллектуальная платформа обработки обращений граждан в call-центры 109.

### Архитектура
- **Frontend**: React + TypeScript + Tailwind CSS + Recharts
- **Backend**: FastAPI (Python)
- **ML Pipeline (в разработке)**: Fine-tuned классификатор (QLoRA) + Fine-tuned эмбеддинги для поиска похожих
- **Database (планируется)**: PostgreSQL + pgvector

### Три модуля
1. **Смарт-классификация** — автоматическая классификация по 10+ категориям (каз/рус). Сейчас: rule-based placeholder. Далее: fine-tuned модель.
2. **Ассистент оператора** — поиск похожих обращений, дубликаты, шаблон ответа. Сейчас: keyword matching. Далее: fine-tuned эмбеддинги.
3. **Ситуационный центр** — дашборд по регионам, детектор всплесков, прогноз нагрузки.

### Запуск
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Frontend поднимется на http://localhost:5173 и обращается к backend на http://localhost:8000.
Swagger-документация API: http://localhost:8000/docs

### Запуск через Docker
```bash
docker-compose up --build
```

### API (основные эндпоинты)
| Метод | Путь | Описание |
|-------|------|----------|
| GET  | `/api/tickets` | список обращений (фильтры `region`, `status`) |
| GET  | `/api/tickets/{id}` | одно обращение |
| POST | `/api/tickets/{id}/classify` | классификация обращения |
| POST | `/api/tickets/{id}/approve` | подтвердить и закрыть обращение |
| GET  | `/api/tickets/{id}/similar` | 3 похожих обращения |
| GET  | `/api/analytics/summary` | сводные метрики |
| GET  | `/api/analytics/regions` | статистика по регионам |
| GET  | `/api/analytics/spikes` | текущие всплески |
| GET  | `/api/analytics/timeline` | нагрузка за 7 дней по категориям |

### Статус
- [x] Архитектура и API-контракты
- [x] UI рабочего места оператора
- [x] UI ситуационного центра
- [x] Rule-based классификатор (placeholder)
- [ ] Fine-tuning классификатора (ждём GPU ресурсы)
- [ ] Fine-tuning эмбеддинг-модели (ждём GPU ресурсы)
- [ ] PostgreSQL + pgvector
- [ ] Прогноз нагрузки
- [ ] NL-запросы к данным

### О placeholder-моделях
Текущий MVP использует детерминированные заглушки, размеченные `# TODO` в коде,
готовые к прямой замене на дообученные модели:
- `backend/services/classifier.py` → fine-tuned классификатор (QLoRA on Llama/BERT)
- `backend/services/embeddings.py` → fine-tuned эмбеддинги + pgvector cosine similarity
- `backend/services/anomaly.py` → статистический детектор аномалий (Z-score / IQR)
