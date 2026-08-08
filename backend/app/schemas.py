from pydantic import BaseModel, Field
from typing import Literal

class ProjectTitle(BaseModel):
    """The first small validation exercise from Phase 0."""

    title: str = Field(min_length=3, max_length=120)

class ProjectCreate(BaseModel):  #ProjectCreate is i/p from client
    title: str = Field(min_length=3, max_length=120)
    summary: str = Field(min_length=10, max_length=1000)
    field: str = Field(min_length=2, max_length=80)
    tags: list[str] = Field(default_factory=list)
    visibility: Literal["private", "public"] = "private"

class Project(BaseModel): #Project is o/p from server
    id: int
    title: str
    summary: str
    field: str
    tags: list[str] = Field(default_factory=list)
    visibility: Literal["private", "public"] = "private"

class ProjectUpdate(BaseModel):
   title: str = Field(min_length=3, max_length=120)
   summary: str  = Field(min_length=10, max_length=1000)
   field: str  = Field(min_length=2, max_length=80)
   tags: list[str] = Field(default_factory=list)
   visibility: Literal["private", "public"] = "private"
