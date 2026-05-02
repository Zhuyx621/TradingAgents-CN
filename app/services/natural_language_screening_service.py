"""
自然语言股票筛选服务
将自然语言查询转换为筛选条件，执行筛选，并支持批量添加自选和分析
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

# 自然语言到筛选条件的提示词模板
SCREENING_PROMPT_TEMPLATE = """
你是一个专业的股票筛选分析师。请将用户的自然语言查询转换为结构化的筛选条件。

用户查询：{query}

请按照以下JSON格式输出筛选条件：
{{
  "conditions": [
    {{
      "field": "字段名",
      "operator": "操作符",
      "value": 值
    }}
  ],
  "order_by": [
    {{
      "field": "排序字段",
      "direction": "asc|desc"
    }}
  ],
  "limit": 数量,
  "description": "筛选条件描述"
}}

可用字段：
- basic: code(代码), name(名称), industry(行业), area(地区), market(市场)
- market_value: total_mv(总市值亿), circ_mv(流通市值亿)
- financial: pe(市盈率), pb(市净率), pe_ttm(市盈率TTM), pb_mrq(市净率MRQ), roe(净资产收益率%)
- trading: turnover_rate(换手率%), volume_ratio(量比)
- price: close(收盘价), pct_chg(涨跌幅%), amount(成交额万)
- technical: ma20(20日均线), rsi14(RSI14), kdj_k(KDJ-K), kdj_d(KDJ-D), kdj_j(KDJ-J), dif(MACD-DIF), dea(MACD-DEA), macd_hist(MACD柱)

可用操作符：
- 比较: >, <, >=, <=, ==
- between: 范围查询，value为数组如 [10, 100]
- in: 包含查询，value为数组

示例：
用户查询："找出市值在50到200亿之间，市盈率低于30的科技股"
输出：
{{
  "conditions": [
    {{"field": "total_mv", "operator": "between", "value": [50, 200]}},
    {{"field": "pe", "operator": "<", "value": 30}},
    {{"field": "industry", "operator": "in", "value": ["电子", "计算机", "通信", "半导体"]}}
  ],
  "order_by": [{{"field": "pe", "direction": "asc"}}],
  "limit": 20,
  "description": "市值50-200亿，PE<30的科技股"
}}

请确保输出是有效的JSON格式，不要包含其他内容。
"""


class NaturalLanguageScreeningService:
    """自然语言股票筛选服务"""
    
    def __init__(self):
        self._llm_client = None
    
    def _get_llm_client(self) -> Any:
        """获取LLM客户端"""
        if self._llm_client is None:
            provider = DEFAULT_CONFIG.get("llm_provider", "openai")
            model = DEFAULT_CONFIG.get("quick_think_llm", "gpt-4o-mini")
            base_url = DEFAULT_CONFIG.get("backend_url")
            
            try:
                self._llm_client = create_llm_client(provider, model, base_url)
                logger.info(f"✅ 初始化LLM客户端成功: {provider}/{model}")
            except Exception as e:
                logger.warning(f"⚠️ 使用默认LLM客户端失败，尝试使用deepseek: {e}")
                try:
                    self._llm_client = create_llm_client("deepseek", "deepseek-chat", "https://api.deepseek.com")
                    logger.info("✅ 初始化DeepSeek客户端成功")
                except Exception as e2:
                    logger.error(f"❌ 初始化LLM客户端失败: {e2}")
                    raise
        
        return self._llm_client
    
    def parse_natural_language(self, query: str) -> Dict[str, Any]:
        """
        将自然语言查询转换为筛选条件
        
        Args:
            query: 用户输入的自然语言查询
            
        Returns:
            包含conditions, order_by, limit, description的字典
        """
        logger.info(f"🔍 开始解析自然语言查询: {query}")
        
        prompt = SCREENING_PROMPT_TEMPLATE.format(query=query)
        
        try:
            llm = self._get_llm_client().get_llm()
            response = llm.invoke(prompt)
            
            # 提取响应内容
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, dict) and 'content' in response:
                content = response['content']
            else:
                content = str(response)
            
            # 清理响应（移除可能的markdown代码块标记）
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # 解析JSON
            result = json.loads(content)
            logger.info(f"✅ 解析成功: {result}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {e}, 响应内容: {content}")
            raise ValueError(f"解析筛选条件失败，请尝试重新输入")
        except Exception as e:
            logger.error(f"❌ 自然语言解析失败: {e}")
            raise ValueError(f"解析失败: {str(e)}")
    
    async def screen_stocks(
        self,
        query: str,
        user_id: str,
        add_to_favorites: bool = True,
        run_analysis: bool = True,
        analysis_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        完整的自然语言筛选流程：
        1. 解析自然语言 -> 筛选条件
        2. 执行筛选
        3. 可选：添加到自选
        4. 可选：批量分析
        
        Args:
            query: 用户输入的自然语言查询
            user_id: 用户ID
            add_to_favorites: 是否添加到自选
            run_analysis: 是否执行分析
            analysis_params: 分析参数
            
        Returns:
            包含筛选结果、自选状态、分析任务的字典
        """
        logger.info(f"🚀 开始自然语言筛选流程: query={query}, user_id={user_id}")
        
        # 1. 解析自然语言
        parsed_result = self.parse_natural_language(query)
        conditions = parsed_result.get("conditions", [])
        order_by = parsed_result.get("order_by", [])
        limit = parsed_result.get("limit", 20)
        description = parsed_result.get("description", query)
        
        # 2. 执行筛选
        from app.services.enhanced_screening_service import get_enhanced_screening_service
        screening_service = get_enhanced_screening_service()
        
        # 构建筛选请求
        screening_result = await screening_service.screen(
            conditions=conditions,
            order_by=order_by,
            limit=limit
        )
        
        screened_stocks = screening_result.get("items", [])
        total = screening_result.get("total", 0)
        
        logger.info(f"📊 筛选完成: 共 {total} 只股票符合条件")
        
        # 3. 添加到自选
        added_stocks = []
        if add_to_favorites and screened_stocks:
            from app.services.favorites_service import FavoritesService
            fav_service = FavoritesService()
            
            for stock in screened_stocks:
                try:
                    stock_code = stock.get("code")
                    stock_name = stock.get("name", "")
                    
                    if stock_code:
                        await fav_service.add_favorite(
                            user_id=user_id,
                            stock_code=stock_code,
                            stock_name=stock_name,
                            market=stock.get("market", "A股"),
                            notes=f"自然语言筛选: {description}"
                        )
                        added_stocks.append(stock_code)
                        logger.info(f"⭐ 添加自选: {stock_code}")
                except Exception as e:
                    logger.warning(f"⚠️ 添加自选失败 {stock.get('code')}: {e}")
        
        # 4. 批量分析
        analysis_tasks = []
        if run_analysis and screened_stocks:
            from app.services.analysis_service import AnalysisService
            from app.models.analysis import SingleAnalysisRequest, AnalysisParameters
            
            analysis_service = AnalysisService()
            
            for stock in screened_stocks[:5]:  # 最多分析5只
                try:
                    stock_code = stock.get("code")
                    if stock_code:
                        request = SingleAnalysisRequest(
                            symbol=stock_code,
                            parameters=AnalysisParameters(
                                research_depth=analysis_params.get("research_depth", "标准") if analysis_params else "标准",
                                selected_analysts=analysis_params.get("analysts", ["market", "fundamentals"]) if analysis_params else ["market", "fundamentals"]
                            )
                        )
                        
                        # 创建分析任务（异步执行）
                        result = await analysis_service.create_analysis_task(user_id, request)
                        analysis_tasks.append({
                            "stock_code": stock_code,
                            "stock_name": stock.get("name"),
                            "task_id": result.get("task_id")
                        })
                        logger.info(f"🔬 创建分析任务: {stock_code} -> {result.get('task_id')}")
                except Exception as e:
                    logger.warning(f"⚠️ 创建分析任务失败 {stock.get('code')}: {e}")
        
        return {
            "success": True,
            "description": description,
            "total_found": total,
            "screened_stocks": screened_stocks,
            "added_to_favorites": added_stocks,
            "analysis_tasks": analysis_tasks,
            "conditions": conditions,
            "order_by": order_by,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
