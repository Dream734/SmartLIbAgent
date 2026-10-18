from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.seat import (
    SeatAreaCreateRequest,
    SeatAreaUpdateRequest,
    SeatCreateRequest,
    SeatReservationCreateRequest,
    SeatUpdateRequest,
)
from app.services import seat_service

router = APIRouter(prefix="/seat", tags=["座位管理"])


# ========== 阅览区 ==========
@router.get("/areas", summary="阅览区列表")
def get_areas(db: Session = Depends(get_db)):
    return Response.success(data=seat_service.get_area_list(db))


@router.post("/areas", summary="新增阅览区")
def create_area(data: SeatAreaCreateRequest, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=seat_service.create_area(db, data))


@router.put("/areas/{area_id}", summary="修改阅览区")
def update_area(area_id: int, data: SeatAreaUpdateRequest, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=seat_service.update_area(db, area_id, data))


@router.delete("/areas/{area_id}", summary="删除阅览区")
def delete_area(area_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    seat_service.delete_area(db, area_id)
    return Response.success()


# ========== 座位 ==========
@router.get("/seats", summary="座位列表")
def get_seats(
    area_id: int | None = None,
    date: date | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    db: Session = Depends(get_db),
):
    return Response.success(data=seat_service.get_seat_list(db, area_id, date, start_time, end_time))


@router.post("/seats", summary="新增座位")
def create_seat(data: SeatCreateRequest, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=seat_service.create_seat(db, data))


@router.put("/seats/{seat_id}", summary="修改座位")
def update_seat(seat_id: int, data: SeatUpdateRequest, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=seat_service.update_seat(db, seat_id, data))


@router.delete("/seats/{seat_id}", summary="删除座位")
def delete_seat(seat_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    seat_service.delete_seat(db, seat_id)
    return Response.success()


# ========== 座位预约 ==========
@router.post("/reservations", summary="预约座位")
def create_reservation(data: SeatReservationCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return Response.success(data=seat_service.create_reservation(db, current_user, data))


@router.get("/reservations/my", summary="我的座位预约")
def my_reservations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return Response.success(data=seat_service.my_reservations(db, current_user))


@router.post("/reservations/{reservation_id}/cancel", summary="取消预约")
def cancel_reservation(reservation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return Response.success(data=seat_service.cancel_reservation(db, current_user, reservation_id))


@router.post("/reservations/{reservation_id}/checkout", summary="离座")
def checkout_reservation(reservation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return Response.success(data=seat_service.checkout_reservation(db, current_user, reservation_id))


@router.post("/reservations/{reservation_id}/approve", summary="审批通过座位预约")
def approve_reservation(reservation_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=seat_service.approve_reservation(db, reservation_id))


@router.post("/reservations/{reservation_id}/reject", summary="驳回座位预约")
def reject_reservation(reservation_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=seat_service.reject_reservation(db, reservation_id))


@router.get("/reservations", summary="所有预约(管理员)")
def get_reservations(page: int = 1, page_size: int = 10, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=seat_service.get_reservation_page_list(db, page, page_size))
