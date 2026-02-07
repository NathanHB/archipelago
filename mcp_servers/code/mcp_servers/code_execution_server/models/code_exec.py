"""Pydantic models for code execution."""

from mcp_schema import FlatBaseModel as BaseModel
from pydantic import ConfigDict, Field


class CodeExecRequest(BaseModel):
    """Request model for code execution."""

    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(
        None,
        description=(
            "Shell command to execute. This runs in bash, NOT a Python interpreter. "
            "Examples:\n"
            "• Simple Python: python -c 'print(1+1)'\n"
            "• Multi-line Python: Write file first, then run:\n"
            "  cat > script.py << 'EOF'\n"
            "  import pandas\n"
            "  print(pandas.__version__)\n"
            "  EOF && python script.py\n"
            "• Shell commands: ls -la, echo hello, etc."
        ),
    )


class CodeExecResponse(BaseModel):
    """Response model for code execution."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Whether execution succeeded")
    output: str = Field(..., description="Output from code execution")
