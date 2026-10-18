<template>
  <div>
    <el-card>
      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="area_name" label="区域" width="140" />
        <el-table-column prop="seat_no" label="座位号" width="100" />
        <el-table-column label="时间段" width="160">
          <template #default="{ row }">{{ row.start_time }} - {{ row.end_time }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" link type="success" @click="approve(row)">通过</el-button>
            <el-button v-if="row.status === 'pending'" link type="danger" @click="reject(row)">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination background layout="prev, pager, next, total" :total="total" v-model:page-size="params.pageSize" v-model:current-page="params.page" @current-change="load" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getReservationPageList, approveReservation, rejectReservation } from '@/api/seat'

const list = ref([])
const total = ref(0)
const loading = ref(false)
const params = reactive({ page: 1, pageSize: 10 })

const statusText = (s) => ({ pending: '待审批', reserved: '已预约', cancelled: '已取消', finished: '已离座' }[s] || s)
const statusType = (s) => ({ pending: 'warning', reserved: 'success', cancelled: 'info', finished: 'warning' }[s] || 'info')

const load = async () => {
  loading.value = true
  try {
    const res = await getReservationPageList({ page: params.page, page_size: params.pageSize })
    if (res.code === 200) {
      list.value = res.data?.items
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const approve = async (row) => {
  try {
    const res = await approveReservation(row.id)
    if (res.code === 200) {
      ElMessage.success('已通过')
      load()
    }
  } catch (e) {
    // 错误提示已由请求拦截器处理
  }
}

const reject = async (row) => {
  try {
    const res = await rejectReservation(row.id)
    if (res.code === 200) {
      ElMessage.success('已驳回')
      load()
    }
  } catch (e) {
    // 错误提示已由请求拦截器处理
  }
}

onMounted(load)
</script>
