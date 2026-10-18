<template>
    <div>
        <el-card>
            <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 16px; font-weight: bold;">AI智能助手</span>
                    <el-button link type="danger" @click="clearMessages">清空对话</el-button>
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
                    >
                        <div v-if="item.thinking" class="thinking-wrap">
                            <div v-if="item.thinkingCollapsed" class="thinking-toggle" @click="toggleThinking(index)">思考过程</div>
                            <template v-else>
                                <div class="thinking-toggle" @click="toggleThinking(index)">收起思考过程</div>
                                <div class="thinking">{{ item.thinking }}</div>
                            </template>
                        </div>
                        <div v-html="parseMarkdown(item.content)"></div>
                    </div>
                </div>
            </div>
            <!-- 输入框 -->
            <div style="margin-top: 12px; display: flex; gap: 8px; align-items: flex-end">
                <el-input
                    v-model="input"
                    type="textarea"
                    :rows="2"
                    placeholder="例如：帮我预约1楼明天上午9点的座位 / 帮我预借《Python编程》"
                    @keydown.enter.exact.prevent="handleSend"
                >
                </el-input>
                <el-button type="primary" @click="handleSend" :loading="loading">发送</el-button>

            </div>




        </el-card>
    </div>
</template>


<script setup>
import { ref, nextTick, watch } from "vue"
import { chatStream } from '@/api/ai'
import { marked } from 'marked'
import DOMPurify from 'dompurify' // 过滤危险的 HTML，防止 XSS 攻击
import { ElMessage, ElMessageBox } from 'element-plus'


const loading = ref(false)
const input = ref('')
const listRef = ref()
const abortController = ref(null)

// 兜底：后端异常时不要把工具返回的原始 JSON 渲染到气泡里
const isToolOutput = (text) => {
    const raw = (text || '').trim()
    if (!raw) return false
    if (raw.includes('<tool_call>') || raw.includes('</tool_call>')) return true
    if (raw.startsWith('{"ok"')) return true
    return raw.includes('"ok"') && ['"books"', '"seats"', '"areas"', '"reservations"', '"borrows"', '"action_type"'].some((key) => raw.includes(key))
}

const STORAGE_KEY = 'lab-agent:ai-chat-messages'

const defaultMessages = () => [
    {role:'assistant',
    content:'您好，我是图书馆智能助手。你可以这样问我：\n\n- 帮我预约 1 楼明天上午 9 点的座位\n- 帮我预借《Python编程》\n- 我预约了哪些座位？'}
]

const loadMessages = () => {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY)
        if (!raw) return defaultMessages()
        const parsed = JSON.parse(raw)
        if (!Array.isArray(parsed)) return defaultMessages()
        const cleaned = parsed.filter(
            (item) => item && ['user', 'assistant'].includes(item.role) &&
                typeof item.content === 'string' &&
                !(item.role === 'assistant' && isToolOutput(item.content))
        )
        return cleaned.length ? cleaned : defaultMessages()
    } catch (error) {
        console.error('读取 AI 对话记录失败：', error)
        return defaultMessages()
    }
}

const messages = ref(loadMessages())

// 切换页面只卸载组件，不销毁 sessionStorage；重新进入时从缓存恢复
watch(
    messages,
    (value) => {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value))
        } catch (error) {
            console.error('保存 AI 对话记录失败：', error)
        }
    },
    { deep: true }
)

const clearMessages = () => {
    ElMessageBox.confirm('确定清空当前对话吗？', '提示', { type: 'warning' })
        .then(() => {
            abortController.value?.abort()
            messages.value = defaultMessages()
            sessionStorage.removeItem(STORAGE_KEY)
            ElMessage.success('已清空')
        })
        .catch(() => {})
}

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

    // 历史里如果残留工具 JSON，不要再次发给后端污染上下文
    const history = messages.value
        .filter(
            (item) => !(item.role === 'assistant' && isToolOutput(item.content))
        )
        .map((item) => ({ role: item.role, content: item.content }))

    messages.value.push({ role: 'assistant', content: '', thinking: '', thinkingCollapsed: false })
    const assistantIndex = messages.value.length - 1
    scrollToBottom()

    const controller = new AbortController()
    abortController.value = controller

    try {
        await chatStream(
            { messages: history },
            {
                signal: controller.signal,
                onThinking: (content) => {
                    const thinking = messages.value[assistantIndex].thinking
                    messages.value[assistantIndex].thinking =
                        (thinking ? `${thinking}\n` : '') + content
                    scrollToBottom()
                },
                onToken: (content) => {
                    messages.value[assistantIndex].content += content
                    if (
                        messages.value[assistantIndex].thinking &&
                        !messages.value[assistantIndex].thinkingCollapsed
                    ) {
                        messages.value[assistantIndex].thinkingCollapsed = true
                    }
                    scrollToBottom()
                },
                onDone: (message) => {
                    messages.value[assistantIndex].content =
                        message?.content || messages.value[assistantIndex].content
                    scrollToBottom()
                },
                onError: (message) => {
                    throw new Error(message || 'AI 回答失败')
                }
            }
        )
    } catch (error) {
        if (error.name === 'AbortError') return
        if (!messages.value[assistantIndex].content) {
            messages.value[assistantIndex].content = 'AI 回答失败，请稍后重试。'
        } else if (isToolOutput(messages.value[assistantIndex].content)) {
            messages.value[assistantIndex].content = 'AI 返回内容异常，请重试。'
        }
        ElMessage.error(error.message || 'AI 对话请求失败')
        console.error('AI 流式对话请求失败：', error)
    } finally {
        loading.value = false
        abortController.value = null
    }
}

const toggleThinking = (index) => {
    messages.value[index].thinkingCollapsed = !messages.value[index].thinkingCollapsed
}

const parseMarkdown = (text) => {
    if (!text) return ''
    if (isToolOutput(text)) {
        return '<p>AI 返回内容异常，请重试。</p>'
    }
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

.thinking {
    font-size: 12px;
    color: #999;
    white-space: pre-wrap;
    margin-bottom: 8px;
    padding-left: 8px;
    border-left: 3px solid #dcdfe6;
}

.thinking-toggle {
    font-size: 12px;
    color: #999;
    cursor: pointer;
    margin-bottom: 6px;
}
</style>
