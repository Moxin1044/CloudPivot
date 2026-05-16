from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FileItem(BaseModel):
    name: str
    path: str
    is_dir: bool = False
    size: int = 0
    permissions: str = ""
    owner: str = ""
    group: str = ""
    modified_at: Optional[str] = None


class ListResponse(BaseModel):
    path: str
    files: List[FileItem] = []


class PathRequest(BaseModel):
    path: str


class RenameRequest(BaseModel):
    path: str
    new_name: str


class MoveRequest(BaseModel):
    source_path: str
    target_path: str


class MkdirRequest(BaseModel):
    path: str
    name: str


class UploadResponse(BaseModel):
    success: bool = True
    path: str = ""
    name: str = ""
    size: int = 0
