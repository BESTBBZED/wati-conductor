"""Plan and execution models."""

from pydantic import BaseModel, Field


class APICall(BaseModel):
    """Single API call in an execution plan."""

    tool: str = Field(description="Tool/function name to call")
    params: dict = Field(default_factory=dict, description="Parameters for the tool")
    description: str = Field(description="Human-readable description")
    is_destructive: bool = Field(default=False, description="Whether this modifies data")
    depends_on: list[int] = Field(
        default_factory=list, description="Indices of steps this depends on"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tool": "search_contacts",
                "params": {"tag": "VIP"},
                "description": "Search for contacts tagged 'VIP'",
                "is_destructive": False,
            }
        }


class ExecutionPlan(BaseModel):
    """Complete execution plan for an instruction."""

    steps: list[APICall] = Field(description="Sequence of API calls")
    explanation: str = Field(description="Plain language explanation of the plan")
    estimated_api_calls: int = Field(description="Total number of API calls")
    requires_confirmation: bool = Field(
        default=False, description="Whether user confirmation is needed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "steps": [
                    {
                        "tool": "search_contacts",
                        "params": {"tag": "VIP"},
                        "description": "Find VIP contacts",
                    }
                ],
                "explanation": "Search for all contacts with VIP tag",
                "estimated_api_calls": 1,
                "requires_confirmation": False,
            }
        }


class ValidationError(BaseModel):
    """Validation error details."""

    field: str = Field(description="Field that failed validation")
    message: str = Field(description="Error message")
    suggestion: str | None = Field(default=None, description="Suggested fix")
