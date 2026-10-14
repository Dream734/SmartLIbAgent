<template>
  <div>
    <el-card>
      <div class="filters">
        <el-input
          v-model="params.keywords"
          placeholder="书名 / 作者 / ISBN"
          clearable
          style="width: 240px; margin-right: 10px"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="params.category_id" placeholder="全部分类" clearable style="width: 160px; margin-right: 10px" @change="handleSearch">
          <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
      </div>
    </el-card>

    <el-card style="margin-top: 10px">
      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column label="封面" width="80">
          <template #default="{ row }">
            <img v-if="row.cover" :src="row.cover" style="width: 50px; height: 60px; object-fit: cover" />
          </template>
        </el-table-column>
        <el-table-column prop="title" label="书名" min-width="160" />
        <el-table-column prop="author" label="作者" width="140" />
        <el-table-column label="分类" width="120">
          <template #default="{ row }">{{ row.category_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="可预借" width="100">
          <template #default="{ row }">{{ row.available }} / {{ row.total }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row)">详情</el-button>
            <el-button link type="success" :disabled="row.available <= 0" @click="borrow(row)">预借</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          background
          layout="prev, pager, next, total"
          :total="total"
          v-model:page-size="params.pageSize"
          v-model:current-page="params.page"
          @current-change="load"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCategoryList, getBookPageList, createBorrow } from '@/api/book'

const router = useRouter()
const tableData = ref([])
const total = ref(0)
const loading = ref(false)
const categories = ref([])

const params = reactive({
  page: 1,
  pageSize: 10,
  keywords: '',
  category_id: null
})

const load = async () => {
  loading.value = true
  try {
    const res = await getBookPageList({
      page: params.page,
      page_size: params.pageSize,
      keywords: params.keywords || undefined,
      category_id: params.category_id || undefined
    })
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  const res = await getCategoryList()
  if (res.code === 200) categories.value = res.data
}

const handleSearch = () => {
  params.page = 1
  load()
}

const goDetail = (row) => router.push(`/books/${row.id}`)

const borrow = async (row) => {
  try {
    const res = await createBorrow({ book_id: row.id })
    if (res.code === 200) {
      ElMessage.success('预借成功')
      load()
    }
  } catch (e) {
    // 错误提示已由请求拦截器处理
  }
}

onMounted(() => {
  loadCategories()
  load()
})
</script>

<style scoped>
.filters {
  display: flex;
  align-items: center;
}
</style>
