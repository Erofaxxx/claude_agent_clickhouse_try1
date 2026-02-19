#!/usr/bin/env python3
"""
ClickHouse AI Agent with Claude
Accepts user queries, generates SQL for ClickHouse, and executes only when confirmed.
"""

import os
import yaml
import asyncio
from typing import Dict, Optional
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, UserMessage, TextBlock, ToolUseBlock


class ClickHouseAgent:
    """AI Agent that interacts with ClickHouse database using Claude."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the agent with configuration."""
        self.config = self._load_config(config_path)
        self.last_sql_query = None
        self.options = self._setup_agent_options()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file with fallback locations."""
        # Try multiple locations in order
        config_locations = [
            config_path,  # User-specified or default "config.yaml"
            os.path.expanduser("~/.config/clickhouse/config.yaml"),  # Ubuntu standard location
            os.path.join(os.path.dirname(__file__), "config.yaml"),  # Script directory
        ]

        for location in config_locations:
            if os.path.exists(location):
                print(f"📂 Loading configuration from: {location}")
                with open(location, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)

        raise FileNotFoundError(
            f"Configuration file not found. Tried locations:\n" +
            "\n".join(f"  - {loc}" for loc in config_locations)
        )

    def _setup_agent_options(self) -> ClaudeAgentOptions:
        """Setup Claude Agent options with ClickHouse MCP server."""
        clickhouse_config = self.config['clickhouse']
        ai_config = self.config['ai']

        # Set Anthropic API key
        os.environ['ANTHROPIC_API_KEY'] = ai_config['api_key']

        # Setup environment variables for ClickHouse MCP server
        # Start with system environment so PATH and other essentials are available
        env = os.environ.copy()
        env.update({
            "CLICKHOUSE_HOST": clickhouse_config['host'],
            "CLICKHOUSE_PORT": str(clickhouse_config['port']),
            "CLICKHOUSE_USER": clickhouse_config['user'],
            "CLICKHOUSE_PASSWORD": clickhouse_config['password'],
            "CLICKHOUSE_DATABASE": clickhouse_config['database'],
            "CLICKHOUSE_SECURE": str(clickhouse_config['secure']).lower(),
        })

        # Create agent options with MCP server configuration
        options = ClaudeAgentOptions(
            allowed_tools=[
                "mcp__mcp-clickhouse__list_databases",
                "mcp__mcp-clickhouse__list_tables",
                "mcp__mcp-clickhouse__run_select_query",
                "mcp__mcp-clickhouse__run_chdb_select_query",
            ],
            mcp_servers={
                "mcp-clickhouse": {
                    "command": "uvx",
                    "args": [
                        "mcp-clickhouse",
                    ],
                    "env": env,
                }
            },
            model=ai_config.get('model', 'claude-sonnet-4'),
        )

        return options

    async def generate_sql(self, user_query: str) -> Optional[str]:
        """
        Generate SQL query based on user's natural language question.
        Does NOT execute the query.
        """
        print(f"\n🤔 Analyzing your question: {user_query}\n")

        prompt = f"""Based on the user's question, explore the ClickHouse database schema and generate an appropriate SQL query.

User question: {user_query}

Please:
1. List available databases and tables
2. Generate a SELECT SQL query that answers the user's question
3. Return ONLY the SQL query without executing it

Do NOT execute the query. Just generate it and show it to me."""

        sql_query = None

        try:
            async for message in query(prompt=prompt, options=self.options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(f"🤖 {block.text}")
                            # Try to extract SQL from the response
                            text = block.text
                            if "SELECT" in text.upper():
                                # Extract SQL query from the text
                                lines = text.split('\n')
                                sql_lines = []
                                in_sql = False
                                for line in lines:
                                    if 'SELECT' in line.upper() or in_sql:
                                        in_sql = True
                                        sql_lines.append(line)
                                        if ';' in line:
                                            break
                                if sql_lines:
                                    sql_query = '\n'.join(sql_lines).strip()

                        if isinstance(block, ToolUseBlock):
                            print(f"🛠️  Tool: {block.name}")
                            print(f"   Input: {block.input}")

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error: {error_msg}")

            # Provide helpful hints for common errors
            if "exit code -9" in error_msg or "Command failed" in error_msg:
                print("\n💡 Troubleshooting tips:")
                print("   1. Make sure 'uv' is installed: curl -LsSf https://astral.sh/uv/install.sh | sh")
                print("   2. After installing uv, reload your shell: source ~/.bashrc")
                print("   3. Verify uv is in PATH: which uvx")
                print("   4. Check ClickHouse connection settings in config.yaml")
            elif "ANTHROPIC_API_KEY" in error_msg:
                print("\n💡 Please set your Anthropic API key in config.yaml")

            return None

        self.last_sql_query = sql_query
        return sql_query

    async def execute_sql(self, sql_query: Optional[str] = None) -> None:
        """Execute the SQL query."""
        if sql_query is None:
            sql_query = self.last_sql_query

        if not sql_query:
            print("❌ No SQL query to execute. Please generate a query first.")
            return

        print(f"\n🚀 Executing SQL query...\n")

        prompt = f"""Execute the following SQL query on the ClickHouse database and show the results:

{sql_query}

Please run this query and display the results in a clear, readable format."""

        try:
            async for message in query(prompt=prompt, options=self.options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(f"📊 {block.text}")

                        if isinstance(block, ToolUseBlock):
                            print(f"🛠️  Tool: {block.name}")
                            if block.name == "mcp__mcp-clickhouse__run_select_query":
                                print(f"   Query: {block.input.get('query', '')}")

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error executing query: {error_msg}")

            # Provide helpful hints for common errors
            if "exit code -9" in error_msg or "Command failed" in error_msg:
                print("\n💡 Troubleshooting tips:")
                print("   1. Make sure 'uv' is installed: curl -LsSf https://astral.sh/uv/install.sh | sh")
                print("   2. After installing uv, reload your shell: source ~/.bashrc")
                print("   3. Verify uv is in PATH: which uvx")
                print("   4. Check ClickHouse connection settings in config.yaml")

    async def interactive_mode(self):
        """Run the agent in interactive mode."""
        print("=" * 70)
        print("ClickHouse AI Agent with Claude")
        print("=" * 70)
        print("\nCommands:")
        print("  - Enter your question in natural language")
        print("  - Type 'execute' or 'run' to execute the last generated SQL query")
        print("  - Type 'exit' or 'quit' to quit")
        print("=" * 70)

        while True:
            try:
                user_input = input("\n💬 You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 Goodbye!")
                    break

                if user_input.lower() in ['execute', 'run', 'exec']:
                    await self.execute_sql()
                else:
                    sql = await self.generate_sql(user_input)
                    if sql:
                        print(f"\n📝 Generated SQL Query:")
                        print("─" * 70)
                        print(sql)
                        print("─" * 70)
                        print("\n💡 Type 'execute' to run this query, or ask another question.")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")


async def main():
    """Main function to run the agent."""
    try:
        agent = ClickHouseAgent()
        await agent.interactive_mode()
    except FileNotFoundError:
        print("❌ Error: config.yaml not found. Please create the configuration file.")
    except Exception as e:
        print(f"❌ Error initializing agent: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
