import os
import shutil
import time
import uuid
from pathlib import Path
from fastapi import APIRouter, File, UploadFile
from app.common.exceptions import BusinessException
from app.common.response import Response
from app.config import ALLOW_EXTENSIONS, MAX_FILE_SIZE, UPLOAD_DIR
from app.schemas.file import FileResponse

router = APIRouter(prefix="/files", tags=["文件管理"])


@router.post("/uploads")
def upload(file: UploadFile = File(...)):  # File(None)，就是可选,File(...)是必填

    if not file.filename:
        raise BusinessException(message="文件名不能为空")

    # 原始的文件名用户头像.jpg
    original_name = os.path.basename(file.filename)

    # 文件后缀·jpg
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOW_EXTENSIONS:
        raise BusinessException(message=f"不支持的文件后缀：{ext}")
    
    # 文件大小校验
    if file.size and file.size > MAX_FILE_SIZE:
        raise BusinessException(message=f"文件不能超过{MAX_FILE_SIZE//1024//1024}MB")
    
    # 设置唯一文件名称     1994156131-ddadaqweqr.jpg
    disk_name = f"{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}{ext}"
    # 文件存储的实际路径
    
    save_path = UPLOAD_DIR / disk_name

    # 流式写文件
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return Response.success(
        data= FileResponse(
        original_name = original_name, 
        disk_name = disk_name, 
        size = file.size, 
        url = f"/uploads/{disk_name}", 
        )
    )
