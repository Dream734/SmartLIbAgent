import request from '@/utils/request'

//AI对话请求


export function chatApi(data) {
    return request({
      url: '/api/ai/chat',
      method: 'post',
      data,
      timeout: 30000
    })
}