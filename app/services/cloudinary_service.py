import cloudinary
import cloudinary.uploader
from app.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

FOLDERS = {
    "avatar": "academic_app/avatars",
    "attachment": "academic_app/attachments",
    "document": "academic_app/documents",
}


def upload_file(
    file_bytes: bytes,
    folder_key: str = "attachment",
    public_id: str | None = None,
    resource_type: str = "auto",   # "image", "raw" for PDFs/docs, or "auto"
) -> dict:
    """
    Uploads a file to Cloudinary and returns the secure URL and public_id.
    resource_type='auto' handles images, PDFs, and other docs in one call.
    """
    folder = FOLDERS.get(folder_key, FOLDERS["attachment"])
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        public_id=public_id,
        resource_type=resource_type,
        overwrite=True if public_id else False,
    )
    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
        "resource_type": result["resource_type"],
        "format": result.get("format"),
        "bytes": result.get("bytes"),
    }


def delete_file(public_id: str, resource_type: str = "image") -> bool:
    """Deletes a file from Cloudinary by its public_id."""
    result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
    return result.get("result") == "ok"
