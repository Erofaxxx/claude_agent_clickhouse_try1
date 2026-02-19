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
        self.config_path = config_path
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

        # Validate and set Anthropic API key
        api_key = ai_config.get('api_key', '')
        if not api_key or api_key == 'sk-ant-api03-YOUR_API_KEY_HERE':
            raise ValueError(
                "❌ Invalid or missing Anthropic API key in config.yaml\n"
                "Please set a valid API key in the 'ai.api_key' field.\n"
                "Get your API key from: https://console.anthropic.com/"
            )
        os.environ['ANTHROPIC_API_KEY'] = api_key
        print(f"✅ API key configured (starts with: {api_key[:15]}...)")

        # Validate ClickHouse configuration
        required_fields = ['host', 'port', 'user', 'password', 'database']
        missing_fields = [field for field in required_fields if not clickhouse_config.get(field)]
        if missing_fields:
            raise ValueError(
                f"❌ Missing required ClickHouse configuration fields: {', '.join(missing_fields)}\n"
                "Please check your config.yaml file."
            )

        print(f"✅ ClickHouse connection: {clickhouse_config['user']}@{clickhouse_config['host']}:{clickhouse_config['port']}/{clickhouse_config['database']}")

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
        print("🔄 Initializing MCP server connection...")

        try:
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
                            "--config", self.config_path
                        ],
                        "env": env,
                    }
                },
                model=ai_config.get('model', 'claude-sonnet-4'),
            )
            print("✅ MCP server connection initialized successfully")
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ Failed to initialize MCP server connection")
            print(f"Error details: {error_msg}\n")

            # Provide detailed troubleshooting information
            if "timeout" in error_msg.lower() or "initialize" in error_msg.lower():
                print("💡 Connection timeout troubleshooting:")
                print("   1. Check if 'uv' is installed: which uvx")
                print("      Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
                print("   2. Verify mcp-clickhouse package can be installed:")
                print("      uvx mcp-clickhouse --help")
                print("   3. Check ClickHouse server is accessible:")
                print(f"      Host: {clickhouse_config['host']}:{clickhouse_config['port']}")
                print("   4. Verify your API key is valid at: https://console.anthropic.com/")
                print("   5. Check network connectivity and firewall settings")
            elif "command not found" in error_msg.lower() or "uvx" in error_msg.lower():
                print("💡 'uv' package manager not found:")
                print("   Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh")
                print("   Then reload your shell: source ~/.bashrc")
            else:
                print("💡 General troubleshooting:")
                print("   1. Verify config.yaml has correct API key and ClickHouse settings")
                print("   2. Check the error message above for specific issues")
                print("   3. Ensure all required dependencies are installed")

            raise

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
            print(f"\n❌ Error generating SQL: {error_msg}")

            # Provide helpful hints for common errors
            if "control request timeout" in error_msg.lower() and "initialize" in error_msg.lower():
                print("\n💡 MCP server initialization timeout - the server is not responding:")
                print("   1. Verify 'uv' is properly installed and in PATH:")
                print("      Run: which uvx")
                print("      If not found, install: curl -LsSf https://astral.sh/uv/install.sh | sh")
                print("      Then reload shell: source ~/.bashrc")
                print("   2. Test mcp-clickhouse package directly:")
                print("      Run: uvx mcp-clickhouse --help")
                print("   3. Check ClickHouse connectivity from the MCP server:")
                print(f"      Host: {self.config['clickhouse']['host']}:{self.config['clickhouse']['port']}")
                print("      Ensure the server is reachable and credentials are correct")
                print("   4. Check if there are any firewall rules blocking the connection")
                print("   5. Try increasing timeout in config.yaml (ai.timeout_seconds)")
            elif "timeout" in error_msg.lower():
                print("\n💡 Timeout error - possible causes:")
                print("   1. MCP server not responding (check if uvx is working)")
                print("   2. ClickHouse server not accessible")
                print("   3. Network connectivity issues")
                print("   4. API rate limits or quota exceeded")
            elif "exit code -9" in error_msg or "Command failed" in error_msg:
                print("\n💡 Process error troubleshooting:")
                print("   1. Make sure 'uv' is installed: curl -LsSf https://astral.sh/uv/install.sh | sh")
                print("   2. After installing uv, reload your shell: source ~/.bashrc")
                print("   3. Verify uv is in PATH: which uvx")
                print("   4. Check ClickHouse connection settings in config.yaml")
            elif "ANTHROPIC_API_KEY" in error_msg or "api_key" in error_msg.lower():
                print("\n💡 API key issue:")
                print("   1. Check your API key in config.yaml is correct")
                print("   2. Get a valid key from: https://console.anthropic.com/")
                print("   3. Ensure the key starts with 'sk-ant-api03-'")
            elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                print("\n💡 Authentication error:")
                print("   1. Verify your Anthropic API key is valid and active")
                print("   2. Check you haven't exceeded your API usage limits")
                print("   3. Ensure billing is set up on your Anthropic account")
            else:
                print("\n💡 For debugging, check:")
                print("   1. Full error message above")
                print("   2. Config file settings (config.yaml)")
                print("   3. Network connectivity to both Claude API and ClickHouse")

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
            print(f"\n❌ Error executing query: {error_msg}")

            # Provide helpful hints for common errors
            if "control request timeout" in error_msg.lower() and "initialize" in error_msg.lower():
                print("\n💡 MCP server initialization timeout - the server is not responding:")
                print("   1. Verify 'uv' is properly installed and in PATH:")
                print("      Run: which uvx")
                print("      If not found, install: curl -LsSf https://astral.sh/uv/install.sh | sh")
                print("      Then reload shell: source ~/.bashrc")
                print("   2. Test mcp-clickhouse package directly:")
                print("      Run: uvx mcp-clickhouse --help")
                print("   3. Check ClickHouse connectivity from the MCP server:")
                print(f"      Host: {self.config['clickhouse']['host']}:{self.config['clickhouse']['port']}")
                print("      Ensure the server is reachable and credentials are correct")
                print("   4. Check if there are any firewall rules blocking the connection")
                print("   5. Try increasing timeout in config.yaml (ai.timeout_seconds)")
            elif "timeout" in error_msg.lower():
                print("\n💡 Timeout error - possible causes:")
                print("   1. Query is taking too long to execute")
                print("   2. ClickHouse server not responding")
                print("   3. Network connectivity issues")
            elif "exit code -9" in error_msg or "Command failed" in error_msg:
                print("\n💡 Process error troubleshooting:")
                print("   1. Make sure 'uv' is installed: curl -LsSf https://astral.sh/uv/install.sh | sh")
                print("   2. After installing uv, reload your shell: source ~/.bashrc")
                print("   3. Verify uv is in PATH: which uvx")
                print("   4. Check ClickHouse connection settings in config.yaml")
            elif "permission" in error_msg.lower() or "access denied" in error_msg.lower():
                print("\n💡 Permission error:")
                print("   1. Check ClickHouse user has SELECT permissions")
                print("   2. Verify database name is correct")
                print("   3. Check user credentials in config.yaml")
            else:
                print("\n💡 For debugging, check:")
                print("   1. Full error message above")
                print("   2. SQL query syntax")
                print("   3. Table and column names exist in the database")

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
    except FileNotFoundError as e:
        print(f"\n❌ Configuration Error: {str(e)}")
        print("\n💡 Create a config.yaml file based on config.yaml.example")
        print("   Copy config.yaml.example to config.yaml and update the values")
    except ValueError as e:
        print(f"\n{str(e)}")
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Failed to initialize agent")
        print(f"Error: {str(e)}")
        print("\n💡 Please check:")
        print("   1. Your config.yaml file is valid YAML format")
        print("   2. All required fields are present (see config.yaml.example)")
        print("   3. Your Anthropic API key is correct")
        print("   4. Your ClickHouse connection details are correct")


if __name__ == "__main__":
    asyncio.run(main())
