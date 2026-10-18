import request from '@/utils/request'

// 阅览区
export function getAreaList() {
  return request({ url: '/api/seat/areas', method: 'get' })
}

export function createArea(data) {
  return request({ url: '/api/seat/areas', method: 'post', data })
}

export function updateArea(id, data) {
  return request({ url: `/api/seat/areas/${id}`, method: 'put', data })
}

export function deleteArea(id) {
  return request({ url: `/api/seat/areas/${id}`, method: 'delete' })
}

// 座位
export function getSeatList(params) {
  return request({ url: '/api/seat/seats', method: 'get', params })
}

export function createSeat(data) {
  return request({ url: '/api/seat/seats', method: 'post', data })
}

export function updateSeat(id, data) {
  return request({ url: `/api/seat/seats/${id}`, method: 'put', data })
}

export function deleteSeat(id) {
  return request({ url: `/api/seat/seats/${id}`, method: 'delete' })
}

// 座位预约
export function createReservation(data) {
  return request({ url: '/api/seat/reservations', method: 'post', data })
}

export function getMyReservations() {
  return request({ url: '/api/seat/reservations/my', method: 'get' })
}

export function cancelReservation(id) {
  return request({ url: `/api/seat/reservations/${id}/cancel`, method: 'post' })
}

export function checkoutReservation(id) {
  return request({ url: `/api/seat/reservations/${id}/checkout`, method: 'post' })
}

export function approveReservation(id) {
  return request({ url: `/api/seat/reservations/${id}/approve`, method: 'post' })
}

export function rejectReservation(id) {
  return request({ url: `/api/seat/reservations/${id}/reject`, method: 'post' })
}

export function getReservationPageList(params) {
  return request({ url: '/api/seat/reservations', method: 'get', params })
}
