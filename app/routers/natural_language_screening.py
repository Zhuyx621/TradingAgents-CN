"""
自然语言股票筛选API路由
支持一句话筛选股票，并可选添加到自选和批量分析
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.routers.auth_db import get_current_user
from app.services.natural_language_screening_service import NaturalLanguageScreeningService

router = APIRouter(tags=["natural_language_screening"])
logger = logging.getLogger("webapi")

# 请求模型
class NaturalLanguageScreeningRequest(BaseModel):
    """自然语言筛选请求"""
    query: str = Field(..., description="自然语言查询，例如：'找出市值在50到200亿之间，市盈率低于30的科技股'")
    add_to_favorites: bool = Field(True, description="是否将筛选结果添加到自选")
    run_analysis: bool = Field(True, description="是否对筛选结果进行分析")
    analysis_params: Optional[Dict[str, Any]] = Field(None, description="分析参数，如 research_depth, analysts")

# 响应模型
class ScreeningResultItem(BaseModel):
    """筛选结果项"""
    code: str
    name: str
    industry: Optional[str] = None
    area: Optional[str] = None
    market: Optional[str] = None
    close: Optional[float] = None
    pct_chg: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    total_mv: Optional[float] = None

class AnalysisTaskItem(BaseModel):
    """分析任务项"""
    stock_code: str
    stock_name: Optional[str] = None
    task_id: str

class NaturalLanguageScreeningResponse(BaseModel):
    """自然语言筛选响应"""
    success: bool
    description: str
    total_found: int
    screened_stocks: List[ScreeningResultItem]
    added_to_favorites: List[str]
    analysis_tasks: List[AnalysisTaskItem]
    conditions: List[Dict[str, Any]]
    order_by: List[Dict[str, str]]
    limit: int
    timestamp: str

# 服务实例
_nl_service = NaturalLanguageScreeningService()


@router.post("/screen", response_model=NaturalLanguageScreeningResponse)
async def screen_by_natural_language(
    request: NaturalLanguageScreeningRequest,
    user: dict = Depends(get_current_user)
):
    """
    一句话筛选股票
    
    使用自然语言查询筛选股票，并可选：
    - 将符合条件的股票添加到自选
    - 对筛选结果进行批量分析
    
    请求示例：
    {
        "query": "找出市值在50到200亿之间，市盈率低于30的科技股",
        "add_to_favorites": true,
        "run_analysis": true,
        "analysis_params": {
            "research_depth": "标准",
            "analysts": ["market", "fundamentals"]
        }
    }
    
    支持的查询示例：
    - "找出市盈率低于20的低估值股票"
    - "市值在100-500亿之间的医药股"
    - "近一周涨幅超过10%的股票"
    - "ROE大于15%的优质公司"
    """
    try:
        logger.info(f"🎯 收到自然语言筛选请求: {request.query}")
        logger.info(f"👤 用户: {user.get('username')}")
        
        # 调用自然语言筛选服务
        result = await _nl_service.screen_stocks(
            query=request.query,
            user_id=user["id"],
            add_to_favorites=request.add_to_favorites,
            run_analysis=request.run_analysis,
            analysis_params=request.analysis_params
        )
        
        logger.info(f"✅ 自然语言筛选完成: 找到 {result['total_found']} 只股票")
        
        return result
        
    except ValueError as e:
        logger.error(f"❌ 筛选参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ 自然语言筛选失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"筛选失败: {str(e)}")


@router.post("/parse")
async def parse_query(
    query: str = Query(..., description="自然语言查询"),
    user: dict = Depends(get_current_user)
):
    """
    仅解析自然语言查询为筛选条件（不执行筛选）
    
    用于预览筛选条件，帮助用户确认查询意图
    """
    try:
        logger.info(f"🔍 解析自然语言查询: {query}")
        
        result = _nl_service.parse_natural_language(query)
        
        return {
            "success": True,
            "description": result.get("description"),
            "conditions": result.get("conditions", []),
            "order_by": result.get("order_by", []),
            "limit": result.get("limit", 20)
        }
        
    except ValueError as e:
        logger.error(f"❌ 解析失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ 解析异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")
