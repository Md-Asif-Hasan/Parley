import os
import base64
import uuid
from pathlib import Path

TEMP_DIR = os.path.join(str(Path.home()), ".parley", "temp_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)


def save_base64_image(base64_data: str, extension: str = "png") -> str:
    """
    Saves a base64 encoded image string to disk and returns the absolute file path.
    """
    # Strip data URL prefix if present
    if "," in base64_data:
        base64_data = base64_data.split(",", 1)[1]

    file_id = str(uuid.uuid4())[:8]
    filename = f"upload_{file_id}.{extension}"
    target_path = os.path.join(TEMP_DIR, filename)

    img_bytes = base64.b64decode(base64_data)
    with open(target_path, "wb") as f:
        f.write(img_bytes)

    return target_path
