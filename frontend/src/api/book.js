import request from '@/utils/request'

// 图书分类
export function getCategoryList() {
  return request({ url: '/api/book/categories', method: 'get' })
}

export function createCategory(data) {
  return request({ url: '/api/book/categories', method: 'post', data })
}

export function updateCategory(id, data) {
  return request({ url: `/api/book/categories/${id}`, method: 'put', data })
}

export function deleteCategory(id) {
  return request({ url: `/api/book/categories/${id}`, method: 'delete' })
}

// 图书
export function getBookPageList(params) {
  return request({ url: '/api/book/books', method: 'get', params })
}

export function getBookDetail(id) {
  return request({ url: `/api/book/books/${id}`, method: 'get' })
}

export function createBook(data) {
  return request({ url: '/api/book/books', method: 'post', data })
}

export function updateBook(id, data) {
  return request({ url: `/api/book/books/${id}`, method: 'put', data })
}

export function deleteBook(id) {
  return request({ url: `/api/book/books/${id}`, method: 'delete' })
}

// 预借/借阅
export function createBorrow(data) {
  return request({ url: '/api/book/borrows', method: 'post', data })
}

export function getMyBorrows() {
  return request({ url: '/api/book/borrows/my', method: 'get' })
}

export function cancelBorrow(id) {
  return request({ url: `/api/book/borrows/${id}/cancel`, method: 'post' })
}

export function approveBorrow(id) {
  return request({ url: `/api/book/borrows/${id}/approve`, method: 'post' })
}

export function rejectBorrow(id) {
  return request({ url: `/api/book/borrows/${id}/reject`, method: 'post' })
}

export function getBorrowPageList(params) {
  return request({ url: '/api/book/borrows', method: 'get', params })
}

export function updateBorrowStatus(id, status) {
  return request({ url: `/api/book/borrows/${id}/status`, method: 'put', params: { status } })
}
