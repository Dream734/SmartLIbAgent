<template>
    <div>
        <el-card>
            <template #header>
                <div style="font-size: 16px; font-weight: bold">
                    <span>AI智能助手</span>
                </div>
            </template>
        
            <div
                ref = "listRef"
                style="
                    height: 480px;
                    overflow-y: auto;
                    padding: 8px 4px;
                    background-color: #f0f0f0;
                    border-radius: 6px;
                "
            >

                <div 
                    v-for="(item, index) in messages" 
                        :key="index"
                        :style="{ display: 'flex', 
                        alignItems: 'flex-start', 
                        justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start', 
                        marginBottom: '12px' }"
                >
                

                    <div
                        class="bubble"
                        :style="{
                            maxWidth: '70%',

                            padding: '10px 12px',
                            borderRadius: '8px',
                            backgroundColor: item.role ==='user' ? '#409eff' :'#fff',
                            color: item.role === 'user' ? '#fff' :'#333', 
                            lineHeight: '1.6',
                            boxShadow: '0 1px 2px rgba(0,0,0,0.06)'
                        }"
                        v-html="parseMarkdown(item.content)"
                    ></div>
                </div>
            </div>
            <!-- 输入框 -->
            <div style="margin-top: 12px; display: flex; gap: 8px; align-items: flex-end">
                <el-input
                    v-model="input"
                    type="textarea"
                    :rows="2"
                    placeholder="问问怎么预约座位，预先借书籍、开放时间..."
                    @keydown.enter.exact.prevent="handleSend"
                    @keydown.enter.shift.top
                >
                </el-input>
                <el-button type="primary" @click="handleSend" :loading="loading">发送</el-button>

            </div>




        </el-card>
    </div>
</template>


<script setup>
import { ref, nextTick } from "vue"
import { chatApi } from '@/api/ai'
import { marked } from 'marked'
import DOMPurify from 'dompurify' // 过滤危险的 HTML，防止 XSS 攻击


const loading = ref(false)
const input = ref('')
const listRef = ref()


const messages = ref([
    {role:'assistant',
    content:'您好，我是图书馆预约智能助手。你可以向我提问怎么预约'}
])



const scrollToBottom =() => {
    nextTick(() => {
    const elem = listRef.value
    if (elem) elem.scrollTop = elem.scrollHeight
    })
}


const handleSend = async () => {
    const text = input.value.trim()
    if (!text || loading.value) return

    messages.value.push({ role: 'user', content: text })
    input.value = ''
    loading.value = true
    scrollToBottom()
    try {
        const res = await chatApi({ messages: messages.value })
        if (res.code === 200) {
            messages.value.push(res.data)
            scrollToBottom()
        }
    } 
    finally {
        loading.value = false
    }
}

const parseMarkdown = (text) => {
    if (!text) return ''
    marked.setOptions({ breaks: true })
    // 使用marked解析，然后用 DOMPurify 清理
    const rawHtml = marked.parse(text)
    return DOMPurify.sanitize(rawHtml)
}

</script>

<style scoped>
/* 去除 markdown 元素的默认外边距，使气泡高度贴合内容 */
.bubble :deep(p),
.bubble :deep(ul),
.bubble :deep(ol),
.bubble :deep(pre) {
    margin: 0;
}

.bubble :deep(ul),
.bubble :deep(ol) {
    padding-left: 1.2em;
}
</style>