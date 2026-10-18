<template>
  <div>
    <el-card>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="我的座位预约" name="seat">
          <el-table :data="reservations" v-loading="loadingSeat" style="width: 100%">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column label="区域" width="140">
              <template #default="{ row }">{{ row.area_name }}</template>
            </el-table-column>
            <el-table-column prop="seat_no" label="座位号" width="100" />
            <el-table-column label="时间段" width="160">
              <template #default="{ row }">{{ row.start_time }} - {{ row.end_time }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="seatStatusType(row.status)">{{ seatStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button v-if="['pending', 'reserved'].includes(row.status)" link type="danger" @click="handleCancelReservation(row)">取消预约</el-button>
                <el-button v-if="row.status === 'reserved'" link type="primary" @click="handleCheckout(row)">离座</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="我的图书预借" name="book">
          <el-table :data="borrows" v-loading="loadingBook" style="width: 100%">
            <el-table-column prop="book_title" label="书名" min-width="160" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="borrowStatusType(row.status)">{{ borrowStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="预借时间" width="180">
              <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
            </el-table-column>
            <el-table-column label="过期时间" width="180">
              <template #default="{ row }">{{ formatTime(row.expire_time) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button v-if="['pending', 'reserved', 'pickup'].includes(row.status)" link type="danger" @click="handleCancelBorrow(row)">取消预借</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMyReservations, cancelReservation as cancelReservationApi, checkoutReservation as checkoutReservationApi } from '@/api/seat'
import { getMyBorrows, cancelBorrow as cancelBorrowApi } from '@/api/book'

const activeTab = ref('seat')
const reservations = ref([])
const borrows = ref([])
const loadingSeat = ref(false)
const loadingBook = ref(false)

const seatStatusText = (s) => ({ pending: '待审批', reserved: '已预约', cancelled: '已取消', finished: '已离座' }[s] || s)
const seatStatusType = (s) => ({ pending: 'warning', reserved: 'success', cancelled: 'info', finished: 'warning' }[s] || 'info')

const borrowStatusText = (s) => ({ pending: '待审批', reserved: '预借中', pickup: '可取', borrowed: '已借', returned: '已还', cancelled: '已取消' }[s] || s)
const borrowStatusType = (s) => ({ pending: 'warning', reserved: 'primary', pickup: 'success', borrowed: 'warning', returned: 'info', cancelled: 'info' }[s] || 'info')

const formatTime = (t) => (t ? t.replace('T', ' ').slice(0, 16) : '-')

const loadReservations = async () => {
  loadingSeat.value = true
  try {
    const res = await getMyReservations()
    if (res.code === 200) reservations.value = res.data
  } finally {
    loadingSeat.value = false
  }
}

const loadBorrows = async () => {
  loadingBook.value = true
  try {
    const res = await getMyBorrows()
    if (res.code === 200) borrows.value = res.data
  } finally {
    loadingBook.value = false
  }
}

const handleCancelReservation = (row) => {
  ElMessageBox.confirm('确定取消该预约吗？', '提示', { type: 'warning' })
    .then(async () => {
      const res = await cancelReservationApi(row.id)
      if (res.code === 200) {
        ElMessage.success('已取消')
        loadReservations()
      }
    })
    .catch(() => {})
}

const handleCheckout = (row) => {
  ElMessageBox.confirm('确认离座吗？', '提示', { type: 'warning' })
    .then(async () => {
      const res = await checkoutReservationApi(row.id)
      if (res.code === 200) {
        ElMessage.success('已离座')
        loadReservations()
      }
    })
    .catch(() => {})
}

const handleCancelBorrow = (row) => {
  ElMessageBox.confirm('确定取消预借吗？', '提示', { type: 'warning' })
    .then(async () => {
      const res = await cancelBorrowApi(row.id)
      if (res.code === 200) {
        ElMessage.success('已取消')
        loadBorrows()
      }
    })
    .catch(() => {})
}

onMounted(() => {
  loadReservations()
  loadBorrows()
})
</script>
