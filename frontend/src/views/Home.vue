<template>
  <div style="max-width: 1200px; margin: 0 auto;">
    <el-card
      shadow="never"
      :body-style="{
        padding: '28px 32px',
        borderRadius: '16px',
        background: 'linear-gradient(135deg, #e8f3ff 0%, #f5f9ff 55%, #ffffff 100%)'
      }"
      style="border: none;"
    >
      <el-row :gutter="20" align="middle">
        <el-col :xs="24" :md="16">
          <el-space :size="14" alignment="center">
            <el-avatar :size="56" :src="userInfo?.avatar" :icon="User" />
            <div>
              <div style="font-size: 26px; font-weight: 700; color: #303133;">
                {{ greeting }}，{{ userName }}
              </div>
              <el-space :size="8" style="margin-top: 6px;">
                <el-tag :type="isAdmin ? 'warning' : 'primary'" effect="light">
                  {{ isAdmin ? '管理员' : '学生' }}
                </el-tag>
                <el-text type="info" size="small">{{ todayText }}</el-text>
              </el-space>
            </div>
          </el-space>

          <div style="margin-top: 16px; color: #606266; font-size: 14px; line-height: 1.7;">
            欢迎回到图书馆选座借阅系统。查座位、借好书、问 AI，一个页面搞定。
          </div>

          <el-space :size="10" wrap style="margin-top: 18px;">
            <el-button type="primary" @click="go('/seat')">预约座位</el-button>
            <el-button @click="go('/books')">预借图书</el-button>
            <el-button type="success" plain @click="go('/ai-chat')">问问 AI</el-button>
          </el-space>
        </el-col>

        <el-col :xs="24" :md="8">
          <div style="display: flex; justify-content: center; align-items: center; min-height: 130px;">
            <el-icon :size="110" color="#79bbff"><Collection /></el-icon>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <div v-loading="loading" style="margin-top: 16px;">
      <el-row :gutter="16">
        <el-col
          v-for="card in statCards"
          :key="card.label"
          :xs="24"
          :sm="8"
          style="margin-bottom: 16px;"
        >
          <el-card shadow="hover" :body-style="{ padding: '20px' }">
            <el-row :gutter="14" align="middle">
              <el-col :span="5">
                <div
                  :style="{
                    width: '46px',
                    height: '46px',
                    borderRadius: '12px',
                    background: card.bg,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }"
                >
                  <el-icon :size="24" :color="card.color">
                    <component :is="card.icon" />
                  </el-icon>
                </div>
              </el-col>
              <el-col :span="19">
                <div style="font-size: 13px; color: #909399;">{{ card.label }}</div>
                <div style="font-size: 30px; font-weight: 700; line-height: 1.2; color: #303133; margin-top: 2px;">
                  {{ displayStat(card.value) }}
                </div>
                <el-text type="info" size="small">{{ card.subtitle }}</el-text>
              </el-col>
            </el-row>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin: 26px 0 12px;">
      <div>
        <div style="font-size: 20px; font-weight: 700; color: #303133;">系统功能</div>
        <div style="font-size: 13px; color: #909399; margin-top: 4px;">从选座到借书，一站式完成</div>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col
        v-for="feature in visibleFeatures"
        :key="feature.title"
        :xs="24"
        :sm="12"
        :md="8"
        style="margin-bottom: 16px;"
      >
        <el-card
          shadow="hover"
          :body-style="{ padding: '20px' }"
          style="height: 100%; cursor: pointer;"
          @click="go(feature.path)"
        >
          <el-space :size="14" alignment="flex-start">
            <div
              :style="{
                width: '46px',
                height: '46px',
                borderRadius: '12px',
                background: feature.bg,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }"
            >
              <el-icon :size="24" :color="feature.color">
                <component :is="feature.icon" />
              </el-icon>
            </div>
            <div>
              <div style="font-size: 16px; font-weight: 600; color: #303133;">{{ feature.title }}</div>
              <div style="font-size: 13px; color: #909399; line-height: 1.6; margin-top: 6px;">
                {{ feature.desc }}
              </div>
              <div style="font-size: 13px; color: #409eff; margin-top: 10px;">进入 →</div>
            </div>
          </el-space>
        </el-card>
      </el-col>
    </el-row>

    <el-card
      shadow="never"
      :body-style="{ padding: '20px' }"
      style="margin-top: 8px; background: #fdf6ec; border-color: #faecd8;"
    >
      <div style="font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 10px;">使用小贴士</div>
      <el-space direction="vertical" :size="6">
        <el-text size="small">开放时间：08:00 - 22:00</el-text>
        <el-text size="small">座位预约只支持整点/半点，单次最长 4 小时</el-text>
        <el-text size="small">图书预借保留 2 天，逾期系统自动取消</el-text>
        <el-text size="small">取消座位预约、查看预借状态请到“我的预约”</el-text>
      </el-space>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Calendar,
  ChatDotRound,
  Collection,
  Setting,
  Tickets,
  User
} from '@element-plus/icons-vue'
import { useUser } from '@/utils/user'
import { getAreaList, getMyReservations, getSeatList } from '@/api/seat'
import { getBookPageList, getMyBorrows } from '@/api/book'

const router = useRouter()
const { userInfo } = useUser()

const loading = ref(false)
const slot = ref({ date: '', start_time: '', end_time: '', label: '' })
const availableSeats = ref(null)
const availableAreaCount = ref(0)
const openAreaCount = ref(0)
const seatsPartial = ref(false)
const bookTotal = ref(null)
const mySeatActive = ref(null)
const myBookActive = ref(null)
const myActiveTotal = ref(null)

const pad = (value) => String(value).padStart(2, '0')
const formatDate = (value) =>
  `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`

// 计算“当前可预约”的时段：未到 8 点用 8 点，超过 22 点用明天 8 点
const buildCurrentSlot = () => {
  const start = new Date()
  start.setSeconds(0, 0)

  const minutes = start.getMinutes()
  if (minutes !== 0 && minutes !== 30) {
    if (minutes < 30) {
      start.setMinutes(30)
    } else {
      start.setHours(start.getHours() + 1, 0, 0, 0)
    }
  }

  let prefix = '今天'
  const open = new Date(start)
  open.setHours(8, 0, 0, 0)
  const close = new Date(start)
  close.setHours(22, 0, 0, 0)

  if (start < open) {
    start.setTime(open.getTime())
  } else if (start >= close) {
    start.setDate(start.getDate() + 1)
    start.setHours(8, 0, 0, 0)
    prefix = '明日'
  }

  let end = new Date(start.getTime() + 60 * 60 * 1000)
  const endLimit = new Date(start)
  endLimit.setHours(22, 0, 0, 0)
  if (end > endLimit) end = endLimit

  const startTime = `${pad(start.getHours())}:${pad(start.getMinutes())}`
  const endTime = `${pad(end.getHours())}:${pad(end.getMinutes())}`

  return {
    date: formatDate(start),
    start_time: startTime,
    end_time: endTime,
    label: `${prefix} ${startTime}-${endTime}`
  }
}

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const userName = computed(
  () => userInfo.value?.name || userInfo.value?.username || '同学'
)
const isAdmin = computed(() => userInfo.value?.role === 'admin')
const todayText = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
  weekday: 'long'
})

const features = [
  {
    title: '座位预约',
    desc: '选择阅览区、日期和时段，查看空闲座位并提交预约。',
    icon: Calendar,
    color: '#409eff',
    bg: '#ecf5ff',
    path: '/seat'
  },
  {
    title: '图书预借',
    desc: '按书名、作者或 ISBN 检索馆藏，在线提交预借申请。',
    icon: Collection,
    color: '#67c23a',
    bg: '#f0f9eb',
    path: '/books'
  },
  {
    title: 'AI 智能助手',
    desc: '用对话查询座位、图书和我的预约，也支持预约与取消。',
    icon: ChatDotRound,
    color: '#e6a23c',
    bg: '#fdf6ec',
    path: '/ai-chat'
  },
  {
    title: '我的预约',
    desc: '查看座位预约和图书预借状态，取消预约或离座。',
    icon: Tickets,
    color: '#909399',
    bg: '#f4f4f5',
    path: '/my'
  },
  {
    title: '后台管理',
    desc: '区域、座位、图书、分类、审批和用户管理。',
    icon: Setting,
    color: '#f56c6c',
    bg: '#fef0f0',
    path: '/admin/areas',
    adminOnly: true
  }
]

const visibleFeatures = computed(() =>
  features.filter((item) => !item.adminOnly || isAdmin.value)
)

const displayStat = (value) => {
  if (loading.value || value === null || value === undefined) return '--'
  return value
}

const seatSubtitle = computed(() => {
  if (availableSeats.value === null) return '数据加载失败'

  const base = slot.value.label || '当前时段'
  const suffix = seatsPartial.value ? '（部分区域失败）' : ''

  if (openAreaCount.value === 0) {
    return `${base} · 当前时段无开放区域`
  }
  if (availableAreaCount.value === 0) {
    return `${base} · 当前时段暂无空闲${suffix}`
  }
  return `${base} · ${availableAreaCount.value} 个阅览区可约${suffix}`
})

const myActiveSubtitle = computed(() => {
  if (myActiveTotal.value === null) return '数据加载失败'
  return `座位 ${mySeatActive.value ?? 0} · 图书 ${myBookActive.value ?? 0}`
})

const statCards = computed(() => [
  {
    label: '可预约座位',
    value: availableSeats.value,
    subtitle: seatSubtitle.value,
    icon: Calendar,
    color: '#409eff',
    bg: '#ecf5ff'
  },
  {
    label: '我的进行中预约',
    value: myActiveTotal.value,
    subtitle: myActiveSubtitle.value,
    icon: Tickets,
    color: '#67c23a',
    bg: '#f0f9eb'
  },
  {
    label: '馆藏图书',
    value: bookTotal.value,
    subtitle: bookTotal.value === null ? '数据加载失败' : '可检索馆藏',
    icon: Collection,
    color: '#e6a23c',
    bg: '#fdf6ec'
  }
])

const go = (path) => {
  router.push(path)
}

const loadSeats = async () => {
  try {
    const areaRes = await getAreaList()
    const areas = (areaRes.data || []).filter((area) => area.status === 1)
    const openAreas = areas.filter(
      (area) =>
        area.open_time <= slot.value.start_time &&
        area.close_time >= slot.value.end_time
    )

    openAreaCount.value = openAreas.length
    if (!openAreas.length) {
      availableSeats.value = 0
      availableAreaCount.value = 0
      seatsPartial.value = false
      return
    }

    const results = await Promise.allSettled(
      openAreas.map((area) =>
        getSeatList({
          area_id: area.id,
          date: slot.value.date,
          start_time: slot.value.start_time,
          end_time: slot.value.end_time
        })
      )
    )

    let total = 0
    let areaCount = 0
    let failed = 0

    results.forEach((result) => {
      if (result.status === 'fulfilled' && result.value?.code === 200) {
        const seats = result.value.data || []
        const count = seats.filter((seat) => seat.status === 1).length
        total += count
        if (count > 0) areaCount += 1
      } else {
        failed += 1
      }
    })

    availableSeats.value = failed === openAreas.length ? null : total
    availableAreaCount.value = areaCount
    seatsPartial.value = failed > 0
  } catch (error) {
    console.error('加载座位统计失败：', error)
    availableSeats.value = null
    availableAreaCount.value = 0
    openAreaCount.value = 0
    seatsPartial.value = false
  }
}

const loadBookTotal = async () => {
  try {
    const res = await getBookPageList({ page: 1, page_size: 1 })
    bookTotal.value = res.data?.total ?? 0
  } catch (error) {
    console.error('加载图书总数失败：', error)
    bookTotal.value = null
  }
}

const loadMyActive = async () => {
  const [seatResult, bookResult] = await Promise.allSettled([
    getMyReservations(),
    getMyBorrows()
  ])

  let seatCount = null
  let bookCount = null

  if (seatResult.status === 'fulfilled') {
    seatCount = (seatResult.value.data || []).filter((item) =>
      ['pending', 'reserved'].includes(item.status)
    ).length
  }
  if (bookResult.status === 'fulfilled') {
    bookCount = (bookResult.value.data || []).filter((item) =>
      ['pending', 'reserved', 'pickup'].includes(item.status)
    ).length
  }

  mySeatActive.value = seatCount
  myBookActive.value = bookCount
  myActiveTotal.value =
    seatCount === null && bookCount === null
      ? null
      : (seatCount || 0) + (bookCount || 0)
}

const loadHomeData = async () => {
  loading.value = true
  slot.value = buildCurrentSlot()
  await Promise.allSettled([loadSeats(), loadBookTotal(), loadMyActive()])
  loading.value = false
}

onMounted(loadHomeData)
</script>
