# Execution

## Running the Application

```bash
# Install dependencies
make install    # runs: uv sync

# Run via module (recommended for dev)
uv run python -m cartamercato_grattatore

# Or after install
uv run cartamercato-grattatore
```

## Execution Flow

1. [cartamercato_grattatore/__main__.py](../cartamercato_grattatore/__main__.py) creates the global context and calls the main method from `cli.py`
2. [cartamercato_grattatore/interface_adapters/cli.py](cartamercato_grattatore/interface_adapters/cli.py) loads configurations, wires all dependencies and start the execution
3. Execution continues under the use cases selected by the user [TO BE DEFINED]

## Logging and Serialization

- Each run creates a serialization directory `logs/{timestamp}-{uuid}/`, that stores logs and artifacts from the session