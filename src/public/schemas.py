from pydantic import BaseModel, Field

class OK(BaseModel):
    success: bool = Field(default=True)

succesMessage = OK(success=True)