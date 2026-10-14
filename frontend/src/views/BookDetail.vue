<template>
  <div>
    <el-card>
      <div class="detail">
        <img v-if="book.cover" :src="book.cover" class="cover" />
        <div class="info">
          <h2>{{ book.title }}</h2>
          <p><span class="label">作者</span>{{ book.author || '-' }}</p>
          <p><span class="label">分类</span>{{ book.category_name || '-' }}</p>
          <p><span class="label">ISBN</span>{{ book.isbn || '-' }}</p>
          <p><span class="label">出版社</span>{{ book.publisher || '-' }}（{{ book.publish_year || '-' }}）</p>
          <p><span class="label">索书号</span>{{ book.location || '-' }}</p>
          <p><span class="label">可预借</span>{{ book.available }} / {{ book.total }}</p>
          <p class="summary">{{ book.summary || '暂无简介' }}</p>
          <div class="actions">
            <el-button type="primary" :disabled="book.available <= 0" @click="borrow">预借</el-button>
            <el-button @click="router.back()">返回</el-button>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getBookDetail, createBorrow } from '@/api/book'

const route = useRoute()
const router = useRouter()
const book = ref({})

const load = async () => {
  const res = await getBookDetail(route.params.id)
  if (res.code === 200) book.value = res.data
}

const borrow = async () => {
  try {
    const res = await createBorrow({ book_id: book.value.id })
    if (res.code === 200) {
      ElMessage.success('预借成功')
      load()
    }
  } catch (e) {
    // 错误提示已由请求拦截器处理
  }
}

onMounted(load)
</script>

<style scoped>
.detail {
  display: flex;
}
.cover {
  width: 180px;
  height: 240px;
  object-fit: cover;
  margin-right: 24px;
  border-radius: 6px;
}
.info p {
  margin: 8px 0;
  color: #333;
}
.label {
  display: inline-block;
  width: 64px;
  color: #909399;
}
.summary {
  line-height: 1.6;
}
.actions {
  margin-top: 16px;
}
</style>
