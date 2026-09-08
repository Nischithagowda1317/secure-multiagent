from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.security.auth import current_user
from app.utils.json_tools import json_safe


router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def overview(request: Request, user=Depends(current_user)):
    repo = request.app.state.services.repository
    projects = repo.table("projects")
    orders = repo.table("sales_orders")
    approvals = repo.table("approval_requests")
    workflow_runs = repo.table("workflow_runs")
    latest_workload = repo.latest_workload()
    permissions = set(user.get("permissions", []))
    result = {
        "company": "NexaCore Technologies",
        "snapshot_date": request.app.state.services.settings.snapshot_date,
        "dataset_counts": repo.dataset_counts(),
        "projects": {
            "total": int(len(projects)),
            "at_risk": int((projects["current_status"] == "At Risk").sum()),
            "high_risk": int((projects["risk_level"] == "High").sum()),
        },
        "sales": {
            "orders": int(len(orders)),
            "sales_usd": round(float(orders["sales_usd"].sum()), 2),
            "profit_usd": round(float(orders["profit_usd"].sum()), 2),
        },
        "approvals": {
            "pending_source": int((approvals["status"] == "Pending").sum()),
            "pending_runtime": len(request.app.state.services.runtime_store.list_approvals("Pending")),
        },
        "workflows": json_safe(workflow_runs["status"].value_counts().to_dict()),
    }
    if "employee.read" in permissions:
        result["workforce"] = {
            "employees": int(len(repo.table("employees"))),
            "overloaded": int((latest_workload["total_workload_percent"] >= 100).sum()),
            "high_or_overloaded": int((latest_workload["total_workload_percent"] >= 90).sum()),
        }
    return result


@router.get("/projects")
async def projects(request: Request, user=Depends(current_user)):
    services = request.app.state.services
    decision = services.rbac.authorize(
        user=user,
        permission="project.read",
        resource_type="project",
        input_text="dashboard project list",
    )
    if decision.decision.decision != "ALLOW":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail=decision.decision.reason)
    frame = services.repository.table("projects").copy()
    return json_safe(frame.to_dict(orient="records"))


@router.get("/projects/{project_id}")
async def project_detail(project_id: str, request: Request, user=Depends(current_user)):
    services = request.app.state.services
    decision = services.rbac.authorize(
        user=user,
        permission="project.read",
        resource_type="project",
        resource_id=project_id,
        input_text=f"dashboard project {project_id}",
    )
    if decision.decision.decision != "ALLOW":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail=decision.decision.reason)
    return services.repository.project_detail(project_id)


@router.get("/hr")
async def hr(request: Request, user=Depends(current_user)):
    from fastapi import HTTPException
    services = request.app.state.services
    decision = services.rbac.authorize(
        user=user,
        permission="employee.read",
        resource_type="employee",
        input_text="dashboard hr summary",
    )
    if decision.decision.decision != "ALLOW":
        raise HTTPException(status_code=403, detail=decision.decision.reason)
    employees = services.repository.table("employees")
    workload = services.repository.latest_workload()
    workload["predicted_status"] = services.models.predict_workload(workload)
    return {
        "headcount_by_department": json_safe(
            employees.groupby("department_name")["employee_id"].count().sort_values(ascending=False).to_dict()
        ),
        "workload_status": json_safe(workload["predicted_status"].value_counts().to_dict()),
        "top_overtime": json_safe(
            employees.sort_values("overtime_hours_ytd", ascending=False)[
                ["employee_id", "full_name", "department_name", "overtime_hours_ytd"]
            ].head(10).to_dict(orient="records")
        ),
    }


@router.get("/sales")
async def sales(request: Request, user=Depends(current_user)):
    from fastapi import HTTPException
    services = request.app.state.services
    decision = services.rbac.authorize(
        user=user,
        permission="sales.read",
        resource_type="sales",
        input_text="dashboard sales summary",
    )
    if decision.decision.decision != "ALLOW":
        raise HTTPException(status_code=403, detail=decision.decision.reason)
    orders = services.repository.table("sales_orders")
    region = orders.groupby("region").agg(sales_usd=("sales_usd", "sum"), profit_usd=("profit_usd", "sum"), orders=("order_id", "count")).reset_index().round(2)
    category = orders.groupby("product_category").agg(sales_usd=("sales_usd", "sum"), profit_usd=("profit_usd", "sum"), orders=("order_id", "count")).reset_index().round(2)
    return {
        "region": json_safe(region.sort_values("sales_usd", ascending=False).to_dict(orient="records")),
        "category": json_safe(category.sort_values("sales_usd", ascending=False).to_dict(orient="records")),
    }


@router.get("/monitoring")
async def monitoring(request: Request, user=Depends(current_user)):
    from fastapi import HTTPException
    services = request.app.state.services
    decision = services.rbac.authorize(
        user=user,
        permission="evaluation.read",
        resource_type="evaluation",
        input_text="dashboard monitoring",
    )
    if decision.decision.decision != "ALLOW":
        raise HTTPException(status_code=403, detail=decision.decision.reason)
    result = services.orchestrator.monitoring_agent.run("agent reliability dashboard")
    return {**result.content, "llm": services.llm.metrics()}
