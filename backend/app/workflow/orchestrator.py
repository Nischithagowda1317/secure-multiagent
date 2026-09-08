from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - fallback is tested separately
    END = START = StateGraph = None

from app.agents.approval_agent import ApprovalAgent
from app.agents.coordinator import CoordinatorAgent
from app.agents.explanation_agent import ExplanationAgent
from app.agents.finance_agent import FinanceAgent
from app.agents.hr_agent import HRAgent
from app.agents.monitoring_agent import MonitoringAgent
from app.agents.project_agent import ProjectAgent
from app.agents.rag_agent import RAGAgent
from app.agents.sales_agent import SalesAgent
from app.agents.security_agent import SecurityAgent
from app.agents.types import AgentResult
from app.agents.validation_agent import ValidationAgent
from app.schemas import AgentTrace, ApprovalInfo, ChatResponse, SourceReference
from app.services.llm_service import LLMService
from app.services.repository import DataRepository
from app.services.reassignment_service import ReassignmentService
from app.services.runtime_store import RuntimeStore
from app.utils.json_tools import json_safe
from app.utils.text import pointwise_answer


class WorkflowState(TypedDict, total=False):
    query: str
    user: dict[str, Any]
    temporary_chunks: list[dict[str, Any]]
    attached_files: list[dict[str, Any]]
    workflow_run_id: str
    plan: dict[str, Any]
    project_context: dict[str, Any]
    reassignment_plan: dict[str, Any] | None
    reassignment_error: str | None
    security: Any
    injection_detected: bool
    results: list[AgentResult]
    durations: dict[str, int]
    validation: dict[str, Any]
    approval: dict[str, Any] | None
    explanation: dict[str, Any]
    final_answer: str
    response: dict[str, Any]


class WorkflowOrchestrator:
    PERMISSIONS = {
        "WFD001": ["ai.query"],
        "WFD002": ["project.read"],
        "WFD003": ["project.read", "employee.read"],
        "WFD004": ["employee.salary.read"],
        "WFD005": ["task.reassign", "project.read", "employee.read"],
        "WFD006": ["sales.read"],
        "WFD007": ["sales.read"],
        "WFD008": ["finance.read", "expense.approve"],
        "WFD009": ["leave.read_own"],
        "WFD010": ["ai.query"],
        "WFD011": ["evaluation.read"],
        "WFD012": ["employee.read", "project.read", "sales.read", "finance.read"],
    }
    RESOURCE_TYPES = {
        "WFD001": "enterprise_document",
        "WFD002": "project",
        "WFD003": "project_and_employee",
        "WFD004": "salary",
        "WFD005": "task_action",
        "WFD006": "sales",
        "WFD007": "sales_action",
        "WFD008": "purchase",
        "WFD009": "leave",
        "WFD010": "security_document",
        "WFD011": "evaluation",
        "WFD012": "executive_data",
    }
    ACTION_WORKFLOWS = {"WFD005", "WFD007", "WFD008"}

    def __init__(
        self,
        *,
        repository: DataRepository,
        runtime_store: RuntimeStore,
        llm: LLMService,
        coordinator: CoordinatorAgent,
        security: SecurityAgent,
        rag: RAGAgent,
        hr: HRAgent,
        project: ProjectAgent,
        sales: SalesAgent,
        finance: FinanceAgent,
        monitoring: MonitoringAgent,
        validation: ValidationAgent,
        explanation: ExplanationAgent,
        approval: ApprovalAgent,
        reassignment: ReassignmentService,
    ):
        self.repository = repository
        self.runtime_store = runtime_store
        self.llm = llm
        self.coordinator = coordinator
        self.security_agent = security
        self.rag_agent = rag
        self.hr_agent = hr
        self.project_agent = project
        self.sales_agent = sales
        self.finance_agent = finance
        self.monitoring_agent = monitoring
        self.validation_agent = validation
        self.explanation_agent = explanation
        self.approval_agent = approval
        self.reassignment_service = reassignment
        self.graph = self._build_graph() if StateGraph else None

    def _build_graph(self):
        graph = StateGraph(WorkflowState)
        graph.add_node("coordinate", self._coordinate)
        graph.add_node("secure", self._secure)
        graph.add_node("execute", self._execute)
        graph.add_node("validate", self._validate)
        graph.add_node("approve", self._approve)
        graph.add_node("explain", self._explain)
        graph.add_node("finalize", self._finalize)
        graph.add_edge(START, "coordinate")
        graph.add_edge("coordinate", "secure")
        graph.add_edge("secure", "execute")
        graph.add_edge("execute", "validate")
        graph.add_edge("validate", "approve")
        graph.add_edge("approve", "explain")
        graph.add_edge("explain", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile()

    async def run(
        self,
        *,
        query: str,
        user: dict[str, Any],
        temporary_chunks: list[dict[str, Any]] | None = None,
        attached_files: list[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        normalized_files = list(attached_files or [])
        if not normalized_files and temporary_chunks:
            # Preserve compatibility for internal callers that predate the
            # richer attachment metadata and provide only temporary RAG chunks.
            grouped: dict[str, list[str]] = {}
            for chunk in temporary_chunks:
                filename = str(chunk.get("document_title") or "attachment")
                grouped.setdefault(filename, []).append(str(chunk.get("chunk_text", "")))
            normalized_files = [
                {
                    "filename": filename,
                    "content_type": "application/octet-stream",
                    "size_bytes": 0,
                    "extracted_text": "\n".join(texts),
                    "chunk_count": len(texts),
                }
                for filename, texts in grouped.items()
            ]
        state: WorkflowState = {
            "query": query,
            "user": user,
            "temporary_chunks": temporary_chunks or [],
            "attached_files": normalized_files,
            "workflow_run_id": f"LIVE-{uuid.uuid4().hex[:12].upper()}",
            "results": [],
            "durations": {},
        }
        if self.graph:
            output = await self.graph.ainvoke(state)
        else:
            output = await self._fallback(state)
        response = ChatResponse.model_validate(output["response"])
        self.runtime_store.save_chat(
            str(user["user_id"]), response.workflow_run_id, query, response.model_dump()
        )
        self.runtime_store.add_audit(
            user_id=str(user["user_id"]),
            event_type="workflow_completed",
            resource_type="workflow",
            resource_id=response.workflow_run_id,
            decision=response.status,
            details={
                "workflow_id": response.workflow_id,
                "confidence": response.confidence,
                "grounding_score": response.grounding_score,
                "approval_required": response.approval.required,
                "agents": [agent.agent_id for agent in response.agents],
            },
        )
        return response

    async def _fallback(self, state: WorkflowState) -> WorkflowState:
        for node in (
            self._coordinate,
            self._secure,
            self._execute,
            self._validate,
            self._approve,
            self._explain,
            self._finalize,
        ):
            update = await node(state)
            state.update(update)
        return state

    async def _coordinate(self, state: WorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        plan, result = self.coordinator.plan(
            state["query"], state.get("attached_files")
        )
        return self._update(
            state,
            result,
            start,
            plan=plan,
            project_context=dict(plan.get("project_context", {})),
        )

    async def _secure(self, state: WorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        workflow_id = state["plan"]["workflow_id"]
        permissions = list(self.PERMISSIONS.get(workflow_id, ["ai.query"]))
        backend_permission = state["plan"].get("backend_required_permission")
        if backend_permission:
            permissions = [str(backend_permission)]
        if workflow_id == "WFD009" and any(
            word in state["query"].lower() for word in ("approve", "reject", "all employees")
        ):
            permissions = ["leave.read_all", "leave.approve"]
        authorization, result = self.security_agent.check_many(
            user=state["user"],
            permissions=permissions,
            resource_type=self.RESOURCE_TYPES.get(workflow_id, "enterprise_resource"),
            resource_id=state.get("project_context", {}).get("project_id"),
            query=state["query"],
        )
        return self._update(
            state,
            result,
            start,
            security=authorization.decision,
            injection_detected=authorization.injection_detected,
        )

    async def _execute(self, state: WorkflowState) -> dict[str, Any]:
        if state["security"].decision != "ALLOW":
            return {}
        workflow_id = state["plan"]["workflow_id"]
        query = state["query"] or "Summarize the attached document."
        user = state["user"]
        results = list(state.get("results", []))
        durations = dict(state.get("durations", {}))
        project_context = dict(state.get("project_context", {}))
        reassignment_plan = state.get("reassignment_plan")
        reassignment_error = state.get("reassignment_error")
        temporary_chunks = (
            state.get("temporary_chunks")
            if state["plan"].get("attachment_context_used")
            else None
        )
        retrieval_scope = str(
            state["plan"].get("retrieval_scope") or "enterprise_only"
        )
        attachment_mode = state["plan"].get("attachment_mode")

        async def run_agent(agent_id: str, function, *args, **kwargs):
            start = time.perf_counter()
            value = function(*args, **kwargs)
            if asyncio.iscoroutine(value):
                value = await value
            results.append(value)
            durations[agent_id] = int((time.perf_counter() - start) * 1000)
            return value

        async def run_project_then_hr() -> tuple[AgentResult, AgentResult | None]:
            nonlocal project_context
            project_result = await run_agent(
                "A005", self.project_agent.run, query, project_context
            )
            project_context = self._normalized_project_context(
                project_context, project_result
            )
            # An unknown project yields no HR access or company-wide fallback.
            if project_context.get("requested") and not project_context.get("found"):
                return project_result, None
            hr_result = await run_agent(
                "A004",
                self.hr_agent.run,
                query,
                user,
                project_context=project_context,
            )
            return project_result, hr_result

        if workflow_id in {"WFD001", "WFD010"}:
            await run_agent(
                "A003",
                self.rag_agent.run,
                query,
                user,
                temporary_chunks,
                retrieval_scope,
                attachment_mode,
            )
        elif workflow_id == "WFD002":
            await run_agent("A005", self.project_agent.run, query, project_context)
        elif workflow_id == "WFD003":
            await run_project_then_hr()
        elif workflow_id == "WFD004":
            await run_agent("A004", self.hr_agent.run, query, user)
        elif workflow_id == "WFD005":
            project_result, hr_result = await run_project_then_hr()
            if hr_result is None:
                reassignment_error = project_result.summary
            else:
                reassignment_plan, reassignment_error = self.reassignment_service.prepare(
                    query=query,
                    project_context=project_context,
                    hr_content=(
                        hr_result.content if isinstance(hr_result.content, dict) else {}
                    ),
                )
                if reassignment_plan and isinstance(project_result.content, dict):
                    project_result.content["reassignment_plan"] = reassignment_plan
        elif workflow_id == "WFD006":
            await run_agent("A006", self.sales_agent.run, query)
        elif workflow_id == "WFD007":
            await run_agent("A006", self.sales_agent.run, query)
            await run_agent("A007", self.finance_agent.run, query)
        elif workflow_id == "WFD008":
            await run_agent("A007", self.finance_agent.run, query)
        elif workflow_id == "WFD009":
            await run_agent("A004", self.hr_agent.run, query, user)
            await run_agent(
                "A003", self.rag_agent.run, query, user, temporary_chunks,
                retrieval_scope, attachment_mode
            )
        elif workflow_id == "WFD011":
            await run_agent("A011", self.monitoring_agent.run, query)
        elif workflow_id == "WFD012":
            await run_agent(
                "A003", self.rag_agent.run, query, user, temporary_chunks,
                retrieval_scope, attachment_mode
            )
            await run_project_then_hr()
            await run_agent("A006", self.sales_agent.run, query)
            await run_agent("A007", self.finance_agent.run, query)

        # A chat attachment is part of the current request regardless of the
        # router's primary business workflow. Add a temporary-document RAG pass
        # whenever the selected workflow did not already invoke the RAG agent.
        if temporary_chunks and not any(
            result.agent_id == "A003" for result in results
        ):
            await run_agent(
                "A003",
                self.rag_agent.run,
                query,
                user,
                temporary_chunks,
                retrieval_scope,
                attachment_mode,
            )
        return {
            "results": results,
            "durations": durations,
            "project_context": project_context,
            "reassignment_plan": reassignment_plan,
            "reassignment_error": reassignment_error,
        }

    def _normalized_project_context(
        self,
        current: dict[str, Any],
        project_result: AgentResult,
    ) -> dict[str, Any]:
        """Preserve the coordinator scope while adding Project Agent membership."""
        candidate: dict[str, Any] = {}
        if isinstance(project_result.content, dict):
            value = project_result.content.get("project_context")
            if isinstance(value, dict):
                candidate = value
        context = {**current, **candidate}
        if context.get("found") and context.get("project_id"):
            member_ids = context.get("member_employee_ids")
            if not isinstance(member_ids, (list, tuple, set)):
                member_ids = self.repository.project_member_ids(
                    str(context["project_id"])
                )
            normalized_ids = list(dict.fromkeys(map(str, member_ids)))
            context["member_employee_ids"] = normalized_ids
            context["member_count"] = len(normalized_ids)
        return context

    async def _validate(self, state: WorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        workflow_id = state["plan"]["workflow_id"]
        force = bool(state["plan"].get("sensitive_action_requested"))
        validation, result = self.validation_agent.run(
            workflow_id=workflow_id,
            results=state.get("results", []),
            router_confidence=float(state["plan"].get("router_confidence", 0.75)),
            security_decision=state["security"].decision,
            injection_detected=bool(state.get("injection_detected", False)),
            force_approval=force,
            query=state["query"],
            project_context=state.get("project_context"),
            reassignment_plan=state.get("reassignment_plan"),
            user_permissions=list(state["user"].get("permissions", [])),
            retrieval_scope=str(
                state["plan"].get("retrieval_scope") or "enterprise_only"
            ),
            attached_files=list(state["plan"].get("attached_files", [])),
        )
        plan = state.get("reassignment_plan")
        if plan is not None:
            plan = dict(plan)
            plan_validation = validation.get("reassignment_plan_validation", {})
            plan["validation_status"] = (
                "Valid" if plan_validation.get("passed") else "Invalid"
            )
        return self._update(
            state, result, start, validation=validation, reassignment_plan=plan
        )

    async def _approve(self, state: WorkflowState) -> dict[str, Any]:
        if state["security"].decision != "ALLOW":
            return {"approval": None}
        if state["validation"].get("status") == "FAIL":
            return {"approval": None}
        if not state["plan"].get("sensitive_action_requested"):
            return {"approval": None}
        if (
            state["plan"]["workflow_id"] == "WFD005"
            and not state.get("reassignment_plan")
        ):
            return {"approval": None}
        needs_review = bool(state["validation"].get("human_review_required"))
        if not needs_review:
            return {"approval": None}
        start = time.perf_counter()
        record, result = self.approval_agent.create(
            state["plan"]["workflow_id"],
            state["query"],
            state["user"],
            str(state["plan"].get("risk_tier", "Medium")),
            reassignment_plan=state.get("reassignment_plan"),
        )
        return self._update(state, result, start, approval=record)

    async def _explain(self, state: WorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        workflow = self.repository.workflow_map[state["plan"]["workflow_id"]]
        explanation, result = self.explanation_agent.run(
            workflow,
            state.get("results", []),
            state["validation"],
            plan=state.get("plan"),
        )
        return self._update(state, result, start, explanation=explanation)

    async def _finalize(self, state: WorkflowState) -> dict[str, Any]:
        domain_results = [
            result
            for result in state.get("results", [])
            if result.agent_id not in {"A001", "A002", "A008", "A009", "A010"}
        ]
        llm_response_generated = False
        retrieval_scope = str(
            state.get("plan", {}).get("retrieval_scope") or "enterprise_only"
        )
        attachment_only = retrieval_scope == "attachment_only"
        attachment_scoped = retrieval_scope in {
            "attachment_only",
            "attachment_plus_enterprise",
        }
        if state["security"].decision != "ALLOW":
            answer = (
                "Access denied. The requested operation requires "
                f"{state['security'].permission}. {state['security'].reason}"
            )
        else:
            attachment_result = next(
                (result for result in domain_results if result.agent_id == "A003"),
                None,
            )
            deterministic_answer = (
                attachment_result.summary
                if attachment_scoped and attachment_result is not None
                else self._reassignment_answer(state)
            )
            if deterministic_answer is None:
                deterministic_answer = self._project_workload_answer(
                    state, domain_results
                )
            evidence = [
                source for result in domain_results for source in result.sources
            ]
            extractive_sections = [
                {"title": result.agent_name, "content": result.summary}
                for result in domain_results
            ]
            if deterministic_answer is None:
                deterministic_answer = self.llm.extractive_answer(
                    state["query"] or "Summarize the attached document.",
                    evidence,
                    extractive_sections,
                )

            # Generative text is created only from results produced after the
            # deterministic security decision. Validation and approval state
            # are context, never instructions that can execute an action.
            if (
                self.llm.generative_enabled
                and state["validation"].get("status") != "FAIL"
                and not attachment_scoped
            ):
                approval_record = state.get("approval")
                structured_sections = [
                    {
                        "title": result.agent_name,
                        "summary": result.summary,
                        "content": result.content,
                    }
                    for result in domain_results
                ]
                structured_sections.append(
                    {
                        "title": "Workflow Control State",
                        "summary": "Deterministic backend state",
                        "content": {
                            "workflow": state["plan"]["workflow_id"],
                            "validation": state["validation"],
                            "approval": {
                                "required": bool(approval_record),
                                "approval_id": (
                                    approval_record.get("approval_id")
                                    if approval_record
                                    else None
                                ),
                                "status": (
                                    approval_record.get("status")
                                    if approval_record
                                    else None
                                ),
                            },
                            "backend_execution_confirmed": False,
                        },
                    }
                )
                answer = await self.llm.synthesize(
                    state["query"] or "Summarize the attached document.",
                    evidence,
                    structured_sections,
                    fallback_text=deterministic_answer,
                    retrieval_scope=retrieval_scope,
                )
                llm_response_generated = True
            else:
                answer = deterministic_answer
        llm_response_validation = self.validation_agent.validate_llm_response(
            answer=answer,
            error_status=(
                self.llm.last_call.error_status
                if llm_response_generated and self.llm.last_call
                else None
            ),
            approval_pending=bool(state.get("approval")),
            numeric_grounding_status=(
                self.llm.last_call.numeric_grounding_status
                if llm_response_generated and self.llm.last_call
                else "not_applied"
            ),
            normalized_numeric_match_count=(
                self.llm.last_call.normalized_numeric_match_count
                if llm_response_generated and self.llm.last_call
                else 0
            ),
        )
        llm_response_validation["applied"] = llm_response_generated
        state["validation"]["llm_response_validation"] = llm_response_validation
        response_warnings = list(state["validation"].get("warnings", []))
        response_warnings.extend(llm_response_validation["warnings"])
        sources = self._unique_sources(
            domain_results if attachment_only else state.get("results", [])
        )
        approval_record = state.get("approval")
        approval = ApprovalInfo(
            required=bool(approval_record),
            approval_id=approval_record.get("approval_id") if approval_record else None,
            status=approval_record.get("status") if approval_record else None,
            required_roles=approval_record.get("required_roles", []) if approval_record else [],
            reason=(
                "The user's requested sensitive action requires human approval."
                if approval_record
                else None
            ),
        )
        if state["security"].decision != "ALLOW":
            status = "Access Denied"
        elif state["validation"].get("status") == "FAIL":
            status = "Validation Failed"
        elif approval_record:
            status = "Awaiting Approval"
        else:
            status = "Completed"
        traces = []
        for sequence, result in enumerate(state.get("results", []), start=1):
            traces.append(
                AgentTrace(
                    sequence=sequence,
                    agent_id=result.agent_id,
                    agent_name=result.agent_name,
                    status="Success",
                    duration_ms=int(state.get("durations", {}).get(result.agent_id, 0)),
                    summary=result.summary,
                    confidence=result.confidence,
                ).model_dump()
            )
        workflow_id = state["plan"]["workflow_id"]
        workflow = self.repository.workflow_map[workflow_id]
        answer = pointwise_answer(answer)
        response = ChatResponse(
            workflow_run_id=state["workflow_run_id"],
            workflow_id=workflow_id,
            workflow_name=str(workflow["workflow_name"]),
            status=status,
            answer=answer,
            sections=[result.section() for result in domain_results],
            security=state["security"],
            agents=traces,
            sources=[SourceReference.model_validate(source) for source in sources],
            confidence=float(state["validation"]["correctness_score"]),
            grounding_score=float(state["validation"]["grounding_score"]),
            approval=approval,
            explanation=state.get("explanation", {}),
            warnings=list(dict.fromkeys(response_warnings)),
        )
        return {"final_answer": answer, "response": json_safe(response.model_dump())}

    @staticmethod
    def _reassignment_answer(state: WorkflowState) -> str | None:
        if state.get("plan", {}).get("workflow_id") != "WFD005":
            return None
        plan = state.get("reassignment_plan")
        approval = state.get("approval")
        if not plan or not approval:
            reason = state.get("reassignment_error")
            if not reason:
                validation = state.get("validation", {}).get(
                    "reassignment_plan_validation", {}
                )
                reason = "; ".join(validation.get("errors", []))
            return f"Reassignment plan could not be prepared. {reason or 'The plan was invalid.'}"
        return "\n".join(
            [
                "Reassignment plan prepared and awaiting approval.",
                "",
                f"Project: {plan['project_name']} ({plan['project_id']})",
                f"Task: {plan['task_id']} - {plan['task_title']}",
                (
                    f"Current Assignee: {plan['source_employee_name']} "
                    f"({plan['source_employee_id']})"
                ),
                (
                    f"New Assignee: {plan['target_employee_name']} "
                    f"({plan['target_employee_id']})"
                ),
                f"Current Assignee Workload: {float(plan['source_workload_percent']):g}%",
                f"New Assignee Workload: {float(plan['target_workload_percent']):g}%",
                f"Reason: {plan['reason']}",
                f"Risk: {plan['risk_tier']}",
                f"Approval ID: {approval['approval_id']}",
                "Status: Awaiting Approval",
            ]
        )

    @staticmethod
    def _project_workload_answer(
        state: WorkflowState, domain_results: list[AgentResult]
    ) -> str | None:
        context = state.get("project_context", {})
        if not context.get("requested"):
            return None
        project_result = next(
            (result for result in domain_results if result.agent_id == "A005"), None
        )
        if project_result is None:
            return None
        if not context.get("found"):
            requested_name = context.get("requested_name") or "requested project"
            return f"Project '{requested_name}' was not found."
        hr_result = next(
            (result for result in domain_results if result.agent_id == "A004"), None
        )
        if not isinstance(project_result.content, dict) or hr_result is None:
            return None

        project = project_result.content.get("project", {})
        metrics = project_result.content.get("task_metrics", {})
        project_name = str(project.get("project_name", context.get("project_name", "Project")))
        lines = [f"{project_name} is currently {project.get('current_status', 'Unknown')}."]
        if project:
            lines.extend(
                [
                    "",
                    f"Current Progress: {project.get('current_progress_percent')}%",
                    f"Expected Progress: {project.get('expected_progress_percent')}%",
                    f"Progress Gap: {project_result.content.get('progress_gap_percent')}%",
                    "",
                    f"Overdue Tasks: {metrics.get('overdue_unfinished', 0)}",
                    f"Blocked Tasks: {metrics.get('blocked', 0)}",
                ]
            )

        hr_content = hr_result.content if isinstance(hr_result.content, dict) else {}
        employees = hr_content.get("employees", [])
        condition = str(hr_content.get("workload_condition", "workload"))
        lines.append("")
        if not context.get("member_employee_ids"):
            lines.append(f"No members are assigned to {project_name}.")
        elif condition == "overloaded" and not employees:
            lines.append("No overloaded team members were found for this project.")
        else:
            titles = {
                "overloaded": f"Overloaded {project_name} Team Members:",
                "available": f"Available {project_name} Team Members:",
                "high_or_overloaded": f"High-Workload {project_name} Team Members:",
                "project_members": f"{project_name} Team Members:",
            }
            lines.append(titles.get(condition, f"{project_name} Team Members:"))
            for index, employee in enumerate(employees, start=1):
                workload = float(employee.get("total_workload_percent", 0))
                workload_text = f"{workload:g}"
                lines.append(
                    f"{index}. {employee.get('full_name')} ({employee.get('employee_id')}) - "
                    f"{workload_text}%"
                )

        risks = project_result.content.get("top_risks", [])
        if risks:
            lines.extend(["", "Primary Risks:"])
            lines.extend(f"- {risk.get('risk_title')}" for risk in risks)
        return "\n".join(lines)

    @staticmethod
    def _update(
        state: WorkflowState,
        result: AgentResult,
        started: float,
        **values: Any,
    ) -> dict[str, Any]:
        results = list(state.get("results", []))
        results.append(result)
        durations = dict(state.get("durations", {}))
        durations[result.agent_id] = int((time.perf_counter() - started) * 1000)
        return {"results": results, "durations": durations, **values}

    @staticmethod
    def _unique_sources(results: list[AgentResult]) -> list[dict[str, Any]]:
        output = []
        seen = set()
        for result in results:
            for source in result.sources:
                normalized = {
                    "source_id": str(source.get("source_id", "source")),
                    "title": str(source.get("title", "Source")),
                    "source_type": str(source.get("source_type", "Data")),
                    "section": source.get("section"),
                    "path": source.get("path"),
                    "score": source.get("score"),
                }
                key = (normalized["source_id"], normalized["section"], normalized["path"])
                if key not in seen:
                    seen.add(key)
                    output.append(normalized)
        return output
