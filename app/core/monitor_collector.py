import asyncio
from datetime import datetime, timezone
from typing import Optional

from app.database import async_session
from app.models.host import Host
from app.models.monitor import HostMetric
from app.core.ssh import ssh_pool
from app.core.logger import logger
from sqlalchemy import select


async def _collect_host_metrics(host: Host) -> Optional[dict]:
    """Collect metrics from a host via SSH. Returns metric dict or None."""
    try:
        conn = await ssh_pool.get_connection(
            host=host.ip_address,
            port=host.port,
            username=host.username,
            password=host.password_encrypted or None,
            private_key=host.private_key_encrypted or None,
            timeout=10,
        )

        # CPU usage
        cpu_cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"
        cpu_result = await conn.run(cpu_cmd, check=False)
        cpu_percent = _parse_float(cpu_result.stdout)

        # Memory usage
        mem_cmd = "free | grep Mem | awk '{printf \"%.2f\", $3/$2 * 100.0}'"
        mem_result = await conn.run(mem_cmd, check=False)
        memory_percent = _parse_float(mem_result.stdout)

        mem_total_cmd = "free -g | grep Mem | awk '{print $2}'"
        mem_total_result = await conn.run(mem_total_cmd, check=False)
        memory_total_gb = _parse_float(mem_total_result.stdout)

        mem_used_cmd = "free -g | grep Mem | awk '{print $3}'"
        mem_used_result = await conn.run(mem_used_cmd, check=False)
        memory_used_gb = _parse_float(mem_used_result.stdout)

        # Disk usage
        disk_cmd = "df -h / | tail -1 | awk '{print $5}' | cut -d'%' -f1"
        disk_result = await conn.run(disk_cmd, check=False)
        disk_percent = _parse_float(disk_result.stdout)

        disk_total_cmd = "df -BG / | tail -1 | awk '{print $2}' | sed 's/G//g'"
        disk_total_result = await conn.run(disk_total_cmd, check=False)
        disk_total_gb = _parse_float(disk_total_result.stdout)

        disk_used_cmd = "df -BG / | tail -1 | awk '{print $3}' | sed 's/G//g'"
        disk_used_result = await conn.run(disk_used_cmd, check=False)
        disk_used_gb = _parse_float(disk_used_result.stdout)

        # Network rate (KB/s) — sample twice with 1s interval
        network_in_kbps, network_out_kbps = await _sample_network_rate(conn)

        # Load average
        load_cmd = "cat /proc/loadavg | awk '{print $1,$2,$3}'"
        load_result = await conn.run(load_cmd, check=False)
        load_1min, load_5min, load_15min = _parse_load(load_result.stdout)

        # OS info
        os_cmd = "cat /etc/os-release | grep -E '^NAME=|^VERSION_ID=' | cut -d= -f2 | tr -d '\"'"
        os_result = await conn.run(os_cmd, check=False)
        os_name, os_version = _parse_os(os_result.stdout)

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_used_gb": memory_used_gb,
            "memory_total_gb": memory_total_gb,
            "disk_percent": disk_percent,
            "disk_used_gb": disk_used_gb,
            "disk_total_gb": disk_total_gb,
            "network_in_kbps": network_in_kbps,
            "network_out_kbps": network_out_kbps,
            "load_1min": load_1min,
            "load_5min": load_5min,
            "load_15min": load_15min,
            "os_name": os_name,
            "os_version": os_version,
        }
    except Exception as e:
        logger.warning(f"Failed to collect metrics from host {host.id} ({host.ip_address}): {e}")
        return None


def _parse_float(val: Optional[str]) -> Optional[float]:
    if not val:
        return None
    try:
        return float(val.strip())
    except (ValueError, TypeError):
        return None


async def _sample_network_rate(conn) -> tuple:
    """Sample /proc/net/dev twice with 1s interval and compute rate in KB/s."""
    import time

    async def _read_net_dev():
        res = await conn.run(
            "cat /proc/net/dev | grep -E 'eth0|ens33|ens160|enp|wlan' | head -1 | awk '{print $2,$10}'",
            check=False,
        )
        return res.stdout

    try:
        first = _read_net_dev()
        t1 = time.time()
        await asyncio.sleep(1)
        second = _read_net_dev()
        t2 = time.time()

        out1 = (await first).strip().split()
        out2 = (await second).strip().split()

        if len(out1) >= 2 and len(out2) >= 2:
            in1 = float(out1[0])
            out1_b = float(out1[1])
            in2 = float(out2[0])
            out2_b = float(out2[1])
            dt = t2 - t1
            if dt > 0:
                in_rate = (in2 - in1) / 1024 / dt   # KB/s
                out_rate = (out2_b - out1_b) / 1024 / dt
                return round(in_rate, 2), round(out_rate, 2)
    except Exception:
        pass
    return None, None


def _parse_load(val: Optional[str]) -> tuple:
    if not val:
        return None, None, None
    parts = val.strip().split()
    if len(parts) >= 3:
        try:
            return float(parts[0]), float(parts[1]), float(parts[2])
        except (ValueError, TypeError):
            pass
    return None, None, None


def _parse_os(val: Optional[str]) -> tuple:
    if not val:
        return None, None
    lines = val.strip().split('\n')
    name = lines[0].strip() if len(lines) > 0 else None
    version = lines[1].strip() if len(lines) > 1 else None
    return name, version


async def collect_all_hosts_metrics():
    """Collect metrics from all hosts and store in database."""
    async with async_session() as db:
        result = await db.execute(select(Host))
        hosts = result.scalars().all()

        for host in hosts:
            metrics = await _collect_host_metrics(host)
            if metrics:
                metric = HostMetric(
                    host_id=host.id,
                    cpu_percent=metrics.get("cpu_percent"),
                    memory_percent=metrics.get("memory_percent"),
                    memory_used_gb=metrics.get("memory_used_gb"),
                    memory_total_gb=metrics.get("memory_total_gb"),
                    disk_percent=metrics.get("disk_percent"),
                    disk_used_gb=metrics.get("disk_used_gb"),
                    disk_total_gb=metrics.get("disk_total_gb"),
                    network_in_kbps=metrics.get("network_in_kbps"),
                    network_out_kbps=metrics.get("network_out_kbps"),
                    load_1min=metrics.get("load_1min"),
                    load_5min=metrics.get("load_5min"),
                    load_15min=metrics.get("load_15min"),
                )
                db.add(metric)

                # Update host OS info if available
                if metrics.get("os_name"):
                    host.os_name = metrics["os_name"]
                if metrics.get("os_version"):
                    host.os_version = metrics["os_version"]
                host.status = "online"
            else:
                host.status = "offline"

        await db.commit()
        logger.info(f"Metrics collected for {len(hosts)} hosts")


async def monitor_collector_loop(interval_seconds: int = 60):
    """Background loop to collect metrics periodically."""
    while True:
        try:
            await collect_all_hosts_metrics()
        except Exception as e:
            logger.error(f"Monitor collector error: {e}")
        await asyncio.sleep(interval_seconds)
