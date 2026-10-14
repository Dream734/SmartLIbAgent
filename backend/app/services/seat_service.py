import re

from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.seat import Seat, SeatArea, SeatReservation
from app.models.user import User
from app.schemas.seat import (
    SeatAreaCreateRequest,
    SeatAreaResponse,
    SeatAreaUpdateRequest,
    SeatCreateRequest,
    SeatReservationCreateRequest,
    SeatReservationResponse,
    SeatResponse,
    SeatUpdateRequest,
)

MAX_DURATION_MINUTES = 4 * 60
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):(00|30)$")


def _to_minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def _validate_time_slot(start_time: str, end_time: str) -> None:
    """时间只能是整点/半点，且 0 < 时长 <= 4 小时"""
    if not _TIME_RE.match(start_time) or not _TIME_RE.match(end_time):
        raise BusinessException(message="时间只能是整点或半点")
    if _to_minutes(start_time) >= _to_minutes(end_time):
        raise BusinessException(message="结束时间必须晚于开始时间")
    if _to_minutes(end_time) - _to_minutes(start_time) > MAX_DURATION_MINUTES:
        raise BusinessException(message="单次预约最长不超过4小时")


# ========== 阅览区 ==========
def get_area_list(db: Session):
    areas = db.query(SeatArea).order_by(SeatArea.floor.asc(), SeatArea.id.asc()).all()
    return [SeatAreaResponse.model_validate(a) for a in areas]


def create_area(db: Session, data: SeatAreaCreateRequest):
    area = SeatArea(**data.model_dump())
    db.add(area)
    db.commit()
    db.refresh(area)
    return SeatAreaResponse.model_validate(area)


def update_area(db: Session, area_id: int, data: SeatAreaUpdateRequest):
    area = db.query(SeatArea).filter(SeatArea.id == area_id).first()
    if not area:
        raise BusinessException(message="区域不存在")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(area, field, value)
    db.commit()
    db.refresh(area)
    return SeatAreaResponse.model_validate(area)


def delete_area(db: Session, area_id: int):
    area = db.query(SeatArea).filter(SeatArea.id == area_id).first()
    if not area:
        raise BusinessException(message="区域不存在")
    if db.query(Seat).filter(Seat.area_id == area_id).count():
        raise BusinessException(message="该区域下还有座位，无法删除")
    db.delete(area)
    db.commit()


# ========== 座位 ==========
def get_seat_list(db: Session, area_id: int | None = None):
    query = db.query(Seat, SeatArea.name).outerjoin(SeatArea, Seat.area_id == SeatArea.id)
    if area_id:
        query = query.filter(Seat.area_id == area_id)
    rows = query.order_by(Seat.id.asc()).all()
    items = []
    for seat, area_name in rows:
        resp = SeatResponse.model_validate(seat)
        resp.area_name = area_name
        items.append(resp)
    return items


def create_seat(db: Session, data: SeatCreateRequest):
    if not db.query(SeatArea).filter(SeatArea.id == data.area_id).first():
        raise BusinessException(message="区域不存在")
    seat = Seat(**data.model_dump())
    db.add(seat)
    db.commit()
    db.refresh(seat)
    return SeatResponse.model_validate(seat)


def update_seat(db: Session, seat_id: int, data: SeatUpdateRequest):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise BusinessException(message="座位不存在")
    if data.area_id is not None and not db.query(SeatArea).filter(SeatArea.id == data.area_id).first():
        raise BusinessException(message="区域不存在")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(seat, field, value)
    db.commit()
    db.refresh(seat)
    return SeatResponse.model_validate(seat)


def delete_seat(db: Session, seat_id: int):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise BusinessException(message="座位不存在")
    active = (
        db.query(SeatReservation)
        .filter(SeatReservation.seat_id == seat_id, SeatReservation.status == "reserved")
        .first()
    )
    if active:
        raise BusinessException(message="该座位有进行中的预约，无法删除")
    db.delete(seat)
    db.commit()


# ========== 座位预约 ==========
def create_reservation(db: Session, user: User, data: SeatReservationCreateRequest):
    seat = db.query(Seat).filter(Seat.id == data.seat_id).first()
    if not seat or seat.status != 1:
        raise BusinessException(message="座位不存在或已停用")
    area = db.query(SeatArea).filter(SeatArea.id == seat.area_id).first()
    if not area or area.status != 1:
        raise BusinessException(message="区域不存在或已停用")

    _validate_time_slot(data.start_time, data.end_time)
    if area.open_time > data.start_time or data.end_time > area.close_time:
        raise BusinessException(message=f"预约时间需在开放时间 {area.open_time}-{area.close_time} 内")

    seat_conflict = (
        db.query(SeatReservation)
        .filter(
            SeatReservation.seat_id == data.seat_id,
            SeatReservation.date == data.date,
            SeatReservation.status == "reserved",
            SeatReservation.start_time < data.end_time,
            SeatReservation.end_time > data.start_time,
        )
        .first()
    )
    if seat_conflict:
        raise BusinessException(message="该座位在所选时段已被预约")

    user_conflict = (
        db.query(SeatReservation)
        .filter(
            SeatReservation.user_id == user.id,
            SeatReservation.date == data.date,
            SeatReservation.status == "reserved",
            SeatReservation.start_time < data.end_time,
            SeatReservation.end_time > data.start_time,
        )
        .first()
    )
    if user_conflict:
        raise BusinessException(message="你在该时段已有预约")

    reservation = SeatReservation(
        user_id=user.id,
        seat_id=data.seat_id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        status="reserved",
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return SeatReservationResponse.model_validate(reservation)


def _get_owned_reservation(db: Session, user: User, reservation_id: int) -> SeatReservation:
    reservation = db.query(SeatReservation).filter(SeatReservation.id == reservation_id).first()
    if not reservation:
        raise BusinessException(message="预约不存在")
    if reservation.user_id != user.id:
        raise BusinessException(message="无权操作该预约")
    return reservation


def cancel_reservation(db: Session, user: User, reservation_id: int):
    reservation = _get_owned_reservation(db, user, reservation_id)
    if reservation.status != "reserved":
        raise BusinessException(message="该预约已取消或已结束")
    reservation.status = "cancelled"
    db.commit()
    return SeatReservationResponse.model_validate(reservation)


def checkout_reservation(db: Session, user: User, reservation_id: int):
    reservation = _get_owned_reservation(db, user, reservation_id)
    if reservation.status != "reserved":
        raise BusinessException(message="该预约已取消或已结束")
    reservation.status = "finished"
    db.commit()
    return SeatReservationResponse.model_validate(reservation)


def my_reservations(db: Session, user: User):
    rows = (
        db.query(SeatReservation, Seat.seat_no, SeatArea.name)
        .join(Seat, SeatReservation.seat_id == Seat.id)
        .join(SeatArea, Seat.area_id == SeatArea.id)
        .filter(SeatReservation.user_id == user.id)
        .order_by(SeatReservation.date.desc(), SeatReservation.start_time.desc())
        .all()
    )
    items = []
    for reservation, seat_no, area_name in rows:
        resp = SeatReservationResponse.model_validate(reservation)
        resp.seat_no = seat_no
        resp.area_name = area_name
        items.append(resp)
    return items


def get_reservation_page_list(db: Session, page: int, page_size: int):
    query = (
        db.query(SeatReservation, Seat.seat_no, SeatArea.name, User.username)
        .join(Seat, SeatReservation.seat_id == Seat.id)
        .join(SeatArea, Seat.area_id == SeatArea.id)
        .join(User, SeatReservation.user_id == User.id)
    )
    total = query.count()
    rows = (
        query.order_by(SeatReservation.date.desc(), SeatReservation.start_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for reservation, seat_no, area_name, username in rows:
        resp = SeatReservationResponse.model_validate(reservation)
        resp.seat_no = seat_no
        resp.area_name = area_name
        resp.username = username
        items.append(resp)
    return PageResponse(list=items, total=total)
