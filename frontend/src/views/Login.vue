<template>

<div class="login-container">
    <div class="login-box">
        <h1 style="font-size:28px">实验室预约系统</h1>
        <div style="margin-top: 5px; margin-bottom: 30px;">基于Agent智能预约系统</div>

        <el-form ref="formRef":rules="rules" :model="form" label-width="0px" style="width: 100%">
            <el-form-item prop="username">
                <el-input size="large" 
                v-model="form.username" 
                placeholder="请输入账号" 
                :prefix-icon="User"
                 />
            </el-form-item>
            <el-form-item prop="password">
                <el-input size="large" 
                type="password"
                v-model="form.password" 
                placeholder="请输入密码" 
                :prefix-icon="Lock"
                show-password
                 />
            </el-form-item>
            <div>
                <el-button type="primary" size="large" style="width: 100%; margin-top: 20px;" @click="Login" :loading="loginLoading">登录</el-button>
                <div style="text-align: right;margin-top: 20px;">还没有账号？请先<router-link style="color: var(--el-color-primary);" to="/register">注册</router-link></div>
            </div>

        </el-form>
    </div>
</div>


</template>

<script setup>
import { reactive, ref } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router' 
import { loginApi } from '@/api/auth'
import { useUser } from '@/utils/user'

const { saveLoginData } = useUser()
 
const formRef = ref()

const rules = {
    username:[{ required:true,message:'请输入账号',trigger:'blur'}],
    password:[{ required:true,message:'请输入密码',trigger:'blur'}]
}

const form = reactive({
    username: '',
    password: ''
})

const loginLoading = ref(false)
const router = useRouter() 


const Login = async () => {
    const valid = await formRef.value.validate().catch(()=> false)//表单验证
    if(!valid)return
    loginLoading.value = true
    try {
        const res = await loginApi(form)
        if (res.code === 200) {
            saveLoginData(res.data)
            ElMessage.success('登录成功')
            await router.push('/home')
        }
    } finally {
        loginLoading.value = false
    }
}
</script>

<style scoped>
.login-container
{
height: 100vh;
display: flex;
justify-content: center;
align-items: center;
}
.login-box {
width: 380px;
border-radius: 8px;
box-shadow: 0 8px 12px rgba(0, 0, 0, 0.1);
padding: 30px;
text-align: center;
background-color: white;
}
</style>

