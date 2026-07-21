import json
import re
from base64 import b64encode
from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.archive import (
    ArchiveChatImport,
    ArchiveDevelopmentTask,
    ArchiveEvent,
    ArchiveInternalMessage,
    ArchiveRequirement,
)
from app.models.user import MiniProgramUser
from app.schemas.archive import ArchiveAssistantSubmitIn, ArchiveChatImportIn, ArchiveRequirementCreate, ArchiveRequirementDraft
from app.services.admin_assistant import _ai_configured, call_ai
from app.services.integrations import get_group_config
from app.services.media_storage import MediaStorageError, read_managed_media_url


FULL_REQUIREMENT_PATTERN = re.compile(r"REQ-\d{8}-\d{3}(?:-\d+)?")
MAIN_REQUIREMENT_PATTERN = re.compile(r"^REQ-\d{8}-\d{3}")


def _json_list(value: Optional[str]) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _date(value: Optional[str]) -> Optional[date]:
    return date.fromisoformat(value) if value else None


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


def _next_requirement_code(db: Session, source_date: date) -> str:
    prefix = f"REQ-{source_date:%Y%m%d}-"
    codes = db.scalars(select(ArchiveRequirement.code).where(ArchiveRequirement.code.like(f"{prefix}%"))).all()
    sequences = []
    for code in codes:
        match = re.match(rf"^{re.escape(prefix)}(\d{{3}})$", code)
        if match:
            sequences.append(int(match.group(1)))
    return f"{prefix}{max(sequences, default=0) + 1:03d}"


def _next_task_code(db: Session) -> str:
    today = date.today()
    prefix = f"DEV-{today:%m%d}-"
    codes = db.scalars(select(ArchiveDevelopmentTask.code).where(ArchiveDevelopmentTask.code.like(f"{prefix}%"))).all()
    sequences = []
    for code in codes:
        match = re.match(rf"^{re.escape(prefix)}(\d+)$", code)
        if match:
            sequences.append(int(match.group(1)))
    return f"{prefix}{max(sequences, default=0) + 1:02d}"


def add_event(
    db: Session,
    requirement: ArchiveRequirement,
    event_type: str,
    detail: str,
    actor_type: str,
    actor_name: Optional[str] = None,
    task: Optional[ArchiveDevelopmentTask] = None,
) -> ArchiveEvent:
    event = ArchiveEvent(
        requirement_id=requirement.id,
        task_id=task.id if task else None,
        event_type=event_type,
        actor_type=actor_type,
        actor_name=actor_name,
        detail=detail,
    )
    db.add(event)
    return event


def add_message(
    db: Session,
    message_type: str,
    title: str,
    content: str,
    requirement: Optional[ArchiveRequirement],
    target_role: str = "admin",
) -> ArchiveInternalMessage:
    message = ArchiveInternalMessage(
        message_type=message_type,
        title=title,
        content=content,
        related_requirement_id=requirement.id if requirement else None,
        target_role=target_role,
        is_read=False,
    )
    db.add(message)
    return message


def create_requirement(
    db: Session,
    payload: ArchiveRequirementCreate,
    *,
    source_type: str,
    admin_id: Optional[int] = None,
    requester_user_id: Optional[int] = None,
    create_task: bool = True,
) -> ArchiveRequirement:
    source_date = _date(payload.source_date) or date.today()
    requirement = ArchiveRequirement(
        code=_next_requirement_code(db, source_date),
        title=payload.title.strip(),
        module=payload.module.strip() or "待确认模块",
        category=payload.category,
        version="V2" if payload.category == "需求变更" else "V1",
        priority=payload.priority,
        status="待开始" if create_task else "待确认",
        owner=(payload.owner or "").strip() or None,
        requester=(payload.requester or "").strip() or None,
        requester_user_id=requester_user_id,
        source_type=source_type,
        source_date=source_date,
        source_text=payload.source_text.strip(),
        description=payload.description.strip(),
        acceptance_criteria=payload.acceptance_criteria.strip(),
        evidence_json=json.dumps(payload.evidence, ensure_ascii=False),
        planned_release=_date(payload.planned_release),
        created_by_admin_id=admin_id,
    )
    db.add(requirement)
    db.flush()
    add_event(
        db,
        requirement,
        "requirement_created",
        f"创建{payload.category}：{payload.title}",
        "customer" if requester_user_id else "admin",
        payload.requester,
    )
    if create_task:
        task = ArchiveDevelopmentTask(
            code=_next_task_code(db),
            requirement_id=requirement.id,
            sub_requirement_code=requirement.code,
            round_number=0,
            title=requirement.title,
            task_type="综合开发",
            owner=requirement.owner,
            end_date=requirement.planned_release,
            status="待开始",
            progress=0,
        )
        db.add(task)
        db.flush()
        add_event(db, requirement, "task_queued", "首次开发任务进入待开始", "system", task=task)
    return requirement


def classify_chat_line(content: str) -> tuple[str, str, str, str, str, int]:
    if re.search(r"打不开|失败|报错|异常|不能用|闪退", content):
        category = "缺陷"
        priority = "紧急" if re.search(r"尽快|马上|紧急|今天", content) else "高"
        title = "后台打卡报表导出失败" if "报表" in content else content[:60]
        description = f"客户反馈“{content}”，需要复现、定位并完成修复。"
        acceptance = "1. 问题可稳定复现并定位；\n2. 修复后原操作正常；\n3. 相关功能回归通过。"
        confidence = 96
    elif re.search(r"改成|修改|不要了|还是|调整", content):
        category = "需求变更"
        priority = "中"
        title = "首页主按钮颜色调整" if "按钮" in content else content[:60]
        description = f"客户对已沟通方案提出调整：“{content}”。"
        acceptance = "1. 按最新确认方案调整；\n2. 未涉及部分不变；\n3. 影响和发布日期重新确认。"
        confidence = 90
    else:
        category = "新功能"
        priority = "中"
        title = "地图页增加路线收藏功能" if "收藏" in content else content[:60]
        description = f"根据客户微信沟通整理：{content}"
        acceptance = "1. 核心操作可完成；\n2. 数据保存正确；\n3. 权限、上限和异常提示明确。"
        confidence = 92
    return category, priority, title, description, acceptance, confidence


def heuristic_requirement_drafts(
    raw_text: str,
    contact: Optional[str],
    evidence: list[str],
) -> list[ArchiveRequirementDraft]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    candidates = [
        line
        for line in lines
        if re.search(r"增加|新增|能不能|希望|改成|修改|不要了|打不开|失败|报错|异常|尽快", line)
    ]
    drafts: list[ArchiveRequirementDraft] = []
    for line in candidates[:20]:
        date_match = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", line)
        source_date = (
            date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
            if date_match
            else date.today()
        )
        speaker_match = re.search(r"\s([^\s：:]{2,16})[：:]", line)
        requester = speaker_match.group(1) if speaker_match else (contact or "客户")
        content = re.split(r"[：:]", line, maxsplit=1)[-1].strip()
        category, priority, title, description, acceptance, confidence = classify_chat_line(content)
        drafts.append(
            ArchiveRequirementDraft(
                title=title,
                module="后台报表" if "报表" in content else "首页界面" if "首页" in content or "按钮" in content else "地图与路线" if "地图" in content or "路线" in content else "待确认模块",
                category=category,
                priority=priority,
                requester=requester,
                source_date=source_date.isoformat(),
                source_text=content,
                description=description,
                acceptance_criteria=acceptance,
                evidence=evidence,
                confidence=confidence,
            )
        )
    return drafts


def _image_data_urls(db: Session, evidence: list[str]) -> list[str]:
    urls: list[str] = []
    for media_url in evidence[:6]:
        try:
            content, content_type = read_managed_media_url(db, media_url)
        except MediaStorageError:
            continue
        if not content_type.startswith("image/") or len(content) > 2 * 1024 * 1024:
            continue
        urls.append(f"data:{content_type};base64,{b64encode(content).decode('ascii')}")
    return urls


def _parse_ai_drafts(
    answer: str,
    raw_text: str,
    contact: Optional[str],
    evidence: list[str],
) -> list[ArchiveRequirementDraft]:
    match = re.search(r"\{[\s\S]*\}", answer)
    if not match:
        raise ValueError("AI response did not contain JSON")
    payload = json.loads(match.group(0))
    records = payload.get("requirements", payload) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("AI response requirements must be a list")
    today = date.today().isoformat()
    allowed_categories = {"新功能", "需求变更", "缺陷", "确认信息", "验证反馈"}
    allowed_priorities = {"紧急", "高", "中", "低"}
    category_aliases = {"bug": "缺陷", "问题": "缺陷", "优化": "需求变更", "功能": "新功能"}
    confidence_by_priority = {"紧急": 95, "高": 88, "中": 78, "低": 68}

    def text_value(value: object, fallback: str) -> str:
        return str(value).strip() if value is not None and str(value).strip() else fallback

    def iso_date(value: object, fallback: Optional[str]) -> Optional[str]:
        if value is None or not str(value).strip():
            return fallback
        match = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", str(value))
        if not match:
            return fallback
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
        except ValueError:
            return fallback

    def confidence_value(value: object, priority: str) -> int:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(0, min(100, int(value)))
        if value is not None:
            match = re.search(r"\d+", str(value))
            if match:
                return max(0, min(100, int(match.group(0))))
        return confidence_by_priority.get(priority, 80)

    drafts = []
    for raw_record in records[:20]:
        record = dict(raw_record) if isinstance(raw_record, dict) else None
        if not isinstance(record, dict):
            continue
        category = text_value(record.get("category"), "确认信息")
        category = category_aliases.get(category.lower(), category)
        priority = text_value(record.get("priority"), "中")
        if priority not in allowed_priorities:
            priority = "中"
        normalized = {
            "title": text_value(record.get("title"), raw_text[:60] or "待确认开发需求"),
            "module": text_value(record.get("module"), "待确认模块"),
            "category": category if category in allowed_categories else "确认信息",
            "priority": priority,
            "requester": text_value(record.get("requester"), contact or "客户"),
            "source_date": iso_date(record.get("source_date") or record.get("sourceDate"), today),
            "source_text": text_value(record.get("source_text") or record.get("sourceText"), raw_text[:8000]),
            "description": text_value(record.get("description"), raw_text[:8000] or "待补充需求描述"),
            "acceptance_criteria": text_value(
                record.get("acceptance_criteria") or record.get("acceptanceCriteria"),
                "由管理员补充可验证的验收标准。",
            ),
            "owner": text_value(record.get("owner"), "") or None,
            "planned_release": iso_date(record.get("planned_release") or record.get("plannedRelease"), None),
            "evidence": evidence,
            "confidence": confidence_value(record.get("confidence"), priority),
        }
        drafts.append(ArchiveRequirementDraft.model_validate(normalized))
    if not drafts:
        raise ValueError("AI response did not produce valid drafts")
    return drafts


def analyze_chat_drafts(db: Session, payload: ArchiveChatImportIn) -> tuple[list[ArchiveRequirementDraft], str, Optional[str]]:
    config = get_group_config(db, "ai")
    fallback = heuristic_requirement_drafts(payload.raw_text, payload.contact, payload.evidence)
    if not _ai_configured(config):
        return fallback, "fallback", "后台大模型未配置，已使用规则整理草稿。"
    system = (
        "你是软件项目需求分析助手。只返回 JSON，不要 Markdown。"
        "格式：{\"requirements\":[{title,module,category,priority,requester,source_date,source_text,description,acceptance_criteria,owner,planned_release,confidence}]}。"
        "category 只能是 新功能、需求变更、缺陷、确认信息、验证反馈；priority 只能是 紧急、高、中、低。"
        "source_date 必须是 YYYY-MM-DD 字符串，confidence 必须是 0 到 100 的整数，不能返回 null 或文字。"
        "仅提取可执行或需要确认的需求，保留原文事实，不臆造。"
    )
    prompt = f"沟通对象：{payload.contact or '客户'}\n聊天原文：\n{payload.raw_text}"
    image_urls = _image_data_urls(db, payload.evidence) if (config.get("AI_VISION_ENABLED") or "").lower() == "true" else None
    try:
        answer = call_ai(config, system, prompt, image_urls)
        return _parse_ai_drafts(answer, payload.raw_text, payload.contact, payload.evidence), "ai", None
    except (RuntimeError, ValueError, json.JSONDecodeError) as error:
        return fallback, "fallback", f"大模型整理失败，已使用规则整理草稿：{error}"


def analyze_chat_import(
    db: Session,
    raw_text: str,
    source_name: str,
    source_type: str,
    contact: Optional[str],
    evidence: list[str],
    admin_id: int,
    drafts: Optional[list[ArchiveRequirementDraft]] = None,
) -> tuple[ArchiveChatImport, list[ArchiveRequirement]]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    imported = ArchiveChatImport(
        source_name=source_name,
        source_type=source_type,
        contact=contact,
        raw_text=raw_text,
        message_count=len(lines),
        recognized_count=0,
        status="processed",
        imported_by_admin_id=admin_id,
    )
    db.add(imported)
    db.flush()
    requirements: list[ArchiveRequirement] = []
    for draft in drafts if drafts is not None else heuristic_requirement_drafts(raw_text, contact, evidence):
        payload = ArchiveRequirementCreate(
            **draft.model_dump(exclude={"confidence"}),
        )
        requirement = create_requirement(db, payload, source_type=source_type, admin_id=admin_id)
        requirements.append(requirement)
        add_message(
            db,
            "微信导入",
            f"微信聊天识别出{payload.category}",
            f"{requirement.code} {requirement.title}，请审核后进入开发。",
            requirement,
        )
    imported.recognized_count = len(requirements)
    db.add(imported)
    return imported, requirements


def get_requirement_by_code(db: Session, code: str) -> ArchiveRequirement:
    main_match = MAIN_REQUIREMENT_PATTERN.match(code)
    if not main_match:
        raise HTTPException(status_code=400, detail="Invalid requirement code")
    requirement = db.scalar(
        select(ArchiveRequirement)
        .options(selectinload(ArchiveRequirement.tasks), selectinload(ArchiveRequirement.events))
        .where(ArchiveRequirement.code == main_match.group(0))
    )
    if requirement is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return requirement


def get_task_by_code(db: Session, task_code: str) -> ArchiveDevelopmentTask:
    task = db.scalar(select(ArchiveDevelopmentTask).where(ArchiveDevelopmentTask.code == task_code))
    if task is None:
        raise HTTPException(status_code=404, detail="Development task not found")
    return task


def tasks_for_full_code(requirement: ArchiveRequirement, full_code: str) -> list[ArchiveDevelopmentTask]:
    tasks = [task for task in requirement.tasks if task.sub_requirement_code == full_code]
    if not tasks:
        raise HTTPException(status_code=404, detail="Requirement round not found")
    return tasks


def start_task(db: Session, task: ArchiveDevelopmentTask, actor_name: str) -> None:
    if task.status != "待开始":
        raise HTTPException(status_code=409, detail="Task is not waiting to start")
    task.status = "开发中"
    task.progress = 35
    task.start_date = date.today()
    task.requirement.status = "开发中"
    add_event(db, task.requirement, "development_started", f"{task.sub_requirement_code} 开始开发", "admin", actor_name, task)


def record_self_test(db: Session, task: ArchiveDevelopmentTask, result: str, detail: str, actor_name: str) -> None:
    if task.status != "开发中":
        raise HTTPException(status_code=409, detail="Task is not in development")
    task.self_test_result = result
    task.self_test_detail = detail or ("自测通过，等待客户验收。" if result == "通过" else "自测未通过，继续修改。")
    task.progress = 100 if result == "通过" else 70
    task.status = "已自测" if result == "通过" else "开发中"
    task.requirement.status = "待客户验收" if result == "通过" else "开发中"
    add_event(db, task.requirement, "self_test", f"自测{result}：{task.self_test_detail}", "admin", actor_name, task)


def notify_acceptance(db: Session, task: ArchiveDevelopmentTask, actor_name: str) -> None:
    if task.status != "已自测":
        raise HTTPException(status_code=409, detail="Task has not passed self-test")
    task.acceptance_notified_at = datetime.now()
    add_message(
        db,
        "客户验收",
        "AI助手已发起客户验收",
        f"请客户验证 {task.sub_requirement_code}「{task.title}」，并反馈通过或未通过及原因。",
        task.requirement,
        "customer",
    )
    add_event(db, task.requirement, "acceptance_notified", "AI助手向客户发送验收消息", "admin", actor_name, task)


def record_acceptance(
    db: Session,
    task: ArchiveDevelopmentTask,
    result: str,
    detail: str,
    actor_type: str,
    actor_name: str,
) -> Optional[ArchiveDevelopmentTask]:
    if task.status != "已自测":
        raise HTTPException(status_code=409, detail="Task is not waiting for acceptance")
    if task.acceptance_notified_at is None and actor_type != "customer":
        raise HTTPException(status_code=409, detail="Send the AI acceptance message first")
    if result == "未通过" and not detail.strip():
        raise HTTPException(status_code=400, detail="Acceptance failure detail is required")
    task.acceptance_result = result
    task.acceptance_detail = detail or "客户确认验收通过。"
    add_event(db, task.requirement, "customer_acceptance", f"客户验收{result}：{task.acceptance_detail}", actor_type, actor_name, task)
    if result == "通过":
        task.status = "已完成"
        task.progress = 100
        active = [
            item
            for item in task.requirement.tasks
            if item.id != task.id and item.status in {"待开始", "开发中", "已自测"}
        ]
        task.requirement.status = "已完成" if not active else _derive_requirement_status(task.requirement.tasks)
        add_message(db, "验收通过", f"{task.sub_requirement_code} 已完成", task.acceptance_detail, task.requirement)
        return None

    task.status = "验收未通过"
    next_round = max((item.round_number for item in task.requirement.tasks), default=0) + 1
    follow_up = ArchiveDevelopmentTask(
        code=_next_task_code(db),
        requirement_id=task.requirement_id,
        sub_requirement_code=f"{task.requirement.code}-{next_round}",
        round_number=next_round,
        title=f"第{next_round}轮改进：{task.title}",
        task_type=task.task_type,
        owner=task.owner,
        end_date=task.end_date,
        status="待开始",
        progress=0,
    )
    db.add(follow_up)
    db.flush()
    task.requirement.status = "待开始"
    add_event(db, task.requirement, "rework_created", f"生成 {follow_up.sub_requirement_code} 并回流待开始", "system", task=follow_up)
    add_message(
        db,
        "验收未通过",
        f"{task.sub_requirement_code} 客户验收未通过",
        f"原因：{task.acceptance_detail}。已生成 {follow_up.sub_requirement_code}。",
        task.requirement,
    )
    return follow_up


def _derive_requirement_status(tasks: list[ArchiveDevelopmentTask]) -> str:
    if any(task.status == "开发中" for task in tasks):
        return "开发中"
    if any(task.status == "待开始" for task in tasks):
        return "待开始"
    if any(task.status == "已自测" for task in tasks):
        return "待客户验收"
    if tasks and all(task.status in {"已完成", "验收未通过"} for task in tasks):
        return "已完成"
    return "已确认"


def requirement_to_dict(requirement: ArchiveRequirement) -> dict:
    return {
        "id": requirement.code,
        "databaseId": requirement.id,
        "title": requirement.title,
        "module": requirement.module,
        "category": requirement.category,
        "version": requirement.version,
        "priority": requirement.priority,
        "status": requirement.status,
        "owner": requirement.owner or "待分配",
        "requester": requirement.requester or "客户",
        "sourceDate": _iso(requirement.source_date),
        "sourceText": requirement.source_text,
        "description": requirement.description,
        "acceptance": requirement.acceptance_criteria,
        "evidence": _json_list(requirement.evidence_json),
        "plannedRelease": _iso(requirement.planned_release),
        "createdAt": _iso(requirement.created_at),
    }


def task_to_dict(task: ArchiveDevelopmentTask) -> dict:
    return {
        "id": task.code,
        "databaseId": task.id,
        "requirementId": task.requirement.code if task.requirement else None,
        "subRequirementId": task.sub_requirement_code,
        "round": task.round_number,
        "title": task.title,
        "type": task.task_type,
        "owner": task.owner or "待分配",
        "startDate": _iso(task.start_date),
        "endDate": _iso(task.end_date),
        "status": task.status,
        "progress": task.progress,
        "selfTestResult": task.self_test_result or "",
        "selfTestDetail": task.self_test_detail or "",
        "acceptanceResult": task.acceptance_result or "",
        "acceptanceDetail": task.acceptance_detail or "",
        "acceptanceNotifiedAt": _iso(task.acceptance_notified_at),
    }


def message_to_dict(message: ArchiveInternalMessage, requirement_code: Optional[str]) -> dict:
    return {
        "id": f"MSG-{message.id}",
        "databaseId": message.id,
        "type": message.message_type,
        "title": message.title,
        "text": message.content,
        "relatedId": requirement_code or "",
        "targetRole": message.target_role,
        "createdAt": _iso(message.created_at),
        "unread": not message.is_read,
    }


def workspace(db: Session, role: str) -> dict:
    requirements = db.scalars(
        select(ArchiveRequirement)
        .options(selectinload(ArchiveRequirement.tasks), selectinload(ArchiveRequirement.events))
        .order_by(ArchiveRequirement.source_date.desc(), ArchiveRequirement.id.desc())
    ).all()
    tasks = [task for requirement in requirements for task in requirement.tasks]
    messages = db.scalars(select(ArchiveInternalMessage).order_by(ArchiveInternalMessage.id.desc()).limit(100)).all()
    requirement_codes = {requirement.id: requirement.code for requirement in requirements}
    imports_count = int(db.scalar(select(func.count()).select_from(ArchiveChatImport)) or 0)
    message_count = int(db.scalar(select(func.sum(ArchiveChatImport.message_count))) or 0)
    validations = [
        {
            "id": f"VAL-{task.id}",
            "requirementId": task.requirement.code,
            "type": "客户验收",
            "environment": "项目环境",
            "tester": task.requirement.requester or "客户",
            "date": _iso(task.updated_at or task.created_at),
            "actualResult": task.acceptance_detail or "等待验证",
            "releaseVersion": task.requirement.version,
            "result": task.acceptance_result or "待验证",
        }
        for task in tasks
        if task.self_test_result == "通过"
    ]
    return {
        "role": role,
        "messageCount": message_count,
        "imports": imports_count,
        "recognitions": [],
        "requirements": [requirement_to_dict(requirement) for requirement in requirements],
        "development": [task_to_dict(task) for task in tasks],
        "validations": validations,
        "siteMessages": [
            message_to_dict(message, requirement_codes.get(message.related_requirement_id))
            for message in messages
            if message.target_role in {"admin", role, "all"}
        ],
    }


def submit_from_assistant(
    db: Session,
    payload: ArchiveAssistantSubmitIn,
    *,
    source_type: str,
    admin_id: Optional[int] = None,
    requester_user: Optional[MiniProgramUser] = None,
) -> ArchiveRequirement:
    today = date.today()
    create_payload = ArchiveRequirementCreate(
        title=payload.title,
        module=payload.module,
        category=payload.category,
        priority=payload.priority,
        requester=payload.requester or (requester_user.nickname if requester_user else "AI助手"),
        source_date=today.isoformat(),
        source_text=payload.description,
        description=payload.description,
        acceptance_criteria=payload.acceptance_criteria,
        evidence=payload.evidence,
    )
    requirement = create_requirement(
        db,
        create_payload,
        source_type=source_type,
        admin_id=admin_id,
        requester_user_id=requester_user.id if requester_user else None,
    )
    add_message(
        db,
        "AI需求",
        f"AI助手提交{payload.category}",
        f"{requirement.code} {requirement.title}，请管理员审核并安排开发。",
        requirement,
    )
    return requirement


def handle_admin_archive_command(db: Session, role: str, username: str, message: str) -> dict:
    full_code = FULL_REQUIREMENT_PATTERN.search(message)
    if not full_code:
        return {
            "answer": "请输入完整需求编号，例如 REQ-20260718-001 或返工编号 REQ-20260718-001-1，并说明查询状态、新建开发任务、自测通过/未通过、通知客户或客户验收通过/未通过。",
            "changed": False,
        }
    code = full_code.group(0)
    requirement = get_requirement_by_code(db, code)
    tasks = tasks_for_full_code(requirement, code)
    if re.search(r"查询|状态|进度", message):
        states = "\n".join(
            f"- {task.title}：{task.status}；自测{task.self_test_result or '未记录'}；验收{task.acceptance_result or '未记录'}"
            for task in tasks
        )
        return {"answer": f"{code}\n{states}\n主需求状态：{requirement.status}", "changed": False}
    if re.search(r"新建开发任务|开始开发|自测通过|自测未通过", message) and role != "super_admin":
        raise HTTPException(status_code=403, detail="Development ledger changes require super admin")
    changed = 0
    if re.search(r"新建开发任务|开始开发", message):
        for task in tasks:
            if task.status == "待开始":
                start_task(db, task, username)
                changed += 1
        answer = f"{code} 已有 {changed} 项进入开发中。"
    elif "自测未通过" in message:
        detail = message.split("自测未通过", 1)[-1].lstrip("：: ")
        for task in tasks:
            if task.status == "开发中":
                record_self_test(db, task, "未通过", detail, username)
                changed += 1
        answer = f"{code} 已记录 {changed} 项自测未通过。"
    elif "自测通过" in message:
        detail = message.split("自测通过", 1)[-1].lstrip("：: ")
        for task in tasks:
            if task.status == "开发中":
                record_self_test(db, task, "通过", detail, username)
                changed += 1
        answer = f"{code} 已记录 {changed} 项自测通过，等待客户验收。"
    elif re.search(r"通知客户|发送验收", message):
        for task in tasks:
            if task.status == "已自测":
                notify_acceptance(db, task, username)
                changed += 1
        answer = f"AI助手已发送 {code} 的客户验收通知，共 {changed} 项。"
    elif "验收未通过" in message:
        detail = message.split("验收未通过", 1)[-1].lstrip("：: ")
        if not detail:
            raise HTTPException(status_code=400, detail="Acceptance failure detail is required")
        follow_ups = []
        for task in tasks:
            if task.status == "已自测":
                follow_up = record_acceptance(db, task, "未通过", detail, "admin", username)
                if follow_up:
                    follow_ups.append(follow_up.sub_requirement_code)
                changed += 1
        answer = f"{code} 已记录验收未通过；新一轮：{', '.join(follow_ups) or '未生成'}。"
    elif "验收通过" in message:
        detail = message.split("验收通过", 1)[-1].lstrip("：: ")
        for task in tasks:
            if task.status == "已自测":
                record_acceptance(db, task, "通过", detail, "admin", username)
                changed += 1
        answer = f"{code} 已记录 {changed} 项客户验收通过。"
    else:
        answer = f"已找到 {code}，当前主需求状态：{requirement.status}。请明确要执行的操作。"
    db.commit()
    return {"answer": answer, "changed": bool(changed)}


def handle_mini_archive_query(db: Session, user: MiniProgramUser, query: str) -> Optional[dict]:
    stripped = query.strip()
    full_code = FULL_REQUIREMENT_PATTERN.search(stripped)
    if full_code:
        requirement = get_requirement_by_code(db, full_code.group(0))
        if requirement.requester_user_id != user.id:
            return {"answer": "没有找到属于你的该需求记录。", "actions": []}
        tasks = tasks_for_full_code(requirement, full_code.group(0))
        if "验收未通过" in stripped:
            detail = stripped.split("验收未通过", 1)[-1].lstrip("：: ")
            if not detail:
                return {"answer": "请在“验收未通过”后填写详细原因。", "actions": []}
            follow_ups = []
            for task in tasks:
                if task.status == "已自测":
                    follow_up = record_acceptance(db, task, "未通过", detail, "customer", user.nickname)
                    if follow_up:
                        follow_ups.append(follow_up.sub_requirement_code)
            db.commit()
            return {"answer": f"已记录验收未通过。改进编号：{', '.join(follow_ups)}。", "actions": []}
        if "验收通过" in stripped:
            for task in tasks:
                if task.status == "已自测":
                    record_acceptance(db, task, "通过", "客户通过AI助手确认。", "customer", user.nickname)
            db.commit()
            return {"answer": f"已记录 {full_code.group(0)} 验收通过，谢谢确认。", "actions": []}
        states = "；".join(f"{task.title}：{task.status}" for task in tasks)
        return {"answer": f"{full_code.group(0)} 当前状态：{states}。", "actions": []}

    prefix_match = re.match(r"^(需求|新功能|bug|Bug|BUG|缺陷|需求变更|验证反馈)\s*[：:]\s*(.+)$", stripped, re.S)
    if not prefix_match:
        return None
    prefix, description = prefix_match.groups()
    category = "缺陷" if prefix.lower() == "bug" or prefix == "缺陷" else "需求变更" if prefix == "需求变更" else "验证反馈" if prefix == "验证反馈" else "新功能"
    payload = ArchiveAssistantSubmitIn(
        category=category,
        title=description[:80],
        description=description,
        requester=user.nickname,
    )
    requirement = submit_from_assistant(db, payload, source_type="mini_assistant", requester_user=user)
    db.commit()
    return {
        "answer": f"已提交并生成需求编号 {requirement.code}。管理员会通过站内消息审核，后续可输入“{requirement.code} 查询状态”。",
        "actions": [{"type": "archive_requirement", "requirement_code": requirement.code}],
    }


def seed_archive_data(db: Session) -> None:
    if db.scalar(select(ArchiveRequirement.id).limit(1)) is not None:
        return
    samples = [
        ("新增秘境路线收藏", "地图与路线", "新功能", "中", "开发中", "王工", "客户张总", "2026-07-18", "路线后续最好可以收藏。", "用户可收藏路线并在个人中心查看。", "收藏、取消收藏、列表查看均可正常使用。", "2026-07-25"),
        ("会员到期前消息提醒", "会员管理", "新功能", "高", "待客户验收", "周工", "客户王经理", "2026-07-17", "会员快到期要提醒一下。", "会员到期前3天发送站内提醒。", "到期前3天生成一次提醒，已续费用户不提醒。", "2026-07-21"),
        ("首页主按钮颜色调整", "首页界面", "需求变更", "低", "待开始", "陈工", "客户张总", "2026-07-16", "按钮还是改成蓝色。", "首页主按钮由绿色方案调整为蓝色。", "蓝色色值确认，文字对比清晰。", "2026-07-22"),
        ("打卡报表支持按日期筛选", "后台报表", "新功能", "中", "已完成", "李工", "客户李工", "2026-07-15", "导出打卡时按日期查。", "报表增加开始和结束日期筛选。", "筛选条件正确作用于列表与导出文件。", "2026-07-19"),
        ("修复弱网下图片重复上传", "内容发布", "缺陷", "高", "已完成", "赵工", "客户运营", "2026-07-14", "网络差时图片会传两遍。", "避免弱网重试产生重复媒体记录。", "弱网重试仅保留一份图片记录。", "2026-07-18"),
    ]
    created = []
    for index, sample in enumerate(samples, start=1):
        title, module, category, priority, status, owner, requester, source_date, source_text, description, acceptance, planned = sample
        requirement = ArchiveRequirement(
            code=f"REQ-{source_date.replace('-', '')}-{index:03d}",
            title=title,
            module=module,
            category=category,
            version="V2" if category == "需求变更" else "V1",
            priority=priority,
            status=status,
            owner=owner,
            requester=requester,
            source_type="seed",
            source_date=date.fromisoformat(source_date),
            source_text=source_text,
            description=description,
            acceptance_criteria=acceptance,
            evidence_json="[]",
            planned_release=date.fromisoformat(planned),
        )
        db.add(requirement)
        db.flush()
        task_status = "开发中" if status == "开发中" else "已自测" if status == "待客户验收" else "待开始" if status == "待开始" else "已完成"
        task = ArchiveDevelopmentTask(
            code=f"DEV-{source_date[5:7]}{source_date[8:10]}-{index:02d}",
            requirement_id=requirement.id,
            sub_requirement_code=requirement.code,
            round_number=0,
            title=title,
            task_type="综合开发",
            owner=owner,
            end_date=date.fromisoformat(planned),
            status=task_status,
            progress=35 if task_status == "开发中" else 100 if task_status in {"已自测", "已完成"} else 0,
            self_test_result="通过" if task_status in {"已自测", "已完成"} else None,
            acceptance_result="通过" if task_status == "已完成" else None,
            acceptance_detail="客户验收通过。" if task_status == "已完成" else None,
        )
        db.add(task)
        db.flush()
        add_event(db, requirement, "seed_created", "初始化档案样本", "system", task=task)
        created.append(requirement)
    add_message(db, "待验证", "会员到期提醒已完成开发", "请安排客户在预发布环境验证。", created[1])
