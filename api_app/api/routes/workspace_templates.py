import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import parse_obj_as
from starlette import status

from api.dependencies.database import get_repository
from db.errors import DuplicateEntity, EntityDoesNotExist, EntityVersionExist
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from models.schemas.resource_template import ResourceTemplateInResponse, ResourceTemplateInformationInList
from models.schemas.workspace_template import WorkspaceTemplateInCreate, WorkspaceTemplateInResponse
from resources import strings
from services.authentication import get_current_admin_user


workspace_templates_admin_router = APIRouter(dependencies=[Depends(get_current_admin_user)])


def get_current_template_by_name(template_name: str, template_repo: ResourceTemplateRepository, resource_type: ResourceType, parent_service_template_name: str = "") -> dict:
    try:
        template = template_repo.get_current_template(template_name, resource_type, parent_service_template_name)
        return template_repo.enrich_template(template)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.TEMPLATE_DOES_NOT_EXIST)
    except DuplicateEntity:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.NO_UNIQUE_CURRENT_FOR_TEMPLATE)
    except Exception as e:
        logging.debug(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)


# WORKSPACE TEMPLATES
@workspace_templates_admin_router.get("/workspace-templates", response_model=ResourceTemplateInformationInList, name=strings.API_GET_WORKSPACE_TEMPLATES)
async def get_workspace_templates(template_repo=Depends(get_repository(ResourceTemplateRepository))) -> ResourceTemplateInformationInList:
    templates_infos = template_repo.get_templates_information(ResourceType.Workspace)
    return ResourceTemplateInformationInList(templates=templates_infos)


@workspace_templates_admin_router.get("/workspace-templates/{workspace_template_name}", response_model=WorkspaceTemplateInResponse, name=strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME, response_model_exclude_none=True)
async def get_current_workspace_template_by_name(workspace_template_name: str, template_repo=Depends(get_repository(ResourceTemplateRepository))) -> WorkspaceTemplateInResponse:
    template = get_current_template_by_name(workspace_template_name, template_repo, ResourceType.Workspace)
    return parse_obj_as(WorkspaceTemplateInResponse, template)


@workspace_templates_admin_router.post("/workspace-templates", status_code=status.HTTP_201_CREATED, response_model=WorkspaceTemplateInResponse, response_model_exclude_none=True, name=strings.API_CREATE_WORKSPACE_TEMPLATES)
async def register_workspace_template(template_input: WorkspaceTemplateInCreate, template_repo=Depends(get_repository(ResourceTemplateRepository))) -> ResourceTemplateInResponse:
    try:
        return template_repo.create_and_validate_template(template_input, ResourceType.Workspace)
    except EntityVersionExist:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_TEMPLATE_VERSION_EXISTS)
