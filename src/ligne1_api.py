"""API locale des profils Ligne 1 : aucune requête réseau vers BC."""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.client_labels import ClientLabelStore, ProfileConflict, CATEGORIES, make_scope
from src.config import db
from src.bc_client import get_secret_file

router = APIRouter(prefix="/api/ligne1", tags=["Profils clients Ligne 1"])


def configured_store():
    with get_secret_file().open(encoding="utf-8") as file:
        config = json.load(file)
    return ClientLabelStore(db, make_scope(config)), {
        "environment": config.get("BC_ENVIRONMENT", "Dev"),
        "company": config.get("BC_COMPANY", "Ferme des Peupliers"),
    }


class RuleInput(BaseModel):
    category: str
    template_300: str
    template_203: str
    enabled: bool = True


class CreateProfile(BaseModel):
    identity: dict
    categories: list[str] = Field(default_factory=list)
    rules: list[RuleInput] = Field(default_factory=list)
    blocked_categories: list[str] = Field(default_factory=list)
    active: bool = True


class FlavourInput(BaseModel):
    item_no: str
    value: str
    revision: int


class SaveProfile(BaseModel):
    revision: int
    display_name: str
    active: bool = True
    rules: list[RuleInput]
    blocked_categories: list[str] | None = None
    identity: dict | None = None
    flavour: FlavourInput | None = None


class ResolveLabels(BaseModel):
    items: list[dict]
    draft: RuleInput | None = None
    draft_flavour: str | None = None


def profile_error(exc):
    return HTTPException(status_code=409 if isinstance(exc, ProfileConflict) else 400, detail=str(exc))


@router.get("/profiles")
def list_profiles():
    store, scope = configured_store()
    return {"profiles": store.list(), "scope": scope, "categories": CATEGORIES}


@router.post("/profiles")
def create_profile(request: CreateProfile):
    try:
        store, _ = configured_store()
        return store.create(request.identity, request.categories, [r.model_dump() for r in request.rules],
                            request.active, request.blocked_categories)
    except ValueError as exc:
        raise profile_error(exc) from exc


@router.put("/profiles/{profile_id}")
def save_profile(profile_id: str, request: SaveProfile):
    try:
        store, _ = configured_store()
        return store.save(profile_id, request.revision, request.display_name, request.active,
                          [r.model_dump() for r in request.rules], request.identity,
                          request.flavour.model_dump() if request.flavour else None, request.blocked_categories)
    except ValueError as exc:
        raise profile_error(exc) from exc


@router.post("/resolve")
def resolve_labels(request: ResolveLabels):
    try:
        store, scope = configured_store()
        if any(item.get("BCScope") and item["BCScope"] != scope for item in request.items):
            raise ValueError("L'environnement BC a changé. Réimportez la commande avant d'appliquer un profil.")
        return {"items": store.resolve(request.items, request.draft.model_dump() if request.draft else None, request.draft_flavour)}
    except ValueError as exc:
        raise profile_error(exc) from exc
