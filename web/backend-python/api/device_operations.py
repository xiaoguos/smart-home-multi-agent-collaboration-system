import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from services.device_operation_service import get_device_operation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/device_operations", tags=["设备操作"])


class OperationRecordRequest(BaseModel):
    """设备操作记录请求"""
    system_user_id: int = Field(..., description="系统用户ID")
    context_id: Optional[str] = Field(None, description="会话上下文ID")
    device_type: str = Field(..., description="设备类型")
    device_name: Optional[str] = Field(None, description="设备名称")
    action: str = Field(..., description="执行的操作")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="操作参数")
    success: bool = Field(..., description="操作是否成功")
    response: Optional[str] = Field(None, description="操作响应")
    error_message: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[int] = Field(None, description="执行时间（毫秒）")
    timestamp: Optional[str] = Field(None, description="时间戳")


class OperationQueryRequest(BaseModel):
    """操作记录查询请求"""
    system_user_id: int = Field(..., description="系统用户ID")
    limit: int = Field(50, description="返回记录数量", ge=1, le=500)
    device_type: Optional[str] = Field(None, description="设备类型过滤")


class StatisticsQueryRequest(BaseModel):
    """统计查询请求"""
    system_user_id: int = Field(..., description="系统用户ID")
    days: int = Field(7, description="统计天数", ge=1, le=90)


@router.post("/save")
async def save_operation_record(record: OperationRecordRequest):
    """
    保存设备操作记录
    
    由 Conductor Agent 在执行设备操作后调用，保存操作记录到数据库
    """
    try:
        service = get_device_operation_service()
        
        # 转换为字典
        operation_record = record.model_dump()
        
        # 保存记录
        success = service.save_operation_record(operation_record)
        
        if success:
            return {
                "success": True,
                "message": "操作记录已保存"
            }
        else:
            raise HTTPException(status_code=500, detail="保存操作记录失败")
    
    except Exception as e:
        logger.error(f"❌ 保存操作记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存操作记录失败: {str(e)}")


@router.post("/query")
async def query_operations(request: OperationQueryRequest):
    """
    查询操作记录
    
    根据用户ID和可选的设备类型查询操作记录
    """
    try:
        service = get_device_operation_service()
        
        records = service.get_recent_operations(
            system_user_id=request.system_user_id,
            limit=request.limit,
            device_type=request.device_type
        )
        
        return {
            "success": True,
            "count": len(records),
            "records": records
        }
    
    except Exception as e:
        logger.error(f"❌ 查询操作记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询操作记录失败: {str(e)}")


@router.post("/statistics")
async def get_statistics(request: StatisticsQueryRequest):
    """
    获取操作统计信息
    
    统计指定天数内的设备操作情况
    """
    try:
        service = get_device_operation_service()
        
        statistics = service.get_operation_statistics(
            system_user_id=request.system_user_id,
            days=request.days
        )
        
        if "error" in statistics:
            raise HTTPException(status_code=500, detail=statistics["error"])
        
        return {
            "success": True,
            "statistics": statistics
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取操作统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取操作统计失败: {str(e)}")

