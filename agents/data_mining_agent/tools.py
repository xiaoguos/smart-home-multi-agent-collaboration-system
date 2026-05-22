from langchain_core.tools import tool
import json
import os
from pydantic import BaseModel, Field
import logging
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
import pymysql
from pymysql.cursors import DictCursor

# 配置日志
logger = logging.getLogger(__name__)


def get_db_config() -> dict:
    """从环境变量读取数据库配置（.env 由 agent.py 提前加载）。"""
    return {
        "host": os.getenv("DATABASE_HOST", "localhost"),
        "port": int(os.getenv("DATABASE_PORT", "9030")),
        "user": os.getenv("DATABASE_USER", "root"),
        "password": os.getenv("DATABASE_PASSWORD", ""),
        "database": os.getenv("DATABASE_NAME", "moss_ai"),
        "charset": os.getenv("DATABASE_CHARSET", "utf8mb4"),
    }


def convert_numpy_types(obj):
    """
    递归转换 numpy 类型为 Python 原生类型，使其可以被 JSON 序列化
    
    Args:
        obj: 任意对象
        
    Returns:
        转换后的对象
    """
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


def get_db_connection():
    """获取数据库连接"""
    try:
        db_config = get_db_config()
        connection = pymysql.connect(
            host=db_config.get("host", "localhost"),
            port=db_config.get("port", 9030),
            user=db_config.get("user", "root"),
            password=db_config.get("password", ""),
            database=db_config.get("database", "moss_ai"),
            charset=db_config.get("charset", "utf8mb4"),
            cursorclass=DictCursor,
            autocommit=True,
            connect_timeout=10,
        )
        return connection
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return None


def extract_time_features(dt: datetime) -> Dict[str, float]:
    """
    从日期时间中提取特征用于聚类

    Args:
        dt: 日期时间对象

    Returns:
        包含时间特征的字典
    """
    return {
        "hour": dt.hour,
        "minute": dt.minute,
        "day_of_week": dt.weekday(),  # 0=周一, 6=周日
        "is_weekend": 1 if dt.weekday() >= 5 else 0,
        "is_morning": 1 if 6 <= dt.hour < 12 else 0,  # 早上 6-12点
        "is_afternoon": 1 if 12 <= dt.hour < 18 else 0,  # 下午 12-18点
        "is_evening": 1 if 18 <= dt.hour < 22 else 0,  # 晚上 18-22点
        "is_night": 1 if dt.hour >= 22 or dt.hour < 6 else 0,  # 夜晚 22-6点
    }


def prepare_clustering_data(operations: List[Dict[str, Any]]) -> tuple:
    """
    准备用于聚类的数据

    Args:
        operations: 设备操作记录列表

    Returns:
        (特征矩阵, 原始数据列表, 特征名称列表)
    """
    features_list = []
    data_records = []

    for op in operations:
        try:
            created_at = op.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            # 提取时间特征
            time_features = extract_time_features(created_at)

            # 设备类型编码（简单的one-hot编码）
            device_type = op.get("device_type", "")
            device_features = {
                "is_ac": 1 if device_type == "air_conditioner" else 0,
                "is_cleaner": 1 if device_type == "air_cleaner" else 0,
                "is_lamp": 1 if device_type == "bedside_lamp" else 0,
            }

            # 合并所有特征
            all_features = {**time_features, **device_features}
            features_list.append(list(all_features.values()))

            # 保存原始数据记录
            data_records.append(
                {
                    "operation": op,
                    "time_features": time_features,
                    "device_type": device_type,
                }
            )

        except Exception as e:
            logger.warning(f"⚠️ 处理操作记录失败: {e}")
            continue

    feature_names = list(all_features.keys()) if features_list else []
    X = np.array(features_list) if features_list else np.array([])

    return X, data_records, feature_names


def cluster_scenes_with_gmm(X: np.ndarray, n_components: int = 5) -> np.ndarray:
    """
    使用高斯混合模型(GMM)进行场景聚类

    Args:
        X: 特征矩阵
        n_components: 聚类数量

    Returns:
        聚类标签数组
    """
    if len(X) == 0:
        return np.array([])

    # 标准化特征
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 使用GMM进行聚类
    actual_components = min(n_components, len(X))  # 确保聚类数不超过样本数
    
    gmm = GaussianMixture(
        n_components=actual_components,
        covariance_type="full",
        max_iter=100,
        random_state=42,
    )

    labels = gmm.fit_predict(X_scaled)
    
    # 统计每个场景的样本数
    unique_labels, counts = np.unique(labels, return_counts=True)
    
    logger.info(f"✅ GMM聚类完成: {len(X)}个样本被分为{actual_components}个场景")
    
    # 打印详细的聚类结果
    for label, count in zip(unique_labels, counts):
        percentage = (count / len(X)) * 100
        logger.debug(f"   场景 {label}: {count} 个样本 ({percentage:.1f}%)")

    return labels


def analyze_scene_patterns(
    data_records: List[Dict], labels: np.ndarray
) -> Dict[int, Dict[str, Any]]:
    """
    分析每个场景的模式特征

    Args:
        data_records: 数据记录列表
        labels: 聚类标签

    Returns:
        场景分析结果字典 {场景ID: 场景特征}
    """
    scenes = {}

    for label in np.unique(labels):
        # 获取该场景的所有记录
        scene_indices = np.where(labels == label)[0]
        scene_records = [data_records[i] for i in scene_indices]

        # 统计时间特征
        hours = [rec["time_features"]["hour"] for rec in scene_records]
        avg_hour = np.mean(hours)

        # 判断时段
        if 6 <= avg_hour < 12:
            time_period = "早上"
        elif 12 <= avg_hour < 18:
            time_period = "下午"
        elif 18 <= avg_hour < 22:
            time_period = "晚上"
        else:
            time_period = "夜晚"

        # 统计设备操作
        device_actions = {}
        for rec in scene_records:
            op = rec["operation"]
            device_type = op.get("device_type", "unknown")
            action = op.get("action", "unknown")

            if device_type not in device_actions:
                device_actions[device_type] = []

            # 解析参数
            params_str = op.get("parameters")
            params = {}
            if params_str:
                try:
                    params = (
                        json.loads(params_str)
                        if isinstance(params_str, str)
                        else params_str
                    )
                except:
                    pass

            device_actions[device_type].append({"action": action, "parameters": params})

        # 生成场景描述
        scene_name = f"场景{label+1}_{time_period}"

        scenes[label] = {
            "scene_id": int(label),  # 转换 numpy.int64 为 int
            "scene_name": scene_name,
            "time_period": time_period,
            "avg_hour": float(round(avg_hour, 1)),  # 转换 numpy.float64 为 float
            "occurrence_count": len(scene_records),
            "device_actions": device_actions,
            "description": generate_scene_description(time_period, device_actions),
        }

    return scenes


def generate_scene_description(
    time_period: str, device_actions: Dict[str, List]
) -> str:
    """
    生成场景描述

    Args:
        time_period: 时间段
        device_actions: 设备操作字典

    Returns:
        场景描述文本
    """
    desc_parts = [f"在{time_period}时段，用户通常会："]

    for device_type, actions in device_actions.items():
        device_name_map = {
            "air_conditioner": "空调",
            "air_cleaner": "空气净化器",
            "bedside_lamp": "床头灯",
        }
        device_name = device_name_map.get(device_type, device_type)

        # 统计最常见的操作
        action_counts = {}
        for action_info in actions:
            action = action_info["action"]
            action_counts[action] = action_counts.get(action, 0) + 1

        most_common_action = (
            max(action_counts, key=action_counts.get) if action_counts else "操作"
        )
        count = action_counts[most_common_action]

        desc_parts.append(f"- 对{device_name}执行「{most_common_action}」（{count}次）")

    return "\n".join(desc_parts)


class SceneQueryArgs(BaseModel):
    user_query: str = Field(
        ...,
        description="用户的场景描述或查询，例如：'我要睡觉了'、'起床了'、'打开空调'",
    )
    system_user_id: int = Field(
        default=1000000001, description="系统用户ID，用于查询该用户的历史数据"
    )
    days: int = Field(default=30, description="查询最近N天的数据，默认30天")


@tool(
    "query_user_scene_habits",
    args_schema=SceneQueryArgs,
    description="基于用户历史行为数据，使用GMM算法分析场景习惯，为用户查询提供个性化设备操作建议",
)
def query_user_scene_habits(
    user_query: str, system_user_id: int = 1000000001, days: int = 30
) -> str:
    """
    查询用户场景习惯，使用GMM进行场景聚类分析

    Args:
        user_query: 用户查询或场景描述
        system_user_id: 系统用户ID
        days: 查询最近N天的数据

    Returns:
        JSON格式的分析结果
    """
    try:
        # 连接数据库
        conn = get_db_connection()
        if not conn:
            return json.dumps(
                {
                    "status": "error",
                    "message": "数据库连接失败",
                    "recommendation": None,
                },
                ensure_ascii=False,
                indent=2,
            )

        try:
            # 查询设备操作历史
            start_date = (datetime.now() - timedelta(days=days)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            sql = """
                SELECT id, system_user_id, created_at, context_id, device_type, 
                       device_name, action, parameters, success
                FROM device_operations
                WHERE system_user_id = %s
                  AND created_at >= %s
                  AND success = TRUE
                ORDER BY created_at DESC
            """

            with conn.cursor() as cursor:
                cursor.execute(sql, (system_user_id, start_date))
                operations = cursor.fetchall()

            print("\n" + "="*80)
            print(f"🔍 【数据挖掘开始】用户习惯分析")
            print("="*80)
            print(f"👤 用户ID: {system_user_id}")
            print(f"📅 查询时间范围: 最近 {days} 天")
            print(f"📊 查询到 {len(operations)} 条设备操作记录")
            print(f"🎯 用户查询: {user_query}")
            logger.info(f"📊 查询到 {len(operations)} 条设备操作记录")

            # 检查数据量
            if len(operations) < 10:
                return json.dumps(
                    {
                        "status": "insufficient_data",
                        "message": f"历史数据不足（仅{len(operations)}条记录），建议使用通用最佳实践",
                        "user_query": user_query,
                        "data_count": len(operations),
                        "recommendation": None,
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            # 准备聚类数据
            print("\n📦 【准备聚类数据】")
            X, data_records, feature_names = prepare_clustering_data(operations)
            print(f"   ✓ 特征矩阵维度: {X.shape if len(X) > 0 else '(0,0)'}")
            print(f"   ✓ 特征列表: {', '.join(feature_names)}")

            if len(X) == 0:
                print("   ❌ 无法准备聚类数据")
                return json.dumps(
                    {
                        "status": "error",
                        "message": "无法准备聚类数据",
                        "recommendation": None,
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            # 执行GMM聚类
            n_clusters = min(5, len(X) // 5)  # 动态确定聚类数
            n_clusters = max(2, n_clusters)  # 至少2个场景

            print(f"\n🤖 【GMM聚类分析】")
            print(f"   ℹ️  样本数量: {len(X)}")
            print(f"   ℹ️  目标场景数: {n_clusters}")
            print(f"   ⏳ 正在执行高斯混合模型聚类...")
            
            labels = cluster_scenes_with_gmm(X, n_components=n_clusters)
            print(f"   ✓ 聚类完成！识别出 {len(np.unique(labels))} 个使用场景")

            # 分析场景模式
            print(f"\n📈 【场景模式分析】")
            scenes = analyze_scene_patterns(data_records, labels)
            
            # 打印每个场景的详细信息
            for scene_id, scene in scenes.items():
                print(f"\n   🎬 场景 #{scene_id + 1}: {scene['time_period']} {scene.get('weekend_info', '')}")
                print(f"      📍 时间段: {scene['time_period']} (平均 {scene['avg_hour']:.1f}:00)")
                print(f"      📊 出现次数: {scene['occurrence_count']} 次")
                print(f"      🔧 设备操作:")
                for device, actions in scene['device_actions'].items():
                    print(f"         • {device}:")
                    for action_info in actions[:3]:  # 只显示前3个操作
                        action_str = f"           - {action_info['action']}"
                        if action_info.get('parameters'):
                            params_str = ', '.join([f"{k}={v}" for k, v in list(action_info['parameters'].items())[:2]])
                            action_str += f" ({params_str})"
                        print(action_str)
                    if len(actions) > 3:
                        print(f"           ... 还有 {len(actions)-3} 个操作")

            # 根据用户查询匹配最相关的场景
            print(f"\n🎯 【场景匹配】")
            print(f"   查询: {user_query}")
            matched_scene = match_scene_by_query(user_query, scenes)
            
            if matched_scene:
                print(f"   ✓ 匹配到场景: {matched_scene['time_period']} - 出现 {matched_scene['occurrence_count']} 次")
            else:
                print(f"   ⚠️ 未找到匹配场景")

            # 生成推荐
            recommendation = None
            if matched_scene:
                print(f"\n💡 【生成推荐】")
                recommendation = generate_recommendation_with_confidence(matched_scene)
                if recommendation:
                    print(f"   ✓ 推荐已生成，包含 {len(recommendation.get('device_operations', []))} 个设备操作")
                    for idx, op in enumerate(recommendation.get('device_operations', []), 1):
                        confidence = op.get('confidence_score', 0)
                        confidence_emoji = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.5 else "🔴"
                        print(f"      {idx}. {op['device_type']}.{op['action']} {confidence_emoji} (置信度: {confidence:.2f})")
                        if op.get('parameters'):
                            params_str = ', '.join([f"{k}={v}" for k, v in list(op['parameters'].items())[:2]])
                            print(f"         参数: {params_str}")
                    
                    print(f"\n   📝 用户反馈说明:")
                    print(f"      • 您有 5 分钟时间修改推荐操作")
                    print(f"      • 修改后的操作置信度会提高")
                    print(f"      • 系统会学习您的修改偏好")
            
            result = {
                "status": "success",
                "message": f"基于最近{days}天的{len(operations)}条记录，识别出{len(scenes)}个使用场景",
                "user_query": user_query,
                "total_operations": len(operations),
                "identified_scenes": len(scenes),
                "matched_scene": matched_scene,
                "all_scenes": list(scenes.values()),
                "recommendation": recommendation,
            }

            print("\n" + "="*80)
            print(f"✅ 【数据挖掘完成】")
            print(f"   总记录数: {len(operations)}")
            print(f"   识别场景: {len(scenes)} 个")
            print(f"   匹配状态: {'成功' if matched_scene else '未匹配'}")
            print(f"   推荐状态: {'已生成' if recommendation else '无'}")
            print("="*80 + "\n")

            # 转换 numpy 类型为 Python 原生类型，确保可以 JSON 序列化
            result = convert_numpy_types(result)
            return json.dumps(result, ensure_ascii=False, indent=2)

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"❌ 场景习惯查询失败: {e}", exc_info=True)
        return json.dumps(
            {
                "status": "error",
                "message": f"分析失败: {str(e)}",
                "recommendation": None,
            },
            ensure_ascii=False,
            indent=2,
        )


def match_scene_by_query(user_query: str, scenes: Dict[int, Dict]) -> Optional[Dict]:
    """
    根据用户查询匹配最相关的场景

    Args:
        user_query: 用户查询文本
        scenes: 场景字典

    Returns:
        匹配的场景信息
    """
    # 简单的关键词匹配策略
    query_lower = user_query.lower()

    # 时间关键词映射
    time_keywords = {
        "早上": ["早上", "早晨", "起床", "上午"],
        "下午": ["下午", "午后"],
        "晚上": ["晚上", "傍晚", "晚饭", "晚餐"],
        "夜晚": ["夜晚", "睡觉", "睡眠", "休息", "晚安"],
    }

    # 设备关键词映射
    device_keywords = {
        "air_conditioner": ["空调", "ac", "制冷", "制热", "温度"],
        "air_cleaner": ["空气净化器", "净化器", "空气", "pm2.5"],
        "bedside_lamp": ["床头灯", "灯", "照明", "亮度"],
    }

    # 找出匹配的时间段
    matched_time_period = None
    for period, keywords in time_keywords.items():
        if any(kw in query_lower for kw in keywords):
            matched_time_period = period
            break

    # 找出匹配的设备类型
    matched_device_type = None
    for device, keywords in device_keywords.items():
        if any(kw in query_lower for kw in keywords):
            matched_device_type = device
            break

    # 评分并选择最佳匹配场景
    best_scene = None
    best_score = 0

    for scene in scenes.values():
        score = 0

        # 时间匹配得分
        if matched_time_period and scene["time_period"] == matched_time_period:
            score += 10

        # 设备匹配得分
        if matched_device_type and matched_device_type in scene["device_actions"]:
            score += 10

        # 出现频率得分（归一化）
        score += scene["occurrence_count"] * 0.1

        if score > best_score:
            best_score = score
            best_scene = scene

    # 如果没有明确匹配，选择出现最频繁的场景
    if best_score == 0 and scenes:
        best_scene = max(scenes.values(), key=lambda s: s["occurrence_count"])

    return best_scene


# 注意：此函数已废弃，请使用 generate_recommendation_with_confidence
# def generate_recommendation(scene: Dict) -> Dict[str, Any]:
#     """已废弃：使用 generate_recommendation_with_confidence 替代"""
#     pass


@tool("get_data_mining_status", description="获取数据挖掘Agent的状态和统计信息")
def get_data_mining_status() -> str:
    """
    获取数据挖掘Agent的状态

    Returns:
        JSON格式的状态信息
    """
    try:
        conn = get_db_connection()
        if not conn:
            return json.dumps(
                {"status": "error", "message": "数据库连接失败"},
                ensure_ascii=False,
                indent=2,
            )

        try:
            # 统计数据库中的记录数
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) as total FROM device_operations WHERE success = TRUE"
                )
                total_ops = cursor.fetchone()["total"]

                cursor.execute(
                    "SELECT COUNT(DISTINCT system_user_id) as users FROM device_operations"
                )
                total_users = cursor.fetchone()["users"]

                cursor.execute(
                    """
                    SELECT device_type, COUNT(*) as count 
                    FROM device_operations 
                    WHERE success = TRUE
                    GROUP BY device_type
                """
                )
                device_stats = cursor.fetchall()

            status_info = {
                "status": "online",
                "message": "数据挖掘Agent运行正常",
                "database_status": "connected",
                "statistics": {
                    "total_operations": total_ops,
                    "total_users": total_users,
                    "device_breakdown": {
                        stat["device_type"]: stat["count"] for stat in device_stats
                    },
                },
                "capabilities": [
                    "GMM场景聚类分析",
                    "用户习惯挖掘",
                    "个性化场景推荐",
                    "历史行为分析",
                    "用户反馈学习",
                    "置信度动态调整",
                ],
            }

            # 转换 numpy 类型为 Python 原生类型
            status_info = convert_numpy_types(status_info)
            return json.dumps(status_info, ensure_ascii=False, indent=2)

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"❌ 获取状态失败: {e}")
        return json.dumps(
            {"status": "error", "message": f"获取状态失败: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


# ============================================
# 增强功能：置信度计算和用户反馈学习
# ============================================


def calculate_action_confidence(
    action_info: Dict[str, Any],
    scene_occurrence: int,
    total_operations: int,
    is_user_modified: bool = False,
) -> float:
    """
    计算设备操作的置信度

    Args:
        action_info: 操作信息（包含频次）
        scene_occurrence: 场景出现次数
        total_operations: 总操作数
        is_user_modified: 是否被用户修改过

    Returns:
        置信度分数（0-1）
    """
    # 基础置信度：基于频次
    frequency = action_info.get("frequency", 1)
    base_confidence = min(frequency / scene_occurrence, 1.0)

    # 场景稳定性：场景出现频率
    scene_stability = min(scene_occurrence / total_operations, 1.0)

    # 综合置信度
    confidence = base_confidence * 0.7 + scene_stability * 0.3

    # 用户修改过的操作，置信度最高
    if is_user_modified:
        confidence = min(confidence * 1.5, 1.0)

    return round(confidence, 3)


def adjust_confidence_by_feedback(
    original_params: Dict, modified_params: Dict, original_confidence: float
) -> float:
    """
    根据用户反馈调整置信度

    Args:
        original_params: 原始推荐参数
        modified_params: 用户修改后的参数
        original_confidence: 原始置信度

    Returns:
        调整后的置信度
    """
    if not original_params or not modified_params:
        return original_confidence * 0.5

    # 计算参数差异
    differences = 0
    total_params = len(original_params)

    for key in original_params:
        if key in modified_params:
            if original_params[key] != modified_params[key]:
                # 计算差异程度
                if isinstance(original_params[key], (int, float)) and isinstance(
                    modified_params[key], (int, float)
                ):
                    # 数值型参数：计算相对差异
                    diff = abs(original_params[key] - modified_params[key]) / max(
                        abs(original_params[key]), 1
                    )
                    differences += min(diff, 1.0)
                else:
                    # 非数值型参数：完全不同
                    differences += 1.0

    # 差异越大，置信度降低越多
    if total_params > 0:
        diff_ratio = differences / total_params
        adjusted_confidence = original_confidence * (
            1 - diff_ratio * 0.8
        )  # 最多降低80%
    else:
        adjusted_confidence = original_confidence * 0.5

    return max(round(adjusted_confidence, 3), 0.1)  # 最低保留0.1


def query_operations_with_db_preprocessing(
    system_user_id: int, days: int = 30, include_confidence: bool = True
) -> List[Dict[str, Any]]:
    """
    从数据库查询操作记录，利用StarRocks进行预处理

    Args:
        system_user_id: 用户ID
        days: 查询天数
        include_confidence: 是否包含置信度信息

    Returns:
        预处理后的操作记录列表（包含特征）
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # 使用视图进行数据库端预处理
        if include_confidence:
            sql = """
                SELECT 
                    id, system_user_id, created_at, context_id,
                    device_type, device_name, action, parameters,
                    confidence_score, is_user_modified, confidence_source,
                    hour, minute, day_of_week, is_weekend,
                    is_morning, is_afternoon, is_evening, is_night
                FROM enhanced_operations_view
                WHERE system_user_id = %s
                  AND created_at >= %s
                ORDER BY created_at DESC
            """
        else:
            sql = """
                SELECT 
                    id, system_user_id, created_at, context_id,
                    device_type, device_name, action, parameters, success
                FROM device_operations
                WHERE system_user_id = %s
                  AND created_at >= %s
                  AND success = TRUE
                ORDER BY created_at DESC
            """

        with conn.cursor() as cursor:
            cursor.execute(sql, (system_user_id, start_date))
            operations = cursor.fetchall()

        logger.info(f"📊 从数据库查询到 {len(operations)} 条记录（已包含预处理特征）")
        return operations

    except Exception as e:
        logger.error(f"❌ 查询操作记录失败: {e}")
        return []
    finally:
        conn.close()


def save_user_feedback(
    system_user_id: int,
    context_id: str,
    original_recommendation: Dict[str, Any],
    user_modification: Dict[str, Any],
    scene_matched: str,
    time_period: str,
) -> bool:
    """
    保存用户反馈到数据库

    Args:
        system_user_id: 用户ID
        context_id: 会话ID
        original_recommendation: 原始推荐
        user_modification: 用户修改
        scene_matched: 匹配的场景
        time_period: 时间段

    Returns:
        是否保存成功
    """
    conn = get_db_connection()
    if not conn:
        return False

    try:
        feedback_id = int(datetime.now().timestamp() * 1000000)

        # 判断反馈类型
        if not user_modification:
            feedback_type = "rejected"
        elif user_modification == original_recommendation:
            feedback_type = "accepted"
        else:
            feedback_type = "modified"

        sql = """
            INSERT INTO user_feedback
            (id, system_user_id, created_at, context_id, 
             original_recommendation, user_modification, scene_matched, time_period,
             feedback_type, feedback_timestamp, is_processed)
            VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, NOW(), FALSE)
        """

        with conn.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    feedback_id,
                    system_user_id,
                    context_id,
                    json.dumps(original_recommendation, ensure_ascii=False),
                    json.dumps(user_modification, ensure_ascii=False),
                    scene_matched,
                    time_period,
                    feedback_type,
                ),
            )

        logger.info(f"✅ 用户反馈已保存: {feedback_type}, scene={scene_matched}")
        return True

    except Exception as e:
        logger.error(f"❌ 保存用户反馈失败: {e}")
        return False
    finally:
        conn.close()


def update_confidence_scores(
    system_user_id: int, feedback_data: Dict[str, Any]
) -> bool:
    """
    根据用户反馈更新置信度分数

    Args:
        system_user_id: 用户ID
        feedback_data: 反馈数据

    Returns:
        是否更新成功
    """
    conn = get_db_connection()
    if not conn:
        return False

    try:
        original_rec = feedback_data.get("original_recommendation", {})
        user_mod = feedback_data.get("user_modification", {})

        for action in original_rec.get("suggested_actions", []):
            device_type = action.get("device_type")
            original_params = action.get("parameters", {})

            # 查找用户修改后的对应操作
            modified_action = None
            for mod_action in user_mod.get("suggested_actions", []):
                if mod_action.get("device_type") == device_type:
                    modified_action = mod_action
                    break

            if modified_action:
                modified_params = modified_action.get("parameters", {})
                original_confidence = action.get("confidence", 0.5)

                # 计算调整后的置信度
                new_confidence = adjust_confidence_by_feedback(
                    original_params, modified_params, original_confidence
                )

                # 保存到数据库
                confidence_id = int(datetime.now().timestamp() * 1000000)
                sql = """
                    INSERT INTO device_operation_confidence
                    (id, operation_id, system_user_id, created_at, device_type,
                     action, parameters, confidence_score, source, is_user_modified,
                     original_confidence, adjustment_reason)
                    VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
                """

                with conn.cursor() as cursor:
                    cursor.execute(
                        sql,
                        (
                            confidence_id,
                            0,  # 临时值，实际应关联具体操作
                            system_user_id,
                            device_type,
                            modified_action.get("action"),
                            json.dumps(modified_params, ensure_ascii=False),
                            new_confidence,
                            "user_feedback",
                            True,
                            original_confidence,
                            f"用户修改，原参数差异调整",
                        ),
                    )

        logger.info(f"✅ 置信度分数已更新")
        return True

    except Exception as e:
        logger.error(f"❌ 更新置信度失败: {e}")
        return False
    finally:
        conn.close()


def generate_recommendation_with_confidence(scene: Dict) -> Dict[str, Any]:
    """
    基于场景生成带置信度的设备操作建议（增强版）

    Args:
        scene: 场景信息

    Returns:
        包含置信度的操作建议字典
    """
    recommendations = {
        "scene_name": scene["scene_name"],
        "time_period": scene["time_period"],
        "confidence": "高" if scene["occurrence_count"] > 10 else "中",
        "suggested_actions": [],
        "feedback_window": 300,  # 5分钟 = 300秒
        "feedback_instruction": "您有5分钟时间对推荐操作进行调整，系统会学习您的偏好",
    }

    # 确保 total_ops 是 Python int
    total_ops = int(scene["occurrence_count"])

    # 为每个设备生成具体建议（包含置信度）
    for device_type, actions in scene["device_actions"].items():
        device_name_map = {
            "air_conditioner": "空调",
            "air_cleaner": "空气净化器",
            "bedside_lamp": "床头灯",
        }
        device_name = device_name_map.get(device_type, device_type)

        # 统计最常见的操作和参数
        action_stats = {}
        for action_info in actions:
            action_key = action_info["action"]
            if action_key not in action_stats:
                action_stats[action_key] = {"count": 0, "parameters": []}
            action_stats[action_key]["count"] += 1
            if action_info["parameters"]:
                action_stats[action_key]["parameters"].append(action_info["parameters"])

        # 选择最常见的操作（带置信度）
        for action, stats in sorted(
            action_stats.items(), key=lambda x: x[1]["count"], reverse=True
        )[:3]:
            # 计算置信度
            confidence = calculate_action_confidence(
                {"frequency": stats["count"]}, total_ops, total_ops
            )

            suggestion = {
                "device_type": device_type,
                "device_name": device_name,
                "action": action,
                "frequency": int(stats["count"]),  # 确保是 Python int
                "parameters": stats["parameters"][0] if stats["parameters"] else {},
                "confidence": float(confidence),  # 确保是 Python float
                "confidence_level": (
                    "高" if confidence > 0.7 else ("中" if confidence > 0.4 else "低")
                ),
            }
            recommendations["suggested_actions"].append(suggestion)

    return recommendations


class FeedbackArgs(BaseModel):
    context_id: str = Field(..., description="会话上下文ID")
    original_recommendation: Dict[str, Any] = Field(
        ..., description="原始推荐内容（JSON）"
    )
    user_modification: Dict[str, Any] = Field(
        ..., description="用户修改后的内容（JSON）"
    )
    system_user_id: int = Field(default=1000000001, description="系统用户ID")


@tool(
    "submit_user_feedback",
    args_schema=FeedbackArgs,
    description="提交用户对推荐操作的反馈（5分钟窗口内），用于改进GMM模型准确性",
)
def submit_user_feedback(
    context_id: str,
    original_recommendation: Dict[str, Any],
    user_modification: Dict[str, Any],
    system_user_id: int = 1000000001,
) -> str:
    """
    提交用户反馈，用于在线学习

    Args:
        context_id: 会话ID
        original_recommendation: 原始推荐
        user_modification: 用户修改
        system_user_id: 用户ID

    Returns:
        反馈处理结果
    """
    try:
        print("\n" + "="*80)
        print(f"📝 【用户反馈处理】")
        print("="*80)
        print(f"👤 用户ID: {system_user_id}")
        print(f"🔖 会话ID: {context_id}")
        
        scene_matched = original_recommendation.get("scene_name", "unknown")
        time_period = original_recommendation.get("time_period", "unknown")
        
        print(f"🎬 场景: {scene_matched} ({time_period})")
        
        # 比较原始推荐和用户修改
        is_modified = user_modification != original_recommendation
        feedback_type = "modified" if is_modified else "accepted"
        
        print(f"\n📊 反馈类型: {feedback_type}")
        
        if is_modified:
            print(f"\n🔄 用户修改详情:")
            orig_ops = original_recommendation.get('device_operations', [])
            user_ops = user_modification.get('device_operations', [])
            
            # 显示修改的操作
            for i, (orig_op, user_op) in enumerate(zip(orig_ops, user_ops), 1):
                if orig_op != user_op:
                    print(f"   {i}. {orig_op.get('device_type')}:")
                    print(f"      原始: {orig_op.get('action')} {orig_op.get('parameters', {})}")
                    print(f"      修改: {user_op.get('action')} {user_op.get('parameters', {})}")
        else:
            print(f"   ✓ 用户接受了原始推荐")

        # 保存反馈
        print(f"\n💾 正在保存反馈到数据库...")
        success = save_user_feedback(
            system_user_id,
            context_id,
            original_recommendation,
            user_modification,
            scene_matched,
            time_period,
        )

        if not success:
            print(f"   ❌ 保存失败")
            return json.dumps(
                {"status": "error", "message": "保存用户反馈失败"},
                ensure_ascii=False,
                indent=2,
            )
        
        print(f"   ✓ 反馈已保存")

        # 更新置信度
        print(f"\n🎯 正在更新置信度模型...")
        update_confidence_scores(
            system_user_id,
            {
                "original_recommendation": original_recommendation,
                "user_modification": user_modification,
            },
        )
        print(f"   ✓ 置信度已更新")

        result = {
            "status": "success",
            "message": "感谢您的反馈！系统已记录您的偏好，将在下次推荐中应用",
            "feedback_type": feedback_type,
            "learning_status": "已更新置信度模型",
            "next_recommendation": "下次将优先考虑您修改后的操作",
        }

        print("\n" + "="*80)
        print(f"✅ 【用户反馈处理完成】")
        print(f"   反馈类型: {feedback_type}")
        print(f"   学习状态: 已更新")
        print("="*80 + "\n")

        # 转换 numpy 类型为 Python 原生类型
        result = convert_numpy_types(result)
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"❌ 提交用户反馈失败: {e}")
        return json.dumps(
            {"status": "error", "message": f"提交反馈失败: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )
