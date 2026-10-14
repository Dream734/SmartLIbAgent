from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SeatAreaResponse(BaseModel):
    id: int
    name: str
    floor: int
    open_time: str
    close_time: str
    status: int

    model_config = ConfigDict(from_attributes=True)


class SeatAreaCreateRequest(BaseModel):
    name: str
    floor: int = 1
    open_time: str = "08:00"
    close_time: str = "22:00"
    status: int = 1


class SeatAreaUpdateRequest(BaseModel):
    name: str | None = None
    floor: int | None = None
    open_time: str | None = None
    close_time: str | None = None
    status: int | None = None


class SeatResponse(BaseModel):
    id: int
    area_id: int
    seat_no: str
    seat_type: str
    status: int
    area_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SeatCreateRequest(BaseModel):
    area_id: int
    seat_no: str
    seat_type: str = "普通"
    status: int = 1


class SeatUpdateRequest(BaseModel):
    area_id: int | None = None
    seat_no: str | None = None
    seat_type: str | None = None
    status: int | None = None


class SeatReservationResponse(BaseModel):
    id: int
    user_id: int
    seat_id: int
    date: date
    start_time: str
    end_time: str
    status: str
    create_time: datetime | None = None
    seat_no: str | None = None
    area_name: str | None = None
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SeatReservationCreateRequest(BaseModel):
    seat_id: int
    date: date
    start_time: str
    end_time: str
