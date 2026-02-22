# Trading Workspace

Персональный торговый воркспейс на **Streamlit + SQLite**.
Ведёт учёт сделок, дневных анализов и наблюдений — с дашбордом и поддержкой графиков.

---

## Возможности

- **Трейды** — открытие, закрытие (Outcome) и разбор (Reviewed) сделок с привязкой к счёту, сетапу и дневному анализу
- **Анализ** — дневной журнал в 4 этапа: Pre-market → Plan → Execution → Post-market; на каждом этапе можно прикреплять графики
- **Наблюдения** — независимые заметки с возможностью привязки к трейдам и этапам анализа
- **Дашборд** — ключевые метрики (Win Rate, avg R:R, Profit Factor), кривая доходности, разбивка по сессиям и сетапам
- **Счета** — управление торговыми счетами с начальным балансом для автоматического расчёта R:R и Reward %
- **Сетапы** — справочник торговых сетапов для классификации сделок

---

## Стек

| Слой | Технология |
|------|------------|
| UI | Streamlit |
| База данных | SQLite (стандартный `sqlite3`) |
| Тесты | pytest |
| Графики | Plotly |
| Данные | pandas |

---

## Установка

```bash
git clone <repo-url>
cd trade_journal

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Запуск

```bash
streamlit run app.py
```

Приложение откроется по адресу `http://localhost:8501`.
База данных `trade_journal.db` создаётся автоматически при первом запуске в директории проекта.

---

## Тесты

```bash
# Все тесты
pytest tests/

# Один файл
pytest tests/test_trades.py -v

# Один тест
pytest tests/test_trades.py::test_create_trade -v

# С отчётом о покрытии
pytest tests/ --cov=db --cov-report=html
```

Тесты используют изолированную SQLite-базу в памяти (фикстура `temp_db` в `conftest.py`) — каждый тест получает чистое окружение.

---

## Архитектура

```
app.py
  └─ pages/           ← по одной странице на раздел (trades, analysis, notes, dashboard, …)
       └─ components/ ← trade_manager, analysis_manager, note_manager, entity_table, …
            └─ helpers.py + utils/  ← вспомогательные функции и утилиты
                 └─ db/             ← CRUD-слой (trades, accounts, analysis, notes, charts, setups)
```

### Ключевые архитектурные решения

**`trade_result` не хранится в БД.**
Результат сделки (Win / Loss / BE) вычисляется на лету из `risk_reward` и `is_missed`:

| Условие | Результат |
|---------|-----------|
| `risk_reward > 0.05` и `is_missed = 0` | **Win** |
| `risk_reward < -0.05` | **Loss** |
| иначе | **BE** (безубыток) |

Порог `BE_THRESHOLD = 0.05` задан в `config.py`. Логика расчёта находится в `helpers.calculate_trade_result()`.

**Защита от SQL-инъекций через имена колонок.**
Каждый CRUD-модуль объявляет `WRITABLE_FIELDS` — множество допустимых имён колонок. Динамически строимые `UPDATE`-запросы проверяют ключи только против этого множества.

**Атомарные транзакции.**
Составные операции (создание трейда + прикрепление чартов + заметок) оборачиваются в контекстный менеджер `db.transaction()`, который делает `COMMIT` при успехе и `ROLLBACK` при любом исключении.

**Check constraint для чартов.**
Каждая строка таблицы `charts` принадлежит ровно одной сущности — трейду, этапу анализа или заметке. Это обеспечено `CHECK`-ограничением в схеме БД.

### Структура БД

```
accounts        ← торговые счета
trades          ← сделки (FK → accounts, setups, analysis)
analysis        ← дневные анализы
analysis_stages ← этапы анализа (pre-market / plan / execution / post-market)
notes           ← наблюдения
setups          ← торговые сетапы
charts          ← скриншоты и чарты (принадлежат ровно одной из 3 сущностей)

trade_notes     ← M2M: trades ↔ notes
analysis_notes  ← M2M: analysis_stages ↔ notes
```

---

## Конфигурация

Все константы задаются в `config.py`:

| Константа | Описание |
|-----------|----------|
| `BE_THRESHOLD` | Порог безубытка для расчёта результата (`0.05`) |
| `ASSETS_VALUES` | Список торгуемых инструментов |
| `DAILY_BIAS_VALUES` | Варианты дневного байеса |
| `LOCAL_TZ` | Локальный часовой пояс для определения торговой сессии |
| `TRADE_RESULT_VALUES` | `Win` / `Loss` / `BE` |
| `TRADE_STATE_VALUES` | `Open` / `Outcome` / `Reviewed` |
| `ANALYSIS_STATE_VALUES` | `pre-market` / `plan` / `execution` / `post-market` |
| `TRADE_SESSION_VALUES` | Frankfurt / LOKZ / London / New York / … |
