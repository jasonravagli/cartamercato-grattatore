import sys
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, ConfigDict

from cartamercato_grattatore.global_utils.singleton import singleton


class GlobalContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    path_serialization_dir: Path


@singleton
class GlobalContextManager:
    def __init__(self) -> None:
        self._initialized = False
        self._global_context: GlobalContext

    def initialize(self) -> None:
        if self._initialized:
            raise RuntimeError("GlobalContextManager is already initialized.")

        ser_dir = self._setup_serialization_dir()
        self._global_context = GlobalContext(path_serialization_dir=ser_dir)

        self._setup_logger(ser_dir)

        self._initialized = True

    def get_global_context(self) -> GlobalContext:
        if not self._initialized:
            raise RuntimeError("GlobalContextManager is not initialized yet.")
        return self._global_context

    def reset(self) -> None:
        """Reset the manager so it can be reinitialized with a fresh directory."""
        self._initialized = False
        self._global_context = None  # type: ignore[assignment]

    def _setup_serialization_dir(self) -> Path:
        path_root = Path("./logs/")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        dir_name = f"{timestamp}-{unique_id}"
        log_dir = path_root / dir_name
        log_dir.mkdir(parents=True, exist_ok=True)

        return log_dir

    def _setup_logger(self, ser_dir: Path) -> None:
        logger.remove()  # Remove default logger (duplicated logs otherwise)
        logger.add(
            sys.stdout,
            colorize=True,
            format="<green>{time}</green> <level>{message}</level>",
            level="INFO",
        )
        logger.add(
            ser_dir / "logfile.log",
            enqueue=True,  # Ensure thread/process safety
            level="INFO",
        )
