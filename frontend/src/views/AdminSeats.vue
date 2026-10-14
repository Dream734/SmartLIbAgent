<template>
  <div>
    <el-card>
      <div style="margin-bottom: 10px; display: flex">
        <el-select v-model="areaId" placeholder="选择区域" clearable style="width: 180px; margin-right: 10px" @change="load">
          <el-option v-for="a in areas" :key="a.id" :label="a.name" :value="a.id" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button type="success" @click="openCreate">新增座位</el-button>
      </div>
      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="seat_no" label="座位号" />
        <el-table-column prop="area_name" label="区域" width="140" />
        <el-table-column prop="seat_type" label="类型" width="120" />
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

    <el-dialog v-model="visible" :title="isEdit ? '编辑座位' : '新增座位'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="区域" prop="area_id">
          <el-select v-model="form.area_id" style="width: 100%">
            <el-option v-for="a in areas" :key="a.id" :label="a.name" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="座位号" prop="seat_no"><el-input v-model="form.seat_no" /></el-form-item>
        <el-form-item label="类型" prop="seat_type">
          <el-select v-model="form.seat_type" style="width: 100%">
            <el-option v-for="t in seatTypes" :key="t" :label="t" :value="t" />
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
import { getAreaList, getSeatList, createSeat, updateSeat, deleteSeat } from '@/api/seat'

const list = ref([])
const areas = ref([])
const areaId = ref(null)
const loading = ref(false)
const visible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const submitting = ref(false)
const formRef = ref()
const seatTypes = ['普通', '靠窗', '电源', '电脑']
const form = reactive({ area_id: null, seat_no: '', seat_type: '普通', status: 1 })
const rules = {
  area_id: [{ required: true, message: '请选择区域', trigger: 'change' }],
  seat_no: [{ required: true, message: '请输入座位号', trigger: 'blur' }]
}

const loadAreas = async () => {
  const res = await getAreaList()
  if (res.code === 200) areas.value = res.data
}

const load = async () => {
  loading.value = true
  try {
    const res = await getSeatList({ area_id: areaId.value || undefined })
    if (res.code === 200) list.value = res.data
  } finally {
    loading.value = false
  }
}

const resetForm = () => Object.assign(form, { area_id: null, seat_no: '', seat_type: '普通', status: 1 })

const openCreate = () => {
  isEdit.value = false
  editId.value = null
  resetForm()
  visible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, { area_id: row.area_id, seat_no: row.seat_no, seat_type: row.seat_type, status: row.status })
  visible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const payload = { area_id: form.area_id, seat_no: form.seat_no, seat_type: form.seat_type, status: form.status }
    const res = isEdit.value ? await updateSeat(editId.value, payload) : await createSeat(payload)
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
  ElMessageBox.confirm(`确定删除座位「${row.seat_no}」吗？`, '提示', { type: 'warning' })
    .then(async () => {
      const res = await deleteSeat(row.id)
      if (res.code === 200) {
        ElMessage.success('删除成功')
        load()
      }
    })
    .catch(() => {})
}

onMounted(() => {
  loadAreas()
  load()
})
</script>
