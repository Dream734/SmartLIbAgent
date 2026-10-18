<template>
  <div>
    <el-card>
      <div style="margin-bottom: 10px; display: flex">
        <el-select v-model="status" placeholder="全部状态" clearable style="width: 160px; margin-right: 10px" @change="handleSearch">
          <el-option label="待审批" value="pending" />
          <el-option label="预借中" value="reserved" />
          <el-option label="可取" value="pickup" />
          <el-option label="已借" value="borrowed" />
          <el-option label="已还" value="returned" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
      </div>

      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column prop="book_title" label="书名" min-width="160" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" link type="success" @click="approve(row)">通过</el-button>
            <el-button v-if="row.status === 'pending'" link type="danger" @click="reject(row)">驳回</el-button>
            <el-button v-if="row.status === 'reserved'" link type="success" @click="changeStatus(row, 'pickup')">标记可取</el-button>
            <el-button v-if="row.status === 'pickup'" link type="primary" @click="changeStatus(row, 'borrowed')">标记已借</el-button>
            <el-button v-if="row.status === 'borrowed'" link type="warning" @click="changeStatus(row, 'returned')">标记已还</el-button>
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
import { getBorrowPageList, updateBorrowStatus, approveBorrow, rejectBorrow } from '@/api/book'

const list = ref([])
const total = ref(0)
const loading = ref(false)
const status = ref(null)
const params = reactive({ page: 1, pageSize: 10 })

const statusText = (s) => ({ pending: '待审批', reserved: '预借中', pickup: '可取', borrowed: '已借', returned: '已还', cancelled: '已取消' }[s] || s)
const statusType = (s) => ({ pending: 'warning', reserved: 'primary', pickup: 'success', borrowed: 'warning', returned: 'info', cancelled: 'info' }[s] || 'info')

const load = async () => {
  loading.value = true
  try {
    const res = await getBorrowPageList({ page: params.page, page_size: params.pageSize, status: status.value || undefined })
    if (res.code === 200) {
      list.value = res.data?.items
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  params.page = 1
  load()
}

const changeStatus = async (row, target) => {
  try {
    const res = await updateBorrowStatus(row.id, target)
    if (res.code === 200) {
      ElMessage.success('操作成功')
      load()
    }
  } catch (e) {
    // 错误提示已由请求拦截器处理
  }
}

const approve = async (row) => {
  try {
    const res = await approveBorrow(row.id)
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
    const res = await rejectBorrow(row.id)
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
