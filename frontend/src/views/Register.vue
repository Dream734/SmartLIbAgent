<template>

<div class="login-container">
    <div class="login-box">
        <h1 style="font-size:28px" margin-bottom="30px">欢迎注册</h1>
        

        <el-form ref="formRef":rules="rules":model="form" label-width="0px" style="width: 100%">
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

             <el-form-item prop="confirmPassword">
                <el-input size="large" 
                type="password"
                v-model="form.confirmPassword" 
                placeholder="请再次输入密码" 
                :prefix-icon="Lock"
                show-password
                 />
            </el-form-item>


            <div>
                <el-button type="primary" size="large" style="width: 100%" :loading ="loadingValue"@click="register">注册</el-button>
                <div style="text-align: right;margin-top: 20px;">已经有账号？请先<router-link style="color: var(--el-color-primary);" to="/login">登录</router-link></div>
            </div>

        </el-form>
    </div>
</div>


</template>

<script setup>
import { reactive, ref } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { registerApi } from '@/api/auth'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()

const form = reactive({
    username: '',
    password: '',
    confirmPassword: ''
})

const loadingValue = ref(false)
const formRef = ref()

const validatePass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请确认密码'))
  } else if (value !== form.password) {
    callback(new Error('两次密码输入不一致'))
  } else {
    callback()
  }
}

const rules = {
    username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
    password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
    confirmPassword: [{ validator: validatePass, trigger: 'blur' }]
}

const register = async () => {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    loadingValue.value = true
    try {
        const res = await registerApi(form)
        if (res.code === 200) {
            ElMessage.success('注册成功')
            await router.push('/login')
        } 
        
    } finally {
        loadingValue.value = false
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

