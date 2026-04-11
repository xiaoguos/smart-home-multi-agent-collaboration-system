"""
滴答清单相关工具
提供滴答清单任务、项目、标签等管理功能
"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
import sys
import os

# 添加父目录到路径以导入backend模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'app', 'backend-python'))

logger = logging.getLogger(__name__)


class DidaTaskArgs(BaseModel):
    """滴答清单任务操作参数"""
    system_user_id: int = Field(..., description="系统用户ID（固定为1000000001）")
    action: str = Field(..., description="操作类型：create_task, get_tasks, update_task, delete_task, complete_task")
    task_id: Optional[str] = Field(None, description="任务ID（更新/删除/完成操作必需）")
    title: Optional[str] = Field(None, description="任务标题（创建操作必需）")
    content: Optional[str] = Field(None, description="任务内容/描述")
    project_id: Optional[str] = Field(None, description="项目ID")


class DidaProjectArgs(BaseModel):
    """滴答清单项目操作参数"""
    system_user_id: int = Field(..., description="系统用户ID（固定为1000000001）")
    action: str = Field(..., description="操作类型：get_projects, create_project, update_project, delete_project")
    project_id: Optional[str] = Field(None, description="项目ID（更新/删除操作必需）")
    name: Optional[str] = Field(None, description="项目名称（创建操作必需）")
    color: Optional[str] = Field(None, description="项目颜色")


def _get_dida_credentials(system_user_id: int) -> Optional[Dict]:
    """
    获取用户的滴答清单凭证
    
    Args:
        system_user_id: 系统用户ID
        
    Returns:
        凭证字典，包含access_token等
    """
    try:
        from database import query, get_db_type, init_database
        
        # 确保数据库已初始化
        init_database(strict_mode=False)
        
        db_type = get_db_type()
        
        if db_type == "mysql":
            sql = """
                SELECT access_token, refresh_token, dida_username
                FROM dida_credentials 
                WHERE system_user_id = %s AND is_active = 1
                ORDER BY updated_at DESC 
                LIMIT 1
            """
        else:
            # StarRocks: 取最新记录
            sql = """
                SELECT access_token, refresh_token, dida_username
                FROM dida_credentials 
                WHERE system_user_id = %s
                ORDER BY updated_at DESC 
                LIMIT 1
            """
        
        result = query(sql, (system_user_id,))
        
        if result and len(result) > 0:
            return result[0]
        
        return None
        
    except Exception as e:
        logger.error(f"获取滴答清单凭证失败: {e}")
        return None


@tool("manage_dida_task", args_schema=DidaTaskArgs, description="管理滴答清单任务（创建、查询、更新、删除、完成）")
def manage_dida_task(
    system_user_id: int,
    action: str,
    task_id: Optional[str] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
    project_id: Optional[str] = None
) -> str:
    """
    管理滴答清单任务
    
    支持的操作：
    - create_task: 创建任务（需要title）
    - get_tasks: 获取任务列表（可选project_id过滤）
    - update_task: 更新任务（需要task_id和要更新的字段）
    - delete_task: 删除任务（需要task_id）
    - complete_task: 完成任务（需要task_id）
    
    Args:
        system_user_id: 系统用户ID
        action: 操作类型
        task_id: 任务ID
        title: 任务标题
        content: 任务内容
        project_id: 项目ID
        
    Returns:
        操作结果的JSON字符串
    """
    try:
        # 获取凭证
        credentials = _get_dida_credentials(system_user_id)
        if not credentials:
            return "❌ 未找到滴答清单绑定信息，请先在账户设置中绑定滴答清单账号"
        
        access_token = credentials["access_token"]
        
        # 导入MCP服务
        from mcp_clients.dida_mcp_service import get_dida_mcp_service
        import asyncio
        
        mcp_service = get_dida_mcp_service()
        
        # 根据操作类型调用不同的MCP方法
        if action == "create_task":
            if not title:
                return "❌ 创建任务需要提供标题（title）"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                mcp_service.create_task(access_token, title, content or "", project_id)
            )
            loop.close()
            
            # MCP直接返回任务对象字典，不是包装在{success: true}中
            if result and isinstance(result, dict) and result.get("id"):
                task_id = result.get("id")
                task_title = result.get("title", title)
                return f"✅ 任务创建成功：{task_title}\n📌 任务ID: {task_id}"
            else:
                return f"❌ 任务创建失败：{str(result) if result else '未知错误'}"
        
        elif action == "get_tasks":
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                mcp_service.get_tasks(access_token, project_id)
            )
            loop.close()
            
            # MCP直接返回任务列表，不是包装在字典中
            if result and isinstance(result, list):
                if not result:
                    return "📋 您目前没有任务"
                
                task_list = []
                for task in result:  # 显示所有任务，不截取
                    task_info = f"- {task.get('title', '未命名任务')}"
                    # 检查是否已完成
                    if task.get('status') == 2 or task.get('isCompleted'):
                        task_info = f"✅ {task_info}"
                    else:
                        task_info = f"📌 {task_info}"
                    
                    # 添加优先级和截止日期信息
                    priority = task.get('priority')
                    if priority == 5:
                        task_info += " [高优先级]"
                    elif priority == 3:
                        task_info += " [中优先级]"
                    
                    due_date = task.get('dueDate')
                    if due_date:
                        task_info += f" 📅 {due_date[:10]}"  # 只显示日期部分
                    
                    task_list.append(task_info)
                
                return f"📋 任务列表（共{len(result)}个）：\n" + "\n".join(task_list)
            else:
                return f"❌ 获取任务失败：{str(result)}"
        
        elif action == "update_task":
            if not task_id:
                return "❌ 更新任务需要提供任务ID（task_id）"
            
            update_data = {}
            if title:
                update_data["title"] = title
            if content:
                update_data["content"] = content
            if project_id:
                update_data["project_id"] = project_id
            
            if not update_data:
                return "❌ 更新任务需要至少提供一个要更新的字段"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                mcp_service.update_task(access_token, task_id, **update_data)
            )
            loop.close()
            
            if result and result.get("success"):
                return "✅ 任务更新成功"
            else:
                return f"❌ 任务更新失败：{result.get('message', '未知错误')}"
        
        elif action == "delete_task":
            if not task_id:
                return "❌ 删除任务需要提供任务ID（task_id）"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                mcp_service.delete_task(access_token, task_id)
            )
            loop.close()
            
            if result and result.get("success"):
                return "✅ 任务删除成功"
            else:
                return f"❌ 任务删除失败：{result.get('message', '未知错误')}"
        
        elif action == "complete_task":
            if not task_id:
                return "❌ 完成任务需要提供任务ID（task_id）"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                mcp_service.complete_task(access_token, task_id)
            )
            loop.close()
            
            if result and result.get("success"):
                return "✅ 任务已标记为完成"
            else:
                return f"❌ 标记任务完成失败：{result.get('message', '未知错误')}"
        
        else:
            return f"❌ 不支持的操作类型：{action}"
    
    except Exception as e:
        logger.error(f"管理滴答清单任务失败: {e}", exc_info=True)
        return f"❌ 操作失败：{str(e)}"


@tool("manage_dida_project", args_schema=DidaProjectArgs, description="管理滴答清单项目（查询、创建、更新、删除）")
def manage_dida_project(
    system_user_id: int,
    action: str,
    project_id: Optional[str] = None,
    name: Optional[str] = None,
    color: Optional[str] = None
) -> str:
    """
    管理滴答清单项目
    
    支持的操作：
    - get_projects: 获取项目列表
    - create_project: 创建项目（需要name）
    - update_project: 更新项目（需要project_id和要更新的字段）
    - delete_project: 删除项目（需要project_id）
    
    Args:
        system_user_id: 系统用户ID
        action: 操作类型
        project_id: 项目ID
        name: 项目名称
        color: 项目颜色
        
    Returns:
        操作结果的JSON字符串
    """
    try:
        # 获取凭证
        credentials = _get_dida_credentials(system_user_id)
        if not credentials:
            return "❌ 未找到滴答清单绑定信息，请先在账户设置中绑定滴答清单账号"
        
        access_token = credentials["access_token"]
        
        # 导入MCP服务
        from mcp_clients.dida_mcp_service import get_dida_mcp_service
        import asyncio
        
        mcp_service = get_dida_mcp_service()
        
        # 根据操作类型调用不同的MCP方法
        if action == "get_projects":
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                mcp_service.get_projects(access_token)
            )
            loop.close()
            
            # MCP直接返回项目列表，不是包装在字典中
            if result and isinstance(result, list):
                if not result:
                    return "📁 您目前没有项目"
                
                project_list = []
                for project in result:  # 显示所有项目，不截取
                    project_info = f"- {project.get('name', '未命名项目')} (ID: {project.get('id')})"
                    project_list.append(project_info)
                
                return f"📁 项目列表（共{len(result)}个）：\n" + "\n".join(project_list)
            else:
                return f"❌ 获取项目失败：{str(result)}"
        
        elif action == "create_project":
            if not name:
                return "❌ 创建项目需要提供名称（name）"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                mcp_service.create_project(access_token, name, color)
            )
            loop.close()
            
            if result and result.get("success"):
                return f"✅ 项目创建成功：{name}"
            else:
                return f"❌ 项目创建失败：{result.get('message', '未知错误')}"
        
        elif action == "update_project":
            if not project_id:
                return "❌ 更新项目需要提供项目ID（project_id）"
            
            update_data = {}
            if name:
                update_data["name"] = name
            if color:
                update_data["color"] = color
            
            if not update_data:
                return "❌ 更新项目需要至少提供一个要更新的字段"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                mcp_service.update_project(access_token, project_id, **update_data)
            )
            loop.close()
            
            if result and result.get("success"):
                return "✅ 项目更新成功"
            else:
                return f"❌ 项目更新失败：{result.get('message', '未知错误')}"
        
        elif action == "delete_project":
            if not project_id:
                return "❌ 删除项目需要提供项目ID（project_id）"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                mcp_service.delete_project(access_token, project_id)
            )
            loop.close()
            
            if result and result.get("success"):
                return "✅ 项目删除成功"
            else:
                return f"❌ 项目删除失败：{result.get('message', '未知错误')}"
        
        else:
            return f"❌ 不支持的操作类型：{action}"
    
    except Exception as e:
        logger.error(f"管理滴答清单项目失败: {e}", exc_info=True)
        return f"❌ 操作失败：{str(e)}"

