<template>
  <div class="nl-screening">
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><ChatDotRound /></el-icon>
        一句话选股
      </h1>
      <p class="page-description">
        用自然语言描述你的选股需求，AI 自动解析并筛选符合条件的股票
      </p>
    </div>

    <el-card class="query-panel" shadow="never">
      <div class="query-input-area">
        <el-input
          v-model="query"
          type="textarea"
          :rows="3"
          placeholder="例如：找出市值在50到200亿之间，市盈率低于30的科技股"
          size="large"
          @keydown.enter.ctrl="handleScreen"
        />
        <div class="query-examples">
          <span class="examples-label">试试这些：</span>
          <el-tag
            v-for="example in examples"
            :key="example"
            class="example-tag"
            type="info"
            @click="query = example"
          >
            {{ example }}
          </el-tag>
        </div>
      </div>

      <div class="query-options">
        <el-checkbox v-model="addToFavorites">添加到自选</el-checkbox>
        <el-checkbox v-model="runAnalysis">自动分析</el-checkbox>
      </div>

      <div class="query-actions">
        <el-button type="info" @click="handleParse" :loading="parseLoading">
          <el-icon><View /></el-icon>
          预览条件
        </el-button>
        <el-button type="primary" @click="handleScreen" :loading="screenLoading" size="large">
          <el-icon><Search /></el-icon>
          开始选股
        </el-button>
      </div>
    </el-card>

    <el-card v-if="parsedConditions" class="parsed-panel" shadow="never">
      <template #header>
        <div class="card-header">
          <span>解析结果：{{ parsedDescription }}</span>
        </div>
      </template>
      <div class="parsed-conditions">
        <div v-for="(cond, idx) in parsedConditions" :key="idx" class="condition-item">
          <el-tag type="warning" size="large">
            {{ cond.field }}
            <span class="operator">{{ cond.operator }}</span>
            {{ formatConditionValue(cond.value) }}
          </el-tag>
        </div>
      </div>
      <div v-if="parsedOrderBy && parsedOrderBy.length > 0" class="parsed-order">
        <span class="order-label">排序：</span>
        <span v-for="(order, idx) in parsedOrderBy" :key="idx">
          {{ order.field }} {{ order.direction === 'asc' ? '升序' : '降序' }}
          <span v-if="idx < parsedOrderBy.length - 1">，</span>
        </span>
      </div>
    </el-card>

    <el-card v-if="screenResults.length > 0" class="results-panel" shadow="never">
      <template #header>
        <div class="card-header">
          <span>筛选结果（{{ screenResults.length }} 只股票）</span>
          <div class="header-actions">
            <el-button
              type="primary"
              @click="batchAnalyze"
              :disabled="selectedStocks.length === 0"
            >
              <el-icon><TrendCharts /></el-icon>
              批量分析（{{ selectedStocks.length }}）
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="paginatedResults"
        @selection-change="handleSelectionChange"
        stripe
        style="width: 100%"
      >
        <el-table-column type="selection" width="55" />

        <el-table-column prop="code" label="股票代码" width="120">
          <template #default="{ row }">
            <el-link type="primary" @click="viewStockDetail(row)">
              {{ row.code }}
            </el-link>
          </template>
        </el-table-column>

        <el-table-column prop="name" label="股票名称" width="150" />

        <el-table-column prop="industry" label="行业" width="120">
          <template #default="{ row }">
            {{ row.industry || '-' }}
          </template>
        </el-table-column>

        <el-table-column prop="close" label="当前价格" width="100" align="right">
          <template #default="{ row }">
            <span v-if="row.close">¥{{ row.close.toFixed(2) }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column prop="pct_chg" label="涨跌幅" width="100" align="right">
          <template #default="{ row }">
            <span
              v-if="row.pct_chg !== null && row.pct_chg !== undefined"
              :class="getChangeClass(row.pct_chg)"
            >
              {{ row.pct_chg > 0 ? '+' : '' }}{{ row.pct_chg.toFixed(2) }}%
            </span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column prop="total_mv" label="市值" width="120" align="right">
          <template #default="{ row }">
            {{ formatMarketCap(row.total_mv) }}
          </template>
        </el-table-column>

        <el-table-column prop="pe" label="市盈率" width="100" align="right">
          <template #default="{ row }">
            <span v-if="row.pe">{{ row.pe.toFixed(2) }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column prop="pb" label="市净率" width="100" align="right">
          <template #default="{ row }">
            <span v-if="row.pb">{{ row.pb.toFixed(2) }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="text" size="small" @click="analyzeSingle(row)">
              分析
            </el-button>
            <el-button type="text" size="small" @click="toggleFavorite(row)">
              <el-icon><Star /></el-icon>
              {{ isFavorited(row.code) ? '取消自选' : '加入自选' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="screenResults.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-empty
      v-else-if="!screenLoading && hasSearched"
      description="未找到符合条件的股票"
      :image-size="200"
    >
      <el-button type="primary" @click="query = ''">
        重新输入
      </el-button>
    </el-empty>

    <el-card v-if="analysisTasks.length > 0" class="analysis-panel" shadow="never">
      <template #header>
        <div class="card-header">
          <span>分析任务已创建</span>
        </div>
      </template>
      <div class="analysis-task-list">
        <div v-for="task in analysisTasks" :key="task.task_id" class="task-item">
          <el-icon><Document /></el-icon>
          <span>{{ task.stock_name || task.stock_code }}</span>
          <el-link type="primary" @click="goToTask(task.task_id)">
            查看任务
          </el-link>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  Search,
  View,
  TrendCharts,
  Star,
  Document
} from '@element-plus/icons-vue'
import {
  naturalLanguageScreeningApi,
  type ScreeningResultItem,
  type ScreeningCondition,
  type ScreeningOrderBy,
  type AnalysisTaskItem
} from '@/api/naturalLanguageScreening'
import { favoritesApi } from '@/api/favorites'
import { normalizeMarketForAnalysis, exchangeCodeToMarket, getMarketByStockCode } from '@/utils/market'

const router = useRouter()

const query = ref('')
const addToFavorites = ref(true)
const runAnalysis = ref(false)

const screenLoading = ref(false)
const parseLoading = ref(false)
const hasSearched = ref(false)

const screenResults = ref<ScreeningResultItem[]>([])
const selectedStocks = ref<ScreeningResultItem[]>([])
const analysisTasks = ref<AnalysisTaskItem[]>([])

const parsedConditions = ref<ScreeningCondition[] | null>(null)
const parsedOrderBy = ref<ScreeningOrderBy[] | null>(null)
const parsedDescription = ref('')

const currentPage = ref(1)
const pageSize = ref(20)

const favoriteSet = ref<Set<string>>(new Set())

const examples = [
  '找出市值在50到200亿之间，市盈率低于30的科技股',
  'ROE大于15%且市盈率低于20的低估值股票',
  '近一周涨幅超过10%的活跃股票',
  '市净率低于2的银行股'
]

const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return screenResults.value.slice(start, end)
})

const formatConditionValue = (value: any): string => {
  if (Array.isArray(value)) {
    return `[${value.join(', ')}]`
  }
  return String(value)
}

const handleParse = async () => {
  if (!query.value.trim()) {
    ElMessage.warning('请输入选股条件')
    return
  }

  parseLoading.value = true
  try {
    const res = await naturalLanguageScreeningApi.parse(query.value.trim())
    const data = (res as any)?.data || res

    parsedConditions.value = data.conditions || []
    parsedOrderBy.value = data.order_by || []
    parsedDescription.value = data.description || query.value

    ElMessage.success('条件解析完成')
  } catch (error: any) {
    ElMessage.error(error?.message || '条件解析失败，请重试')
  } finally {
    parseLoading.value = false
  }
}

const handleScreen = async () => {
  if (!query.value.trim()) {
    ElMessage.warning('请输入选股条件')
    return
  }

  screenLoading.value = true
  hasSearched.value = true
  screenResults.value = []
  analysisTasks.value = []

  try {
    const res = await naturalLanguageScreeningApi.screen({
      query: query.value.trim(),
      add_to_favorites: addToFavorites.value,
      run_analysis: runAnalysis.value
    })
    const data = (res as any)?.data || res

    screenResults.value = data.screened_stocks || []
    analysisTasks.value = data.analysis_tasks || []
    parsedConditions.value = data.conditions || []
    parsedOrderBy.value = data.order_by || []
    parsedDescription.value = data.description || query.value

    currentPage.value = 1

    if (data.added_to_favorites && data.added_to_favorites.length > 0) {
      data.added_to_favorites.forEach((code: string) => favoriteSet.value.add(code))
    }

    if (screenResults.value.length > 0) {
      ElMessage.success(`筛选完成，找到 ${screenResults.value.length} 只股票`)
    } else {
      ElMessage.info('未找到符合条件的股票')
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '筛选失败，请重试')
  } finally {
    screenLoading.value = false
  }
}

const handleSelectionChange = (selection: ScreeningResultItem[]) => {
  selectedStocks.value = selection
}

const batchAnalyze = () => {
  if (selectedStocks.value.length === 0) {
    ElMessage.warning('请先选择要分析的股票')
    return
  }

  router.push({
    name: 'BatchAnalysis',
    query: {
      stocks: selectedStocks.value.map(s => s.code).filter(Boolean).join(','),
      market: 'CN'
    }
  })
}

const analyzeSingle = (stock: ScreeningResultItem) => {
  if (!stock.code) return
  router.push({
    name: 'SingleAnalysis',
    query: {
      stock: stock.code,
      market: normalizeMarketForAnalysis(stock.market || 'A股')
    }
  })
}

const viewStockDetail = (stock: ScreeningResultItem) => {
  if (!stock.code) return
  router.push({
    name: 'StockDetail',
    params: { code: stock.code }
  })
}

const goToTask = (taskId: string) => {
  router.push({
    name: 'TaskCenterHome',
    query: { taskId }
  })
}

const isFavorited = (code: string) => favoriteSet.value.has(code)

const toggleFavorite = async (stock: ScreeningResultItem) => {
  try {
    const code = stock.code
    if (!code) {
      ElMessage.error('股票代码缺失，无法加入自选')
      return
    }
    if (favoriteSet.value.has(code)) {
      const res = await favoritesApi.remove(code)
      if ((res as any)?.success === false) throw new Error((res as any)?.message || '取消失败')
      favoriteSet.value.delete(code)
      ElMessage.success(`已取消自选：${stock.name || code}`)
    } else {
      let marketType = 'A股'
      if (stock.market) {
        marketType = exchangeCodeToMarket(stock.market)
      } else {
        marketType = getMarketByStockCode(code)
      }

      const payload = {
        symbol: code,
        stock_code: code,
        stock_name: stock.name || code,
        market: marketType
      }
      const res = await favoritesApi.add(payload)
      if ((res as any)?.success === false) throw new Error((res as any)?.message || '添加失败')
      favoriteSet.value.add(code)
      ElMessage.success(`已加入自选：${stock.name || code}`)
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '自选操作失败')
  }
}

const getChangeClass = (changePercent: number) => {
  if (changePercent > 0) return 'text-red'
  if (changePercent < 0) return 'text-green'
  return ''
}

const formatMarketCap = (marketCap?: number) => {
  if (!marketCap) return '-'
  if (marketCap >= 10000) {
    return `${(marketCap / 10000).toFixed(2)}万亿`
  }
  return `${marketCap.toFixed(2)}亿`
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
}

const loadFavorites = async () => {
  try {
    const resp = await favoritesApi.list()
    const list = (resp as any)?.data || resp
    const set = new Set<string>()
    ;(list || []).forEach((item: any) => {
      const code = item.symbol || item.stock_code || item.code
      if (code) set.add(code)
    })
    favoriteSet.value = set
  } catch (e) {
    console.warn('加载自选列表失败', e)
  }
}

onMounted(() => {
  loadFavorites()
})
</script>

<style lang="scss" scoped>
.nl-screening {
  .page-header {
    margin-bottom: 24px;

    .page-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 24px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin: 0 0 8px 0;
    }

    .page-description {
      color: var(--el-text-color-regular);
      margin: 0;
    }
  }

  .query-panel {
    margin-bottom: 24px;

    .query-input-area {
      .query-examples {
        margin-top: 12px;
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;

        .examples-label {
          color: var(--el-text-color-secondary);
          font-size: 13px;
        }

        .example-tag {
          cursor: pointer;
          transition: all 0.2s;

          &:hover {
            background-color: var(--el-color-primary-light-9);
            border-color: var(--el-color-primary);
            color: var(--el-color-primary);
          }
        }
      }
    }

    .query-options {
      margin-top: 16px;
      display: flex;
      gap: 24px;
    }

    .query-actions {
      display: flex;
      justify-content: center;
      gap: 16px;
      margin-top: 24px;
    }
  }

  .parsed-panel {
    margin-bottom: 24px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .parsed-conditions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;

      .condition-item {
        .operator {
          margin: 0 4px;
          font-weight: bold;
          color: var(--el-color-danger);
        }
      }
    }

    .parsed-order {
      margin-top: 12px;
      color: var(--el-text-color-secondary);

      .order-label {
        font-weight: 500;
      }
    }
  }

  .results-panel {
    margin-bottom: 24px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .header-actions {
        display: flex;
        gap: 8px;
      }
    }

    .pagination-wrapper {
      display: flex;
      justify-content: center;
      margin-top: 24px;
    }
  }

  .analysis-panel {
    margin-bottom: 24px;

    .analysis-task-list {
      display: flex;
      flex-direction: column;
      gap: 12px;

      .task-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        background: var(--el-fill-color-light);
        border-radius: 6px;
      }
    }
  }

  .text-red {
    color: #f56c6c;
  }

  .text-green {
    color: #67c23a;
  }

  .text-gray {
    color: var(--el-text-color-placeholder);
  }
}
</style>
