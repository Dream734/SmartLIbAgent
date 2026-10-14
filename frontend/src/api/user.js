import request from '@/utils/request'

export function getUserInfo(data) {
  return request({
    url: '/api/user/me',
    method: 'get'
  })
}

// 修改当前登录用户的个人信息
export function updateUserInfo(data) {
  return request({
    url: '/api/user/me',
    method: 'put',
    data
  })
}

export function updatePassword(data) {
  return request({
    url: '/api/user/password',
    method: 'put',
    data
  })
}

// 分页模糊查询用户列表
export function getUserPageList(params) {
  return request({
    url: '/api/user/list',
    method: 'get',
    params
  })
}

// 管理员：新增用户
export function createUser(data) {
  return request({
    url: '/api/user',
    method: 'post',
    data
  })
}

// 管理员：修改用户
export function updateUser(id, data) {
  return request({
    url: `/api/user/${id}`,
    method: 'put',
    data
  })
}

// 管理员：删除用户
export function deleteUser(id) {
  return request({
    url: `/api/user/${id}`,
    method: 'delete'
  })
}
