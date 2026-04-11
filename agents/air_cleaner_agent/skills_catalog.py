"""A2A AgentSkill 定义与 LLM 可用的技能说明（与 __main__.py 中 AgentCard 保持一致）。"""

from __future__ import annotations

from a2a.types import AgentSkill

_SKILLS_CACHE: list[AgentSkill] | None = None
_SKILLS_BY_ID: dict[str, AgentSkill] | None = None


def build_air_purifier_skills() -> list[AgentSkill]:
    """供 AgentCard 注册与模型侧展示使用。"""
    global _SKILLS_CACHE
    if _SKILLS_CACHE is not None:
        return _SKILLS_CACHE
    _SKILLS_CACHE = [
        AgentSkill(
            id="control_air_purifier",
            name="Air Purifier Control",
            description=(
                "控制桌面空气净化器（zhimi-oa1），包括电源、风扇等级、工作模式、LED亮度，"
                "查询PM2.5、湿度、滤芯寿命等"
            ),
            tags=["air purifier", "air quality", "PM2.5", "home automation", "smart home"],
            examples=[
                "打开空气净化器",
                "查询当前PM2.5",
                "设置为睡眠模式",
                "把风扇调到高速",
                "关闭LED灯",
            ],
        ),
    ]
    return _SKILLS_CACHE


def get_skill_by_id(skill_id: str) -> AgentSkill | None:
    global _SKILLS_BY_ID
    if _SKILLS_BY_ID is None:
        _SKILLS_BY_ID = {s.id: s for s in build_air_purifier_skills()}
    return _SKILLS_BY_ID.get(skill_id)


def format_skills_for_llm() -> str:
    """将已注册技能写入系统提示，使模型明确能力与 A2A skill id 对应关系。"""
    lines = [
        "## 本 Agent 在 A2A 中注册的 Skills",
        "客户端可在 Message 或 MessageSendParams 的 metadata 中传入 skillId；"
        "若用户请求与某条技能说明一致，请优先用下方工具完成。",
        "",
    ]
    for s in build_air_purifier_skills():
        lines.append(f"- **skill id**: `{s.id}` — **{s.name}**")
        lines.append(f"  - {s.description}")
        if s.examples:
            lines.append(f"  - 示例说法: {'；'.join(s.examples)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def user_message_skill_prefix(skill_id: str | None) -> str:
    """当请求携带 skillId 时，在用户消息前附加简短技能上下文。"""
    if not skill_id:
        return ""
    sk = get_skill_by_id(skill_id)
    if not sk:
        return (
            f"[A2A skillId={skill_id}，本地未匹配到已注册技能，请仍根据用户意图选用工具]\n\n"
        )
    return (
        f"[A2A 指定技能: {sk.name}（`{sk.id}`）]\n{sk.description}\n\n"
    )
