from fastapi import APIRouter, HTTPException

from ..constants import api_id_to_index, index_to_name

router = APIRouter()


@router.get("/classes/{class_id}/")
def get_class(class_id: int):
    """1-indeksli sınıf referansı. İstemci cls'i `classes/<index+1>/` olarak üretir."""
    index = api_id_to_index(class_id)
    name = index_to_name(index)
    if name is None:
        raise HTTPException(status_code=404, detail="Class not found.")
    return {"id": class_id, "index": index, "name": name}
