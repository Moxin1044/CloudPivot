from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.docker import DockerHost, ContainerInfo
from app.models.user import User
from app.schemas.docker import (
    DockerHostCreate, DockerHostResponse,
    ContainerResponse, ContainerStatsResponse,
    ContainerLogResponse, ContainerActionRequest,
    ExecRequest, ImageResponse,
)
from app.dependencies import get_current_user
from app.core.docker_client import docker_client
from app.core.logger import logger

router = APIRouter(prefix="/docker", tags=["Docker"])


# ===== Docker Hosts =====
@router.get("/hosts", response_model=list[DockerHostResponse], summary="获取Docker主机列表")
async def list_docker_hosts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DockerHost))
    return result.scalars().all()


@router.post("/hosts", response_model=DockerHostResponse, status_code=status.HTTP_201_CREATED, summary="添加Docker主机")
async def create_docker_host(
    data: DockerHostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    docker_host = DockerHost(**data.model_dump())
    db.add(docker_host)
    await db.flush()
    await db.refresh(docker_host)
    return docker_host


@router.delete("/hosts/{host_id}", summary="删除Docker主机")
async def delete_docker_host(
    host_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DockerHost).where(DockerHost.id == host_id))
    docker_host = result.scalar_one_or_none()
    if not docker_host:
        raise HTTPException(status_code=404, detail="Docker host not found")
    await db.delete(docker_host)
    return {"message": "Docker host deleted"}


# ===== Containers =====
@router.get("/containers", response_model=list[ContainerResponse], summary="获取容器列表")
async def list_containers(
    all: bool = False,
    current_user: User = Depends(get_current_user),
):
    try:
        containers = await docker_client.list_containers(all=all)
        result = []
        for c in containers:
            names = c.get("Names", [])
            name = names[0].lstrip("/") if names else None
            result.append(ContainerResponse(
                id=c.get("Id", "")[:12],
                name=name,
                image=c.get("Image"),
                status=c.get("Status"),
                state=c.get("State"),
                ports=c.get("Ports"),
                labels=c.get("Labels"),
                created=c.get("Created"),
            ))
        return result
    except Exception as e:
        logger.error(f"Failed to list containers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list containers: {e}")


@router.get("/containers/{container_id}", summary="获取容器详情")
async def get_container(
    container_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        return await docker_client.get_container(container_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Container not found: {e}")


@router.post("/containers/{container_id}/start", summary="启动容器")
async def start_container(
    container_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        await docker_client.start_container(container_id)
        return {"message": f"Container {container_id} started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start container: {e}")


@router.post("/containers/{container_id}/stop", summary="停止容器")
async def stop_container(
    container_id: str,
    data: ContainerActionRequest = ContainerActionRequest(),
    current_user: User = Depends(get_current_user),
):
    try:
        await docker_client.stop_container(container_id, timeout=data.timeout)
        return {"message": f"Container {container_id} stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop container: {e}")


@router.post("/containers/{container_id}/restart", summary="重启容器")
async def restart_container(
    container_id: str,
    data: ContainerActionRequest = ContainerActionRequest(),
    current_user: User = Depends(get_current_user),
):
    try:
        await docker_client.restart_container(container_id, timeout=data.timeout)
        return {"message": f"Container {container_id} restarted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart container: {e}")


@router.delete("/containers/{container_id}", summary="删除容器")
async def remove_container(
    container_id: str,
    force: bool = False,
    current_user: User = Depends(get_current_user),
):
    try:
        await docker_client.remove_container(container_id, force=force)
        return {"message": f"Container {container_id} removed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove container: {e}")


@router.get("/containers/{container_id}/logs", response_model=ContainerLogResponse, summary="获取容器日志")
async def get_container_logs(
    container_id: str,
    tail: int = 100,
    current_user: User = Depends(get_current_user),
):
    try:
        logs = await docker_client.container_logs(container_id, tail=tail)
        if isinstance(logs, list):
            logs = "\n".join(str(l) for l in logs)
        return ContainerLogResponse(logs=logs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {e}")


@router.get("/containers/{container_id}/stats", response_model=ContainerStatsResponse, summary="获取容器Stats")
async def get_container_stats(
    container_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        stats = await docker_client.container_stats(container_id)
        # Parse Docker stats
        cpu_delta = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0) - \
                    stats.get("precpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
        system_delta = stats.get("cpu_stats", {}).get("system_cpu_usage", 0) - \
                       stats.get("precpu_stats", {}).get("system_cpu_usage", 0)
        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * 100

        mem_usage = stats.get("memory_stats", {}).get("usage", 0)
        mem_limit = stats.get("memory_stats", {}).get("limit", 0)
        mem_percent = (mem_usage / mem_limit * 100) if mem_limit > 0 else 0

        return ContainerStatsResponse(
            cpu_percent=round(cpu_percent, 2),
            memory_usage_mb=round(mem_usage / 1024 / 1024, 2),
            memory_limit_mb=round(mem_limit / 1024 / 1024, 2),
            memory_percent=round(mem_percent, 2),
            pids=stats.get("pids_stats", {}).get("current"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")


@router.post("/containers/{container_id}/exec", summary="在容器内执行命令")
async def exec_in_container(
    container_id: str,
    data: ExecRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = await docker_client.exec_in_container(container_id, data.command, data.tty)
        return {"exec_id": result, "message": "Command executed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to exec: {e}")


# ===== Images =====
@router.get("/images", response_model=list[ImageResponse], summary="获取镜像列表")
async def list_images(
    current_user: User = Depends(get_current_user),
):
    try:
        images = await docker_client.list_images()
        result = []
        for img in images:
            repo_tags = img.get("RepoTags", ["<none>:<none>"])
            size_mb = round(img.get("Size", 0) / 1024 / 1024, 2)
            result.append(ImageResponse(
                id=img.get("Id", "")[:19],
                repo_tags=repo_tags,
                size_mb=size_mb,
                created=img.get("Created"),
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list images: {e}")


@router.post("/images/pull", summary="拉取镜像")
async def pull_image(
    repository: str,
    tag: str = "latest",
    current_user: User = Depends(get_current_user),
):
    try:
        await docker_client.pull_image(repository, tag)
        return {"message": f"Image {repository}:{tag} pulled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pull image: {e}")


@router.delete("/images/{image_id}", summary="删除镜像")
async def remove_image(
    image_id: str,
    force: bool = False,
    current_user: User = Depends(get_current_user),
):
    try:
        await docker_client.remove_image(image_id, force=force)
        return {"message": f"Image {image_id} removed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove image: {e}")


# ===== Docker Info =====
@router.get("/info", summary="获取Docker信息")
async def docker_info(current_user: User = Depends(get_current_user)):
    try:
        info = await docker_client.docker_info()
        version = await docker_client.docker_version()
        return {"info": info, "version": version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Docker info: {e}")
