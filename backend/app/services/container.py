from __future__ import annotations

from dataclasses import dataclass

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
from app.agents.validation_agent import ValidationAgent
from app.ml.registry import ModelRegistry
from app.security.rbac import RBACService
from app.services.document_service import DocumentService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.reassignment_service import ReassignmentService
from app.services.repository import DataRepository
from app.services.runtime_store import RuntimeStore
from app.settings import Settings
from app.workflow.orchestrator import WorkflowOrchestrator


@dataclass
class ServiceContainer:
    settings: Settings
    repository: DataRepository
    runtime_store: RuntimeStore
    models: ModelRegistry
    rbac: RBACService
    rag: RAGService
    llm: LLMService
    documents: DocumentService
    reassignment: ReassignmentService
    orchestrator: WorkflowOrchestrator


def build_services(settings: Settings) -> ServiceContainer:
    runtime_store = RuntimeStore(settings.runtime_root / "assistant_runtime.db")
    repository = DataRepository(settings, runtime_store)
    models = ModelRegistry(settings)
    rbac = RBACService(runtime_store)
    rag_service = RAGService(settings, repository, runtime_store)
    llm = LLMService(settings)
    documents = DocumentService(settings, runtime_store, rag_service)
    reassignment = ReassignmentService(
        repository, models, settings.snapshot_date
    )

    coordinator = CoordinatorAgent(repository, models)
    security = SecurityAgent(rbac)
    rag_agent = RAGAgent(rag_service, llm)
    hr_agent = HRAgent(repository, models)
    project_agent = ProjectAgent(repository, models, settings.snapshot_date)
    sales_agent = SalesAgent(repository, models)
    finance_agent = FinanceAgent(repository)
    monitoring_agent = MonitoringAgent(repository)
    validation_agent = ValidationAgent(repository)
    explanation_agent = ExplanationAgent()
    approval_agent = ApprovalAgent(runtime_store)

    orchestrator = WorkflowOrchestrator(
        repository=repository,
        runtime_store=runtime_store,
        llm=llm,
        coordinator=coordinator,
        security=security,
        rag=rag_agent,
        hr=hr_agent,
        project=project_agent,
        sales=sales_agent,
        finance=finance_agent,
        monitoring=monitoring_agent,
        validation=validation_agent,
        explanation=explanation_agent,
        approval=approval_agent,
        reassignment=reassignment,
    )
    return ServiceContainer(
        settings=settings,
        repository=repository,
        runtime_store=runtime_store,
        models=models,
        rbac=rbac,
        rag=rag_service,
        llm=llm,
        documents=documents,
        reassignment=reassignment,
        orchestrator=orchestrator,
    )
