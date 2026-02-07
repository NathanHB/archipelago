import os

from loguru import logger
from models.code_exec import (
    CodeExecRequest,
    CodeExecResponse,
)
from utils.decorators import make_async_background
from utils.sandbox import (
    DEFAULT_LIBRARY_PATH,
    run_sandboxed_command,
    verify_sandbox_library_available,
)

FS_ROOT = os.getenv("APP_FS_ROOT", "/filesystem")
CODE_EXEC_COMMAND_TIMEOUT = os.getenv("CODE_EXEC_COMMAND_TIMEOUT", "300")
SANDBOX_LIBRARY_PATH = os.getenv("SANDBOX_LIBRARY_PATH", DEFAULT_LIBRARY_PATH)
# Paths to hide from code execution
BLOCKED_PATHS = ["/app", "/.apps_data"]


def verify_sandbox_available() -> None:
    """Verify sandbox library is available. Call at server startup, not import time.

    Raises:
        RuntimeError: If the sandbox_fs.so library is not found.
    """
    verify_sandbox_library_available(SANDBOX_LIBRARY_PATH)


@make_async_background
def code_exec(request: CodeExecRequest) -> CodeExecResponse:
    """Execute shell commands in a sandboxed bash environment."""
    # Reject None code - allow empty string (valid in bash)
    if request.code is None:
        return CodeExecResponse(
            success=False,
            output="Error: Required parameter 'code' (command to execute)",
        )

    # Safety net: detect raw Python code and provide helpful error
    code_stripped = request.code.strip()

    def looks_like_python_import(code: str) -> bool:
        """Check if code looks like a Python import vs shell command.

        'import' is also an ImageMagick command for screenshots, e.g.:
        - import screenshot.png
        - import -window root desktop.png

        Python imports look like:
        - import module
        - import module.submodule
        - import module as alias
        """
        if not code.startswith("import "):
            return False
        rest = code[7:].strip()  # After "import "
        # Shell import typically has options (-flag) or file paths
        if rest.startswith("-") or "/" in rest.split()[0] if rest else False:
            return False
        # Shell import targets typically have file extensions
        first_documents = rest.split()[0] if rest else ""
        if "." in first_documents and first_documents.rsplit(".", 1)[-1].lower() in (
            "png",
            "jpg",
            "jpeg",
            "gif",
            "bmp",
            "tiff",
            "webp",
            "pdf",
            "ps",
            "eps",
        ):
            return False
        return True

    python_indicators = (
        looks_like_python_import(code_stripped),
        code_stripped.startswith("from "),
        code_stripped.startswith("def "),
        code_stripped.startswith("class "),
        code_stripped.startswith("async def "),
        code_stripped.startswith("@"),  # decorators
    )
    if any(python_indicators):
        return CodeExecResponse(
            success=False,
            output=(
                "Error: It looks like you passed raw Python code. This tool executes shell "
                "commands, not Python directly. To run Python:\n"
                "• One-liner: python -c 'your_code_here'\n"
                "• Multi-line: Write to file first, then run:\n"
                "  cat > script.py << 'EOF'\n"
                "  your_code\n"
                "  EOF && python script.py"
            ),
        )

    try:
        timeout_value = int(CODE_EXEC_COMMAND_TIMEOUT)
    except ValueError:
        error_msg = f"Invalid timeout value: {CODE_EXEC_COMMAND_TIMEOUT}"
        logger.error(error_msg)
        return CodeExecResponse(
            success=False,
            output=f"Configuration error: {error_msg}",
        )

    try:
        # Use LD_PRELOAD-sandboxed execution
        result = run_sandboxed_command(
            command=request.code,
            timeout=timeout_value,
            working_dir=FS_ROOT,
            blocked_paths=BLOCKED_PATHS,
            library_path=SANDBOX_LIBRARY_PATH,
        )

        if result.timed_out:
            logger.error(f"Command timed out after {timeout_value} seconds")
            return CodeExecResponse(
                success=False,
                output=f"Command execution timed out after {timeout_value} seconds",
            )

        if result.error:
            logger.error(f"Error running command: {result.error}")
            return CodeExecResponse(
                success=False,
                output=f"System error: {result.error}",
            )

        if result.return_code != 0:
            logger.error(f"Command failed with exit code {result.return_code}")
            output = result.stdout if result.stdout else ""
            if result.stderr:
                output += f"\nError output:\n{result.stderr}"
            return CodeExecResponse(
                success=False,
                output=f"{output}\n\nCommand failed with exit code {result.return_code}",
            )

        return CodeExecResponse(
            success=True,
            output=result.stdout,
        )
    except FileNotFoundError:
        error_msg = f"Working directory not found: {FS_ROOT}"
        logger.error(error_msg)
        return CodeExecResponse(
            success=False,
            output=f"Configuration error: {error_msg}",
        )
    except OSError as e:
        error_msg = f"OS error when executing command: {e}"
        logger.error(error_msg)
        return CodeExecResponse(
            success=False,
            output=f"System error: {error_msg}",
        )
