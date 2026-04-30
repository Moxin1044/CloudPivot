from fastapi import APIRouter, Request
from pydantic import BaseModel


# 功能模块
import time

# 辅助模块
auxiliary_router = APIRouter(prefix="/auxiliary")

class DelayRequest(BaseModel):
    client_timestamp: int  # 毫秒级时间戳

@auxiliary_router.get("/get_server_timestamp", summary="获取服务器时间戳（毫秒级）")
async def get_server_timestamp():
    """
    获取服务器时间戳（毫秒级）
    """
    server_ts = int(time.time() * 1000)
    return {
        "server_timestamp_ms": server_ts,  # 标准毫秒时间戳
        "status": "success"
    }


@auxiliary_router.post("/get_delay", summary="获取延迟")
async def get_delay(request: DelayRequest):
    """
    获取延迟（POST接口）
    :param request: 客户端请求体，包含时间戳
    :return: 延迟时间（毫秒）
    """
    server_timestamp = int(time.time() * 1000)
    # 从模型中获取参数
    time_diff = server_timestamp - request.client_timestamp

    return {
        "client_timestamp_ms": request.client_timestamp,
        "server_timestamp_ms": server_timestamp,
        "time_diff_ms": time_diff,
        "status": "success"
    }


@auxiliary_router.get("/get_ip", summary="单独获取请求者IP地址")
async def get_ip(request: Request):
    """
    独立接口：仅获取请求客户端的真实IP地址
    兼容Nginx/反向代理环境
    """
    # 优先获取代理传递的真实IP（服务器部署必备）
    client_ip = request.headers.get("X-Forwarded-For")
    if not client_ip:
        # 无代理时，直接获取客户端IP
        client_ip = request.client.host

    return {
        "status": "success",
        "client_ip": client_ip.strip()  # 客户端真实IP
    }