import os
import zipfile


def create_photos_zip(photo_paths: list[str], output_zip_path: str) -> str:
    """Pack a list of local file paths into a single zip archive.

    Blocking: run via ``asyncio.to_thread`` when calling from async code.
    Uses ZIP_STORED because photos are already compressed and do not deflate.
    """
    os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_STORED) as zipf:
        for idx, path in enumerate(photo_paths, 1):
            if os.path.isfile(path):
                ext = os.path.splitext(path)[1] or ".jpg"
                filename = f"photo_{idx:02d}{ext}"
                zipf.write(path, arcname=filename)
    return output_zip_path
