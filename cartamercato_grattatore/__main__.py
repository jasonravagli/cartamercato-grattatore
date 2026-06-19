from cartamercato_grattatore.global_utils.global_context import GlobalContextManager
from cartamercato_grattatore.interface_adapters.cli import main as cli_main


def main() -> None:
    GlobalContextManager().initialize()
    cli_main()


if __name__ == "__main__":
    main()
