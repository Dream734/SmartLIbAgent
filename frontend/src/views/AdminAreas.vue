<template>
  <div>
    <el-card>
      <div style="margin-bottom: 10px">
        <el-button type="success" @click="openCreate">新增区域</el-button>
      </div>
      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="区域名称" />
        <el-table-column prop="floor" label="楼层" width="100" />
        <el-table-column prop="open_time" label="开放时间" width="120" />
        <el-table-column prop="close_time" label="关闭时间" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'error'">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="visible" :title="isEdit ? '编辑区域' : '新增区域'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="楼层" prop="floor"><el-input-number v-model="form.floor" :min="1" /></el-form-item>
        <el-form-item label="开放时间" prop="open_time">
          <el-select v-model="form.open_time">
            <el-option v-for="s in slots" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="关闭时间" prop="close_time">
          <el-select v-model="form.close_time">
            <el-option v-for="s in slots" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
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
import { getAreaList, createArea, updateArea, deleteArea } from '@/api/seat'

const list = ref([])
const loading = ref(false)
const visible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const submitting = ref(false)
const formRef = ref()
const form = reactive({ name: '', floor: 1, open_time: '08:00', close_time: '22:00', status: 1 })
const rules = { name: [{ required: true, message: '请输入区域名称', trigger: 'blur' }] }

const slots = []
for (let m = 480; m <= 1320; m += 30) {
  slots.push(`${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`)
}

const load = async () => {
  loading.value = true
  try {
    const res = await getAreaList()
    if (res.code === 200) list.value = res.data
  } finally {
    loading.value = false
  }
}

const resetForm = () => Object.assign(form, { name: '', floor: 1, open_time: '08:00', close_time: '22:00', status: 1 })

const openCreate = () => {
  isEdit.value = false
  editId.value = null
  resetForm()
  visible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, { name: row.name, floor: row.floor, open_time: row.open_time, close_time: row.close_time, status: row.status })
  visible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const payload = { name: form.name, floor: form.floor, open_time: form.open_time, close_time: form.close_time, status: form.status }
    const res = isEdit.value ? await updateArea(editId.value, payload) : await createArea(payload)
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
  ElMessageBox.confirm(`确定删除区域「${row.name}」吗？`, '提示', { type: 'warning' })
    .then(async () => {
      const res = await deleteArea(row.id)
      if (res.code === 200) {
        ElMessage.success('删除成功')
        load()
      }
    })
    .catch(() => {})
}

onMounted(load)
</script>
