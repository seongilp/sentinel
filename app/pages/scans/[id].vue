<script setup lang="ts">
import {
  ArrowLeft, Loader2, Ban, Database, RefreshCw,
  ShieldAlert, Shield, ShieldCheck
} from 'lucide-vue-next'

const route = useRoute()
const scanId = Number(route.params.id)

interface ScanResult {
  id: number; schema_name: string; table_name: string; column_name: string
  data_type: string | null; pii_type: string; confidence: number
  sensitivity_level: string; status: string; detector: string | null; evidence: string | null
}
interface Scan {
  id: number; connection_id: number; status: string; sample_size: number
  confidence_threshold: number; total_tables: number | null; total_columns: number | null
  pii_columns_found: number | null; error_message: string | null
  started_at: string | null; completed_at: string | null; created_at: string
}

const scan = ref<Scan | null>(null)
const results = ref<ScanResult[]>([])
const loading = ref(true)
const polling = ref<ReturnType<typeof setInterval> | null>(null)

const piiColor: Record<string, string> = {
  email: '#2563eb', phone: '#16a34a', resident_id: '#dc2626',
  credit_card: '#7c3aed', name: '#d97706', address: '#ea580c',
  password: '#b91c1c', account_number: '#db2777',
  ip_address: '#4f46e5', birth_date: '#0891b2',
}
function getPiiColor(type: string) { return piiColor[type] || '#6b7280' }

function getConfidenceColor(v: number) {
  if (v >= 0.9) return '#16a34a'
  if (v >= 0.6) return '#d97706'
  return '#9ca3af'
}

function getStatusStyle(status: string) {
  if (status === 'completed') return 'color:#16a34a'
  if (status === 'running')   return 'color:#2563eb'
  if (status === 'failed')    return 'color:#dc2626'
  if (status === 'cancelled') return 'color:#6b7280'
  return 'color:var(--foreground)'
}

const groupedResults = computed(() => {
  const groups: Record<string, ScanResult[]> = {}
  for (const r of results.value) {
    const key = `${r.schema_name}.${r.table_name}`
    if (!groups[key]) groups[key] = []
    groups[key].push(r)
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
})

const expandedGroups = ref<Set<string>>(new Set())
function toggleGroup(key: string) {
  if (expandedGroups.value.has(key)) expandedGroups.value.delete(key)
  else expandedGroups.value.add(key)
}

function formatDuration(start: string | null, end: string | null): string {
  if (!start) return '-'
  const s = new Date(start), e = end ? new Date(end) : new Date()
  const secs = Math.floor((e.getTime() - s.getTime()) / 1000)
  return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m ${secs % 60}s`
}

async function loadData() {
  const [s, r] = await Promise.all([
    $fetch<Scan>(`/api/scans/${scanId}`),
    $fetch<ScanResult[]>(`/api/scans/${scanId}/results`).catch(() => []),
  ])
  scan.value = s
  results.value = r
  if (expandedGroups.value.size === 0) {
    const groups: Record<string, ScanResult[]> = {}
    for (const row of r) {
      const key = `${row.schema_name}.${row.table_name}`
      if (!groups[key]) groups[key] = []
      groups[key].push(row)
    }
    for (const key of Object.keys(groups)) expandedGroups.value.add(key)
  }
}

async function cancelScan() {
  await $fetch(`/api/scans/${scanId}/cancel`, { method: 'POST' })
  await loadData()
}

function startPolling() {
  polling.value = setInterval(async () => {
    await loadData()
    if (scan.value?.status !== 'running' && scan.value?.status !== 'pending') stopPolling()
  }, 2000)
}
function stopPolling() {
  if (polling.value) { clearInterval(polling.value); polling.value = null }
}

onMounted(async () => {
  await loadData()
  loading.value = false
  if (scan.value?.status === 'running' || scan.value?.status === 'pending') startPolling()
})
onUnmounted(stopPolling)
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <div class="px-8 pt-8 pb-6">
      <NuxtLink to="/scans"
        class="inline-flex items-center gap-1.5 text-[12px] mb-4 transition-colors back-link">
        <ArrowLeft class="w-3.5 h-3.5" /> Back to Scans
      </NuxtLink>

      <div v-if="loading" class="h-8 w-48 rounded animate-pulse" style="background: var(--border);" />
      <div v-else-if="scan" class="flex items-start justify-between">
        <div>
          <h1 class="font-display text-2xl font-bold tracking-tight" style="color: var(--foreground);">Scan #{{ scan.id }}</h1>
          <p class="text-[13px] mt-1 font-mono" style="color: var(--muted-foreground);">
            Connection #{{ scan.connection_id }} · {{ new Date(scan.created_at).toLocaleString('ko-KR') }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button v-if="['running','pending'].includes(scan.status)"
            @click="cancelScan"
            class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] cancel-btn">
            <Ban class="w-3.5 h-3.5" /> Cancel
          </button>
          <button @click="loadData" class="icon-btn">
            <RefreshCw class="w-4 h-4" :class="scan.status === 'running' ? 'animate-spin' : ''" />
          </button>
        </div>
      </div>
    </div>

    <!-- Stats bar -->
    <div v-if="scan" class="px-8 mb-6">
      <div class="grid grid-cols-5 gap-3">
        <div v-for="stat in [
          { label: 'STATUS',    value: scan.status.toUpperCase(), isStatus: true },
          { label: 'DURATION',  value: formatDuration(scan.started_at, scan.completed_at), isStatus: false },
          { label: 'TABLES',    value: scan.total_tables ?? '-', isStatus: false },
          { label: 'COLUMNS',   value: scan.total_columns ?? '-', isStatus: false },
          { label: 'PII FOUND', value: scan.pii_columns_found ?? '-', isStatus: false },
        ]" :key="stat.label"
          class="stat-card">
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-value"
            :style="stat.isStatus ? getStatusStyle(scan.status) : (stat.label === 'PII FOUND' && Number(stat.value) > 0 ? 'color:#dc2626' : 'color:var(--foreground)')">
            {{ stat.value }}
          </div>
        </div>
      </div>
    </div>

    <!-- Running indicator -->
    <div v-if="scan?.status === 'running'" class="px-8 mb-4">
      <div class="flex items-center gap-3 p-3 rounded-lg running-banner">
        <Loader2 class="w-4 h-4 animate-spin" style="color: #2563eb;" />
        <span class="text-[13px]" style="color: #2563eb;">스캔이 실행 중입니다. 2초마다 자동으로 갱신됩니다...</span>
      </div>
    </div>

    <!-- Error -->
    <div v-if="scan?.error_message" class="px-8 mb-4">
      <div class="p-3 rounded-lg error-banner text-[13px]">{{ scan.error_message }}</div>
    </div>

    <!-- Results -->
    <div class="flex-1 overflow-auto px-8 pb-8">
      <!-- No results -->
      <div v-if="!loading && results.length === 0 && scan?.status === 'completed'"
        class="flex flex-col items-center py-16 text-center">
        <div class="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4"
          style="background: #f0fdf4; border: 1px solid #bbf7d0;">
          <ShieldCheck class="w-6 h-6" style="color: #16a34a;" />
        </div>
        <h3 class="font-display font-semibold mb-1" style="color: var(--foreground);">PII가 탐지되지 않았습니다</h3>
        <p class="text-[13px]" style="color: var(--muted-foreground);">설정된 임계값({{ scan?.confidence_threshold }}) 이상의 개인정보가 없습니다.</p>
      </div>

      <!-- Grouped results -->
      <div v-else-if="results.length > 0" class="space-y-2">
        <div v-for="[tableKey, cols] in groupedResults" :key="tableKey"
          class="group-card rounded-xl overflow-hidden">

          <!-- Table group header -->
          <button class="w-full flex items-center gap-3 px-5 py-3 group-header text-left"
            @click="toggleGroup(tableKey)">
            <Database class="w-4 h-4 flex-shrink-0" style="color: var(--muted-foreground);" />
            <span class="flex-1 text-[13px] font-mono font-semibold" style="color: var(--foreground);">{{ tableKey }}</span>
            <span class="text-[11px] mr-1" style="color: var(--muted-foreground);">{{ cols.length }} column{{ cols.length > 1 ? 's' : '' }}</span>
            <svg v-if="expandedGroups.has(tableKey)" class="w-4 h-4" style="color: var(--muted-foreground);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m18 15-6-6-6 6"/></svg>
            <svg v-else class="w-4 h-4" style="color: var(--muted-foreground);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
          </button>

          <!-- Column rows -->
          <div v-if="expandedGroups.has(tableKey)">
            <div v-for="(col, i) in cols" :key="col.id"
              class="col-row flex items-center gap-4 px-5 py-3"
              :style="i > 0 ? 'border-top: 1px solid var(--border);' : ''">

              <!-- Column name -->
              <code class="text-[12px] font-mono font-semibold w-36 truncate" style="color: var(--foreground);">{{ col.column_name }}</code>

              <!-- Data type -->
              <span class="text-[11px] w-20 flex-shrink-0" style="color: var(--muted-foreground);">{{ col.data_type || 'unknown' }}</span>

              <!-- PII type badge (fixed width so bar always starts at same position) -->
              <div class="w-32 flex-shrink-0">
                <span class="pii-badge"
                  :style="{ color: getPiiColor(col.pii_type), background: getPiiColor(col.pii_type) + '18' }">
                  {{ col.pii_type }}
                </span>
              </div>

              <!-- Confidence bar + % (fixed width section) -->
              <div class="flex items-center gap-3 flex-shrink-0 w-44">
                <div class="confidence-track flex-1">
                  <div class="confidence-fill"
                    :style="{ width: `${(col.confidence * 100).toFixed(0)}%`, background: getConfidenceColor(col.confidence) }" />
                </div>
                <span class="text-[11px] font-mono font-semibold w-8 text-right"
                  :style="{ color: getConfidenceColor(col.confidence) }">
                  {{ (col.confidence * 100).toFixed(0) }}%
                </span>
              </div>

              <!-- Sensitivity badge -->
              <span class="sensitivity-badge flex-shrink-0"
                :class="{
                  'sens-high':   col.sensitivity_level === 'high',
                  'sens-medium': col.sensitivity_level === 'medium',
                  'sens-low':    col.sensitivity_level === 'low',
                }">
                {{ col.sensitivity_level }}
              </span>

              <!-- Detector -->
              <span class="text-[11px] w-20 text-right flex-shrink-0" style="color: var(--muted-foreground);">{{ col.detector || '-' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.back-link { color: var(--muted-foreground); }
.back-link:hover { color: var(--foreground); }

.icon-btn {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: var(--muted-foreground); transition: background 0.12s, color 0.12s;
}
.icon-btn:hover { background: var(--muted); color: var(--foreground); }

.cancel-btn {
  border: 1px solid #fecaca; color: #dc2626; border-radius: 8px;
  transition: background 0.12s;
}
.cancel-btn:hover { background: #fef2f2; }

.stat-card {
  border-radius: 12px; border: 1px solid var(--border);
  background: var(--card); padding: 14px 18px;
  box-shadow: 0 1px 3px oklch(0.128 0.018 257 / 4%);
}
.stat-label {
  font-size: 10px; font-weight: 700; letter-spacing: 0.07em;
  text-transform: uppercase; color: var(--muted-foreground); margin-bottom: 6px;
  font-family: var(--font-mono);
}
.stat-value {
  font-family: var(--font-display); font-size: 18px; font-weight: 800;
  letter-spacing: -0.02em; line-height: 1;
}

.running-banner {
  border: 1px solid #bfdbfe; background: #eff6ff;
}
.error-banner {
  border: 1px solid #fecaca; background: #fef2f2; color: #dc2626;
}

.group-card {
  border: 1px solid var(--border); background: var(--card);
  box-shadow: 0 1px 3px oklch(0.128 0.018 257 / 4%);
}
.group-header {
  background: var(--background);
  border-bottom: 1px solid var(--border);
  transition: background 0.1s;
}
.group-header:hover {
  background: color-mix(in oklch, var(--primary) 3%, var(--background));
}

.col-row { transition: background 0.1s; }
.col-row:hover { background: color-mix(in oklch, var(--primary) 3%, transparent); }

.pii-badge {
  display: inline-block; font-size: 11px; font-weight: 700;
  font-family: var(--font-mono); padding: 2px 8px; border-radius: 20px;
  white-space: nowrap;
}

.confidence-track {
  height: 6px; border-radius: 99px; overflow: hidden;
  background: var(--border);
}
.confidence-fill { height: 100%; border-radius: 99px; transition: width 0.3s; }

.sensitivity-badge {
  display: inline-block; font-size: 11px; font-weight: 700;
  padding: 2px 9px; border-radius: 20px; text-transform: capitalize;
}
.sens-high   { color: #dc2626; background: #fef2f2; }
.sens-medium { color: #ea580c; background: #fff7ed; }
.sens-low    { color: #16a34a; background: #f0fdf4; }
</style>
