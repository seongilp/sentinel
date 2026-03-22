<script setup lang="ts">
import {
  FileSpreadsheet, FileText, RefreshCw, Shield, TrendingUp,
  AlertTriangle, AlertCircle, CheckCircle, Database, ChevronDown, X, Activity
} from 'lucide-vue-next'

interface Connection { id: number; name: string; db_type: string }
interface Scan { id: number; connection_id: number; status: string; created_at: string }
interface PiiItem {
  id: number; scan_id: number; connection_id: number
  schema_name: string; table_name: string; column_name: string
  pii_type: string; confidence: number; sensitivity_level: string; status: string
}

interface TrendPoint { date: string; total: number; high: number; medium: number; low: number }

const connections = ref<Connection[]>([])
const scans = ref<Scan[]>([])
const items = ref<PiiItem[]>([])
type TrendMode = '1h' | '1d' | '7d' | '14d' | '30d'
const TREND_MODES: TrendMode[] = ['1h', '1d', '7d', '14d', '30d']
function trendApiParams(mode: TrendMode) {
  if (mode === '1h') return 'hours=1'
  if (mode === '1d') return 'hours=24'
  return `days=${mode.replace('d', '')}`
}

const trendData = ref<TrendPoint[]>([])
const trendMode = ref<TrendMode>('30d')
const loading = ref(false)
const loadingTrend = ref(false)

const selectedConnId = ref<number | null>(null)
const selectedScanId = ref<number | null>(null)
const showScanDropdown = ref(false)

// Scans filtered by selected connection
const filteredScans = computed(() =>
  selectedConnId.value === null
    ? scans.value
    : scans.value.filter(s => s.connection_id === selectedConnId.value && s.status === 'completed')
)

const selectedConnName = computed(() =>
  connections.value.find(c => c.id === selectedConnId.value)?.name ?? '전체 커넥션'
)

const selectedScanLabel = computed(() => {
  if (selectedScanId.value === null) return '전체 스캔'
  const s = scans.value.find(s => s.id === selectedScanId.value)
  return s ? `Scan #${s.id} (${new Date(s.created_at).toLocaleDateString('ko-KR')})` : `Scan #${selectedScanId.value}`
})

// Summary stats
const piiTypeSummary = computed(() => {
  const counts: Record<string, number> = {}
  for (const i of items.value) counts[i.pii_type] = (counts[i.pii_type] || 0) + 1
  return Object.entries(counts).sort((a, b) => b[1] - a[1])
})

const sensitivitySummary = computed(() => {
  const c = { high: 0, medium: 0, low: 0 }
  for (const i of items.value) {
    if (c[i.sensitivity_level as keyof typeof c] !== undefined)
      c[i.sensitivity_level as keyof typeof c]++
  }
  return c
})

const maxCount = computed(() => piiTypeSummary.value.length > 0 ? piiTypeSummary.value[0][1] : 1)

// Group by table for connection view
const tableGroups = computed(() => {
  const groups: Record<string, { schema: string; table: string; items: PiiItem[]; highCount: number }> = {}
  for (const item of items.value) {
    const key = `${item.schema_name}.${item.table_name}`
    if (!groups[key]) groups[key] = { schema: item.schema_name, table: item.table_name, items: [], highCount: 0 }
    groups[key].items.push(item)
    if (item.sensitivity_level === 'high') groups[key].highCount++
  }
  return Object.values(groups).sort((a, b) => b.highCount - a.highCount || b.items.length - a.items.length)
})

const sensitivityFilter = ref<string | null>(null)

function toggleSensitivityFilter(level: string | null) {
  sensitivityFilter.value = sensitivityFilter.value === level ? null : level
}

const filteredItems = computed(() =>
  sensitivityFilter.value
    ? items.value.filter(i => i.sensitivity_level === sensitivityFilter.value)
    : items.value
)

const filteredTableGroups = computed(() => {
  const groups: Record<string, { schema: string; table: string; items: PiiItem[]; highCount: number }> = {}
  for (const item of filteredItems.value) {
    const key = `${item.schema_name}.${item.table_name}`
    if (!groups[key]) groups[key] = { schema: item.schema_name, table: item.table_name, items: [], highCount: 0 }
    groups[key].items.push(item)
    if (item.sensitivity_level === 'high') groups[key].highCount++
  }
  return Object.values(groups).sort((a, b) => b.highCount - a.highCount || b.items.length - a.items.length)
})

const expandedTables = ref<Set<string>>(new Set())
function toggleTable(key: string) {
  if (expandedTables.value.has(key)) expandedTables.value.delete(key)
  else expandedTables.value.add(key)
}

const piiColor: Record<string, string> = {
  email: '#2563eb', phone: '#16a34a', resident_id: '#dc2626',
  credit_card: '#7c3aed', name: '#d97706', address: '#ea580c',
  password: '#b91c1c', account_number: '#db2777',
  ip_address: '#4f46e5', birth_date: '#0891b2',
  passport: '#0d9488', driver_license: '#64748b', ssn: '#9333ea',
}
function getPiiColor(type: string) { return piiColor[type] || '#6b7280' }

function dbTypeLabel(t: string) {
  return { mysql: 'MySQL', postgresql: 'PostgreSQL', oracle: 'Oracle', mongodb: 'MongoDB', clickhouse: 'ClickHouse' }[t] ?? t
}

async function selectConnection(id: number | null) {
  selectedConnId.value = id
  selectedScanId.value = null
  await Promise.all([loadInventory(), loadTrend()])
}

async function selectScan(id: number | null) {
  selectedScanId.value = id
  showScanDropdown.value = false
  await loadInventory()
}

async function loadInventory() {
  loading.value = true
  const params: Record<string, string> = {}
  if (selectedConnId.value !== null) params.connection_id = String(selectedConnId.value)
  if (selectedScanId.value !== null) params.scan_id = String(selectedScanId.value)
  const qs = new URLSearchParams(params).toString()
  items.value = await $fetch<PiiItem[]>(`/api/reports/pii-inventory${qs ? '?' + qs : ''}`).catch(() => [])
  loading.value = false
}

async function loadTrend() {
  loadingTrend.value = true
  let qs = trendApiParams(trendMode.value)
  if (selectedConnId.value !== null) qs += `&connection_id=${selectedConnId.value}`
  trendData.value = await $fetch<TrendPoint[]>(`/api/reports/daily-trend?${qs}`).catch(() => [])
  loadingTrend.value = false
}

async function setTrendMode(m: TrendMode) {
  trendMode.value = m
  await loadTrend()
}

function exportFile(format: 'csv' | 'xlsx') {
  const params: Record<string, string> = { format }
  if (selectedConnId.value !== null) params.connection_id = String(selectedConnId.value)
  if (selectedScanId.value !== null) params.scan_id = String(selectedScanId.value)
  window.open(`/api/reports/export?${new URLSearchParams(params)}`, '_blank')
}

onMounted(async () => {
  ;[connections.value, scans.value] = await Promise.all([
    $fetch<Connection[]>('/api/connections').catch(() => []),
    $fetch<Scan[]>('/api/scans').catch(() => []),
  ])
  await Promise.all([loadInventory(), loadTrend()])
})
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <div class="px-8 pt-8 pb-5 flex items-start justify-between flex-shrink-0">
      <div>
        <h1 class="font-display text-2xl font-bold tracking-tight" style="color: var(--foreground);">Reports</h1>
        <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">PII 인벤토리와 컴플라이언스 리포트를 확인하고 내보냅니다.</p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="loadInventory" class="icon-btn">
          <RefreshCw class="w-4 h-4" :class="loading ? 'animate-spin' : ''" />
        </button>
        <button @click="exportFile('csv')" class="export-btn">
          <FileText class="w-3.5 h-3.5" /> CSV
        </button>
        <button @click="exportFile('xlsx')" class="export-btn">
          <FileSpreadsheet class="w-3.5 h-3.5" /> Excel
        </button>
      </div>
    </div>

    <div class="flex-1 flex overflow-hidden">
      <!-- Left sidebar: Connection list -->
      <div class="w-56 flex-shrink-0 border-r flex flex-col" style="border-color: var(--border);">
        <div class="px-4 py-3 flex-shrink-0">
          <p class="text-[10px] font-bold tracking-widest uppercase" style="color: var(--muted-foreground);">커넥션</p>
        </div>
        <div class="flex-1 overflow-auto px-2 pb-4 space-y-0.5">
          <!-- All connections -->
          <button
            @click="selectConnection(null)"
            class="conn-item w-full"
            :class="selectedConnId === null ? 'conn-item-active' : ''">
            <div class="flex items-center gap-2 min-w-0">
              <Shield class="w-3.5 h-3.5 flex-shrink-0" />
              <span class="text-[13px] font-medium truncate">전체</span>
            </div>
          </button>

          <button
            v-for="conn in connections"
            :key="conn.id"
            @click="selectConnection(conn.id)"
            class="conn-item w-full"
            :class="selectedConnId === conn.id ? 'conn-item-active' : ''">
            <div class="flex items-center gap-2 min-w-0">
              <Database class="w-3.5 h-3.5 flex-shrink-0" />
              <span class="text-[13px] font-medium truncate">{{ conn.name }}</span>
            </div>
            <span class="db-type-chip flex-shrink-0">{{ dbTypeLabel(conn.db_type) }}</span>
          </button>
        </div>
      </div>

      <!-- Main content -->
      <div class="flex-1 overflow-auto px-6 py-5 space-y-5">

        <!-- Filter bar: scan selector -->
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <span class="text-[13px] font-semibold" style="color: var(--foreground);">{{ selectedConnName }}</span>
            <span v-if="selectedScanId" class="filter-chip">
              {{ selectedScanLabel }}
              <button @click="selectScan(null)" class="ml-1 hover:opacity-70"><X class="w-3 h-3" /></button>
            </span>
          </div>

          <!-- Scan selector (only when connection selected) -->
          <div v-if="selectedConnId !== null" class="relative">
            <button @click="showScanDropdown = !showScanDropdown" class="scan-select-btn">
              <span class="text-[12px]">{{ selectedScanLabel }}</span>
              <ChevronDown class="w-3.5 h-3.5" />
            </button>
            <div v-if="showScanDropdown"
              class="dropdown-panel absolute right-0 top-full mt-1 z-20 w-64">
              <button @click="selectScan(null)" class="dropdown-item" :class="selectedScanId === null ? 'dropdown-item-active' : ''">
                전체 스캔
              </button>
              <template v-if="filteredScans.length > 0">
                <div class="dropdown-divider" />
                <button
                  v-for="s in filteredScans" :key="s.id"
                  @click="selectScan(s.id)"
                  class="dropdown-item"
                  :class="selectedScanId === s.id ? 'dropdown-item-active' : ''">
                  <span class="font-mono text-[11px]">#{{ s.id }}</span>
                  <span class="ml-auto text-[11px]" style="color: var(--muted-foreground);">
                    {{ new Date(s.created_at).toLocaleDateString('ko-KR') }}
                  </span>
                </button>
              </template>
              <div v-else class="px-3 py-2 text-[12px]" style="color: var(--muted-foreground);">완료된 스캔 없음</div>
            </div>
          </div>
        </div>

        <!-- Summary cards -->
        <div class="grid grid-cols-4 gap-3">
          <div class="stat-card" :class="sensitivityFilter === null ? 'stat-card-active' : ''"
            style="cursor: pointer;" @click="sensitivityFilter = null">
            <div class="stat-label"><TrendingUp class="w-3 h-3" /> TOTAL PII</div>
            <div class="stat-value" style="color: var(--primary);">{{ items.length }}</div>
            <div class="stat-sub">탐지된 전체 컬럼</div>
          </div>
          <div class="stat-card" style="border-color: #fecaca; background: #fef2f2; cursor: pointer;"
            :class="sensitivityFilter === 'high' ? 'stat-card-active-high' : ''"
            @click="toggleSensitivityFilter('high')">
            <div class="stat-label" style="color: #ef4444;"><AlertCircle class="w-3 h-3" /> HIGH RISK</div>
            <div class="stat-value" style="color: #dc2626;">{{ sensitivitySummary.high }}</div>
            <div class="stat-sub" style="color: #ef4444;">즉시 조치 필요</div>
          </div>
          <div class="stat-card" style="border-color: #fed7aa; background: #fff7ed; cursor: pointer;"
            :class="sensitivityFilter === 'medium' ? 'stat-card-active-medium' : ''"
            @click="toggleSensitivityFilter('medium')">
            <div class="stat-label" style="color: #f97316;"><AlertTriangle class="w-3 h-3" /> MEDIUM RISK</div>
            <div class="stat-value" style="color: #ea580c;">{{ sensitivitySummary.medium }}</div>
            <div class="stat-sub" style="color: #f97316;">검토 권장</div>
          </div>
          <div class="stat-card" style="border-color: #bbf7d0; background: #f0fdf4; cursor: pointer;"
            :class="sensitivityFilter === 'low' ? 'stat-card-active-low' : ''"
            @click="toggleSensitivityFilter('low')">
            <div class="stat-label" style="color: #22c55e;"><CheckCircle class="w-3 h-3" /> LOW RISK</div>
            <div class="stat-value" style="color: #16a34a;">{{ sensitivitySummary.low }}</div>
            <div class="stat-sub" style="color: #22c55e;">낮은 민감도</div>
          </div>
        </div>

        <!-- Active filter chip -->
        <div v-if="sensitivityFilter" class="flex items-center gap-2">
          <span class="text-[12px]" style="color: var(--muted-foreground);">필터:</span>
          <span class="filter-chip">
            {{ sensitivityFilter.toUpperCase() }} RISK
            <button @click="sensitivityFilter = null" class="ml-1 hover:opacity-70"><X class="w-3 h-3" /></button>
          </span>
          <span class="text-[12px]" style="color: var(--muted-foreground);">{{ filteredItems.length }}개 항목</span>
        </div>

        <!-- PII Type Distribution -->
        <div v-if="piiTypeSummary.length > 0" class="section-card">
          <h3 class="section-title mb-4">PII TYPE DISTRIBUTION</h3>
          <div class="space-y-2.5">
            <div v-for="[type, count] in piiTypeSummary" :key="type" class="flex items-center gap-3">
              <div class="w-28 flex items-center gap-1.5 flex-shrink-0">
                <div class="w-2 h-2 rounded-full flex-shrink-0" :style="{ background: getPiiColor(type) }" />
                <span class="text-[12px] font-medium truncate" style="color: var(--foreground);">{{ type }}</span>
              </div>
              <div class="flex-1 h-1.5 rounded-full overflow-hidden" style="background: var(--border);">
                <div class="h-full rounded-full transition-all duration-700"
                  :style="{ width: `${(count / maxCount * 100).toFixed(1)}%`, background: getPiiColor(type) }" />
              </div>
              <span class="count-chip w-10 text-right flex-shrink-0"
                :style="{ color: getPiiColor(type), background: getPiiColor(type) + '18' }">
                {{ count }}
              </span>
            </div>
          </div>
        </div>

        <!-- Daily Trend Chart -->
        <div class="section-card">
          <div class="flex items-center justify-between mb-4">
            <h3 class="section-title flex items-center gap-2">
              <Activity class="w-3.5 h-3.5" /> DAILY TREND
            </h3>
            <div class="flex items-center gap-1">
              <button
                v-for="m in TREND_MODES" :key="m"
                @click="setTrendMode(m)"
                class="trend-day-btn"
                :class="trendMode === m ? 'trend-day-btn-active' : ''">
                {{ m }}
              </button>
            </div>
          </div>
          <div v-if="loadingTrend" class="h-[200px] rounded-lg animate-pulse" style="background: var(--border);" />
          <ReportsTrendChart v-else :data="trendData" />
        </div>

        <!-- Loading skeleton -->
        <div v-if="loading" class="space-y-2">
          <div v-for="i in 5" :key="i" class="h-11 rounded-xl animate-pulse" style="background: var(--border);" />
        </div>

        <!-- Empty state -->
        <div v-else-if="items.length === 0" class="section-card flex flex-col items-center py-16 text-center">
          <Shield class="w-10 h-10 mb-3" style="color: var(--border);" />
          <p class="text-[13px]" style="color: var(--muted-foreground);">PII 탐지 결과가 없습니다. 먼저 스캔을 실행하세요.</p>
        </div>

        <!-- Table-grouped inventory -->
        <div v-else class="space-y-2">
          <div
            v-for="group in filteredTableGroups"
            :key="`${group.schema}.${group.table}`"
            class="section-card !p-0 overflow-hidden">
            <!-- Table header row -->
            <button
              class="w-full flex items-center gap-3 px-4 py-3 text-left group"
              style="border-bottom: 1px solid var(--border);"
              @click="toggleTable(`${group.schema}.${group.table}`)">
              <span class="font-mono text-[12px]" style="color: var(--muted-foreground);">{{ group.schema }}.</span>
              <span class="font-mono text-[13px] font-semibold" style="color: var(--foreground);">{{ group.table }}</span>
              <div class="flex items-center gap-1.5 ml-auto flex-shrink-0">
                <span v-if="group.highCount > 0"
                  class="risk-chip high">
                  <AlertCircle class="w-3 h-3" /> HIGH ×{{ group.highCount }}
                </span>
                <span class="risk-chip neutral">{{ group.items.length }} 컬럼</span>
                <ChevronDown
                  class="w-4 h-4 transition-transform duration-200"
                  style="color: var(--muted-foreground);"
                  :style="expandedTables.has(`${group.schema}.${group.table}`) ? 'transform: rotate(180deg)' : ''" />
              </div>
            </button>

            <!-- Expanded rows -->
            <div v-if="expandedTables.has(`${group.schema}.${group.table}`)">
              <div
                v-for="(item, i) in group.items" :key="item.id"
                class="flex items-center gap-4 px-4 py-2.5 table-row-hover"
                :style="i > 0 ? 'border-top: 1px solid var(--border);' : ''">
                <!-- Column name -->
                <span class="w-40 font-mono text-[12px] font-semibold flex-shrink-0" style="color: var(--foreground);">
                  {{ item.column_name }}
                </span>
                <!-- PII badge -->
                <span class="w-32 flex-shrink-0">
                  <span class="pii-badge"
                    :style="{ color: getPiiColor(item.pii_type), background: getPiiColor(item.pii_type) + '18' }">
                    {{ item.pii_type }}
                  </span>
                </span>
                <!-- Confidence bar -->
                <div class="w-32 flex items-center gap-2 flex-shrink-0">
                  <div class="flex-1 h-1.5 rounded-full overflow-hidden" style="background: var(--border);">
                    <div class="h-full rounded-full"
                      :style="{
                        width: `${(item.confidence * 100).toFixed(0)}%`,
                        background: item.confidence >= 0.9 ? '#16a34a' : item.confidence >= 0.6 ? '#d97706' : '#9ca3af'
                      }" />
                  </div>
                  <span class="text-[11px] font-mono font-semibold w-8 text-right flex-shrink-0"
                    :style="{ color: item.confidence >= 0.9 ? '#16a34a' : item.confidence >= 0.6 ? '#d97706' : 'var(--muted-foreground)' }">
                    {{ (item.confidence * 100).toFixed(0) }}%
                  </span>
                </div>
                <!-- Sensitivity -->
                <span class="sensitivity-badge"
                  :class="{
                    'badge-high':   item.sensitivity_level === 'high',
                    'badge-medium': item.sensitivity_level === 'medium',
                    'badge-low':    item.sensitivity_level === 'low',
                  }">{{ item.sensitivity_level }}</span>
                <!-- Status -->
                <span class="status-badge ml-auto"
                  :class="{
                    'status-pending':   item.status === 'pending',
                    'status-confirmed': item.status === 'confirmed',
                    'status-dismissed': item.status === 'dismissed',
                  }">{{ item.status }}</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
/* Sidebar */
.conn-item {
  display: flex; align-items: center; justify-content: space-between;
  gap: 6px; padding: 7px 10px; border-radius: 8px;
  text-align: left; transition: background 0.1s;
  color: var(--foreground);
}
.conn-item:hover { background: color-mix(in oklch, var(--primary) 6%, transparent); }
.conn-item-active { background: color-mix(in oklch, var(--primary) 10%, transparent) !important; }
.conn-item-active span { color: var(--primary) !important; }

.db-type-chip {
  font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 10px;
  color: var(--muted-foreground); background: var(--border);
}

/* Filter bar */
.filter-chip {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 20px;
  color: var(--primary); background: color-mix(in oklch, var(--primary) 10%, transparent);
}
.scan-select-btn {
  display: flex; align-items: center; gap: 6px;
  height: 30px; padding: 0 10px; border-radius: 8px;
  border: 1px solid var(--border); color: var(--foreground);
  background: var(--card); transition: border-color 0.12s;
}
.scan-select-btn:hover { border-color: var(--primary); }

/* Dropdown */
.dropdown-panel {
  border-radius: 10px; border: 1px solid var(--border);
  background: var(--card); box-shadow: 0 8px 24px oklch(0.128 0.018 257 / 12%);
  overflow: hidden; max-height: 280px; overflow-y: auto;
}
.dropdown-item {
  display: flex; align-items: center; width: 100%;
  padding: 8px 12px; font-size: 13px; text-align: left;
  color: var(--foreground); transition: background 0.1s;
}
.dropdown-item:hover { background: color-mix(in oklch, var(--primary) 6%, transparent); }
.dropdown-item-active { background: color-mix(in oklch, var(--primary) 10%, transparent); color: var(--primary); }
.dropdown-divider { height: 1px; background: var(--border); margin: 2px 0; }

/* Buttons */
.icon-btn {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: var(--muted-foreground); transition: background 0.12s, color 0.12s;
}
.icon-btn:hover { background: var(--muted); color: var(--foreground); }
.export-btn {
  display: flex; align-items: center; gap: 6px;
  height: 32px; padding: 0 12px; border-radius: 8px;
  border: 1px solid var(--border); font-size: 12px; font-weight: 600;
  color: var(--foreground); background: var(--card);
  transition: border-color 0.12s, background 0.12s;
}
.export-btn:hover {
  border-color: var(--primary);
  background: color-mix(in oklch, var(--primary) 5%, transparent);
}

/* Stat cards */
.stat-card {
  border-radius: 12px; border: 1px solid var(--border);
  background: var(--card); padding: 14px 18px;
  box-shadow: 0 1px 3px oklch(0.128 0.018 257 / 4%);
}
.stat-label {
  display: flex; align-items: center; gap: 5px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase;
  color: var(--muted-foreground); margin-bottom: 6px;
}
.stat-value {
  font-family: var(--font-display); font-size: 26px; font-weight: 800;
  letter-spacing: -0.03em; line-height: 1; margin-bottom: 3px;
}
.stat-sub { font-size: 11px; color: var(--muted-foreground); }

/* Section card */
.section-card {
  border-radius: 12px; border: 1px solid var(--border);
  background: var(--card); padding: 18px;
  box-shadow: 0 1px 3px oklch(0.128 0.018 257 / 4%);
}
.section-title {
  font-size: 11px; font-weight: 700; letter-spacing: 0.07em;
  text-transform: uppercase; color: var(--muted-foreground);
}
.count-chip {
  display: inline-block;
  font-size: 11px; font-weight: 700; font-family: var(--font-mono);
  padding: 1px 7px; border-radius: 20px;
}

/* Table groups */
.table-row-hover { transition: background 0.1s; }
.table-row-hover:hover { background: color-mix(in oklch, var(--primary) 3%, transparent); }

.risk-chip {
  display: inline-flex; align-items: center; gap: 3px;
  font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 20px;
}
.risk-chip.high { color: #dc2626; background: #fef2f2; }
.risk-chip.neutral { color: var(--muted-foreground); background: var(--border); }

/* Badges */
.pii-badge {
  display: inline-block; font-size: 11px; font-weight: 600;
  font-family: var(--font-mono); padding: 2px 8px; border-radius: 20px;
}
.sensitivity-badge {
  display: inline-block; font-size: 11px; font-weight: 700;
  padding: 2px 9px; border-radius: 20px; text-transform: capitalize;
}
.badge-high   { color: #dc2626; background: #fef2f2; }
.badge-medium { color: #ea580c; background: #fff7ed; }
.badge-low    { color: #16a34a; background: #f0fdf4; }
.status-badge {
  display: inline-block; font-size: 11px; font-weight: 600;
  padding: 2px 9px; border-radius: 20px; text-transform: capitalize;
}
.status-pending   { color: #2563eb; background: #eff6ff; }
.status-confirmed { color: #16a34a; background: #f0fdf4; }
.status-dismissed { color: #6b7280; background: #f3f4f6; }

/* Stat card filter active states */
.stat-card { transition: box-shadow 0.12s, transform 0.12s; }
.stat-card:hover { box-shadow: 0 2px 8px oklch(0.128 0.018 257 / 8%); transform: translateY(-1px); }
.stat-card-active { box-shadow: 0 0 0 2px var(--primary); }
.stat-card-active-high { box-shadow: 0 0 0 2px #ef4444; }
.stat-card-active-medium { box-shadow: 0 0 0 2px #f97316; }
.stat-card-active-low { box-shadow: 0 0 0 2px #22c55e; }

/* Trend */
.trend-day-btn {
  height: 26px; padding: 0 10px; border-radius: 6px;
  font-size: 11px; font-weight: 600; font-family: var(--font-mono);
  color: var(--muted-foreground); transition: background 0.1s, color 0.1s;
}
.trend-day-btn:hover { background: var(--muted); color: var(--foreground); }
.trend-day-btn-active {
  background: color-mix(in oklch, var(--primary) 10%, transparent);
  color: var(--primary);
}
</style>
