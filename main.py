from fastapi import FastAPI
# 导入子路由
from routers.auxiliary import auxiliary_router

app = FastAPI(
    title="CloudPivot Server",
    version="1.0",
    description="CloudPivot Server API",
)

# 注册子路由
app.include_router(auxiliary_router)
