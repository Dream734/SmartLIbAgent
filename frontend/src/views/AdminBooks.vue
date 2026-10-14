<template>
  <div>
    <el-card>
      <div style="margin-bottom: 10px; display: flex">
        <el-input v-model="params.keywords" placeholder="书名 / 作者 / ISBN" clearable style="width: 240px; margin-right: 10px" @keyup.enter="handleSearch" />
        <el-select v-model="params.category_id" placeholder="全部分类" clearable style="width: 160px; margin-right: 10px" @change="handleSearch">
          <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button type="success" @click="openCreate">新增图书</el-button>
      </div>
      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="书名" min-width="160" />
        <el-table-column prop="author" label="作者" width="140" />
        <el-table-column label="分类" width="120">
          <template #default="{ row }">{{ row.category_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="可预借" width="100">
          <template #default="{ row }">{{ row.available }} / {{ row.total }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'error'">{{ row.status === 1 ? '上架' : '下架' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination background layout="prev, pager, next, total" :total="total" v-model:page-size="params.pageSize" v-model:current-page="params.page" @current-change="load" />
      </div>
    </el-card>

    <el-dialog v-model="visible" :title="isEdit ? '编辑图书' : '新增图书'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="书名" prop="title"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="作者" prop="author"><el-input v-model="form.author" /></el-form-item>
        <el-form-item label="ISBN"><el-input v-model="form.isbn" /></el-form-item>
        <el-form-item label="出版社"><el-input v-model="form.publisher" /></el-form-item>
        <el-form-item label="出版年份"><el-input-number v-model="form.publish_year" :min="0" /></el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category_id" clearable style="width: 100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="封面URL"><el-input v-model="form.cover" /></el-form-item>
        <el-form-item label="总册数"><el-input-number v-model="form.total" :min="0" /></el-form-item>
        <el-form-item label="可借数"><el-input-number v-model="form.available" :min="0" /></el-form-item>
        <el-form-item label="索书号"><el-input v-model="form.location" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="form.summary" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="form.status" :active-value="1" :inactive-value="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCategoryList, getBookPageList, createBook, updateBook, deleteBook } from '@/api/book'

const list = ref([])
const total = ref(0)
const categories = ref([])
const loading = ref(false)
const visible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const submitting = ref(false)
const formRef = ref()
const params = reactive({ page: 1, pageSize: 10, keywords: '', category_id: null })
const form = reactive({ title: '', author: '', isbn: '', publisher: '', publish_year: null, category_id: null, cover: '', total: 1, available: 1, location: '', summary: '', status: 1 })
const rules = {
  title: [{ required: true, message: '请输入书名', trigger: 'blur' }],
  author: [{ required: true, message: '请输入作者', trigger: 'blur' }]
}

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
      list.value = res.data?.list
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

const resetForm = () =>
  Object.assign(form, { title: '', author: '', isbn: '', publisher: '', publish_year: null, category_id: null, cover: '', total: 1, available: 1, location: '', summary: '', status: 1 })

const openCreate = () => {
  isEdit.value = false
  editId.value = null
  resetForm()
  visible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    title: row.title,
    author: row.author,
    isbn: row.isbn,
    publisher: row.publisher,
    publish_year: row.publish_year,
    category_id: row.category_id,
    cover: row.cover,
    total: row.total,
    available: row.available,
    location: row.location,
    summary: row.summary,
    status: row.status
  })
  visible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const payload = {
      title: form.title,
      author: form.author,
      isbn: form.isbn || null,
      publisher: form.publisher || null,
      publish_year: form.publish_year,
      category_id: form.category_id,
      cover: form.cover || null,
      total: form.total,
      available: form.available,
      location: form.location || null,
      summary: form.summary || null,
      status: form.status
    }
    const res = isEdit.value ? await updateBook(editId.value, payload) : await createBook(payload)
    if (res.code === 200) {
      ElMessage.success('保存成功')
      visible.value = false
      load()
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除图书「${row.title}」吗？`, '提示', { type: 'warning' })
    .then(async () => {
      const res = await deleteBook(row.id)
      if (res.code === 200) {
        ElMessage.success('删除成功')
        load()
      }
    })
    .catch(() => {})
}

onMounted(() => {
  loadCategories()
  load()
})
</script>
