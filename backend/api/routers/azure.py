"""Azure environment and deployment inspection endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from ...core.config import settings
from ...schemas import AzureDeployment, AzureDeployments, AzureStatus

router = APIRouter()


@router.get("/azure", response_model=AzureStatus, tags=["ops"])
def azure_status() -> AzureStatus:
    resource = settings.azure_foundry_resource
    project = settings.azure_foundry_project
    identity = settings.azure_ai_auth.lower() == "identity"

    foundry_url = portal_url = None
    if resource:
        foundry_url = "https://ai.azure.com/"
        if settings.azure_resource_group and project:
            portal_url = (
                "https://portal.azure.com/#@/resource/subscriptions//resourceGroups/"
                f"{settings.azure_resource_group}/providers/Microsoft.CognitiveServices/"
                f"accounts/{resource}/overview"
            )

    deployments = AzureDeployments(
        available=False,
        reason=None if identity else (
            "Listing deployments reads the Azure control plane, which requires Microsoft "
            "Entra authentication. This app is running with AZURE_AI_AUTH=key (the Docker "
            "default). Run it locally after `az login` to see them."
        ),
    )
    subscription_id = None

    if identity and resource and settings.azure_resource_group:
        try:
            import httpx
            from azure.identity import DefaultAzureCredential

            token = DefaultAzureCredential().get_token(
                "https://management.azure.com/.default"
            )
            headers = {"Authorization": f"Bearer {token.token}"}
            subscriptions = httpx.get(
                "https://management.azure.com/subscriptions",
                params={"api-version": "2022-12-01"},
                headers=headers,
                timeout=20,
            ).json().get("value", [])
            if subscriptions:
                subscription_id = subscriptions[0]["subscriptionId"]
                url = (
                    f"https://management.azure.com/subscriptions/{subscription_id}"
                    f"/resourceGroups/{settings.azure_resource_group}"
                    f"/providers/Microsoft.CognitiveServices/accounts/{resource}/deployments"
                )
                data = httpx.get(
                    url,
                    params={"api-version": "2023-05-01"},
                    headers=headers,
                    timeout=20,
                ).json()
                items = []
                for deployment in data.get("value", []):
                    properties = deployment.get("properties", {})
                    sku = deployment.get("sku", {})
                    items.append(AzureDeployment(
                        name=deployment.get("name"),
                        model=(properties.get("model") or {}).get("name"),
                        version=(properties.get("model") or {}).get("version"),
                        sku=sku.get("name"),
                        capacity=sku.get("capacity"),
                        state=properties.get("provisioningState"),
                    ))
                deployments = AzureDeployments(available=True, items=items)
        except Exception as error:
            deployments = AzureDeployments(
                available=False,
                reason=f"{type(error).__name__}: {error}",
            )

    return AzureStatus(
        configured=bool(settings.azure_ai_endpoint),
        auth=settings.azure_ai_auth,
        auth_note=None if identity else (
            "Key authentication: the Agent Service and the control plane are unavailable. "
            "This is expected inside Docker, where there is no `az login` to borrow."
        ),
        resource=resource or None,
        resource_group=settings.azure_resource_group or None,
        project=project or None,
        location=settings.azure_location or None,
        subscription_id=subscription_id,
        inference_endpoint=settings.azure_ai_endpoint or None,
        project_endpoint=settings.azure_ai_project_endpoint or None,
        openai_endpoint=settings.azure_openai_endpoint or None,
        chat_deployment=settings.azure_ai_chat_deployment,
        embedding_deployment=settings.azure_ai_embedding_deployment,
        foundry_url=foundry_url,
        portal_url=portal_url,
        deployments=deployments,
    )
