# Architecture

The project follows the **clean Architecture** with strict layer separation.

```text
cartamercato_grattatore/                 # Application code
├── __main__.py                  # Entrypoint of the application
├── domain/                      # What the system is (framework-independent)
│   ├── data_models/             # Core entities
│   ├── ports/                   # Abstract interfaces defining the functionalities of the main building blocks
│   └── exceptions/              # Domain exceptions
├── application/                 # What the system does (use cases, depends on domain ports only)
│   └── use_cases/               # Orchestrate bulding blocks, entities, and functionalities from the domain to provide a complete functionality
├── infrastructure/              # How things are done (port implementations and utilities)
├── interface_adapters/          # How the application is served and executed (DI wirings, application startup, use case invocations)
├── global_utils/                # Run-wide utils (e.g. logging setup, serialization dir setup, etc.)
└── utils/                       # Application-wide utils (e.g. template loading)
tests/                           # Unit tests
assets/                          # Assets required to run the project (additional data, resources, etc.)
└── prompts/                     # Jinja templates used by agents and LLMs
```
