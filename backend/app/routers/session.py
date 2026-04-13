from fastapi import APIRouter

from ..models.memory import memory_store
from ..schemas import BootstrapRequest, BootstrapResponse


router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/bootstrap", response_model=BootstrapResponse)
def bootstrap(req: BootstrapRequest) -> BootstrapResponse:
    session_id = memory_store.create_or_get(req.client_session_id, req.summary, req.signals)
    return BootstrapResponse(session_id=session_id)


