# ClickHouse AI Agent с Claude

AI-агент на Python, который принимает запросы пользователя на естественном языке, генерирует SQL-запросы для ClickHouse и выполняет их только после подтверждения пользователя.

## Возможности

- 🤖 Понимает запросы на естественном языке (на русском и английском)
- 🔍 Автоматически исследует схему базы данных ClickHouse
- 📝 Генерирует SQL-запросы без автоматического выполнения
- ✅ Выполняет запросы только после явного подтверждения пользователя
- 🛠️ Использует ClickHouse MCP Server для безопасной работы с БД
- 💬 Интерактивный режим работы

## Архитектура

Агент использует:
- **Claude Agent SDK** - для создания AI-агента
- **ClickHouse MCP Server** - для безопасного доступа к ClickHouse
- **Claude Sonnet 4.6** - языковая модель для понимания запросов и генерации SQL

## Требования

- Python 3.10 или выше
- `uv` - менеджер пакетов Python (для запуска MCP сервера)
- Доступ к ClickHouse базе данных
- Anthropic API key

## Установка

### 1. Установите Python зависимости

```bash
pip install -r requirements.txt
```

### 2. Установите uv (если ещё не установлен)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Или на Windows:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Настройте конфигурацию

Файл `config.yaml` уже содержит все необходимые параметры:

```yaml
clickhouse:
  host: rc1b-vsrkuug8qh3pkkeg.mdb.yandexcloud.net
  port: 9440
  user: User_main
  password: click_security_house_7659
  database: ym_sanok
  secure: true

ai:
  provider: anthropic
  api_key: sk-ant-api03-...
  model: claude-sonnet-4-6
  temperature: 0.0
  max_tokens: 1000
```

**Важно:** Для продакшен использования рекомендуется хранить чувствительные данные (пароли, API ключи) в переменных окружения.

### 4. Настройте SSL сертификат (опционально)

Если требуется SSL сертификат для подключения к ClickHouse:

```bash
mkdir -p /root/.clickhouse-client/
# Поместите ваш root.crt в /root/.clickhouse-client/root.crt
```

## Использование

### Запуск агента

```bash
python clickhouse_agent.py
```

### Интерактивный режим

После запуска агент переходит в интерактивный режим:

```
======================================================================
ClickHouse AI Agent with Claude
======================================================================

Commands:
  - Enter your question in natural language
  - Type 'execute' or 'run' to execute the last generated SQL query
  - Type 'exit' or 'quit' to quit
======================================================================
```

### Примеры использования

#### Пример 1: Генерация SQL запроса

```
💬 You: Покажи топ 10 записей из базы данных

🤖 Analyzing your question...
🛠️ Tool: mcp__mcp-clickhouse__list_tables
🤖 Here's the SQL query to show top 10 records...

📝 Generated SQL Query:
──────────────────────────────────────────────────────────────────────
SELECT * FROM your_table LIMIT 10;
──────────────────────────────────────────────────────────────────────

💡 Type 'execute' to run this query, or ask another question.
```

#### Пример 2: Выполнение запроса

```
💬 You: execute

🚀 Executing SQL query...
📊 Results:
[Результаты запроса будут показаны здесь]
```

#### Пример 3: Новый запрос

```
💬 You: Сколько всего записей в таблице?

🤖 Analyzing your question...
🛠️ Tool: mcp__mcp-clickhouse__list_tables
🤖 Here's the SQL query to count records...

📝 Generated SQL Query:
──────────────────────────────────────────────────────────────────────
SELECT COUNT(*) FROM your_table;
──────────────────────────────────────────────────────────────────────
```

## Команды

- **Любой текст** - задайте вопрос на естественном языке для генерации SQL
- **execute / run / exec** - выполнить последний сгенерированный SQL запрос
- **exit / quit / q** - выйти из программы

## Архитектура решения

```
┌─────────────┐
│   User      │
│  (Natural   │
│  Language)  │
└──────┬──────┘
       │
       v
┌─────────────────────────────────┐
│  ClickHouse Agent               │
│  (clickhouse_agent.py)          │
│                                 │
│  - Parse user input             │
│  - Generate SQL (no execute)    │
│  - Execute on confirmation      │
└───────┬──────────────┬──────────┘
        │              │
        v              v
┌──────────────┐  ┌──────────────────┐
│ Claude API   │  │ ClickHouse MCP   │
│ (Sonnet 4.6) │  │ Server           │
└──────────────┘  └────────┬─────────┘
                           │
                           v
                  ┌────────────────┐
                  │  ClickHouse DB │
                  │  (ym_sanok)    │
                  └────────────────┘
```

## Как это работает

1. **Пользователь вводит вопрос** на естественном языке
2. **Агент отправляет запрос Claude** с инструкцией исследовать схему БД
3. **Claude использует MCP инструменты** для получения информации о таблицах
4. **Claude генерирует SQL запрос** на основе схемы и вопроса пользователя
5. **Агент показывает SQL** пользователю БЕЗ выполнения
6. **Пользователь проверяет SQL** и вводит "execute" для выполнения
7. **Агент выполняет запрос** через MCP сервер и показывает результаты

## Безопасность

- ✅ Запросы не выполняются автоматически
- ✅ Пользователь всегда видит SQL перед выполнением
- ✅ Использование MCP сервера для контролируемого доступа к БД
- ⚠️ В продакшене храните credentials в переменных окружения

## Ограничения

- Поддерживаются только SELECT запросы (безопасность MCP сервера)
- Требуется доступ к интернету для Claude API
- Требуется установка `uv` для работы MCP сервера

## Устранение проблем

### Ошибка: "config.yaml not found"
Убедитесь, что файл `config.yaml` находится в той же директории, что и `clickhouse_agent.py`.

### Ошибка: "ANTHROPIC_API_KEY not set"
Проверьте, что API ключ указан в `config.yaml` или установлен в переменной окружения.

### Ошибка: "uv command not found"
Установите `uv` менеджер пакетов: https://github.com/astral-sh/uv

### Проблемы с подключением к ClickHouse
- Проверьте параметры подключения в `config.yaml`
- Убедитесь, что сервер ClickHouse доступен
- Проверьте наличие SSL сертификата, если используется secure: true

## Дополнительная информация

- [Документация Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk)
- [Документация ClickHouse MCP Server](https://github.com/ergut/mcp-clickhouse)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [ClickHouse Documentation](https://clickhouse.com/docs)

## Лицензия

MIT
