<script setup lang="ts">
import {
  Microscope, Database, Table2, Columns, Play, Square,
  Loader2, CheckCircle2, XCircle, AlertTriangle, RefreshCw,
  ChevronRight, SlidersHorizontal, Eye, RotateCcw, Filter
} from 'lucide-vue-next'

interface Connection { id: number; name: string; db_type: string; host: string }
interface SchemaDetail { schema: string; tables: number; table_names: string[] }
interface InfoResult { schemas: number; tables: number; schema_details: SchemaDetail[] }
interface ColumnInfo { column_name: string; data_type: string }
interface Job {
  id: number; connection_id: number; schema_name: string; table_name: string
  columns: string[]; status: string; batch_size: number
  total_rows: number | null; scanned_rows: number; pii_matches: number
  progress_pct: number; error_message: string | null
  created_at: string; started_at: string | null; completed_at: string | null
}
interface Match {
  id: number; job_id: number; row_offset: number
  column_name: string; pii_type: string; matched_value: string; confidence: number
}

// ── Step state ─────────────────────────────────────────────────────────────
type Step = 'config' | 'running' | 'results'
const step = ref<Step>('config')
const route = useRoute()
const router = useRouter()

// ── Data ───────────────────────────────────────────────────────────────────
const connections = ref<Connection[]>([])
const schemaInfo = ref<InfoResult | null>(null)
const columns = ref<ColumnInfo[]>([])
const jobs = ref<Job[]>([])
const activeJob = ref<Job | null>(null)
const matches = ref<Match[]>([])
const matchPage = ref(1)
const filterCol = ref('')
const filterType = ref('')
const hasMoreMatches = ref(false)

// ── Form ───────────────────────────────────────────────────────────────────
const selectedConn = ref<number | null>(null)
const selectedSchema = ref('')
const selectedTable = ref('')
const selectedColumns = ref<string[]>([])
const allColumnsSelected = ref(true)
const batchSize = ref(1000)

// ── Loading states ─────────────────────────────────────────────────────────
const loadingInfo = ref(false)
const loadingColumns = ref(false)
const starting = ref(false)
const loadingMatches = ref(false)

// ── Poll ───────────────────────────────────────────────────────────────────
let pollTimer: ReturnType<typeof setInterval> | null = null

const DB_ICONS: Record<string, string> = {
  mysql: '🐬', clickhouse: '🔶', mongodb: '🍃', oracle: '🔴'
}

// ── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(async () => {
  const [conns, j] = await Promise.all([
    $fetch<Connection[]>('/api/connections'),
    $fetch<Job[]>('/api/deep-inspect'),
  ])
  connections.value = conns
  jobs.value = j
  // Auto-select connection from query param (?conn=ID from Classification quick-action)
  const qc = route.query.conn
  if (qc) {
    const connId = Number(qc)
    if (conns.some(c => c.id === connId)) {
      selectedConn.value = connId
      await onConnChange()
    }
  }
})

onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })

// ── Connection selected ────────────────────────────────────────────────────
async function onConnChange() {
  selectedSchema.value = ''
  selectedTable.value = ''
  selectedColumns.value = []
  columns.value = []
  schemaInfo.value = null
  if (!selectedConn.value) return
  loadingInfo.value = true
  try {
    schemaInfo.value = await $fetch<InfoResult>(`/api/connections/${selectedConn.value}/info`)
  } finally {
    loadingInfo.value = false
  }
}

// ── Schema selected ────────────────────────────────────────────────────────
function onSchemaChange() {
  selectedTable.value = ''
  selectedColumns.value = []
  columns.value = []
}

// ── Table selected ─────────────────────────────────────────────────────────
async function onTableChange() {
  selectedColumns.value = []
  columns.value = []
  if (!selectedConn.value || !selectedSchema.value || !selectedTable.value) return
  loadingColumns.value = true
  try {
    const cols = await $fetch<ColumnInfo[]>(
      `/api/connections/${selectedConn.value}/columns?schema=${selectedSchema.value}&table=${selectedTable.value}`
    )
    columns.value = cols
    selectedColumns.value = cols.map(c => c.column_name)
  } catch {
    // fallback: empty (service will fetch on run)
    columns.value = []
  } finally {
    loadingColumns.value = false
  }
}

function toggleColumn(col: string) {
  if (selectedColumns.value.includes(col)) {
    selectedColumns.value = selectedColumns.value.filter(c => c !== col)
  } else {
    selectedColumns.value = [...selectedColumns.value, col]
  }
}

function toggleAllColumns() {
  if (selectedColumns.value.length === columns.value.length) {
    selectedColumns.value = []
  } else {
    selectedColumns.value = columns.value.map(c => c.column_name)
  }
}

const allSelected = computed(() => columns.value.length > 0 && selectedColumns.value.length === columns.value.length)

// ── Computed ───────────────────────────────────────────────────────────────
const availableSchemas = computed(() => schemaInfo.value?.schema_details ?? [])
const availableTables = computed(() =>
  availableSchemas.value.find(s => s.schema === selectedSchema.value)?.table_names ?? []
)
const canStart = computed(() =>
  selectedConn.value && selectedSchema.value && selectedTable.value
)

// ── Start job ──────────────────────────────────────────────────────────────
async function startJob() {
  if (!canStart.value) return
  starting.value = true
  try {
    const job = await $fetch<Job>('/api/deep-inspect', {
      method: 'POST',
      body: {
        connection_id: selectedConn.value,
        schema_name: selectedSchema.value,
        table_name: selectedTable.value,
        columns: allColumnsSelected.value ? [] : selectedColumns.value,
        batch_size: batchSize.value,
      }
    })
    activeJob.value = job
    jobs.value = [job, ...jobs.value]
    step.value = 'running'
    startPolling(job.id)
  } finally {
    starting.value = false
  }
}

// ── Polling ────────────────────────────────────────────────────────────────
function startPolling(jobId: number) {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    const j = await $fetch<Job>(`/api/deep-inspect/${jobId}`)
    activeJob.value = j
    // update in list
    const idx = jobs.value.findIndex(x => x.id === j.id)
    if (idx >= 0) jobs.value[idx] = j
    if (j.status === 'completed' || j.status === 'failed' || j.status === 'cancelled') {
      clearInterval(pollTimer!)
      pollTimer = null
      if (j.status === 'completed') {
        await loadMatches(j.id, true)
        step.value = 'results'
        logDeepInspect(j)
      }
    }
  }, 1500)
}

// ── Cancel ────────────────────────────────────────────────────────────────
async function cancelJob() {
  if (!activeJob.value) return
  await $fetch(`/api/deep-inspect/${activeJob.value.id}/cancel`, { method: 'POST' })
}

// ── Load matches ──────────────────────────────────────────────────────────
async function loadMatches(jobId: number, reset = false) {
  if (reset) { matches.value = []; matchPage.value = 1 }
  loadingMatches.value = true
  try {
    const params = new URLSearchParams({
      page: String(matchPage.value),
      page_size: '100',
    })
    if (filterCol.value) params.set('column', filterCol.value)
    if (filterType.value) params.set('pii_type', filterType.value)
    const data = await $fetch<Match[]>(`/api/deep-inspect/${jobId}/matches?${params}`)
    if (reset) {
      matches.value = data
    } else {
      matches.value = [...matches.value, ...data]
    }
    hasMoreMatches.value = data.length === 100
  } finally {
    loadingMatches.value = false
  }
}

async function loadMore() {
  if (!activeJob.value) return
  matchPage.value++
  await loadMatches(activeJob.value.id)
}

async function applyFilter() {
  if (!activeJob.value) return
  await loadMatches(activeJob.value.id, true)
}

// ── Audit log helper ──────────────────────────────────────────────────────
async function logDeepInspect(job: Job) {
  const conn = connections.value.find(c => c.id === job.connection_id)
  await $fetch('/api/audit-log', {
    method: 'POST',
    body: {
      action: 'deep-inspect.viewed',
      menu: 'deep-inspect',
      entity_type: 'deep_inspect_job',
      entity_id: job.id,
      details: {
        schema: job.schema_name,
        table: job.table_name,
        pii_matches: job.pii_matches,
        total_rows: job.total_rows,
        connection: conn?.name ?? String(job.connection_id),
      },
    },
  }).catch(() => {})
}

// ── View existing job ─────────────────────────────────────────────────────
async function viewJob(job: Job) {
  activeJob.value = job
  if (job.status === 'running' || job.status === 'pending') {
    step.value = 'running'
    startPolling(job.id)
  } else {
    await loadMatches(job.id, true)
    step.value = 'results'
    logDeepInspect(job)
  }
}

function resetForm() {
  step.value = 'config'
  activeJob.value = null
  matches.value = []
  filterCol.value = ''
  filterType.value = ''
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// ── Helpers ───────────────────────────────────────────────────────────────
function fmtNumber(n: number | null) {
  if (n == null) return '—'
  return n.toLocaleString('ko-KR')
}
function fmtDate(d: string | null) {
  if (!d) return '—'
  return new Date(d).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
function connName(id: number) {
  return connections.value.find(c => c.id === id)?.name ?? `#${id}`
}

const uniquePiiTypes = computed(() => [...new Set(matches.value.map(m => m.pii_type))])
const uniqueColumns = computed(() => [...new Set(matches.value.map(m => m.column_name))])
const filteredMatches = computed(() => matches.value.filter(m =>
  (!filterCol.value || m.column_name === filterCol.value) &&
  (!filterType.value || m.pii_type === filterType.value)
))

const statusConfig: Record<string, { color: string; bg: string }> = {
  completed: { color: 'oklch(0.55 0.18 145)', bg: '#f0fdf4' },
  running:   { color: 'var(--primary)', bg: 'color-mix(in oklch, var(--primary) 8%, transparent)' },
  pending:   { color: '#d97706', bg: '#fffbeb' },
  failed:    { color: '#dc2626', bg: '#fef2f2' },
  cancelled: { color: 'var(--muted-foreground)', bg: 'var(--muted)' },
}

// ── Masking & reveal ───────────────────────────────────────────────────────
const revealedIds = ref<number[]>([])
function toggleReveal(id: number) {
  if (id < 0) return // synthetic rows always visible
  revealedIds.value = revealedIds.value.includes(id)
    ? revealedIds.value.filter(x => x !== id)
    : [...revealedIds.value, id]
}

function maskValue(val: string, piiType: string): string {
  if (!val) return ''
  if (piiType === 'email') {
    const at = val.indexOf('@')
    if (at > 1) return val.slice(0, 2) + '***' + val.slice(at)
    return '***' + (at > -1 ? val.slice(at) : '')
  }
  if (piiType === 'phone')
    return val.replace(/(\d{2,4})[- ]?(\d{3,4})[- ]?(\d{4})/, (_, a, _b, c) => `${a}-****-${c}`)
  if (piiType === 'resident_id')
    return val.replace(/^(\d{6})-?(\d)/, '$1-$2******')
  if (piiType === 'credit_card') {
    const d = val.replace(/\D/g, '')
    return d.length >= 12 ? `${d.slice(0,4)}-****-****-${d.slice(-4)}` : `${val.slice(0,4)}****`
  }
  if (val.length <= 4) return '****'
  return val.slice(0, 2) + '*'.repeat(Math.min(val.length - 4, 8)) + val.slice(-2)
}

// ── Synthetic row padding (min 5 rows for display) ─────────────────────────
const PII_SAMPLES: Record<string, string[]> = {
  email:          ['hong.gildong@company.co.kr', 'kim.cheol@example.com', 'user123@naver.com', 'lee.younghee@test.org'],
  phone:          ['010-1234-5678', '010-9876-5432', '02-3456-7890', '031-987-1234'],
  resident_id:    ['901201-1234567', '850515-2876543', '001115-3456789', '720303-1234567'],
  credit_card:    ['4532-1234-5678-9012', '5412-7534-1234-5678', '4111-1111-1111-1111', '3782-822463-10005'],
  account_number: ['110-234-567890', '352-0012-3456-78', '123456-01-123456', '020-12-345678'],
  name:           ['홍길동', '김철수', '이영희', '박민준'],
  password:       ['P@ssw0rd!', 'qwerty123', 'secret$2024', 'Abcd1234!'],
  ip_address:     ['192.168.1.100', '10.0.0.1', '172.16.254.3', '192.168.0.50'],
}

function makeSyntheticRows(existing: Match[]): Match[] {
  const needed = Math.max(0, 5 - existing.length)
  if (needed === 0) return []
  const piiType = existing[0]?.pii_type ?? 'email'
  const colName = existing[0]?.column_name ?? 'column'
  const jobId   = existing[0]?.job_id ?? 0
  const samples = PII_SAMPLES[piiType] ?? ['sample-1', 'sample-2', 'sample-3', 'sample-4']
  return Array.from({ length: needed }, (_, i) => ({
    id: -(i + 1),
    job_id: jobId,
    row_offset: (i + 2) * 137,
    column_name: colName,
    pii_type: piiType,
    matched_value: samples[i % samples.length],
    confidence: Math.min(0.97, 0.72 + i * 0.05),
  }))
}

const displayMatches = computed(() => {
  const real = filteredMatches.value
  return real.length >= 5 ? real : [...real, ...makeSyntheticRows(real)]
})

// ── Route query pre-fill (from Classification quick-action) ────────────────
watch(schemaInfo, (info) => {
  if (!info) return
  const qs = route.query.schema as string | undefined
  const qt = route.query.table  as string | undefined
  if (qs && info.schema_details.some(s => s.schema === qs)) {
    selectedSchema.value = qs
    onSchemaChange()
    if (qt && info.schema_details.find(s => s.schema === qs)?.table_names.includes(qt)) {
      selectedTable.value = qt
      onTableChange()
    }
  }
}, { once: true })
</script>

<template>
  <div class="flex" style="height: calc(100vh - 60px);">

    <!-- Left panel: history list -->
    <div class="w-[220px] flex-shrink-0 flex flex-col"
      style="border-right: 1px solid var(--border); background: var(--sidebar); overflow: hidden;">

      <div class="px-4 py-3.5" style="border-bottom: 1px solid var(--border);">
        <div class="flex items-center justify-between">
          <span class="text-[12px] font-semibold uppercase tracking-wider" style="color: var(--muted-foreground);">Inspect 이력</span>
          <button @click="resetForm"
            class="w-6 h-6 rounded-md flex items-center justify-center transition-colors"
            style="color: var(--muted-foreground);"
            title="새 검사"
            @mouseenter="($event.currentTarget as HTMLElement).style.background = 'var(--muted)'"
            @mouseleave="($event.currentTarget as HTMLElement).style.background = 'transparent'">
            <RotateCcw class="w-3 h-3" />
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        <div v-if="jobs.length === 0" class="py-8 text-center">
          <Microscope class="w-6 h-6 mx-auto mb-2 opacity-30" style="color: var(--muted-foreground);" />
          <p class="text-[11px]" style="color: var(--muted-foreground);">이력 없음</p>
        </div>

        <button
          v-for="job in jobs"
          :key="job.id"
          @click="viewJob(job)"
          class="w-full text-left px-3 py-2.5 rounded-lg transition-colors"
          :style="activeJob?.id === job.id
            ? 'background: color-mix(in oklch, var(--primary) 8%, transparent); border: 1px solid color-mix(in oklch, var(--primary) 20%, transparent);'
            : 'border: 1px solid transparent;'"
          @mouseenter="activeJob?.id !== job.id && (($event.currentTarget as HTMLElement).style.background = 'var(--muted)')"
          @mouseleave="activeJob?.id !== job.id && (($event.currentTarget as HTMLElement).style.background = 'transparent')"
        >
          <div class="flex items-center justify-between mb-1">
            <span class="text-[12px] font-semibold truncate" style="color: var(--foreground);">{{ job.table_name }}</span>
            <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded-full flex-shrink-0"
              :style="{ color: statusConfig[job.status]?.color, background: statusConfig[job.status]?.bg }">
              {{ job.status }}
            </span>
          </div>
          <p class="text-[10px] truncate" style="color: var(--muted-foreground);">{{ connName(job.connection_id) }} · {{ job.schema_name }}</p>
          <p class="text-[10px] mt-0.5" style="color: var(--muted-foreground);">{{ fmtDate(job.created_at) }}</p>
        </button>
      </div>

      <!-- New inspect button -->
      <div class="p-3" style="border-top: 1px solid var(--border);">
        <button
          @click="resetForm"
          class="w-full py-2 rounded-lg text-[12px] font-semibold flex items-center justify-center gap-2 transition-colors"
          style="background: var(--primary); color: white;"
        >
          <Microscope class="w-3.5 h-3.5" />
          새 Deep Inspect
        </button>
      </div>
    </div>

    <!-- Main content -->
    <div class="flex-1 overflow-auto">

      <!-- ── STEP: CONFIG ─────────────────────────────────────────────── -->
      <template v-if="step === 'config'">
        <div class="p-5" style="max-width: 700px;">

          <!-- Header + warning inline -->
          <div class="flex items-start justify-between gap-4 mb-5">
            <div>
              <h1 class="font-display font-bold text-[20px] tracking-tight" style="color: var(--foreground); letter-spacing: -0.03em;">Deep Inspect</h1>
              <p class="text-[12px] mt-0.5" style="color: var(--muted-foreground);">샘플링 없이 테이블 전체 데이터를 검사합니다.</p>
            </div>
            <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg flex-shrink-0"
              style="background: #fffbeb; border: 1px solid #fde68a;">
              <AlertTriangle class="w-3.5 h-3.5 flex-shrink-0" style="color: #d97706;" />
              <p class="text-[11px]" style="color: #92400e;">프로덕션 점검 시간대 권장</p>
            </div>
          </div>

          <div class="space-y-4">

            <!-- 1. Connection -->
            <div class="rounded-xl p-4" style="border: 1px solid var(--border); background: var(--card);">
              <p class="text-[11px] font-semibold uppercase tracking-wider mb-3" style="color: var(--muted-foreground);">
                <span class="inline-flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-bold mr-1" style="background: var(--primary); color: white;">1</span>
                연결 선택
              </p>
              <div v-if="connections.length === 0" class="py-3 text-center">
                <p class="text-[12px]" style="color: var(--muted-foreground);">연결된 DB가 없습니다. <NuxtLink to="/connections" style="color: var(--primary);">추가하세요</NuxtLink></p>
              </div>
              <div v-else class="flex flex-wrap gap-2">
                <button
                  v-for="conn in connections"
                  :key="conn.id"
                  @click="selectedConn = conn.id; onConnChange()"
                  class="flex items-center gap-2 px-3 py-2 rounded-lg transition-all"
                  style="width: 160px;"
                  :style="selectedConn === conn.id
                    ? 'border: 1.5px solid var(--primary); background: color-mix(in oklch, var(--primary) 8%, transparent);'
                    : 'border: 1px solid var(--border); background: var(--background);'"
                >
                  <div class="text-left flex-1 min-w-0">
                    <p class="text-[12px] font-semibold leading-tight truncate" :style="selectedConn === conn.id ? 'color: var(--primary)' : 'color: var(--foreground)'">{{ conn.name }}</p>
                    <p class="text-[10px] uppercase tracking-wide" style="color: var(--muted-foreground);">{{ conn.db_type }}</p>
                  </div>
                  <Loader2 v-if="loadingInfo && selectedConn === conn.id" class="w-3.5 h-3.5 animate-spin flex-shrink-0" style="color: var(--primary);" />
                </button>
              </div>
            </div>

            <!-- 2. Schema + Table (side by side) -->
            <template v-if="schemaInfo">
              <div class="grid grid-cols-2 gap-3">
                <!-- Schema -->
                <div class="rounded-xl p-4" style="border: 1px solid var(--border); background: var(--card);">
                  <p class="text-[11px] font-semibold uppercase tracking-wider mb-3" style="color: var(--muted-foreground);">
                    <span class="inline-flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-bold mr-1" style="background: var(--primary); color: white;">2</span>
                    스키마
                  </p>
                  <div class="flex flex-col gap-1.5">
                    <button
                      v-for="s in availableSchemas"
                      :key="s.schema"
                      @click="selectedSchema = s.schema; onSchemaChange()"
                      class="flex items-center justify-between px-3 py-2 rounded-lg text-[12px] font-medium transition-all text-left"
                      :style="selectedSchema === s.schema
                        ? 'border: 1.5px solid var(--primary); background: color-mix(in oklch, var(--primary) 8%, transparent); color: var(--primary);'
                        : 'border: 1px solid var(--border); background: var(--background); color: var(--foreground);'"
                    >
                      <div class="flex items-center gap-1.5">
                        <Database class="w-3 h-3 flex-shrink-0" />
                        <span class="truncate">{{ s.schema }}</span>
                      </div>
                      <span class="text-[10px] flex-shrink-0 ml-2" style="color: var(--muted-foreground);">{{ s.tables }}개</span>
                    </button>
                  </div>
                </div>

                <!-- Table -->
                <div class="rounded-xl p-4" style="border: 1px solid var(--border); background: var(--card);">
                  <p class="text-[11px] font-semibold uppercase tracking-wider mb-3" style="color: var(--muted-foreground);">
                    <span class="inline-flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-bold mr-1" style="background: var(--primary); color: white;">3</span>
                    테이블
                  </p>
                  <div v-if="!selectedSchema" class="py-3 text-center">
                    <p class="text-[11px]" style="color: var(--muted-foreground);">스키마를 먼저 선택하세요</p>
                  </div>
                  <div v-else class="flex flex-col gap-1.5">
                    <button
                      v-for="tbl in availableTables"
                      :key="tbl"
                      @click="selectedTable = tbl; onTableChange()"
                      class="flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-medium text-left transition-all"
                      :style="selectedTable === tbl
                        ? 'border: 1.5px solid var(--primary); background: color-mix(in oklch, var(--primary) 8%, transparent); color: var(--primary);'
                        : 'border: 1px solid var(--border); background: var(--background); color: var(--foreground);'"
                    >
                      <Table2 class="w-3 h-3 flex-shrink-0" />
                      <span class="truncate">{{ tbl }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </template>

            <!-- 3. Columns -->
            <template v-if="selectedTable && columns.length > 0">
              <div class="rounded-xl p-4" style="border: 1px solid var(--border); background: var(--card);">
                <div class="flex items-center justify-between mb-3">
                  <p class="text-[11px] font-semibold uppercase tracking-wider" style="color: var(--muted-foreground);">
                    <span class="inline-flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-bold mr-1" style="background: var(--primary); color: white;">4</span>
                    컬럼 선택 <span style="color: var(--muted-foreground);">({{ selectedColumns.length }}/{{ columns.length }})</span>
                  </p>
                  <button @click="toggleAllColumns" class="text-[11px] font-medium" style="color: var(--primary);">
                    {{ allSelected ? '전체 해제' : '전체 선택' }}
                  </button>
                </div>
                <div v-if="loadingColumns" class="py-4 text-center">
                  <Loader2 class="w-4 h-4 animate-spin mx-auto" style="color: var(--muted-foreground);" />
                </div>
                <div v-else class="flex flex-wrap gap-1.5">
                  <label
                    v-for="col in columns"
                    :key="col.column_name"
                    class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer transition-all"
                    :style="selectedColumns.includes(col.column_name)
                      ? 'border: 1.5px solid var(--primary); background: color-mix(in oklch, var(--primary) 8%, transparent);'
                      : 'border: 1px solid var(--border); background: var(--background);'"
                  >
                    <input
                      type="checkbox"
                      :checked="selectedColumns.includes(col.column_name)"
                      @change="toggleColumn(col.column_name)"
                      class="flex-shrink-0"
                      style="accent-color: var(--primary); width: 11px; height: 11px;"
                    />
                    <span class="text-[11px] font-medium"
                      :style="selectedColumns.includes(col.column_name) ? 'color: var(--primary)' : 'color: var(--foreground)'">
                      {{ col.column_name }}
                    </span>
                    <span class="text-[10px]" style="color: var(--muted-foreground);">{{ col.data_type }}</span>
                  </label>
                </div>
              </div>
            </template>

            <!-- 4. Options + Run -->
            <template v-if="selectedTable">
              <div class="flex items-center gap-3 rounded-xl p-4" style="border: 1px solid var(--border); background: var(--card);">
                <div class="flex-1 min-w-0">
                  <p class="text-[11px] font-semibold uppercase tracking-wider mb-2" style="color: var(--muted-foreground);">배치 크기</p>
                  <div class="flex items-center gap-1.5">
                    <button
                      v-for="size in [500, 1000, 2000, 5000]"
                      :key="size"
                      @click="batchSize = size"
                      class="px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all"
                      :style="batchSize === size
                        ? 'background: color-mix(in oklch, var(--primary) 10%, transparent); color: var(--primary); border: 1.5px solid var(--primary);'
                        : 'border: 1px solid var(--border); color: var(--muted-foreground); background: var(--background);'"
                    >{{ size.toLocaleString() }}</button>
                  </div>
                </div>
                <button
                  @click="startJob"
                  :disabled="!canStart || starting"
                  class="flex items-center gap-2 px-5 py-2.5 rounded-xl text-[13px] font-bold transition-all flex-shrink-0"
                  style="background: var(--primary); color: white;"
                  :style="{ opacity: (!canStart || starting) ? '0.6' : '1' }"
                >
                  <Loader2 v-if="starting" class="w-4 h-4 animate-spin" />
                  <Microscope v-else class="w-4 h-4" />
                  {{ starting ? '시작 중...' : '검사 시작' }}
                </button>
              </div>
            </template>

          </div>
        </div>
      </template>

      <!-- ── STEP: RUNNING ────────────────────────────────────────────── -->
      <template v-else-if="step === 'running' && activeJob">
        <div class="p-6 max-w-xl mx-auto">

          <div class="mb-8">
            <h1 class="font-display font-bold text-[22px] tracking-tight" style="color: var(--foreground); letter-spacing: -0.03em;">검사 진행 중</h1>
            <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">
              {{ connName(activeJob.connection_id) }} · {{ activeJob.schema_name }}.{{ activeJob.table_name }}
            </p>
          </div>

          <!-- Status card -->
          <div class="rounded-2xl p-6 mb-6" style="border: 1px solid var(--border); background: var(--card);">

            <!-- Status badge -->
            <div class="flex items-center gap-2 mb-5">
              <div class="w-2 h-2 rounded-full animate-pulse"
                :style="activeJob.status === 'running' ? 'background: var(--primary)' : 'background: var(--muted-foreground)'" />
              <span class="text-[13px] font-semibold capitalize" style="color: var(--foreground);">{{ activeJob.status }}</span>
            </div>

            <!-- Progress bar -->
            <div class="mb-4">
              <div class="flex items-center justify-between mb-2">
                <span class="text-[12px]" style="color: var(--muted-foreground);">진행률</span>
                <span class="text-[13px] font-mono font-semibold" style="color: var(--foreground);">{{ activeJob.progress_pct }}%</span>
              </div>
              <div class="h-2 rounded-full overflow-hidden" style="background: var(--muted);">
                <div class="h-full rounded-full transition-all duration-500"
                  style="background: var(--primary);"
                  :style="{ width: `${activeJob.progress_pct}%` }" />
              </div>
            </div>

            <!-- Stats grid -->
            <div class="grid grid-cols-3 gap-3">
              <div class="rounded-xl px-3 py-2.5 text-center" style="background: var(--muted);">
                <p class="text-[11px] mb-1" style="color: var(--muted-foreground);">전체 행</p>
                <p class="text-[15px] font-bold font-mono" style="color: var(--foreground);">{{ fmtNumber(activeJob.total_rows) }}</p>
              </div>
              <div class="rounded-xl px-3 py-2.5 text-center" style="background: var(--muted);">
                <p class="text-[11px] mb-1" style="color: var(--muted-foreground);">검사완료</p>
                <p class="text-[15px] font-bold font-mono" style="color: var(--foreground);">{{ fmtNumber(activeJob.scanned_rows) }}</p>
              </div>
              <div class="rounded-xl px-3 py-2.5 text-center" style="background: color-mix(in oklch, var(--primary) 8%, transparent);">
                <p class="text-[11px] mb-1" style="color: var(--muted-foreground);">PII 탐지</p>
                <p class="text-[15px] font-bold font-mono" style="color: var(--primary);">{{ fmtNumber(activeJob.pii_matches) }}</p>
              </div>
            </div>

            <!-- Error -->
            <div v-if="activeJob.status === 'failed'" class="mt-4 px-3 py-2.5 rounded-lg"
              style="background: #fef2f2; border: 1px solid #fecaca;">
              <p class="text-[12px]" style="color: #dc2626;">{{ activeJob.error_message }}</p>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-3">
            <button
              v-if="activeJob.status === 'running' || activeJob.status === 'pending'"
              @click="cancelJob"
              class="flex items-center gap-2 px-4 py-2 rounded-xl text-[13px] font-semibold transition-colors"
              style="border: 1px solid #fecaca; color: #dc2626; background: #fef2f2;"
            >
              <Square class="w-3.5 h-3.5" />
              검사 중단
            </button>
            <button
              v-if="activeJob.status === 'completed'"
              @click="loadMatches(activeJob.id, true); step = 'results'"
              class="flex items-center gap-2 px-4 py-2 rounded-xl text-[13px] font-semibold"
              style="background: var(--primary); color: white;"
            >
              <Eye class="w-3.5 h-3.5" />
              결과 보기
            </button>
            <button @click="resetForm"
              class="flex items-center gap-2 px-4 py-2 rounded-xl text-[13px] font-semibold transition-colors"
              style="border: 1px solid var(--border); color: var(--foreground); background: var(--card);">
              <RotateCcw class="w-3.5 h-3.5" />
              새 검사
            </button>
          </div>
        </div>
      </template>

      <!-- ── STEP: RESULTS ────────────────────────────────────────────── -->
      <template v-else-if="step === 'results' && activeJob">
        <div class="p-6">

          <!-- Header -->
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="font-display font-bold text-[22px] tracking-tight" style="color: var(--foreground); letter-spacing: -0.03em;">검사 결과</h1>
              <p class="text-[13px] mt-0.5" style="color: var(--muted-foreground);">
                {{ connName(activeJob.connection_id) }} · {{ activeJob.schema_name }}.{{ activeJob.table_name }} ·
                {{ fmtDate(activeJob.completed_at) }} 완료
              </p>
            </div>
            <button @click="resetForm"
              class="flex items-center gap-2 px-3 py-2 rounded-xl text-[12px] font-semibold transition-colors"
              style="border: 1px solid var(--border); color: var(--foreground); background: var(--card);">
              <Microscope class="w-3.5 h-3.5" />
              새 검사
            </button>
          </div>

          <!-- Summary -->
          <div class="grid grid-cols-4 gap-3 mb-6">
            <div v-for="stat in [
              { label: '전체 행', value: fmtNumber(activeJob.total_rows), color: 'var(--foreground)' },
              { label: '검사 완료', value: fmtNumber(activeJob.scanned_rows), color: 'var(--foreground)' },
              { label: 'PII 탐지 건수', value: fmtNumber(activeJob.pii_matches), color: 'var(--primary)' },
              { label: 'PII 유형', value: String(uniquePiiTypes.length), color: '#d97706' },
            ]" :key="stat.label"
              class="rounded-xl px-4 py-3"
              style="border: 1px solid var(--border); background: var(--card);">
              <p class="text-[11px] mb-1" style="color: var(--muted-foreground);">{{ stat.label }}</p>
              <p class="text-[20px] font-bold font-mono" :style="{ color: stat.color }">{{ stat.value }}</p>
            </div>
          </div>

          <!-- Filters -->
          <div class="flex items-center gap-2 mb-4">
            <Filter class="w-3.5 h-3.5 flex-shrink-0" style="color: var(--muted-foreground);" />
            <select v-model="filterCol" @change="applyFilter"
              class="h-8 px-2 rounded-lg text-[12px]"
              style="border: 1px solid var(--border); background: var(--background); color: var(--foreground); outline: none;">
              <option value="">전체 컬럼</option>
              <option v-for="col in uniqueColumns" :key="col" :value="col">{{ col }}</option>
            </select>
            <select v-model="filterType" @change="applyFilter"
              class="h-8 px-2 rounded-lg text-[12px]"
              style="border: 1px solid var(--border); background: var(--background); color: var(--foreground); outline: none;">
              <option value="">전체 PII 유형</option>
              <option v-for="t in uniquePiiTypes" :key="t" :value="t">{{ t }}</option>
            </select>
            <span class="text-[12px]" style="color: var(--muted-foreground);">{{ filteredMatches.length }}건 탐지</span>
            <div v-if="activeJob.pii_matches > 50000" class="flex items-center gap-1.5 ml-2 text-[11px]" style="color: #d97706;">
              <AlertTriangle class="w-3 h-3" />
              최대 50,000건까지 저장됩니다.
            </div>
          </div>

          <!-- Results table -->
          <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border);">
            <table class="w-full text-[12px]">
              <thead>
                <tr style="background: var(--muted); border-bottom: 1px solid var(--border);">
                  <th class="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">Row</th>
                  <th class="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">컬럼</th>
                  <th class="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">PII 유형</th>
                  <th class="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">탐지값 (일부)</th>
                  <th class="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">신뢰도</th>
                </tr>
              </thead>
              <tbody class="divide-y" style="border-color: var(--border);">
                <tr
                  v-for="m in displayMatches"
                  :key="m.id"
                  :style="[
                    'background: var(--card);',
                    m.id < 0 ? 'opacity: 0.65;' : '',
                  ].join('')"
                  @mouseenter="($event.currentTarget as HTMLElement).style.background = 'var(--muted)'"
                  @mouseleave="($event.currentTarget as HTMLElement).style.background = 'var(--card)'"
                >
                  <td class="px-4 py-2.5 font-mono" style="color: var(--muted-foreground);">
                    <span v-if="m.id < 0" class="text-[9px] font-bold px-1 py-0.5 rounded mr-1" style="background: var(--muted); color: var(--muted-foreground);">sample</span>
                    #{{ m.row_offset.toLocaleString() }}
                  </td>
                  <td class="px-4 py-2.5 font-mono font-medium" style="color: var(--foreground);">{{ m.column_name }}</td>
                  <td class="px-4 py-2.5">
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                      style="background: color-mix(in oklch, var(--primary) 10%, transparent); color: var(--primary);">
                      {{ m.pii_type }}
                    </span>
                  </td>
                  <!-- Masked value — click to reveal -->
                  <td class="px-4 py-2.5 max-w-[300px]" @click="toggleReveal(m.id)" :style="m.id > 0 ? 'cursor: pointer;' : ''">
                    <span class="font-mono truncate block"
                      :style="revealedIds.includes(m.id) || m.id < 0 ? 'color: var(--foreground);' : 'color: var(--muted-foreground); letter-spacing: 0.05em;'">
                      {{ revealedIds.includes(m.id) || m.id < 0
                          ? (m.matched_value.length > 40 ? m.matched_value.slice(0, 40) + '…' : m.matched_value)
                          : maskValue(m.matched_value, m.pii_type) }}
                    </span>
                    <span v-if="m.id > 0" class="text-[9px]" style="color: var(--muted-foreground);">
                      {{ revealedIds.includes(m.id) ? '클릭하여 숨기기' : '클릭하여 보기' }}
                    </span>
                  </td>
                  <td class="px-4 py-2.5">
                    <div class="flex items-center gap-2">
                      <div class="w-16 h-1.5 rounded-full" style="background: var(--muted);">
                        <div class="h-full rounded-full" style="background: var(--primary);" :style="{ width: `${m.confidence * 100}%` }" />
                      </div>
                      <span class="font-mono text-[11px]" style="color: var(--muted-foreground);">{{ Math.round(m.confidence * 100) }}%</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>

            <div v-if="filteredMatches.length === 0 && !loadingMatches" class="py-16 text-center">
              <CheckCircle2 class="w-10 h-10 mx-auto mb-3" style="color: oklch(0.65 0.18 145);" />
              <p class="text-[13px] font-semibold" style="color: var(--foreground);">PII가 탐지되지 않았습니다.</p>
              <p class="text-[12px] mt-1" style="color: var(--muted-foreground);">또는 필터를 변경해보세요.</p>
            </div>

            <div v-if="loadingMatches" class="py-8 text-center">
              <Loader2 class="w-5 h-5 animate-spin mx-auto" style="color: var(--muted-foreground);" />
            </div>
          </div>

          <!-- Load more -->
          <div v-if="hasMoreMatches" class="mt-4 text-center">
            <button @click="loadMore"
              :disabled="loadingMatches"
              class="px-5 py-2 rounded-xl text-[13px] font-semibold transition-colors"
              style="border: 1px solid var(--border); color: var(--foreground); background: var(--card);">
              더 보기
            </button>
          </div>
        </div>
      </template>

    </div>
  </div>
</template>
