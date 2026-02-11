# FEEMS MCP Server

This is a Model Context Protocol (MCP) server for the FEEMS (Fuel, Emissions, Energy Calculation for Machinery System) library.

It allows LLMs to interact with the FEEMS library to perform calculations related to marine power systems, fuel consumption, and emissions.

## Installation

1.  Navigate to this directory:
    ```bash
    cd feems_mcp
    ```

2.  Create a virtual environment and install dependencies:
    ```bash
    uv venv .venv
    source .venv/bin/activate
    uv pip install -e .. # Install parent feems package in editable mode
    uv pip install mcp pandas numpy
    ```
    *Note: If you don't use `uv`, strictly use `python -m venv .venv`, `source .venv/bin/activate`, and `pip install ...`.*

## Usage

### Running the Server

You can run the server directly using Python:

```bash
python server.py
```

However, MCP servers are typically run by an MCP client (like Claude Desktop or an IDE extension).

### Configuring for Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "feems": {
      "command": "/path/to/feems_mcp/.venv/bin/python",
      "args": ["/path/to/feems_mcp/server.py"]
    }
  }
}
```

Make sure to replace `/path/to/feems_mcp` with the absolute path to this directory.

## Available Tools

-   `list_component_types`: Lists all available component types in FEEMS (e.g., MAIN_ENGINE, GENSET).
-   `calculate_engine_fuel_consumption`: Calculates fuel consumption and BSFC for an engine given its rated power, speed, BSFC curve, and current load.

## Extending

To add more tools, edit `server.py` and decorate new functions with `@mcp.tool()`. You can expose more complex FEEMS functionality, such as full system simulations, by wrapping the relevant FEEMS classes and methods.
