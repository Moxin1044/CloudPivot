from __future__ import annotations

from typing import Optional, List, Dict, Any
from aiodocker import Docker
from app.config import settings
from app.core.logger import logger


class DockerClient:
    """Async Docker client wrapper for container management."""

    def __init__(self, docker_host: Optional[str] = None):
        self._docker_host = docker_host or settings.DOCKER_HOST
        self._client: Optional[Docker] = None

    async def _get_client(self) -> Docker:
        if self._client is None:
            self._client = Docker(self._docker_host)
        return self._client

    async def close(self):
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None

    # Container operations
    async def list_containers(self, all: bool = False) -> List[Dict[str, Any]]:
        client = await self._get_client()
        return await client.containers.list(all=all)

    async def get_container(self, container_id: str) -> Dict[str, Any]:
        client = await self._get_client()
        container = client.containers.container(container_id)
        return await container.show()

    async def start_container(self, container_id: str) -> bool:
        client = await self._get_client()
        container = client.containers.container(container_id)
        await container.start()
        return True

    async def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        client = await self._get_client()
        container = client.containers.container(container_id)
        await container.stop(t=timeout)
        return True

    async def restart_container(self, container_id: str, timeout: int = 10) -> bool:
        client = await self._get_client()
        container = client.containers.container(container_id)
        await container.restart(t=timeout)
        return True

    async def remove_container(self, container_id: str, force: bool = False) -> bool:
        client = await self._get_client()
        container = client.containers.container(container_id)
        await container.delete(force=force)
        return True

    async def container_logs(
        self, container_id: str, tail: int = 100, follow: bool = False
    ) -> str:
        client = await self._get_client()
        container = client.containers.container(container_id)
        logs = await container.log(stdout=True, stderr=True, tail=tail, follow=follow)
        return logs

    async def container_stats(self, container_id: str) -> Dict[str, Any]:
        client = await self._get_client()
        container = client.containers.container(container_id)
        stats = await container.stats(stream=False)
        return stats

    async def exec_in_container(
        self, container_id: str, command: str, tty: bool = True
    ) -> tuple:
        client = await self._get_client()
        container = client.containers.container(container_id)
        exec_id = await container.exec(
            Cmd=["/bin/sh", "-c", command],
            AttachStdout=True,
            AttachStderr=True,
            Tty=tty,
        )
        return exec_id

    # Image operations
    async def list_images(self) -> List[Dict[str, Any]]:
        client = await self._get_client()
        return await client.images.list()

    async def pull_image(self, repository: str, tag: str = "latest") -> Dict[str, Any]:
        client = await self._get_client()
        return await client.images.pull(repository, tag=tag)

    async def remove_image(self, image_id: str, force: bool = False) -> bool:
        client = await self._get_client()
        await client.images.delete(image_id, force=force)
        return True

    # Docker info
    async def docker_info(self) -> Dict[str, Any]:
        client = await self._get_client()
        return await client.system.info()

    async def docker_version(self) -> Dict[str, Any]:
        client = await self._get_client()
        return await client.version()


docker_client = DockerClient()
