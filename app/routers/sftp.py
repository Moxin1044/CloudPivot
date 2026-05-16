from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncssh
import os
import stat
from datetime import datetime
from typing import List

from app.database import get_db
from app.models.host import Host
from app.models.user import User
from app.dependencies import get_current_user
from app.schemas.sftp import (
    FileItem, ListResponse, PathRequest,
    RenameRequest, MoveRequest, MkdirRequest, UploadResponse,
)
from app.config import settings
from app.core.logger import logger

router = APIRouter(prefix="/sftp", tags=["SFTP"])


async def get_host_connection(host_id: int, db: AsyncSession) -> tuple[Host, asyncssh.SSHClientConnection]:
    """Get host info and establish SSH connection."""
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    try:
        connect_kwargs = {
            "host": host.ip_address,
            "port": host.port,
            "username": host.username,
            "known_hosts": None,
            "connect_timeout": settings.WEBSSH_SSH_TIMEOUT,
        }
        if host.auth_type.value == "key" and host.private_key_encrypted:
            pk = host.private_key_encrypted
            if "-----BEGIN" in pk:
                connect_kwargs["client_keys"] = [asyncssh.import_private_key(pk)]
            else:
                connect_kwargs["client_keys"] = [pk]
        elif host.password_encrypted:
            connect_kwargs["password"] = host.password_encrypted

        conn = await asyncssh.connect(**connect_kwargs)
        return host, conn
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SSH connection failed: {str(e)}")


@router.get("/{host_id}/list", response_model=ListResponse, summary="列出目录文件")
async def list_directory(
    host_id: int,
    path: str = Query("/"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    host, conn = await get_host_connection(host_id, db)
    try:
        async with conn.start_sftp_client() as sftp:
            try:
                entries = await sftp.listdir(path)
            except (OSError, IOError) as e:
                raise HTTPException(status_code=400, detail=f"Cannot list directory: {str(e)}")

            files: List[FileItem] = []
            dir_entries = []
            file_entries = []
            for entry in entries:
                try:
                    full_path = f"{path.rstrip('/')}/{entry}" if path != "/" else f"/{entry}"
                    attr = await sftp.stat(full_path)
                    item = FileItem(
                        name=entry,
                        path=full_path,
                        is_dir=stat.S_ISDIR(attr.permissions),
                        size=attr.size or 0,
                        permissions=stat.filemode(attr.permissions) if attr.permissions else "",
                        modified_at=datetime.fromtimestamp(attr.mtime).isoformat() if attr.mtime else None,
                    )
                    if item.is_dir:
                        dir_entries.append(item)
                    else:
                        file_entries.append(item)
                except Exception:
                    # Skip entries we can't stat
                    pass

            # Sort: .. first (if not at root), then other dirs alphabetically, then files alphabetically
            parent_entry = None
            other_dir_entries = []
            for item in dir_entries:
                if item.name == '..':
                    parent_entry = item
                else:
                    other_dir_entries.append(item)

            other_dir_entries.sort(key=lambda x: x.name.lower())
            file_entries.sort(key=lambda x: x.name.lower())

            sorted_files: List[FileItem] = []
            if parent_entry:
                sorted_files.append(parent_entry)
            sorted_files.extend(other_dir_entries)
            sorted_files.extend(file_entries)

            return ListResponse(path=path, files=sorted_files)
    finally:
        conn.close()
        await conn.wait_closed()


@router.post("/{host_id}/mkdir", summary="创建文件夹")
async def create_directory(
    host_id: int,
    body: MkdirRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    host, conn = await get_host_connection(host_id, db)
    try:
        async with conn.start_sftp_client() as sftp:
            new_path = f"{body.path.rstrip('/')}/{body.name}"
            try:
                await sftp.mkdir(new_path)
            except (OSError, IOError) as e:
                raise HTTPException(status_code=400, detail=f"Cannot create directory: {str(e)}")
            return {"success": True, "path": new_path}
    finally:
        conn.close()
        await conn.wait_closed()


@router.post("/{host_id}/rename", summary="重命名文件/文件夹")
async def rename_file(
    host_id: int,
    body: RenameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    host, conn = await get_host_connection(host_id, db)
    try:
        async with conn.start_sftp_client() as sftp:
            parent = os.path.dirname(body.path)
            new_path = f"{parent.rstrip('/')}/{body.new_name}" if parent else f"/{body.new_name}"
            try:
                await sftp.rename(body.path, new_path)
            except (OSError, IOError) as e:
                raise HTTPException(status_code=400, detail=f"Cannot rename: {str(e)}")
            return {"success": True, "old_path": body.path, "new_path": new_path}
    finally:
        conn.close()
        await conn.wait_closed()


@router.post("/{host_id}/move", summary="移动文件/文件夹")
async def move_file(
    host_id: int,
    body: MoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    host, conn = await get_host_connection(host_id, db)
    try:
        async with conn.start_sftp_client() as sftp:
            name = os.path.basename(body.source_path)
            target = f"{body.target_path.rstrip('/')}/{name}"
            try:
                await sftp.rename(body.source_path, target)
            except (OSError, IOError) as e:
                raise HTTPException(status_code=400, detail=f"Cannot move: {str(e)}")
            return {"success": True, "source": body.source_path, "target": target}
    finally:
        conn.close()
        await conn.wait_closed()


@router.post("/{host_id}/copy", summary="复制文件/文件夹")
async def copy_file(
    host_id: int,
    body: MoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    host, conn = await get_host_connection(host_id, db)
    try:
        name = os.path.basename(body.source_path)
        target = f"{body.target_path.rstrip('/')}/{name}"

        # Use SFTP for files, shell command for recursive directory copy
        result = await conn.run(f"cp -r '{body.source_path}' '{target}'", check=False)
        if result.exit_status != 0:
            raise HTTPException(
                status_code=400,
                detail=f"Copy failed: {result.stderr or 'Unknown error'}"
            )
        return {"success": True, "source": body.source_path, "target": target}
    finally:
        conn.close()
        await conn.wait_closed()


@router.post("/{host_id}/delete", summary="删除文件/文件夹")
async def delete_file(
    host_id: int,
    body: PathRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    host, conn = await get_host_connection(host_id, db)
    try:
        async with conn.start_sftp_client() as sftp:
            try:
                attr = await sftp.stat(body.path)
                if stat.S_ISDIR(attr.permissions):
                    # Recursively remove directory
                    await _rmdir_recursive(sftp, body.path)
                else:
                    await sftp.remove(body.path)
            except (OSError, IOError) as e:
                raise HTTPException(status_code=400, detail=f"Cannot delete: {str(e)}")
            return {"success": True, "path": body.path}
    finally:
        conn.close()
        await conn.wait_closed()


async def _rmdir_recursive(sftp: asyncssh.SFTPClient, path: str):
    """Recursively remove a directory via SFTP."""
    entries = await sftp.listdir(path)
    for entry in entries:
        full = f"{path.rstrip('/')}/{entry}" if path != "/" else f"/{entry}"
        try:
            attr = await sftp.stat(full)
            if stat.S_ISDIR(attr.permissions):
                await _rmdir_recursive(sftp, full)
            else:
                await sftp.remove(full)
        except Exception:
            pass
    await sftp.rmdir(path)


@router.get("/{host_id}/download", summary="下载文件")
async def download_file(
    host_id: int,
    path: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    host, conn = await get_host_connection(host_id, db)
    sftp = None
    try:
        sftp = await conn.start_sftp_client()
        try:
            attr = await sftp.stat(path)
            if stat.S_ISDIR(attr.permissions):
                raise HTTPException(status_code=400, detail="Cannot download a directory")
        except (OSError, IOError) as e:
            raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")

        filename = os.path.basename(path)
        file_size = attr.size

        async def file_stream():
            f = None
            try:
                f = await sftp.open(path, 'rb')
                while True:
                    chunk = await f.read(65536)
                    if not chunk:
                        break
                    yield chunk
            finally:
                try:
                    if f:
                        await f.close()
                except Exception:
                    pass
                try:
                    if sftp:
                        await sftp.exit()
                except Exception:
                    pass
                try:
                    conn.close()
                    await conn.wait_closed()
                except Exception:
                    pass

        return StreamingResponse(
            file_stream(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(file_size),
            },
        )
    except HTTPException:
        # Clean up on error before streaming starts
        try:
            if sftp:
                await sftp.exit()
        except Exception:
            pass
        try:
            conn.close()
            await conn.wait_closed()
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            if sftp:
                await sftp.exit()
        except Exception:
            pass
        try:
            conn.close()
            await conn.wait_closed()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/{host_id}/upload", response_model=UploadResponse, summary="上传文件")
async def upload_file(
    host_id: int,
    path: str = Query("/"),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    host, conn = await get_host_connection(host_id, db)
    results = []
    try:
        async with conn.start_sftp_client() as sftp:
            for file in files:
                target_path = f"{path.rstrip('/')}/{file.filename}"
                try:
                    async with sftp.open(target_path, 'wb') as remote_file:
                        while True:
                            chunk = await file.read(65536)
                            if not chunk:
                                break
                            await remote_file.write(chunk)
                    results.append({
                        "success": True,
                        "path": target_path,
                        "name": file.filename,
                        "size": file.size or 0,
                    })
                except Exception as e:
                    results.append({
                        "success": False,
                        "path": target_path,
                        "name": file.filename,
                        "error": str(e),
                    })
    finally:
        conn.close()
        await conn.wait_closed()

    if results and all(r["success"] for r in results):
        return results[0] if len(results) == 1 else results[0]
    elif results:
        first_fail = next((r for r in results if not r["success"]), None)
        if first_fail:
            raise HTTPException(status_code=400, detail=first_fail["error"])
    raise HTTPException(status_code=400, detail="Upload failed")


@router.get("/{host_id}/exists", summary="检查路径是否存在")
async def path_exists(
    host_id: int,
    path: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    host, conn = await get_host_connection(host_id, db)
    try:
        async with conn.start_sftp_client() as sftp:
            try:
                attr = await sftp.stat(path)
                return {
                    "exists": True,
                    "is_dir": stat.S_ISDIR(attr.permissions),
                    "size": attr.size or 0,
                }
            except (OSError, IOError):
                return {"exists": False}
    finally:
        conn.close()
        await conn.wait_closed()
