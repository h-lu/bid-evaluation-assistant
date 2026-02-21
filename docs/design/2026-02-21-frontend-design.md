# 前端设计规范

> 版本：v1.0
> 设计日期：2026-02-21
> 来源参考：Vue 3 官方文档、Element Plus 设计规范

---

## 一、技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Vue** | 3.4+ | 前端框架 |
| **TypeScript** | 5.0+ | 类型支持 |
| **Vite** | 5.0+ | 构建工具 |
| **Element Plus** | 2.5+ | UI 组件库 |
| **Vue Router** | 4.x | 路由管理 |
| **Pinia** | 2.x | 状态管理 |
| **Axios** | 1.x | HTTP 客户端 |
| **PDF.js** | 4.x | PDF 查看器 |

---

## 二、项目结构

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                    # API 接口
│   │   ├── index.ts            # Axios 实例配置
│   │   ├── auth.ts             # 认证接口
│   │   ├── project.ts          # 项目接口
│   │   ├── document.ts         # 文档接口
│   │   ├── evaluation.ts       # 评估接口
│   │   └── retrieval.ts        # 检索接口
│   │
│   ├── assets/                 # 静态资源
│   │   ├── styles/
│   │   │   ├── variables.scss  # SCSS 变量
│   │   │   └── global.scss     # 全局样式
│   │   └── images/
│   │
│   ├── components/             # 公共组件
│   │   ├── common/
│   │   │   ├── PageHeader.vue
│   │   │   ├── SearchBar.vue
│   │   │   └── Pagination.vue
│   │   ├── document/
│   │   │   ├── DocumentUpload.vue
│   │   │   ├── DocumentList.vue
│   │   │   └── PdfViewer.vue
│   │   ├── evaluation/
│   │   │   ├── EvalProgress.vue
│   │   │   ├── EvalResultCard.vue
│   │   │   ├── PointToPointTable.vue
│   │   │   └── ReviewDialog.vue
│   │   └── layout/
│   │       ├── AppLayout.vue
│   │       ├── Sidebar.vue
│   │       └── Header.vue
│   │
│   ├── composables/            # 组合式函数
│   │   ├── useAuth.ts
│   │   ├── usePagination.ts
│   │   └── useNotification.ts
│   │
│   ├── router/                 # 路由配置
│   │   ├── index.ts
│   │   └── routes.ts
│   │
│   ├── stores/                 # 状态管理
│   │   ├── index.ts
│   │   ├── auth.ts
│   │   ├── project.ts
│   │   └── evaluation.ts
│   │
│   ├── types/                  # TypeScript 类型
│   │   ├── api.ts
│   │   ├── project.ts
│   │   ├── document.ts
│   │   └── evaluation.ts
│   │
│   ├── views/                  # 页面组件
│   │   ├── auth/
│   │   │   └── LoginView.vue
│   │   ├── dashboard/
│   │   │   └── DashboardView.vue
│   │   ├── project/
│   │   │   ├── ProjectListView.vue
│   │   │   ├── ProjectCreateView.vue
│   │   │   └── ProjectDetailView.vue
│   │   ├── document/
│   │   │   ├── DocumentListView.vue
│   │   │   └── DocumentDetailView.vue
│   │   ├── evaluation/
│   │   │   ├── EvaluationListView.vue
│   │   │   ├── EvaluationDetailView.vue
│   │   │   └── EvaluationReportView.vue
│   │   └── retrieval/
│   │       └── KnowledgeQueryView.vue
│   │
│   ├── App.vue
│   └── main.ts
│
├── .env.example
├── .eslintrc.cjs
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## 三、核心页面设计

### 3.1 页面路由

```typescript
// src/router/routes.ts
import type { RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue')
      },
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('@/views/project/ProjectListView.vue')
      },
      {
        path: 'projects/create',
        name: 'ProjectCreate',
        component: () => import('@/views/project/ProjectCreateView.vue')
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('@/views/project/ProjectDetailView.vue')
      },
      {
        path: 'documents',
        name: 'DocumentList',
        component: () => import('@/views/document/DocumentListView.vue')
      },
      {
        path: 'documents/:id',
        name: 'DocumentDetail',
        component: () => import('@/views/document/DocumentDetailView.vue')
      },
      {
        path: 'evaluations',
        name: 'EvaluationList',
        component: () => import('@/views/evaluation/EvaluationListView.vue')
      },
      {
        path: 'evaluations/:id',
        name: 'EvaluationDetail',
        component: () => import('@/views/evaluation/EvaluationDetailView.vue')
      },
      {
        path: 'evaluations/:id/report',
        name: 'EvaluationReport',
        component: () => import('@/views/evaluation/EvaluationReportView.vue')
      },
      {
        path: 'query',
        name: 'KnowledgeQuery',
        component: () => import('@/views/retrieval/KnowledgeQueryView.vue')
      }
    ]
  }
]
```

### 3.2 页面布局

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  Header (用户信息、通知、设置)                                                        │
├────────────┬────────────────────────────────────────────────────────────────────────┤
│            │                                                                        │
│  Sidebar   │                         Main Content                                  │
│            │                                                                        │
│  ├ 仪表盘  │   ┌──────────────────────────────────────────────────────────────┐    │
│  ├ 项目    │   │  Page Header (标题 + 操作按钮)                                 │    │
│  ├ 文档    │   └──────────────────────────────────────────────────────────────┘    │
│  ├ 评估    │                                                                        │
│  └ 知识库  │   ┌──────────────────────────────────────────────────────────────┐    │
│            │   │                                                              │    │
│            │   │                    Page Content                              │    │
│            │   │                                                              │    │
│            │   │                                                              │    │
│            │   │                                                              │    │
│            │   │                                                              │    │
│            │   │                                                              │    │
│            │   └──────────────────────────────────────────────────────────────┘    │
│            │                                                                        │
└────────────┴────────────────────────────────────────────────────────────────────────┘
```

### 3.3 核心页面设计

#### 3.3.1 评估报告页面（点对点应答格式）

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  评估报告 - 医疗器械采购项目                                                          │
│  评估日期: 2026-02-20    供应商: 供应商A     总分: 92.5    推荐: ✓ 通过              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ 一、资格审查                                                        通过 ✓   │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │ ┌────┬──────────┬────────────────┬────────────────┬────────┬───────┬─────┐ │   │
│  │ │序号│  评审项   │   招标要求      │   投标响应      │ 符合度 │ 得分  │溯源 │ │   │
│  │ ├────┼──────────┼────────────────┼────────────────┼────────┼───────┼─────┤ │   │
│  │ │ 1  │ 注册资本  │ ≥1000万元      │ 5000万元       │ ✓完全  │ 10/10 │[📄] │ │   │
│  │ │    │          │[招标文件P5]📄  │[投标文件P12]📄 │        │       │     │ │   │
│  │ ├────┼──────────┼────────────────┼────────────────┼────────┼───────┼─────┤ │   │
│  │ │ 2  │ 营业执照  │ 有效期内        │ 有效至2030年    │ ✓完全  │ 10/10 │[📄] │ │   │
│  │ │    │          │[招标文件P5]📄  │[投标文件P10]📄 │        │       │     │ │   │
│  │ └────┴──────────┴────────────────┴────────────────┴────────┴───────┴─────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ 二、技术评分                                                        45/50    │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │ ...                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ 综合评价                                                                     │   │
│  │ • 技术参数全面优于招标要求                                                   │   │
│  │ • 商务报价具有竞争力                                                         │   │
│  │ • 资质证书齐全有效                                                           │   │
│  │                                                                             │   │
│  │ 风险提示: 无                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  [导出PDF] [导出Excel] [返回列表]                                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

#### 3.3.2 PDF 查看器 + 溯源高亮

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  PDF 查看器 - 投标文件-供应商A.pdf                                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  [◀] [▶]  页码: 12 / 50    [🔍-] [🔍+] [⬇下载] [✕关闭]                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                             │   │
│  │  ... 其他内容 ...                                                           │   │
│  │                                                                             │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │ ████████████████████████████████████████████████████████████████    │   │   │
│  │  │ █ 注册资本：5000万元人民币                                        █    │   │   │
│  │  │ █ (黄色高亮显示引用内容)                                          █    │   │   │
│  │  │ ████████████████████████████████████████████████████████████████    │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                             │   │
│  │  ... 其他内容 ...                                                           │   │
│  │                                                                             │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 四、核心组件设计

### 4.1 点对点评估表格组件

```vue
<!-- src/components/evaluation/PointToPointTable.vue -->
<template>
  <el-table :data="items" border style="width: 100%">
    <el-table-column type="index" label="序号" width="60" />

    <el-table-column prop="criteriaName" label="评审项" width="150" />

    <el-table-column label="招标要求" width="250">
      <template #default="{ row }">
        <div class="requirement-cell">
          <p>{{ row.requirement }}</p>
          <el-link type="primary" @click="openDocument(row.requirementSource)">
            <el-icon><Document /></el-icon>
            {{ row.requirementSource }}
          </el-link>
        </div>
      </template>
    </el-table-column>

    <el-table-column label="投标响应" width="250">
      <template #default="{ row }">
        <div class="response-cell">
          <p>{{ row.response }}</p>
          <el-link type="primary" @click="openDocument(row.responseSource)">
            <el-icon><Document /></el-icon>
            {{ row.responseSource }}
          </el-link>
        </div>
      </template>
    </el-table-column>

    <el-table-column label="符合度" width="100" align="center">
      <template #default="{ row }">
        <el-tag :type="getComplianceType(row.complianceStatus)">
          {{ getComplianceLabel(row.complianceStatus) }}
        </el-tag>
      </template>
    </el-table-column>

    <el-table-column label="得分" width="100" align="center">
      <template #default="{ row }">
        <span :class="{ 'text-success': row.score === row.maxScore }">
          {{ row.score }}/{{ row.maxScore }}
        </span>
      </template>
    </el-table-column>

    <el-table-column label="评分理由" min-width="200">
      <template #default="{ row }">
        <el-tooltip :content="row.reasoning" placement="top">
          <span class="reasoning-text">{{ row.reasoning }}</span>
        </el-tooltip>
      </template>
    </el-table-column>

    <el-table-column label="置信度" width="100" align="center">
      <template #default="{ row }">
        <el-progress
          :percentage="row.confidence * 100"
          :status="row.confidence >= 0.9 ? 'success' : row.confidence >= 0.7 ? '' : 'warning'"
        />
      </template>
    </el-table-column>

    <el-table-column label="操作" width="100" v-if="showReview">
      <template #default="{ row }">
        <el-button type="primary" link @click="reviewItem(row)">
          审核
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { EvalItem } from '@/types/evaluation'

defineProps<{
  items: EvalItem[]
  showReview?: boolean
}>()

const emit = defineEmits<{
  openDocument: [source: string]
  reviewItem: [item: EvalItem]
}>()

const getComplianceType = (status: string) => {
  const types: Record<string, string> = {
    full: 'success',
    partial: 'warning',
    none: 'danger'
  }
  return types[status] || 'info'
}

const getComplianceLabel = (status: string) => {
  const labels: Record<string, string> = {
    full: '完全符合',
    partial: '部分符合',
    none: '不符合'
  }
  return labels[status] || status
}

const openDocument = (source: string) => {
  emit('openDocument', source)
}

const reviewItem = (item: EvalItem) => {
  emit('reviewItem', item)
}
</script>

<style scoped lang="scss">
.requirement-cell,
.response-cell {
  p {
    margin-bottom: 8px;
    line-height: 1.5;
  }
}

.reasoning-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.text-success {
  color: var(--el-color-success);
  font-weight: bold;
}
</style>
```

### 4.2 PDF 查看器组件

```vue
<!-- src/components/document/PdfViewer.vue -->
<template>
  <el-dialog
    v-model="visible"
    :title="fileName"
    width="80%"
    top="5vh"
    destroy-on-close
  >
    <template #header>
      <div class="pdf-header">
        <span>{{ fileName }}</span>
        <div class="pdf-controls">
          <el-button-group>
            <el-button @click="prevPage" :disabled="currentPage <= 1">
              <el-icon><ArrowLeft /></el-icon>
            </el-button>
            <el-button disabled>{{ currentPage }} / {{ totalPages }}</el-button>
            <el-button @click="nextPage" :disabled="currentPage >= totalPages">
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </el-button-group>
          <el-button-group>
            <el-button @click="zoomOut">
              <el-icon><ZoomOut /></el-icon>
            </el-button>
            <el-button disabled>{{ Math.round(scale * 100) }}%</el-button>
            <el-button @click="zoomIn">
              <el-icon><ZoomIn /></el-icon>
            </el-button>
          </el-button-group>
          <el-button @click="download">
            <el-icon><Download /></el-icon>
            下载
          </el-button>
        </div>
      </div>
    </template>

    <div class="pdf-container" ref="containerRef">
      <canvas ref="canvasRef"></canvas>
      <!-- 高亮层 -->
      <div class="highlight-layer" v-if="highlightBbox">
        <div
          class="highlight-box"
          :style="highlightStyle"
        ></div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'

// 设置 worker
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js'

const props = defineProps<{
  modelValue: boolean
  fileUrl: string
  fileName: string
  highlightPage?: number
  highlightBbox?: { x1: number; y1: number; x2: number; y2: number }
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const containerRef = ref<HTMLDivElement>()
const canvasRef = ref<HTMLCanvasElement>()
const pdfDoc = ref<pdfjsLib.PDFDocumentProxy>()
const currentPage = ref(1)
const totalPages = ref(0)
const scale = ref(1.5)

const highlightStyle = computed(() => {
  if (!props.highlightBbox || !containerRef.value) return {}
  const { x1, y1, x2, y2 } = props.highlightBbox
  return {
    left: `${x1 * scale.value}px`,
    top: `${y1 * scale.value}px`,
    width: `${(x2 - x1) * scale.value}px`,
    height: `${(y2 - y1) * scale.value}px`
  }
})

const renderPage = async (pageNum: number) => {
  if (!pdfDoc.value || !canvasRef.value) return

  const page = await pdfDoc.value.getPage(pageNum)
  const viewport = page.getViewport({ scale: scale.value })

  const canvas = canvasRef.value
  const context = canvas.getContext('2d')
  if (!context) return

  canvas.height = viewport.height
  canvas.width = viewport.width

  await page.render({
    canvasContext: context,
    viewport: viewport
  }).promise
}

const loadPdf = async () => {
  if (!props.fileUrl) return

  const loadingTask = pdfjsLib.getDocument(props.fileUrl)
  pdfDoc.value = await loadingTask.promise
  totalPages.value = pdfDoc.value.numPages

  if (props.highlightPage) {
    currentPage.value = props.highlightPage
  }

  await renderPage(currentPage.value)
}

watch(() => props.fileUrl, loadPdf, { immediate: true })

watch(currentPage, (page) => {
  renderPage(page)
})

watch(scale, () => {
  renderPage(currentPage.value)
})

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

const zoomIn = () => {
  if (scale.value < 3) {
    scale.value += 0.25
  }
}

const zoomOut = () => {
  if (scale.value > 0.5) {
    scale.value -= 0.25
  }
}

const download = () => {
  window.open(props.fileUrl, '_blank')
}
</script>

<style scoped lang="scss">
.pdf-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.pdf-controls {
  display: flex;
  gap: 12px;
}

.pdf-container {
  position: relative;
  overflow: auto;
  max-height: 70vh;
  text-align: center;
  background: #f5f5f5;
  padding: 20px;
}

.highlight-layer {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}

.highlight-box {
  position: absolute;
  background-color: rgba(255, 255, 0, 0.3);
  border: 2px solid #f0ad4e;
}
</style>
```

### 4.3 评估进度组件

```vue
<!-- src/components/evaluation/EvalProgress.vue -->
<template>
  <el-card class="eval-progress">
    <template #header>
      <div class="progress-header">
        <span>评估进度</span>
        <el-tag :type="statusType">{{ statusLabel }}</el-tag>
      </div>
    </template>

    <el-steps :active="activeStep" finish-status="success" align-center>
      <el-step title="检索文档" :description="stepDescription.retrieve" />
      <el-step title="资格审查" :description="stepDescription.qualification" />
      <el-step title="技术评分" :description="stepDescription.technical" />
      <el-step title="商务评分" :description="stepDescription.commercial" />
      <el-step title="人工审核" :description="stepDescription.review" v-if="needsReview" />
      <el-step title="完成" :description="stepDescription.complete" />
    </el-steps>

    <div class="progress-stats" v-if="totalSuppliers > 0">
      <el-progress
        :percentage="progressPercentage"
        :format="() => `${completedSuppliers}/${totalSuppliers}`"
      />
      <p>已评估 {{ completedSuppliers }} / {{ totalSuppliers }} 位供应商</p>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
  totalSuppliers: number
  completedSuppliers: number
  needsReview: boolean
  currentStep?: string
}>()

const statusType = computed(() => {
  const types: Record<string, string> = {
    pending: 'info',
    in_progress: 'warning',
    human_review: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[props.status] || 'info'
})

const statusLabel = computed(() => {
  const labels: Record<string, string> = {
    pending: '待评估',
    in_progress: '评估中',
    human_review: '人工审核',
    completed: '已完成',
    failed: '失败'
  }
  return labels[props.status] || props.status
})

const activeStep = computed(() => {
  if (props.status === 'completed') return 6
  if (props.status === 'human_review') return 5
  if (!props.currentStep) return 0

  const steps: Record<string, number> = {
    retrieve: 1,
    qualification: 2,
    technical: 3,
    commercial: 4
  }
  return steps[props.currentStep] || 0
})

const progressPercentage = computed(() => {
  if (props.totalSuppliers === 0) return 0
  return Math.round((props.completedSuppliers / props.totalSuppliers) * 100)
})

const stepDescription = computed(() => ({
  retrieve: props.currentStep === 'retrieve' ? '进行中...' : '',
  qualification: props.currentStep === 'qualification' ? '进行中...' : '',
  technical: props.currentStep === 'technical' ? '进行中...' : '',
  commercial: props.currentStep === 'commercial' ? '进行中...' : '',
  review: props.needsReview ? '待审核' : '跳过',
  complete: props.status === 'completed' ? '评估完成' : ''
}))
</script>

<style scoped lang="scss">
.eval-progress {
  margin-bottom: 20px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-stats {
  margin-top: 24px;
  text-align: center;

  p {
    margin-top: 8px;
    color: var(--el-text-color-secondary);
  }
}
</style>
```

---

## 五、状态管理

### 5.1 认证 Store

```typescript
// src/stores/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types/api'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const userRole = computed(() => user.value?.role || 'viewer')

  const login = async (username: string, password: string) => {
    const response = await authApi.login({ username, password })
    token.value = response.data.access_token
    user.value = response.data.user
    localStorage.setItem('token', response.data.access_token)
  }

  const logout = async () => {
    await authApi.logout()
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  const fetchUser = async () => {
    if (!token.value) return
    try {
      const response = await authApi.getCurrentUser()
      user.value = response.data
    } catch {
      token.value = null
      localStorage.removeItem('token')
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    userRole,
    login,
    logout,
    fetchUser
  }
})
```

### 5.2 评估 Store

```typescript
// src/stores/evaluation.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { EvaluationSession, EvalResult, EvalItem } from '@/types/evaluation'
import * as evalApi from '@/api/evaluation'

export const useEvaluationStore = defineStore('evaluation', () => {
  const currentSession = ref<EvaluationSession | null>(null)
  const results = ref<EvalResult[]>([])
  const currentResult = ref<EvalResult | null>(null)

  const createSession = async (projectId: number, supplierIds: number[]) => {
    const response = await evalApi.createSession({ project_id: projectId, supplier_ids: supplierIds })
    currentSession.value = response.data
    return response.data
  }

  const startEvaluation = async (sessionId: number) => {
    await evalApi.startEvaluation(sessionId)
    if (currentSession.value) {
      currentSession.value.status = 'in_progress'
    }
  }

  const fetchResults = async (sessionId: number) => {
    const response = await evalApi.getResults(sessionId)
    results.value = response.data
  }

  const fetchResultDetail = async (sessionId: number, resultId: number) => {
    const response = await evalApi.getResultDetail(sessionId, resultId)
    currentResult.value = response.data
  }

  const submitReview = async (sessionId: number, itemIds: number[], action: string, comment?: string) => {
    await evalApi.submitReview(sessionId, { item_ids: itemIds, action, comment })
  }

  return {
    currentSession,
    results,
    currentResult,
    createSession,
    startEvaluation,
    fetchResults,
    fetchResultDetail,
    submitReview
  }
})
```

---

## 六、API 集成

### 6.1 Axios 配置

```typescript
// src/api/index.ts
import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const instance: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
instance.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
instance.interceptors.response.use(
  (response) => {
    if (response.data.success === false) {
      ElMessage.error(response.data.error?.message || '请求失败')
      return Promise.reject(response.data.error)
    }
    return response.data
  },
  (error) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      window.location.href = '/login'
    } else {
      const message = error.response?.data?.error?.message || error.message || '网络错误'
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default instance
```

### 6.2 评估 API

```typescript
// src/api/evaluation.ts
import api from './index'
import type { EvaluationSession, EvalResult, EvalItem } from '@/types/evaluation'

export const createSession = (data: { project_id: number; supplier_ids: number[] }) =>
  api.post<{ data: EvaluationSession }>('/evaluations', data)

export const getSession = (id: number) =>
  api.get<{ data: EvaluationSession }>(`/evaluations/${id}`)

export const startEvaluation = (id: number) =>
  api.post(`/evaluations/${id}/start`)

export const getResults = (sessionId: number) =>
  api.get<{ data: EvalResult[] }>(`/evaluations/${sessionId}/results`)

export const getResultDetail = (sessionId: number, resultId: number) =>
  api.get<{ data: EvalResult & { items: EvalItem[] } }>(`/evaluations/${sessionId}/results/${resultId}`)

export const submitReview = (sessionId: number, data: { item_ids: number[]; action: string; comment?: string }) =>
  api.post(`/evaluations/${sessionId}/review`, data)

export const getReport = (sessionId: number) =>
  api.get<{ data: any }>(`/evaluations/${sessionId}/report`)
```

---

## 七、样式规范

### 7.1 主题变量

```scss
// src/assets/styles/variables.scss

// 主色调
$primary-color: #409eff;
$success-color: #67c23a;
$warning-color: #e6a23c;
$danger-color: #f56c6c;
$info-color: #909399;

// 文字颜色
$text-primary: #303133;
$text-regular: #606266;
$text-secondary: #909399;
$text-placeholder: #c0c4cc;

// 边框
$border-color: #dcdfe6;
$border-radius: 4px;

// 间距
$spacing-xs: 4px;
$spacing-sm: 8px;
$spacing-md: 16px;
$spacing-lg: 24px;
$spacing-xl: 32px;

// 布局
$sidebar-width: 220px;
$header-height: 60px;
$content-max-width: 1400px;
```

### 7.2 全局样式

```scss
// src/assets/styles/global.scss

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}

// 页面容器
.page-container {
  padding: $spacing-lg;
  max-width: $content-max-width;
  margin: 0 auto;
}

// 卡片间距
.card-grid {
  display: grid;
  gap: $spacing-md;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
}

// 表格样式
.el-table {
  .el-table__header {
    background-color: #f5f7fa;
  }
}

// 高亮文字
.highlight {
  background-color: rgba($warning-color, 0.2);
  padding: 2px 4px;
  border-radius: 2px;
}

// 审核标记
.review-required {
  border-left: 3px solid $warning-color;
}

.review-approved {
  border-left: 3px solid $success-color;
}

.review-rejected {
  border-left: 3px solid $danger-color;
}
```

---

## 八、构建配置

### 8.1 Vite 配置

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
```

### 8.2 Package.json

```json
{
  "name": "bid-evaluation-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext .vue,.ts,.tsx",
    "format": "prettier --write src/**/*.{vue,ts,tsx,scss}"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "element-plus": "^2.5.0",
    "axios": "^1.6.0",
    "pdfjs-dist": "^4.0.0",
    "@element-plus/icons-vue": "^2.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "typescript": "^5.3.0",
    "vue-tsc": "^1.8.0",
    "sass": "^1.69.0",
    "@types/node": "^20.10.0",
    "eslint": "^8.55.0",
    "prettier": "^3.1.0"
  }
}
```

---

*文档版本：v1.0*
*创建日期：2026-02-21*
*参考来源：Vue 3 官方文档、Element Plus 设计规范*
