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

### Вариант A: Установка на Ubuntu сервере (рекомендуется)

#### 1. Подключитесь к вашему Ubuntu серверу

```bash
ssh root@your-server-ip
```

#### 2. Клонируйте репозиторий или скопируйте файлы

```bash
# Создайте директорию для проекта
mkdir -p ~/text_to_clickhouse_sql
cd ~/text_to_clickhouse_sql

# Скопируйте файлы clickhouse_agent.py и requirements.txt на сервер
# Например, используя scp с локальной машины:
# scp clickhouse_agent.py requirements.txt root@your-server-ip:~/text_to_clickhouse_sql/
```

#### 3. Установите Python зависимости

```bash
pip install -r requirements.txt
```

#### 4. Установите uv (если ещё не установлен)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# После установки перезагрузите оболочку или выполните:
source ~/.bashrc
```

#### 5. Настройте конфигурацию

Создайте конфигурационный файл в стандартной директории:

```bash
# Создайте директорию для конфигурации
mkdir -p ~/.config/clickhouse

# Создайте файл конфигурации
nano ~/.config/clickhouse/config.yaml
```

Содержимое файла `~/.config/clickhouse/config.yaml`:

```yaml
clickhouse:
  host: rc1b-vsrkuug8qh3pkkeg.mdb.yandexcloud.net
  port: 9440
  user: analyst_ym
  password: StrongPass123!
  database: ym_sanok
  secure: true
  openSSL:
    client:
      caConfig: /root/.clickhouse-client/root.crt

ai:
  provider: anthropic
  api_key: sk-ant-api03-YOUR_API_KEY_HERE
  model: claude-sonnet-4-6
  temperature: 0.0
  max_tokens: 1000
  timeout_seconds: 30
  enable_schema_access: true
  database: ym_sanok
```

**Важно:**
- Замените `YOUR_API_KEY_HERE` на ваш реальный Anthropic API ключ
- Убедитесь, что SSL сертификат находится по пути `/root/.clickhouse-client/root.crt`

```bash
# Проверьте наличие сертификата
ls -la /root/.clickhouse-client/root.crt
```

#### 6. Обновите путь к конфигурации в программе

По умолчанию программа ищет `config.yaml` в текущей директории. Для использования конфигурации из `~/.config/clickhouse/`, запустите программу с указанием пути:

```bash
cd ~/text_to_clickhouse_sql
python clickhouse_agent.py
```

Или измените путь в коде, отредактировав `clickhouse_agent.py`:

```python
# Найдите строку:
def __init__(self, config_path: str = "config.yaml"):

# Измените на:
def __init__(self, config_path: str = os.path.expanduser("~/.config/clickhouse/config.yaml")):
```

### Вариант B: Локальная установка

#### 1. Установите Python зависимости

```bash
pip install -r requirements.txt
```

#### 2. Установите uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Или на Windows:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 3. Создайте config.yaml в директории проекта

Скопируйте `config.yaml.example` в `config.yaml` и заполните своими данными:

```bash
cp config.yaml.example config.yaml
nano config.yaml
```

## Использование

### Запуск агента

**На Ubuntu сервере:**

```bash
# Перейдите в директорию проекта
cd ~/text_to_clickhouse_sql

# Запустите агент (если используется ~/.config/clickhouse/config.yaml)
python clickhouse_agent.py

# Или создайте символическую ссылку на конфигурацию:
ln -s ~/.config/clickhouse/config.yaml ~/text_to_clickhouse_sql/config.yaml
python clickhouse_agent.py
```

**Локально:**

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

**На сервере Ubuntu:**
```bash
# Убедитесь, что конфигурация существует
ls -la ~/.config/clickhouse/config.yaml

# Создайте символическую ссылку в директорию проекта
cd ~/text_to_clickhouse_sql
ln -s ~/.config/clickhouse/config.yaml config.yaml
```

**Локально:**
Убедитесь, что файл `config.yaml` находится в той же директории, что и `clickhouse_agent.py`.

### Ошибка: "ANTHROPIC_API_KEY not set"
Проверьте, что API ключ указан в `config.yaml` или в `~/.config/clickhouse/config.yaml`.

### Ошибка: "uv command not found"
```bash
# Установите uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Перезагрузите оболочку
source ~/.bashrc

# Проверьте установку
uv --version
```

### Проблемы с подключением к ClickHouse
- Проверьте параметры подключения в `~/.config/clickhouse/config.yaml`
- Убедитесь, что используется правильный пользователь: `analyst_ym`
- Убедитесь, что сервер ClickHouse доступен с вашего сервера
- Проверьте наличие SSL сертификата:
  ```bash
  ls -la /root/.clickhouse-client/root.crt
  ```
- Проверьте права доступа к сертификату:
  ```bash
  chmod 600 /root/.clickhouse-client/root.crt
  ```

### Тестирование подключения к ClickHouse

Перед запуском агента можно проверить подключение к ClickHouse:

```bash
clickhouse-client \
  --host rc1b-vsrkuug8qh3pkkeg.mdb.yandexcloud.net \
  --port 9440 \
  --user analyst_ym \
  --password 'StrongPass123!' \
  --database ym_sanok \
  --secure \
  --query "SELECT 1"
```

## Дополнительная информация

- [Документация Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk)
- [Документация ClickHouse MCP Server](https://github.com/ergut/mcp-clickhouse)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [ClickHouse Documentation](https://clickhouse.com/docs)

## Лицензия

MIT
