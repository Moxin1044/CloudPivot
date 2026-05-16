"""
SSH登录日志采集器
从目标主机的 /var/log/auth.log (Debian/Ubuntu) 或 /var/log/secure (RHEL/CentOS)
解析SSH登录记录并入库
"""
import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import async_session
from app.models.host import Host
from app.models.ssh_login_log import SSHLoginLog
from app.core.ssh import ssh_pool
from app.core.logger import logger


# auth.log / secure 中的SSH登录相关正则
# Accepted publickey for root from 192.168.1.1 port 12345 ssh2: RSA SHA256:xxx
ACCEPTED_RE = re.compile(
    r'^(\w+\s+\d+\s+\d+:\d+:\d+)\s+\S+\s+sshd\[\d+\]:\s+'
    r'Accepted\s+(\w+)\s+for\s+(\S+)\s+from\s+(\S+)\s+port\s+(\d+)',
    re.MULTILINE
)

# Failed password for root from 192.168.1.1 port 12345 ssh2
FAILED_RE = re.compile(
    r'^(\w+\s+\d+\s+\d+:\d+:\d+)\s+\S+\s+sshd\[\d+\]:\s+'
    r'Failed\s+(\w+)\s+for\s+(?:invalid\s+user\s+)?(\S+)\s+from\s+(\S+)\s+port\s+(\d+)',
    re.MULTILINE
)

# Connection closed by authenticating user root 192.168.1.1 port 12345 [preauth]
# 用于计算会话时长（简化处理）

# Message of the day / 系统标识，用于判断日志文件路径
LOG_PATH_DEBIAN = "/var/log/auth.log"
LOG_PATH_RHEL = "/var/log/secure"


def _parse_syslog_timestamp(ts_str: str, year: int = None) -> Optional[datetime]:
    """解析 syslog 格式时间戳，如 'May 16 14:30:00'"""
    if year is None:
        year = datetime.now(timezone.utc).year
    try:
        dt = datetime.strptime(f"{year} {ts_str}", "%Y %b %d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


async def _detect_log_path(conn) -> str:
    """检测远程主机的日志文件路径"""
    result = await conn.run(f"test -f {LOG_PATH_DEBIAN} && echo {LOG_PATH_DEBIAN} || echo {LOG_PATH_RHEL}", check=False)
    path = result.stdout.strip()
    return path if path else LOG_PATH_RHEL


async def _read_remote_log(conn, log_path: str, lines: int = 2000) -> str:
    """读取远程主机日志最后N行"""
    result = await conn.run(f"tail -n {lines} {log_path} 2>/dev/null || echo ''", check=False)
    return result.stdout or ""


async def collect_host_ssh_logs(host: Host, db: AsyncSession) -> int:
    """
    采集单个主机的SSH登录日志
    返回新插入的记录数
    """
    from app.core.security import decrypt_data

    password = None
    private_key = None
    if host.password_encrypted:
        password = decrypt_data(host.password_encrypted)
    if host.private_key_encrypted:
        private_key = decrypt_data(host.private_key_encrypted)

    try:
        conn = await ssh_pool.get_connection(
            host=host.ip_address,
            port=host.port,
            username=host.username,
            password=password,
            private_key=private_key,
            timeout=15,
        )
    except Exception as e:
        logger.warning(f"SSH log collector: cannot connect to host {host.name}({host.ip_address}): {e}")
        return 0

    try:
        log_path = await _detect_log_path(conn)
        raw_logs = await _read_remote_log(conn, log_path, lines=2000)
        if not raw_logs.strip():
            return 0

        # 查询该主机已入库的最新时间，避免重复
        result = await db.execute(
            select(func.max(SSHLoginLog.login_at)).where(SSHLoginLog.host_id == host.id)
        )
        latest_login_at = result.scalar()

        records: List[SSHLoginLog] = []
        year = datetime.now(timezone.utc).year

        for match in ACCEPTED_RE.finditer(raw_logs):
            ts_str, auth_method, username, ip, port = match.groups()
            login_at = _parse_syslog_timestamp(ts_str, year)
            if not login_at:
                continue
            # 跨年处理：如果解析出的时间比最新记录晚很多，可能是去年
            if latest_login_at and login_at > latest_login_at + timedelta(days=1):
                login_at = login_at.replace(year=year - 1)
            if latest_login_at and login_at <= latest_login_at:
                continue

            records.append(SSHLoginLog(
                host_id=host.id,
                username=username,
                login_ip=ip,
                login_port=int(port),
                auth_method=auth_method,
                is_success=True,
                login_at=login_at,
                raw_log=match.group(0),
            ))

        for match in FAILED_RE.finditer(raw_logs):
            ts_str, auth_method, username, ip, port = match.groups()
            login_at = _parse_syslog_timestamp(ts_str, year)
            if not login_at:
                continue
            if latest_login_at and login_at > latest_login_at + timedelta(days=1):
                login_at = login_at.replace(year=year - 1)
            if latest_login_at and login_at <= latest_login_at:
                continue

            records.append(SSHLoginLog(
                host_id=host.id,
                username=username,
                login_ip=ip,
                login_port=int(port),
                auth_method=auth_method,
                is_success=False,
                fail_reason="Authentication failure",
                login_at=login_at,
                raw_log=match.group(0),
            ))

        if records:
            # 去重：同一秒同一IP同一用户只保留一条
            seen = set()
            unique_records = []
            for r in records:
                key = (r.host_id, r.username, r.login_ip, r.login_at.replace(microsecond=0))
                if key not in seen:
                    seen.add(key)
                    unique_records.append(r)
            records = unique_records

            db.add_all(records)
            await db.commit()
            logger.info(f"SSH log collector: inserted {len(records)} records for host {host.name}")
            return len(records)
        return 0
    except Exception as e:
        logger.error(f"SSH log collector: error collecting logs from {host.name}: {e}")
        await db.rollback()
        return 0
    finally:
        await ssh_pool.release_connection(host.ip_address, host.port, host.username)


async def analyze_ssh_logs(db: AsyncSession, host_id: Optional[int] = None, hours: int = 24):
    """
    对SSH登录日志进行分析，标记异常行为：
    - 暴力破解：同一IP在短时间内大量失败
    - 新IP登录：该IP历史上首次出现
    """
    from sqlalchemy import and_

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = select(SSHLoginLog).where(
        and_(SSHLoginLog.login_at >= since, SSHLoginLog.is_analyzed == False)
    )
    if host_id:
        query = query.where(SSHLoginLog.host_id == host_id)
    result = await db.execute(query)
    logs = result.scalars().all()
    if not logs:
        return 0

    # 统计每个IP的失败次数（用于暴力破解检测）
    ip_fail_counts = {}
    for log in logs:
        if not log.is_success:
            ip_fail_counts.setdefault(log.login_ip, 0)
            ip_fail_counts[log.login_ip] += 1

    # 检测历史上出现过的IP
    all_ips_result = await db.execute(select(SSHLoginLog.login_ip).distinct())
    known_ips = {ip for ip in all_ips_result.scalars().all() if ip}

    updated = 0
    for log in logs:
        changed = False
        # 暴力破解：同一IP失败>=5次
        if not log.is_success and ip_fail_counts.get(log.login_ip, 0) >= 5:
            log.is_brute_force = True
            log.risk_level = "danger"
            changed = True
        # 新IP
        if log.login_ip and log.login_ip not in known_ips:
            log.is_new_ip = True
            if log.risk_level == "safe":
                log.risk_level = "warning"
            changed = True
        log.is_analyzed = True
        if changed:
            updated += 1

    await db.commit()
    return updated


async def ssh_log_collector_loop(interval_seconds: int = 300):
    """后台任务：定期采集所有主机的SSH登录日志并分析"""
    while True:
        try:
            async with async_session() as db:
                result = await db.execute(select(Host))
                hosts = result.scalars().all()
                total = 0
                for host in hosts:
                    try:
                        n = await collect_host_ssh_logs(host, db)
                        total += n
                    except Exception as e:
                        logger.error(f"SSH log collector loop: host {host.name} error: {e}")
                if total > 0:
                    analyzed = await analyze_ssh_logs(db)
                    logger.info(f"SSH log collector: analyzed {analyzed} records")
        except Exception as e:
            logger.error(f"SSH log collector loop error: {e}")
        await asyncio.sleep(interval_seconds)
