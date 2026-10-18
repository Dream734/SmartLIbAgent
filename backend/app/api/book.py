from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.book import (
    BookCategoryCreateRequest,
    BookCategoryUpdateRequest,
    BookCreateRequest,
    BookUpdateRequest,
    BorrowCreateRequest,
)
from app.services import book_service

router = APIRouter(prefix="/book", tags=["图书管理"])


# ========== 分类 ==========
@router.get("/categories", summary="图书分类列表")
def get_categories(db: Session = Depends(get_db)):
    return Response.success(data=book_service.get_category_list(db))


@router.post("/categories", summary="新增分类")
def create_category(data: BookCategoryCreateRequest, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=book_service.create_category(db, data))


@router.put("/categories/{category_id}", summary="修改分类")
def update_category(category_id: int, data: BookCategoryUpdateRequest, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=book_service.update_category(db, category_id, data))


@router.delete("/categories/{category_id}", summary="删除分类")
def delete_category(category_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    book_service.delete_category(db, category_id)
    return Response.success()


# ========== 图书 ==========
@router.get("/books", summary="图书分页列表")
def get_books(page: int = 1, page_size: int = 10, keywords: str | None = None, category_id: int | None = None, db: Session = Depends(get_db)):
    return Response.success(data=book_service.get_book_page_list(db, page, page_size, keywords, category_id))


@router.get("/books/{book_id}", summary="图书详情")
def get_book(book_id: int, db: Session = Depends(get_db)):
    return Response.success(data=book_service.get_book_detail(db, book_id))


@router.post("/books", summary="新增图书")
def create_book(data: BookCreateRequest, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=book_service.create_book(db, data))


@router.put("/books/{book_id}", summary="修改图书")
def update_book(book_id: int, data: BookUpdateRequest, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=book_service.update_book(db, book_id, data))


@router.delete("/books/{book_id}", summary="删除图书")
def delete_book(book_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    book_service.delete_book(db, book_id)
    return Response.success()


# ========== 预借/借阅 ==========
@router.post("/borrows", summary="预借图书")
def create_borrow(data: BorrowCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return Response.success(data=book_service.create_borrow(db, current_user, data))


@router.get("/borrows/my", summary="我的预借")
def my_borrows(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return Response.success(data=book_service.my_borrows(db, current_user))


@router.post("/borrows/{borrow_id}/cancel", summary="取消预借")
def cancel_borrow(borrow_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return Response.success(data=book_service.cancel_borrow(db, current_user, borrow_id))


@router.post("/borrows/{borrow_id}/approve", summary="审批通过图书预借")
def approve_borrow(borrow_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=book_service.approve_borrow(db, borrow_id))


@router.post("/borrows/{borrow_id}/reject", summary="驳回图书预借")
def reject_borrow(borrow_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=book_service.reject_borrow(db, borrow_id))


@router.get("/borrows", summary="借阅列表(管理员)")
def get_borrows(page: int = 1, page_size: int = 10, status: str | None = None, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=book_service.get_borrow_page_list(db, page, page_size, status))


@router.put("/borrows/{borrow_id}/status", summary="借阅状态流转(管理员)")
def update_borrow_status(borrow_id: int, status: str, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=book_service.update_borrow_status(db, borrow_id, status))
