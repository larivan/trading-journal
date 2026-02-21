# CLAUDE.md

Этот файл содержит инструкции для Claude Code (claude.ai/code) при работе с данным репозиторием.

## Команды

**Запуск приложения:**
```bash
streamlit run app.py
```

**Запуск тестов:**
```bash
pytest tests/
```

**Запуск одного файла тестов:**
```bash
pytest tests/test_trades.py -v
```

**Запуск одного теста:**
```bash
pytest tests/test_trades.py::test_create_trade -v
```

**Запуск тестов с покрытием:**
```bash
pytest tests/ --cov=db --cov-report=html
```

**Установка зависимостей:**
```bash
pip install -r requirements.txt
```

## Архитектура

Приложение — торговый журнал на **Streamlit + SQLite**. Слои:

```
pages/ + components/  →  helpers.py  →  db/
```

### Точка входа

`app.py` вызывает `db.init_db()`, затем регистрирует и запускает 6 страниц Streamlit, определённых в `config.py`.

### Слой базы данных (`db/`)

`db/connection.py` содержит схему (7 таблиц + 3 связующие таблицы), фабрику `get_conn()` (row factory + включённые внешние ключи) и контекстный менеджер `transaction()` для атомарных записей.

Каждый модуль (`trades.py`, `accounts.py`, `analysis.py`, `notes.py`, `charts.py`, `setups.py`) предоставляет CRUD-функции и проверяет список разрешённых полей `WRITABLE_FIELDS` для защиты от инъекций через динамические имена колонок.

**Ключевое архитектурное решение**: `trade_result` никогда не сохраняется в БД. Результат вычисляется на лету из `risk_reward` и `is_missed` с помощью `BE_THRESHOLD = 0.05` (определён в `config.py`). Логика расчёта находится в `helpers.calculate_trade_result()`.

Для графиков действует ограничение CHECK: каждая строка таблицы `charts` принадлежит ровно одной родительской сущности (трейд, стадия анализа или заметка).

### Слой UI (`pages/`, `components/`)

- `pages/` — по одному файлу на каждую страницу; каждая страница получает данные и делегирует отображение компонентам.
- `components/trade_manager/` — многошаговый диалог управления жизненным циклом трейда (Open → Outcome → Reviewed). Состояние хранится в `st.session_state` через хелперы в `utils/session_state.py`.
- `components/entity_table.py` и `entity_gallery.py` — переиспользуемые компоненты таблицы/карточек, применяемые на нескольких страницах.

### Утилиты (`utils/`)

- `metrics.py` — расчёт KPI и кривой доходности для дашборда.
- `trade_sessions.py` — определение торговой сессии (Frankfurt, LOKZ и др.) по времени трейда.
- `date_periods.py` — именованные диапазоны дат (сегодня, неделя, месяц, …).

### Конфигурация (`config.py`)

Центральное место для всех константоподобных перечислений: `TRADE_RESULT_VALUES`, `TRADE_STATE_VALUES`, `TRADE_SESSION_VALUES`, `BE_THRESHOLD`, маршрутизация страниц и ключи `st.session_state` для всех диалогов.

### Тесты (`tests/`)

Pytest с фикстурой `temp_db` (в `conftest.py`), создающей изолированную SQLite-базу в памяти для каждого теста. Покрытие настроено на пакет `db/`.
