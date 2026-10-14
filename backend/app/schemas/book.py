from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookCategoryResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class BookCategoryCreateRequest(BaseModel):
    name: str


class BookCategoryUpdateRequest(BaseModel):
    name: str | None = None


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: str | None = None
    publisher: str | None = None
    publish_year: int | None = None
    category_id: int | None = None
    cover: str | None = None
    total: int
    available: int
    location: str | None = None
    summary: str | None = None
    status: int
    category_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BookCreateRequest(BaseModel):
    title: str
    author: str
    isbn: str | None = None
    publisher: str | None = None
    publish_year: int | None = None
    category_id: int | None = None
    cover: str | None = None
    total: int = 1
    available: int = 1
    location: str | None = None
    summary: str | None = None
    status: int = 1


class BookUpdateRequest(BaseModel):
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    publish_year: int | None = None
    category_id: int | None = None
    cover: str | None = None
    total: int | None = None
    available: int | None = None
    location: str | None = None
    summary: str | None = None
    status: int | None = None


class BorrowRecordResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    status: str
    create_time: datetime | None = None
    expire_time: datetime | None = None
    borrow_time: datetime | None = None
    return_time: datetime | None = None
    book_title: str | None = None
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BorrowCreateRequest(BaseModel):
    book_id: int
