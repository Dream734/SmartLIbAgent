<template>
  <div>
    <el-card>
      <div class="filters">
        <el-select v-model="areaId" placeholder="选择区域" style="width: 180px; margin-right: 10px" @change="loadSeats">
          <el-option v-for="a in areas" :key="a.id" :label="`${a.name}（${a.floor}F）`" :value="a.id" />
        </el-select>
        <el-date-picker
          v-model="date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择日期"
          style="width: 160px; margin-right: 10px"
          @change="loadSeats"
        />
        <el-select v-model="startTime" placeholder="开始时间" style="width: 130px; margin-right: 10px" @change="loadSeats">
          <el-option v-for="s in slots" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="endTime" placeholder="结束时间" style="width: 130px; margin-right: 10px" @change="loadSeats">
          <el-option v-for="s in slots" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button type="primary" @click="loadSeats">查询座位</el-button>
      </div>
    </el-card>

    <el-card style="margin-top: 10px">
      <div v-loading="loading" class="seat-grid">
        <div
          v-for="seat in seats"
          :key="seat.id"
          class="seat-item"
          :class="{ disabled: seat.status !== 1 }"
          @click="bookSeat(seat)"
        >
          <div class="seat-no">{{ seat.seat_no }}</div>
          <div class="seat-type">{{ seat.seat_type }}</div>
        </div>
        <el-empty v-if="!loading && !seats.length" description="请先选择区域并查询" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAreaList, getSeatList, createReservation } from '@/api/seat'

const areas = ref([])
const areaId = ref(null)
const seats = ref([])
const loading = ref(false)

const formatDate = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

const date = ref(formatDate(new Date()))
const startTime = ref('')
const endTime = ref('')

const currentArea = computed(() => areas.value.find((a) => a.id === areaId.value))

const generateSlots = (open, close) => {
  const [oh, om] = open.split(':').map(Number)
  const [ch, cm] = close.split(':').map(Number)
  let cur = oh * 60 + om
  const end = ch * 60 + cm
  const result = []
  while (cur <= end) {
    result.push(`${String(Math.floor(cur / 60)).padStart(2, '0')}:${String(cur % 60).padStart(2, '0')}`)
    cur += 30
  }
  return result
}

const slots = computed(() =>
  currentArea.value ? generateSlots(currentArea.value.open_time, currentArea.value.close_time) : generateSlots('08:00', '22:00')
)

const toMinutes = (t) => {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

const loadAreas = async () => {
  const res = await getAreaList()
  if (res.code === 200) areas.value = res.data
}

const loadSeats = async () => {
  if (!areaId.value) {
    ElMessage.warning('请选择区域')
    return
  }
  loading.value = true
  try {
    const res = await getSeatList({
      area_id: areaId.value,
      date: date.value,
      start_time: startTime.value || undefined,
      end_time: endTime.value || undefined
    })
    if (res.code === 200) seats.value = res.data
  } finally {
    loading.value = false
  }
}

const bookSeat = async (seat) => {
  if (seat.status !== 1) {
    ElMessage.warning('该座位已停用')
    return
  }
  if (!date.value || !startTime.value || !endTime.value) {
    ElMessage.warning('请选择日期和起止时间')
    return
  }
  const start = toMinutes(startTime.value)
  const end = toMinutes(endTime.value)
  if (end <= start) {
    ElMessage.warning('结束时间必须晚于开始时间')
    return
  }
  if (end - start > 240) {
    ElMessage.warning('单次预约最长4小时')
    return
  }
  await ElMessageBox.confirm(
    `确认申请座位 ${seat.seat_no}（${date.value} ${startTime.value}-${endTime.value}）？`,
    '确认申请',
    { type: 'info' }
  )
    .then(async () => {
      const res = await createReservation({
        seat_id: seat.id,
        date: date.value,
        start_time: startTime.value,
        end_time: endTime.value
      })
      if (res.code === 200) ElMessage.success('申请已提交，等待管理员审批')
    })
    .catch(() => {})
}

onMounted(loadAreas)
</script>

<style scoped>
.filters {
  display: flex;
  align-items: center;
}
.seat-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  min-height: 120px;
}
.seat-item {
  width: 88px;
  padding: 12px 0;
  text-align: center;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  cursor: pointer;
}
.seat-item:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}
.seat-item.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.seat-no {
  font-size: 16px;
  font-weight: bold;
}
.seat-type {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
