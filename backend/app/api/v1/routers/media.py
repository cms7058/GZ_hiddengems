from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.media_storage import MediaStorageError, read_managed_media, read_managed_thumbnail


router = APIRouter()


@router.get("/{key:path}", include_in_schema=False)
def get_media(key: str, thumbnail: bool = False, db: Session = Depends(get_db)) -> Response:
    """Deliver managed media from the configured API domain for mini-program use."""
    try:
        content, media_type = read_managed_thumbnail(db, key) if thumbnail else read_managed_media(db, key)
    except MediaStorageError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    # Uploaded keys are immutable. The URL's version suffix changes when an
    # admin selects a different cover, so browsers can safely retain thumbs.
    return Response(content=content, media_type=media_type, headers={"Cache-Control": "public, max-age=604800, immutable"})
