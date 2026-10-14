import request from '@/utils/request'



export function uploadFileApi(file){
    const formData = new FormData()
    formData.append('file', file)
    return request({ 
        url: '/api/files/uploads' ,
        method: 'post',
        data: formData,
        headers: { 'Content-Type': 'multipart' }
    }) 
    

}