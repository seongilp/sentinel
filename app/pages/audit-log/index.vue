<script setup lang="ts">
import {
  ScrollText, RefreshCw, CheckCircle2, XCircle, Info,
  ChevronDown, X, Search, Filter
} from 'lucide-vue-next'

interface AuditLog {
  id: number
  user_id: string
  menu: string | null
  action: string
  entity_type: string | null
  entity_id: number | null
  result: string
  details: string | null
  created_at: string
}

const logs = ref<AuditLog[]>([])
const loading = ref(false)

const { userAuditEvents, initLockedEvents } = useUsers()
onMounted(() => initLockedEvents())

// Filters
const filterMenu = ref<string | null>(null)
const filterResult = ref<string | null>(null)
const filterAction = ref('')
const showFilterMenu = ref(false)
const showFilterResult = ref(false)

const menuOptions = [
  { value: 'connections', label: 'Connections' },
  { value: 'scans',       label: 'Scans' },
  { value: 'rules',       label: 'Rules' },
  { value: 'settings',    label: 'Settings' },
  { value: 'users',       label: 'Users' },
]

const resultOptions = [
  { value: 'success', label: '성공', color: '#16a34a' },
  { value: 'failure', label: '실패', color: '#dc2626' },
  { value: 'info',    label: '정보', color: '#2563eb' },
]

// Per-action human descriptions
const actionMeta: Record<string, { label: string; desc: (d: Record<string,unknown>, entityId: number|null) => string }> = {
  'connection.created':  { label: '커넥션 생성', desc: (d) => `"${d.name}" (${d.db_type}) 커넥션이 생성되었습니다.` },
  'connection.updated':  { label: '커넥션 수정', desc: (d) => `"${d.name}" (${d.db_type}) 커넥션이 수정되었습니다.` },
  'connection.deleted':  { label: '커넥션 삭제', desc: (d) => `"${d.name}" (${d.db_type}) 커넥션이 삭제되었습니다.` },
  'scan.created':        { label: '스캔 시작',   desc: (d, id) => d.scheduled ? `스캔 #${id}이 스케줄로 등록되었습니다.` : d.rerun_of ? `스캔 #${d.rerun_of}을 재실행했습니다. (새 스캔 #${id})` : `스캔 #${id}이 실행 요청되었습니다.` },
  'scan.completed':      { label: '스캔 완료',   desc: (d, id) => `스캔 #${id} 완료 — 테이블 ${d.total_tables}개, 컬럼 ${d.total_columns}개, PII ${d.pii_columns_found}개 탐지.` },
  'scan.failed':         { label: '스캔 실패',   desc: (d, id) => `스캔 #${id} 실패: ${d.error || '알 수 없는 오류'}` },
  'scan.scheduled':      { label: '스케줄 설정', desc: (d, id) => d.cron ? `스캔 #${id} 스케줄: ${d.cron}` : `스캔 #${id} 스케줄이 해제되었습니다.` },
  'user.locked':         { label: '계정 잠금',   desc: (d) => `"${d.username}" 계정이 90일 미로그인으로 자동 잠금되었습니다.` },
  'user.unlocked':       { label: '잠금 해제',   desc: (d) => `"${d.username}" 계정 잠금이 "${d.by}"에 의해 해제되었습니다.` },
}

// Convert user audit events to AuditLog shape and merge with API logs
const allLogs = computed<AuditLog[]>(() => {
  const userLogs: AuditLog[] = userAuditEvents.value.map((e, i) => ({
    id: -(i + 1),
    user_id: e.by,
    menu: 'users',
    action: e.action,
    entity_type: 'user',
    entity_id: null,
    result: e.action === 'user.locked' ? 'info' : 'success',
    details: JSON.stringify({ username: e.username, by: e.by }),
    created_at: e.created_at,
  }))
  const menuF = filterMenu.value
  const resultF = filterResult.value
  const actionF = filterAction.value.toLowerCase()
  const combined = [...userLogs, ...logs.value].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
  return combined.filter(l => {
    if (menuF && l.menu !== menuF) return false
    if (resultF && l.result !== resultF) return false
    if (actionF && !l.action.toLowerCase().includes(actionF)) return false
    return true
  })
})

function getActionLabel(action: string) { return actionMeta[action]?.label ?? action }

function getDescription(log: AuditLog) {
  const meta = actionMeta[log.action]
  if (!meta) return log.details ?? ''
  try {
    const d = log.details ? JSON.parse(log.details) : {}
    return meta.desc(d, log.entity_id)
  } catch {
    return log.details ?? ''
  }
}

function parseDetails(details: string | null): Record<string, unknown> {
  if (!details) return {}
  try { return JSON.parse(details) } catch { return {} }
}

// Result chips
function resultStyle(r: string) {
  if (r === 'success') return { color: '#16a34a', bg: '#f0fdf4', icon: 'success' }
  if (r === 'failure') return { color: '#dc2626', bg: '#fef2f2', icon: 'failure' }
  return { color: '#2563eb', bg: '#eff6ff', icon: 'info' }
}

// Menu chip color
const menuColor: Record<string, string> = {
  connections: '#7c3aed', scans: '#2563eb', rules: '#d97706',
  settings: '#6b7280', system: '#9ca3af',
}
function getMenuColor(menu: string | null) { return menuColor[menu ?? 'system'] ?? '#9ca3af' }

// Action category color
const actionColor: Record<string, string> = {
  'connection.created': '#16a34a', 'connection.updated': '#d97706', 'connection.deleted': '#dc2626',
  'scan.created': '#2563eb', 'scan.completed': '#16a34a', 'scan.failed': '#dc2626',
  'scan.scheduled': '#7c3aed',
  'user.locked': '#be123c', 'user.unlocked': '#0891b2',
}
function getActionColor(action: string) { return actionColor[action] || 'var(--muted-foreground)' }

function formatDate(d: string) {
  const dt = new Date(d)
  return dt.toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' })
    + ' ' + dt.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatDateFull(d: string) { return new Date(d).toLocaleString('ko-KR') }

// Expanded detail rows
const expandedId = ref<number | null>(null)
function toggleDetail(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

async function load() {
  loading.value = true
  const params = new URLSearchParams()
  if (filterMenu.value)   params.set('menu',   filterMenu.value)
  if (filterResult.value) params.set('result', filterResult.value)
  if (filterAction.value) params.set('action', filterAction.value)
  const qs = params.toString()
  logs.value = await $fetch<AuditLog[]>(`/api/audit-log${qs ? '?' + qs : ''}`).catch(() => [])
  loading.value = false
}

function setMenu(v: string | null) {
  filterMenu.value = v; showFilterMenu.value = false; load()
}
function setResult(v: string | null) {
  filterResult.value = v; showFilterResult.value = false; load()
}
function clearFilters() {
  filterMenu.value = null; filterResult.value = null; filterAction.value = ''; load()
}

const hasFilter = computed(() => filterMenu.value || filterResult.value || filterAction.value)

onMounted(load)
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <div class="px-8 pt-8 pb-5 flex items-start justify-between flex-shrink-0">
      <div>
        <h1 class="font-display text-2xl font-bold tracking-tight" style="color: var(--foreground);">Audit Log</h1>
        <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">모든 사용자 활동과 시스템 이벤트를 기록합니다.</p>
      </div>
      <button @click="load" class="icon-btn">
        <RefreshCw class="w-4 h-4" :class="loading ? 'animate-spin' : ''" />
      </button>
    </div>

    <!-- Filter bar -->
    <div class="px-8 pb-4 flex items-center gap-2 flex-shrink-0 flex-wrap">
      <!-- Search by action keyword -->
      <div class="search-box">
        <Search class="w-3.5 h-3.5 flex-shrink-0" style="color: var(--muted-foreground);" />
        <input
          v-model="filterAction"
          @input="load"
          placeholder="액션 검색..."
          class="bg-transparent outline-none text-[12px] w-36"
          style="color: var(--foreground);" />
      </div>

      <!-- Menu filter -->
      <div class="relative">
        <button @click="showFilterMenu = !showFilterMenu" class="filter-btn" :class="filterMenu ? 'filter-btn-active' : ''">
          <Filter class="w-3 h-3" />
          {{ filterMenu ? menuOptions.find(m => m.value === filterMenu)?.label : '메뉴' }}
          <ChevronDown class="w-3 h-3" />
        </button>
        <div v-if="showFilterMenu" class="dropdown-panel absolute left-0 top-full mt-1 z-20 w-44">
          <button @click="setMenu(null)" class="dropdown-item" :class="!filterMenu ? 'dropdown-item-active' : ''">전체</button>
          <div class="dropdown-divider" />
          <button v-for="opt in menuOptions" :key="opt.value"
            @click="setMenu(opt.value)"
            class="dropdown-item" :class="filterMenu === opt.value ? 'dropdown-item-active' : ''">
            {{ opt.label }}
          </button>
        </div>
      </div>

      <!-- Result filter -->
      <div class="relative">
        <button @click="showFilterResult = !showFilterResult" class="filter-btn" :class="filterResult ? 'filter-btn-active' : ''">
          <Filter class="w-3 h-3" />
          {{ filterResult ? resultOptions.find(r => r.value === filterResult)?.label : '결과' }}
          <ChevronDown class="w-3 h-3" />
        </button>
        <div v-if="showFilterResult" class="dropdown-panel absolute left-0 top-full mt-1 z-20 w-36">
          <button @click="setResult(null)" class="dropdown-item" :class="!filterResult ? 'dropdown-item-active' : ''">전체</button>
          <div class="dropdown-divider" />
          <button v-for="opt in resultOptions" :key="opt.value"
            @click="setResult(opt.value)"
            class="dropdown-item" :class="filterResult === opt.value ? 'dropdown-item-active' : ''">
            <span class="w-2 h-2 rounded-full mr-2 flex-shrink-0" :style="{ background: opt.color }" />
            {{ opt.label }}
          </button>
        </div>
      </div>

      <!-- Active filter chips -->
      <div v-if="hasFilter" class="flex items-center gap-1.5">
        <span v-if="filterMenu" class="filter-chip">
          {{ menuOptions.find(m => m.value === filterMenu)?.label }}
          <button @click="setMenu(null)"><X class="w-3 h-3" /></button>
        </span>
        <span v-if="filterResult" class="filter-chip">
          {{ resultOptions.find(r => r.value === filterResult)?.label }}
          <button @click="setResult(null)"><X class="w-3 h-3" /></button>
        </span>
        <button @click="clearFilters" class="text-[11px] font-medium underline" style="color: var(--muted-foreground);">초기화</button>
      </div>

      <div class="ml-auto text-[11px]" style="color: var(--muted-foreground);">{{ allLogs.length }}건</div>
    </div>

    <!-- Log list -->
    <div class="flex-1 overflow-auto px-8 pb-8">
      <div v-if="loading" class="space-y-1.5">
        <div v-for="i in 8" :key="i" class="h-14 rounded-xl animate-pulse" style="background: var(--border);" />
      </div>

      <div v-else-if="allLogs.length === 0" class="section-card flex flex-col items-center py-20 text-center">
        <ScrollText class="w-10 h-10 mb-3" style="color: var(--border);" />
        <p class="text-[13px]" style="color: var(--muted-foreground);">활동 이력이 없습니다.</p>
      </div>

      <!-- Table -->
      <div v-else class="section-card overflow-hidden !p-0">
        <!-- Column headers -->
        <div class="grid log-grid px-4 py-2.5 border-b" style="background: var(--background); border-color: var(--border);">
          <span class="col-header">시간</span>
          <span class="col-header">사용자</span>
          <span class="col-header">메뉴</span>
          <span class="col-header">행위</span>
          <span class="col-header">내용</span>
          <span class="col-header">결과</span>
        </div>

        <template v-for="(log, i) in allLogs" :key="log.id + '-' + i">
          <!-- Main row -->
          <div
            class="log-row grid log-grid px-4 py-3 cursor-pointer"
            :style="i > 0 ? 'border-top: 1px solid var(--border);' : ''"
            @click="toggleDetail(log.id)">

            <!-- Time -->
            <div class="flex flex-col gap-0.5">
              <span class="text-[12px] font-mono font-medium tabular-nums" style="color: var(--foreground);">
                {{ formatDate(log.created_at) }}
              </span>
            </div>

            <!-- User -->
            <div class="flex items-center">
              <span class="user-chip">{{ log.user_id }}</span>
            </div>

            <!-- Menu -->
            <div class="flex items-center">
              <span v-if="log.menu" class="menu-chip"
                :style="{ color: getMenuColor(log.menu), background: getMenuColor(log.menu) + '18' }">
                {{ log.menu }}
              </span>
              <span v-else class="text-[11px]" style="color: var(--muted-foreground);">—</span>
            </div>

            <!-- Action -->
            <div class="flex items-center">
              <span class="action-chip"
                :style="{ color: getActionColor(log.action), background: getActionColor(log.action) + '18' }">
                {{ getActionLabel(log.action) }}
              </span>
            </div>

            <!-- Description -->
            <div class="flex items-center min-w-0">
              <span class="text-[12px] truncate" style="color: var(--foreground);">{{ getDescription(log) }}</span>
            </div>

            <!-- Result -->
            <div class="flex items-center gap-1.5">
              <CheckCircle2 v-if="log.result === 'success'" class="w-4 h-4 flex-shrink-0" style="color: #16a34a;" />
              <XCircle      v-else-if="log.result === 'failure'" class="w-4 h-4 flex-shrink-0" style="color: #dc2626;" />
              <Info         v-else class="w-4 h-4 flex-shrink-0" style="color: #2563eb;" />
              <span class="text-[11px] font-semibold"
                :style="{ color: resultStyle(log.result).color }">
                {{ log.result }}
              </span>
            </div>
          </div>

          <!-- Expanded detail row -->
          <div v-if="expandedId === log.id"
            class="px-4 py-3 border-t"
            style="background: var(--background); border-color: var(--border);">
            <div class="flex flex-wrap gap-6 text-[12px]">
              <div>
                <span class="detail-label">ID</span>
                <span class="font-mono" style="color: var(--foreground);">#{{ log.id }}</span>
              </div>
              <div>
                <span class="detail-label">시각</span>
                <span class="font-mono" style="color: var(--foreground);">{{ formatDateFull(log.created_at) }}</span>
              </div>
              <div v-if="log.entity_type && log.entity_id">
                <span class="detail-label">대상</span>
                <span class="font-mono" style="color: var(--foreground);">{{ log.entity_type }} #{{ log.entity_id }}</span>
              </div>
              <div v-if="log.details">
                <span class="detail-label">상세</span>
                <span class="font-mono" style="color: var(--foreground);">
                  <template v-for="(v, k) in parseDetails(log.details)" :key="k">
                    <span class="mr-3"><span style="color: var(--muted-foreground);">{{ k }}=</span>{{ v }}</span>
                  </template>
                </span>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Grid layout */
.log-grid {
  grid-template-columns: 130px 90px 100px 110px 1fr 80px;
  gap: 12px;
  align-items: center;
}

.col-header {
  font-size: 10px; font-weight: 700; letter-spacing: 0.07em;
  text-transform: uppercase; color: var(--muted-foreground);
}

/* Buttons */
.icon-btn {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: var(--muted-foreground); transition: background 0.12s, color 0.12s;
}
.icon-btn:hover { background: var(--muted); color: var(--foreground); }

/* Search box */
.search-box {
  display: flex; align-items: center; gap: 6px;
  height: 30px; padding: 0 10px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--card);
  transition: border-color 0.12s;
}
.search-box:focus-within { border-color: var(--primary); }

/* Filter button */
.filter-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 30px; padding: 0 10px; border-radius: 8px;
  border: 1px solid var(--border); font-size: 12px; font-weight: 500;
  color: var(--foreground); background: var(--card);
  transition: border-color 0.12s;
}
.filter-btn:hover { border-color: var(--primary); }
.filter-btn-active { border-color: var(--primary); color: var(--primary); }

/* Filter chip */
.filter-chip {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 20px;
  color: var(--primary); background: color-mix(in oklch, var(--primary) 10%, transparent);
}

/* Dropdown */
.dropdown-panel {
  border-radius: 10px; border: 1px solid var(--border);
  background: var(--card); box-shadow: 0 8px 24px oklch(0.128 0.018 257 / 12%);
  overflow: hidden;
}
.dropdown-item {
  display: flex; align-items: center; width: 100%;
  padding: 7px 12px; font-size: 12px; text-align: left;
  color: var(--foreground); transition: background 0.1s;
}
.dropdown-item:hover { background: color-mix(in oklch, var(--primary) 6%, transparent); }
.dropdown-item-active { background: color-mix(in oklch, var(--primary) 10%, transparent); color: var(--primary); }
.dropdown-divider { height: 1px; background: var(--border); margin: 2px 0; }

/* Section card */
.section-card {
  border-radius: 12px; border: 1px solid var(--border);
  background: var(--card);
  box-shadow: 0 1px 3px oklch(0.128 0.018 257 / 4%);
}

/* Log row */
.log-row { transition: background 0.1s; }
.log-row:hover { background: color-mix(in oklch, var(--primary) 3%, transparent); }

/* Chips */
.user-chip {
  display: inline-block; font-size: 11px; font-weight: 600; font-family: var(--font-mono);
  padding: 2px 8px; border-radius: 20px;
  color: var(--muted-foreground); background: var(--border);
}
.menu-chip {
  display: inline-block; font-size: 11px; font-weight: 700;
  padding: 2px 8px; border-radius: 20px; text-transform: capitalize;
}
.action-chip {
  display: inline-block; font-size: 11px; font-weight: 600;
  padding: 2px 8px; border-radius: 20px;
}

/* Detail row */
.detail-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--muted-foreground); margin-right: 6px;
}
</style>
