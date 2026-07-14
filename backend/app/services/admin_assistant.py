import json
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import ContentMedia, TravelNote, UserComment
from app.models.user import CheckinRecord


DOCS_ROOT = Path(__file__).resolve().parents[3] / "docs"
KNOWLEDGE_FILES = ("miniprogram-design.md", "admin-operation-guide.md")


def pending_summary(db: Session) -> dict[str, int]:
    return {
        "checkins": _pending_count(db, CheckinRecord),
        "travel_notes": _pending_count(db, TravelNote),
        "comments": _pending_count(db, UserComment),
        "media": _pending_count(db, ContentMedia),
    }


def _pending_count(db: Session, model: Any) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(model.status == "pending")) or 0)


def answer_admin_question(config: dict[str, str], message: str, mode: str, summary: dict[str, int]) -> dict[str, str]:
    knowledge = find_knowledge(message, mode)
    system = (
        "You are the Guizhou Hidden Gems admin assistant. Answer in the user's language. "
        "Use the supplied product knowledge. Never claim an action has been executed. "
        "For content review, provide a non-binding recommendation, explain uncertainty, and require human approval. "
        "For coordinates, explain lawful on-site collection, coordinate verification, and protected-location handling."
    )
    context = (
        f"Mode: {mode}\n"
        f"Pending items: checkins={summary['checkins']}, notes={summary['travel_notes']}, "
        f"comments={summary['comments']}, media={summary['media']}\n\n"
        f"Knowledge base:\n{knowledge}"
    )
    if not _ai_configured(config):
        return {
            "answer": local_answer(mode, summary, knowledge),
            "source": "knowledge_base",
        }


def answer_content_review(config: dict[str, str], message: str, image_urls: list[str], summary: dict[str, int]) -> dict[str, str]:
    knowledge = find_knowledge(message, "review")
    if not _ai_configured(config):
        return {"answer": local_answer("review", summary, knowledge), "source": "knowledge_base"}
    vision_enabled = (config.get("AI_VISION_ENABLED") or "").lower() == "true"
    system = (
        "You help an administrator review user-generated travel content. Give a non-binding recommendation: "
        "approve, manual review, or reject; list risks and uncertainty. Never make the final moderation decision."
    )
    try:
        answer = call_ai(config, system, f"{message}\n\n审核规则参考：\n{knowledge}", image_urls if vision_enabled else None)
        if not vision_enabled:
            answer += "\n\n提示：当前未启用图片视觉初审，媒体内容仍需管理员人工查看。"
        return {"answer": answer, "source": "ai"}
    except RuntimeError as error:
        return {"answer": f"大模型暂不可用：{error}\n\n{local_answer('review', summary, knowledge)}", "source": "knowledge_base"}
    try:
        answer = call_ai(config, system, f"{context}\n\nAdministrator request:\n{message}")
        return {"answer": answer, "source": "ai"}
    except RuntimeError as error:
        return {
            "answer": f"大模型暂不可用：{error}\n\n{local_answer(mode, summary, knowledge)}",
            "source": "knowledge_base",
        }


def find_knowledge(message: str, mode: str) -> str:
    query = set((message.lower() + " " + mode).replace("，", " ").replace("。", " ").split())
    snippets: list[str] = []
    for filename in KNOWLEDGE_FILES:
        path = DOCS_ROOT / filename
        if not path.exists():
            continue
        for block in path.read_text(encoding="utf-8").split("\n\n"):
            normalized = block.lower()
            if mode in normalized or any(word and word in normalized for word in query):
                snippets.append(block.strip())
            if len(snippets) >= 8:
                break
    return "\n\n".join(snippets)[:7000] or "请参考后台管理操作文档中的对应菜单说明。"


def local_answer(mode: str, summary: dict[str, int], knowledge: str) -> str:
    pending = f"当前待审：打卡 {summary['checkins']}，游记 {summary['travel_notes']}，留言 {summary['comments']}，媒体 {summary['media']}。"
    if mode == "spot_summary":
        return f"尚未配置可用大模型，无法自动生成双语简介。请在接口管理中配置并测试大模型后重试。\n{pending}\n\n参考：\n{knowledge}"
    if mode == "review":
        return f"尚未配置可用大模型，无法进行智能初审。请先人工检查文字、媒体、地点关联和安全风险；任何自动建议都必须由管理员确认。\n{pending}\n\n参考：\n{knowledge}"
    return f"{pending}\n\n参考操作说明：\n{knowledge}"


def _ai_configured(config: dict[str, str]) -> bool:
    return bool((config.get("AI_API_BASE") or "").strip() and (config.get("AI_MODEL") or "").strip() and (config.get("AI_API_KEY") or "").strip())


def call_ai(config: dict[str, str], system: str, prompt: str, image_urls: Optional[list[str]] = None) -> str:
    api_base = (config.get("AI_API_BASE") or "").strip().rstrip("/")
    url = api_base if api_base.endswith("/chat/completions") else f"{api_base}/chat/completions"
    user_content: Any = prompt
    if image_urls:
        user_content = [{"type": "text", "text": prompt}]
        for url in image_urls[:6]:
            user_content.append({"type": "image_url", "image_url": {"url": url}})
    payload = json.dumps(
        {
            "model": config["AI_MODEL"].strip(),
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_content}],
            "temperature": 0.2,
        }
    ).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={"Authorization": f"Bearer {config['AI_API_KEY'].strip()}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"服务返回 HTTP {error.code}") from error
    except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(str(error)) from error
    choices = data.get("choices") if isinstance(data, dict) else []
    content = choices[0].get("message", {}).get("content") if choices else ""
    if not content:
        raise RuntimeError("服务未返回有效回答")
    return str(content)[:8000]
