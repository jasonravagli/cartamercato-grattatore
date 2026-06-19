# SW Engineering Guidelines and Coding Style

## Apply OOP wherever possible

- **Prefer OOP over functional programming**: classes are well-identifiable components of the project, easy to extend
- When designing and implementing classes, SOLID principles must always be respected
- **Interfaces**: when meaningful, define interfaces and subclass them in concrete classes to foster abstraction and replaceability of components
- **Override Enforcement**: When defining an interface, inherit from `EnforceOverrides` (from library `overrides`) and use `@override` decorator in subclasses to ensure that abstract methods are implemented and signature respected

## Error Handling

- Domain-specific exception classes (more generic, to be caught at the use-case level) in `domain/exceptions/`
- Implementation-specific exception classes (more specific, to be caught at the infrastructure level) in `infrastructure/exceptions/`
- Catch specific exceptions (not bare `except:`)
- Re-raise infrastructure exceptions as domain exception

## Testing Standards

- Add tests for new behavior — cover success, failure, and edge cases.
- **Plan tests before writing them.**
- Tests should be written based on the expected behavior of the class under test, not the implmentatation details.
- Use the **TDD naming convention** for test methods: `test_<method>_when_<condition>_then/should_<expectation>`.
- Use pytest patterns, not `unittest.TestCase`.
- Use `spec/autospec` when mocking.
- Use `time_machine` for time-dependent tests. Do not use `datetime.now()`
- Use `@pytest.mark.parametrize` for multiple similar inputs.
- Use `@pytest.mark.db_test` for tests that require database access.
- Common test fixtures: `tests/conftest.py`
- Do not use caplog in tests, prefer checking logic and not log output.

## Naming Conventions

- Abstract classes: `Base*` prefix (e.g. `BaseParser`)
- Config classes: `*Config` suffix (`ParserConfig`)
- Private methods: `_snake_case()`
- Public methods: `snake_case()`
- Private fields: `_snake_case` (with leading underscore); prefer private fields over public when possible
- Enums: `UPPER_SNAKE_CASE` using `StrEnum`

## Other Guidelines

- **Always format and check Python files with ruff immediately after writing or editing them**: `uv run ruff format <file_path>` and `uv run ruff check --fix <file_path>`. Do this for every Python file you create or modify, before moving on to the next step.
- **Dependency Injection**: Constructor-based (manual wiring in `cli.py`)
- **Singleton**: Use the Singleton pattern through `@singleton` decorator from `global_utils/singleton.py` when a unique shared instance is required for a class
- **Clean docstrings**: Always write docstrings for classes, methods, and functions you implement. Docstrings should be informative for a user, concise, and explain implementation details only if strictly required.
- **Typing**: All functions require type annotations for parameters and return types
- **Type Safety**: Pydantic `BaseModel` must be used for configuration classes and data models
- **Logging**: Use `loguru` logger (initialized via `GlobalContextManager`)
  - Named parameters: `logger.info("msg: {var}", var=value)`
  - Exceptions: `logger.exception()` for full traceback
- **Public methods befor private ones**: public methods should appear before private ones inside a class, to improve readability.
