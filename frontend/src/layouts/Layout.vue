<template>
  <div>
    <el-container style="min-height: 100vh;">
      <el-header
        style="display: flex; border-bottom: 1px solid #eaeaea; align-items: center; background-color: #f5f7fa; height: 60px;"
      >
        <div style="flex: 1; display: flex; align-items: center; font-size: 24px; font-weight: bold;">
          <img src="@/assets/imgs/logo.png" style="height: 40px; margin-left: 10px;" />
          <div style="margin-left: 10px;">智能实验室预约系统</div>
        </div>

        <div style="display: flex; align-items: center;">
          <el-dropdown @command="handleCommand">
            <div style="display: flex; align-items: center; cursor: pointer;">
              <img :src="userInfo.avatar" alt="User" style="width: 30px; border-radius: 50%;" />
              <div style="margin-left: 3px">{{ userInfo.name }}</div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-container>
        <el-aside width="220px" style="background-color: #fff; border-right: 1px solid #eaeaea;">
          <el-menu
            router
            style="height: 100%;"
            :default-active="route.path"
          >
            <el-menu-item index="/home">
              <el-icon><icon-menu /></el-icon>
              <span>系统首页</span>
            </el-menu-item>

            <el-menu-item index="/lab">
              <el-icon><House /></el-icon>
              <span>实验室列表</span>
            </el-menu-item>

            <el-menu-item index="/equ">
              <el-icon><Setting /></el-icon>
              <span>设备列表管理</span>
            </el-menu-item>

            <el-menu-item index="/user" v-if="userInfo?.role === 'admin'">
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <el-container>
          <el-main>
            <router-view></router-view>
          </el-main>
        </el-container>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { Menu as IconMenu, Setting, User, House } from '@element-plus/icons-vue'
import { logout } from '@/utils/auth'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/utils/user'

const router = useRouter()
const route = useRoute()
const { userInfo } = useUser()

const handleCommand = (command) => {
  if (command === 'profile') {
    router.push('/profile')
  }else if (command === 'password') {
    router.push('/password')
    }
  else if (command === 'logout') {
    logout()
    router.push('/login')
  } 
}

</script>