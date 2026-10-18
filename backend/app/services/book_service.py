from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.book import Book, BookCategory, BorrowRecord
from app.models.user import User
from app.schemas.book import (
    BookCategoryCreateRequest,
    BookCategoryResponse,
    BookCategoryUpdateRequest,
    BookCreateRequest,
    BookResponse,
    BookUpdateRequest,
    BorrowCreateRequest,
    BorrowRecordResponse,
)

BORROW_RESERVE_DAYS = 2


# ========== 分类 ==========
def get_category_list(db: Session):
    categories = db.query(BookCategory).order_by(BookCategory.id.asc()).all()
    return [BookCategoryResponse.model_validate(c) for c in categories]


def create_category(db: Session, data: BookCategoryCreateRequest):
    if db.query(BookCategory).filter(BookCategory.name == data.name).first():
        raise BusinessException(message="分类已存在")
    category = BookCategory(name=data.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return BookCategoryResponse.model_validate(category)


def update_category(db: Session, category_id: int, data: BookCategoryUpdateRequest):
    category = db.query(BookCategory).filter(BookCategory.id == category_id).first()
    if not category:
        raise BusinessException(message="分类不存在")
    if data.name is not None:
        exist = (
            db.query(BookCategory)
            .filter(BookCategory.name == data.name, BookCategory.id != category_id)
            .first()
        )
        if exist:
            raise BusinessException(message="分类已存在")
        category.name = data.name
    db.commit()
    db.refresh(category)
    return BookCategoryResponse.model_validate(category)


def delete_category(db: Session, category_id: int):
    category = db.query(BookCategory).filter(BookCategory.id == category_id).first()
    if not category:
        raise BusinessException(message="分类不存在")
    if db.query(Book).filter(Book.category_id == category_id).count():
        raise BusinessException(message="该分类下还有图书，无法删除")
    db.delete(category)
    db.commit()


# ========== 图书 ==========
def get_book_page_list(db: Session, page: int, page_size: int, keywords: str | None = None, category_id: int | None = None):
    filters = []
    if category_id:
        filters.append(Book.category_id == category_id)
    if keywords:
        keyword = f"%{keywords}%"
        filters.append(or_(Book.title.ilike(keyword), Book.author.ilike(keyword), Book.isbn.ilike(keyword)))

    total = db.query(Book).filter(*filters).count()
    rows = (
        db.query(Book, BookCategory.name)
        .outerjoin(BookCategory, Book.category_id == BookCategory.id)
        .filter(*filters)
        .order_by(Book.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for book, category_name in rows:
        resp = BookResponse.model_validate(book)
        resp.category_name = category_name
        items.append(resp)
    return PageResponse(items=items, total=total)


def get_book_detail(db: Session, book_id: int):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise BusinessException(message="图书不存在")
    category_name = None
    if book.category_id:
        category = db.query(BookCategory).filter(BookCategory.id == book.category_id).first()
        category_name = category.name if category else None
    resp = BookResponse.model_validate(book)
    resp.category_name = category_name
    return resp


def create_book(db: Session, data: BookCreateRequest):
    book = Book(**data.model_dump())
    if book.available > book.total:
        book.available = book.total
    db.add(book)
    db.commit()
    db.refresh(book)
    return BookResponse.model_validate(book)


def update_book(db: Session, book_id: int, data: BookUpdateRequest):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise BusinessException(message="图书不存在")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(book, field, value)
    if book.available > book.total:
        book.available = book.total
    if book.available < 0:
        book.available = 0
    db.commit()
    db.refresh(book)
    return BookResponse.model_validate(book)


def delete_book(db: Session, book_id: int):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise BusinessException(message="图书不存在")
    active = (
        db.query(BorrowRecord)
        .filter(BorrowRecord.book_id == book_id, BorrowRecord.status.in_(["pending", "reserved", "pickup", "borrowed"]))
        .first()
    )
    if active:
        raise BusinessException(message="该图书有未完成的借阅，无法删除")
    db.delete(book)
    db.commit()


# ========== 预借/借阅 ==========
def _expire_overdue_borrows(db: Session):
    """惰性过期：待审批或预借超过 2 天未处理自动取消并释放库存"""
    now = datetime.now()
    overdue = (
        db.query(BorrowRecord)
        .filter(
            BorrowRecord.status.in_(["pending", "reserved"]),
            BorrowRecord.expire_time.isnot(None),
            BorrowRecord.expire_time < now,
        )
        .all()
    )
    if not overdue:
        return
    for record in overdue:
        record.status = "cancelled"
        book = db.query(Book).filter(Book.id == record.book_id).first()
        if book:
            book.available += 1
    db.commit()


def check_borrow(
    db: Session,
    user: User,
    data: BorrowCreateRequest,
    for_update: bool = False,
):
    """只做预借校验，不扣库存、不写借阅表。"""
    book_query = db.query(Book).filter(Book.id == data.book_id)
    if for_update:
        book_query = book_query.with_for_update()
    book = book_query.first()
    if not book or book.status != 1:
        raise BusinessException(message="图书不存在或已下架")
    if book.available <= 0:
        raise BusinessException(message="该图书暂无可预借库存")
    exist = (
        db.query(BorrowRecord)
        .filter(
            BorrowRecord.user_id == user.id,
            BorrowRecord.book_id == data.book_id,
            BorrowRecord.status.in_(["pending", "reserved", "pickup", "borrowed"]),
        )
        .first()
    )
    if exist:
        raise BusinessException(message="你已预借或借阅该图书")

    return book


def create_borrow(db: Session, user: User, data: BorrowCreateRequest):
    _expire_overdue_borrows(db)
    book = check_borrow(db, user, data, for_update=True)

    book.available -= 1
    record = BorrowRecord(
        user_id=user.id,
        book_id=data.book_id,
        status="pending",
        expire_time=datetime.now() + timedelta(days=BORROW_RESERVE_DAYS),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return BorrowRecordResponse.model_validate(record)


def my_borrows(db: Session, user: User):
    _expire_overdue_borrows(db)
    rows = (
        db.query(BorrowRecord, Book.title)
        .join(Book, BorrowRecord.book_id == Book.id)
        .filter(BorrowRecord.user_id == user.id)
        .order_by(BorrowRecord.create_time.desc())
        .all()
    )
    items = []
    for record, title in rows:
        resp = BorrowRecordResponse.model_validate(record)
        resp.book_title = title
        items.append(resp)
    return items


def cancel_borrow(db: Session, user: User, borrow_id: int):
    _expire_overdue_borrows(db)
    record = db.query(BorrowRecord).filter(BorrowRecord.id == borrow_id).first()
    if not record:
        raise BusinessException(message="记录不存在")
    if record.user_id != user.id:
        raise BusinessException(message="无权操作该记录")
    # 幂等：已经取消/刚被惰性过期清理的记录，直接返回成功，避免用户点取消时提示“不可取消”
    if record.status == "cancelled":
        return BorrowRecordResponse.model_validate(record)
    # pickup 表示书已到馆但用户还没取走，仍允许取消并释放库存
    if record.status not in ("pending", "reserved", "pickup"):
        raise BusinessException(message="该预借当前状态不可取消")
    record.status = "cancelled"
    book = db.query(Book).filter(Book.id == record.book_id).first()
    if book:
        book.available += 1
    db.commit()
    return BorrowRecordResponse.model_validate(record)


def approve_borrow(db: Session, borrow_id: int):
    """管理员审批通过图书预借"""
    _expire_overdue_borrows(db)
    record = db.query(BorrowRecord).filter(BorrowRecord.id == borrow_id).first()
    if not record:
        raise BusinessException(message="记录不存在")
    if record.status != "pending":
        raise BusinessException(message="该申请已处理")
    record.status = "reserved"
    record.expire_time = datetime.now() + timedelta(days=BORROW_RESERVE_DAYS)
    db.commit()
    db.refresh(record)
    return BorrowRecordResponse.model_validate(record)


def reject_borrow(db: Session, borrow_id: int):
    """管理员驳回图书预借"""
    _expire_overdue_borrows(db)
    record = db.query(BorrowRecord).filter(BorrowRecord.id == borrow_id).first()
    if not record:
        raise BusinessException(message="记录不存在")
    if record.status != "pending":
        raise BusinessException(message="该申请已处理")
    record.status = "cancelled"
    book = db.query(Book).filter(Book.id == record.book_id).first()
    if book:
        book.available += 1
    db.commit()
    db.refresh(record)
    return BorrowRecordResponse.model_validate(record)


def get_borrow_page_list(db: Session, page: int, page_size: int, status: str | None = None):
    _expire_overdue_borrows(db)
    query = (
        db.query(BorrowRecord, Book.title, User.username)
        .join(Book, BorrowRecord.book_id == Book.id)
        .join(User, BorrowRecord.user_id == User.id)
    )
    if status:
        query = query.filter(BorrowRecord.status == status)
    total = query.count()
    rows = (
        query.order_by(BorrowRecord.create_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for record, title, username in rows:
        resp = BorrowRecordResponse.model_validate(record)
        resp.book_title = title
        resp.username = username
        items.append(resp)
    return PageResponse(items=items, total=total)


def update_borrow_status(db: Session, borrow_id: int, status: str):
    _expire_overdue_borrows(db)
    if status not in ("pickup", "borrowed", "returned"):
        raise BusinessException(message="无效的状态")
    record = db.query(BorrowRecord).filter(BorrowRecord.id == borrow_id).first()
    if not record:
        raise BusinessException(message="记录不存在")
    if record.status == "pending":
        raise BusinessException(message="该预借申请尚未审批，请先通过或驳回")
    if status == "borrowed" and record.borrow_time is None:
        record.borrow_time = datetime.now()
    if status == "returned" and record.status != "returned":
        record.return_time = datetime.now()
        book = db.query(Book).filter(Book.id == record.book_id).first()
        if book:
            book.available += 1
    record.status = status
    db.commit()
    db.refresh(record)
    return BorrowRecordResponse.model_validate(record)
