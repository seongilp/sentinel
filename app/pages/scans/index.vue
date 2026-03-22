<script setup lang="ts">
import {
  Plus, ScanSearch, Loader2, CheckCircle2, XCircle,
  Clock, Play, Ban, ChevronRight, X, Database,
  AlertTriangle, Calendar, Layers, RefreshCw, CalendarClock, Repeat2
} from 'lucide-vue-next'

interface Connection { id: number; name: string; db_type: string; host: string }
interface Scan {
  id: number; connection_id: number; status: string
  sample_size: number; confidence_threshold: number
  total_tables: number | null; total_columns: number | null; pii_columns_found: number | null
  error_message: string | null; started_at: string | null; completed_at: string | null
  created_at: string; cron_expression: string | null; is_scheduled: boolean
}

const scans = ref<Scan[]>([])
const connections = ref<Connection[]>([])
const loading = ref(false)
const drawerOpen = ref(false)
const saving = ref(false)
const formError = ref('')
const pollingTimer = ref<ReturnType<typeof setInterval> | null>(null)
const rerunningId = ref<number | null>(null)
const schedulingId = ref<number | null>(null)
const scheduleModalScan = ref<Scan | null>(null)
const scheduleModalCron = ref('')

// ── Form ─────────────────────────────────────────────────────────────────────
const form = ref({
  connection_id: '' as number | '',
  sample_size: 100,
  confidence_threshold: 0.5,
  target_schemas: '',
  scan_type: 'once' as 'once' | 'scheduled',
  cron_expression: '0 9 * * *',
})

// ── Cron presets ──────────────────────────────────────────────────────────────
const cronPresets = [
  { label: 'Hourly',   cron: '0 * * * *',  desc: '매시간 정각' },
  { label: 'Daily',    cron: '0 9 * * *',  desc: '매일 오전 9시' },
  { label: 'Weekly',   cron: '0 9 * * 1',  desc: '매주 월요일 오전 9시' },
  { label: 'Monthly',  cron: '0 9 1 * *',  desc: '매월 1일 오전 9시' },
]

function describeCron(expr: string): string {
  const preset = cronPresets.find(p => p.cron === expr)
  if (preset) return preset.desc
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) return '잘못된 cron 형식'
  const [min, hr, day, , dow] = parts
  if (dow !== '*') return `매주 지정 요일 ${hr}:${min.padStart(2,'0')}`
  if (day !== '*') return `매월 ${day}일 ${hr}:${min.padStart(2,'0')}`
  if (hr !== '*') return `매일 ${hr}:${min.padStart(2,'0')}`
  return `매시간 ${min}분`
}

// ── Status config ─────────────────────────────────────────────────────────────
const statusConfig: Record<string, { label: string; color: string; bg: string; icon: any }> = {
  pending:   { label: 'Pending',   color: 'var(--muted-foreground)', bg: 'var(--muted)',  icon: Clock         },
  running:   { label: 'Running',   color: '#2563eb',                 bg: '#eff6ff',       icon: Loader2       },
  completed: { label: 'Completed', color: '#16a34a',                 bg: '#f0fdf4',       icon: CheckCircle2  },
  failed:    { label: 'Failed',    color: '#dc2626',                 bg: '#fef2f2',       icon: XCircle       },
  cancelled: { label: 'Cancelled', color: '#6b7280',                 bg: '#f3f4f6',       icon: Ban           },
  scheduled: { label: 'Scheduled', color: '#7c3aed',                 bg: '#f5f3ff',       icon: CalendarClock },
}
function getStatus(s: string) { return statusConfig[s] ?? statusConfig.pending }

function formatDuration(start: string | null, end: string | null): string {
  if (!start) return '-'
  const secs = Math.floor((new Date(end ?? '').getTime() - new Date(start).getTime()) / 1000)
  if (isNaN(secs) || secs < 0) return '-'
  return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m ${secs % 60}s`
}
function formatDate(d: string) {
  return new Date(d).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const connNameMap = computed(() => Object.fromEntries(connections.value.map(c => [c.id, c.name])))
function connName(id: number) { return connNameMap.value[id] ?? `Connection #${id}` }

const hasRunning = computed(() => scans.value.some(s => s.status === 'running' || s.status === 'pending'))

// Scheduled scans always pinned to the top
const sortedScans = computed(() => [
  ...scans.value.filter(s => s.is_scheduled),
  ...scans.value.filter(s => !s.is_scheduled),
])

async function loadScans() { scans.value = await $fetch<Scan[]>('/api/scans') }
async function loadConnections() { connections.value = await $fetch<Connection[]>('/api/connections') }

// ── Create scan ───────────────────────────────────────────────────────────────
async function startScan() {
  if (!form.value.connection_id) { formError.value = '연결을 선택하세요.'; return }
  if (form.value.scan_type === 'scheduled' && !form.value.cron_expression.trim()) {
    formError.value = 'Cron 표현식을 입력하세요.'; return
  }
  saving.value = true; formError.value = ''
  try {
    const schemas = form.value.target_schemas
      ? form.value.target_schemas.split(',').map(s => s.trim()).filter(Boolean)
      : null
    await $fetch('/api/scans', {
      method: 'POST',
      body: {
        connection_id: Number(form.value.connection_id),
        sample_size: form.value.sample_size,
        confidence_threshold: form.value.confidence_threshold,
        target_schemas: schemas,
        cron_expression: form.value.scan_type === 'scheduled' ? form.value.cron_expression : null,
      },
    })
    drawerOpen.value = false
    await loadScans()
    if (form.value.scan_type === 'once') startPolling()
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    formError.value = err?.data?.detail ?? '스캔 시작 실패'
  } finally { saving.value = false }
}

// ── Re-run ────────────────────────────────────────────────────────────────────
async function rerunScan(id: number, event: Event) {
  event.preventDefault()
  rerunningId.value = id
  try {
    await $fetch(`/api/scans/${id}/rerun`, { method: 'POST' })
    await loadScans()
    startPolling()
  } finally { rerunningId.value = null }
}

// ── Schedule modal ────────────────────────────────────────────────────────────
function openScheduleModal(scan: Scan, event: Event) {
  event.preventDefault()
  scheduleModalScan.value = scan
  scheduleModalCron.value = scan.cron_expression ?? '0 9 * * *'
}
async function applySchedule() {
  if (!scheduleModalScan.value) return
  schedulingId.value = scheduleModalScan.value.id
  try {
    await $fetch(`/api/scans/${scheduleModalScan.value.id}/schedule`, {
      method: 'POST',
      body: { cron_expression: scheduleModalCron.value || null },
    })
    scheduleModalScan.value = null
    await loadScans()
  } finally { schedulingId.value = null }
}
async function removeSchedule(scan: Scan, event: Event) {
  event.preventDefault()
  schedulingId.value = scan.id
  try {
    await $fetch(`/api/scans/${scan.id}/schedule`, { method: 'POST', body: { cron_expression: null } })
    await loadScans()
  } finally { schedulingId.value = null }
}

// ── Cancel / polling ──────────────────────────────────────────────────────────
async function cancelScan(id: number) { await $fetch(`/api/scans/${id}/cancel`, { method: 'POST' }); await loadScans() }

function startPolling() {
  if (pollingTimer.value) return
  pollingTimer.value = setInterval(async () => { await loadScans(); if (!hasRunning.value) stopPolling() }, 2000)
}
function stopPolling() { if (pollingTimer.value) { clearInterval(pollingTimer.value); pollingTimer.value = null } }

function openDrawer() {
  form.value = { connection_id: '', sample_size: 100, confidence_threshold: 0.5, target_schemas: '', scan_type: 'once', cron_expression: '0 9 * * *' }
  formError.value = ''; drawerOpen.value = true
}

onMounted(async () => {
  loading.value = true
  await Promise.all([loadScans(), loadConnections()])
  loading.value = false
  if (hasRunning.value) startPolling()
})
onUnmounted(stopPolling)
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="px-8 pt-8 pb-6 flex items-start justify-between">
      <div>
        <h1 class="font-display text-2xl font-bold tracking-tight" style="color: var(--foreground);">Scans</h1>
        <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">PII 탐지 스캔 작업을 관리합니다.</p>
      </div>
      <button @click="openDrawer" class="btn-primary flex items-center gap-2">
        <Plus class="w-4 h-4" /> New Scan
      </button>
    </div>

    <div class="flex-1 overflow-auto px-8 pb-8">
      <div v-if="loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-24 rounded-xl animate-pulse" style="background: var(--border);" />
      </div>

      <div v-else-if="scans.length === 0" class="flex flex-col items-center justify-center py-24 text-center">
        <div class="w-14 h-14 rounded-full flex items-center justify-center mb-4"
          style="background: var(--muted); border: 1px solid var(--border);">
          <ScanSearch class="w-6 h-6" style="color: var(--muted-foreground);" />
        </div>
        <h3 class="font-display font-semibold mb-1" style="color: var(--foreground);">스캔 이력이 없습니다</h3>
        <p class="text-[13px] max-w-xs mb-5" style="color: var(--muted-foreground);">데이터베이스 연결을 추가하고 첫 번째 PII 스캔을 시작하세요.</p>
        <button @click="openDrawer" class="btn-primary flex items-center gap-2">
          <Plus class="w-4 h-4" /> New Scan
        </button>
      </div>

      <div v-else class="space-y-3">
        <NuxtLink v-for="scan in sortedScans" :key="scan.id"
          :to="scan.is_scheduled ? undefined : `/scans/${scan.id}`"
          class="scan-card block rounded-xl border p-5 group"
          :class="scan.is_scheduled ? 'cursor-default' : ''"
          style="background: var(--card); border-color: var(--border);">
          <div class="flex items-start gap-4">
            <!-- Status badge -->
            <div class="flex-shrink-0 mt-0.5">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border"
                :style="{ color: getStatus(scan.status).color, background: getStatus(scan.status).bg, borderColor: getStatus(scan.status).color + '40' }">
                <component :is="getStatus(scan.status).icon" class="w-3 h-3"
                  :class="scan.status === 'running' ? 'animate-spin' : ''" />
                {{ getStatus(scan.status).label }}
              </span>
            </div>

            <!-- Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-[13px] font-semibold" style="color: var(--foreground);">Scan #{{ scan.id }}</span>
                <span class="text-[11px]" style="color: var(--muted-foreground);">· {{ connName(scan.connection_id) }}</span>
                <!-- Cron badge -->
                <span v-if="scan.is_scheduled && scan.cron_expression"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold"
                  style="background: #f5f3ff; color: #7c3aed; border: 1px solid #ddd6fe;">
                  <CalendarClock class="w-3 h-3" />{{ scan.cron_expression }}
                </span>
              </div>
              <div class="flex items-center gap-4 text-[12px]" style="color: var(--muted-foreground);">
                <span class="flex items-center gap-1"><Calendar class="w-3 h-3" />{{ formatDate(scan.created_at) }}</span>
                <span v-if="scan.is_scheduled && scan.cron_expression" class="flex items-center gap-1">
                  <Repeat2 class="w-3 h-3" />{{ describeCron(scan.cron_expression) }}
                </span>
                <span v-else-if="scan.total_tables !== null" class="flex items-center gap-1">
                  <Layers class="w-3 h-3" />{{ scan.total_tables }} tables · {{ scan.total_columns }} cols
                </span>
                <span v-if="scan.status === 'running'" style="color: #2563eb;">{{ formatDuration(scan.started_at, null) }} elapsed</span>
                <span v-else-if="scan.completed_at">{{ formatDuration(scan.started_at, scan.completed_at) }}</span>
              </div>
              <p v-if="scan.error_message" class="text-[12px] mt-1 truncate" style="color: #dc2626;">{{ scan.error_message }}</p>
            </div>

            <!-- Right actions -->
            <div class="flex flex-col items-end gap-2 flex-shrink-0">
              <!-- PII count -->
              <div v-if="scan.pii_columns_found !== null && !scan.is_scheduled" class="text-right">
                <div class="text-xl font-display font-bold"
                  :style="{ color: scan.pii_columns_found > 0 ? 'var(--primary)' : 'var(--muted-foreground)' }">
                  {{ scan.pii_columns_found }}
                </div>
                <div class="text-[11px]" style="color: var(--muted-foreground);">PII cols</div>
              </div>

              <!-- Action buttons -->
              <div class="flex items-center gap-1.5">
                <!-- Cancel (running/pending) -->
                <button v-if="['running','pending'].includes(scan.status)"
                  class="action-btn action-btn-danger" @click.prevent="cancelScan(scan.id)">
                  <Ban class="w-3 h-3" /> Cancel
                </button>

                <!-- Re-run (completed/failed/cancelled) -->
                <button v-if="['completed','failed','cancelled'].includes(scan.status)"
                  class="action-btn" @click="rerunScan(scan.id, $event)">
                  <Loader2 v-if="rerunningId === scan.id" class="w-3 h-3 animate-spin" />
                  <RefreshCw v-else class="w-3 h-3" />
                  Re-run
                </button>

                <!-- Schedule (non-scheduled scans) -->
                <button v-if="!scan.is_scheduled"
                  class="action-btn action-btn-purple" @click="openScheduleModal(scan, $event)">
                  <CalendarClock class="w-3 h-3" /> Schedule
                </button>

                <!-- Remove schedule (scheduled scans) -->
                <button v-if="scan.is_scheduled"
                  class="action-btn action-btn-danger" @click="removeSchedule(scan, $event)">
                  <Loader2 v-if="schedulingId === scan.id" class="w-3 h-3 animate-spin" />
                  <Ban v-else class="w-3 h-3" />
                  Unschedule
                </button>
              </div>
            </div>

            <ChevronRight v-if="!scan.is_scheduled" class="w-4 h-4 flex-shrink-0 mt-1 self-center"
              style="color: var(--border);" />
          </div>
        </NuxtLink>
      </div>
    </div>

    <!-- Backdrop -->
    <Transition name="fade">
      <div v-if="drawerOpen || scheduleModalScan" class="fixed inset-0 z-40"
        style="background: oklch(0.128 0.018 257 / 40%);"
        @click="drawerOpen = false; scheduleModalScan = null" />
    </Transition>

    <!-- ── New Scan Drawer ───────────────────────────────────────────────── -->
    <Transition name="slide-right">
      <div v-if="drawerOpen" class="fixed right-0 top-0 h-full w-[460px] z-50 flex flex-col shadow-2xl"
        style="background: var(--card); border-left: 1px solid var(--border);">
        <div class="flex items-center justify-between px-6 py-5" style="border-bottom: 1px solid var(--border);">
          <div>
            <h2 class="font-display font-bold text-[17px]" style="color: var(--foreground);">New Scan</h2>
            <p class="text-[12px] mt-0.5" style="color: var(--muted-foreground);">스캔할 DB와 옵션을 선택하세요.</p>
          </div>
          <button @click="drawerOpen = false" class="icon-btn"><X class="w-4 h-4" /></button>
        </div>

        <div class="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          <!-- Connection -->
          <div>
            <label class="field-label">Database Connection *</label>
            <div v-if="connections.length === 0" class="p-3 rounded-xl border-2 border-dashed text-[12px] text-center"
              style="border-color: var(--border); color: var(--muted-foreground);">
              먼저 <NuxtLink to="/connections" style="color: var(--primary);" class="font-semibold hover:underline">DB 연결</NuxtLink>을 추가하세요.
            </div>
            <div v-else class="space-y-2">
              <button v-for="conn in connections" :key="conn.id"
                class="w-full flex items-center gap-3 p-3 rounded-xl border text-left transition-all"
                :style="form.connection_id === conn.id
                  ? 'border-color: var(--primary); background: color-mix(in oklch, var(--primary) 6%, transparent);'
                  : 'border-color: var(--border); background: var(--background);'"
                @click="form.connection_id = conn.id">
                <Database class="w-4 h-4 flex-shrink-0"
                  :style="{ color: form.connection_id === conn.id ? 'var(--primary)' : 'var(--muted-foreground)' }" />
                <div>
                  <div class="text-[13px] font-medium" style="color: var(--foreground);">{{ conn.name }}</div>
                  <div class="text-[11px] font-mono" style="color: var(--muted-foreground);">{{ conn.db_type }} · {{ conn.host }}</div>
                </div>
              </button>
            </div>
          </div>

          <!-- Scan type toggle -->
          <div>
            <label class="field-label">실행 방식</label>
            <div class="grid grid-cols-2 gap-2">
              <button class="type-btn" :class="form.scan_type === 'once' ? 'type-btn-active' : ''"
                @click="form.scan_type = 'once'">
                <Play class="w-4 h-4" />
                <div>
                  <div class="text-[13px] font-semibold">One-time</div>
                  <div class="text-[11px] opacity-60">즉시 1회 실행</div>
                </div>
              </button>
              <button class="type-btn" :class="form.scan_type === 'scheduled' ? 'type-btn-active type-btn-purple' : ''"
                @click="form.scan_type = 'scheduled'">
                <CalendarClock class="w-4 h-4" />
                <div>
                  <div class="text-[13px] font-semibold">Scheduled</div>
                  <div class="text-[11px] opacity-60">주기적 반복 실행</div>
                </div>
              </button>
            </div>
          </div>

          <!-- Cron options (scheduled only) -->
          <div v-if="form.scan_type === 'scheduled'" class="space-y-3">
            <div>
              <label class="field-label">반복 주기 프리셋</label>
              <div class="grid grid-cols-2 gap-2">
                <button v-for="p in cronPresets" :key="p.cron"
                  class="cron-preset-btn text-left"
                  :class="form.cron_expression === p.cron ? 'cron-preset-active' : ''"
                  @click="form.cron_expression = p.cron">
                  <div class="text-[12px] font-semibold" style="color: var(--foreground);">{{ p.label }}</div>
                  <div class="text-[11px]" style="color: var(--muted-foreground);">{{ p.desc }}</div>
                </button>
              </div>
            </div>
            <div>
              <label class="field-label">Cron 표현식 <span style="color: var(--muted-foreground); font-weight:400;">(분 시 일 월 요일)</span></label>
              <input v-model="form.cron_expression" type="text" placeholder="0 9 * * 1"
                class="field-input font-mono" />
              <p v-if="form.cron_expression" class="text-[11px] mt-1 flex items-center gap-1" style="color: #7c3aed;">
                <Repeat2 class="w-3 h-3" /> {{ describeCron(form.cron_expression) }}
              </p>
            </div>
          </div>

          <!-- Sample size -->
          <div>
            <label class="field-label">Sample Size <span style="color: var(--muted-foreground); font-weight: 400;">(컬럼당 샘플링 행 수)</span></label>
            <div class="flex items-center gap-3">
              <input v-model="form.sample_size" type="range" min="10" max="1000" step="10" class="flex-1" style="accent-color: var(--primary);" />
              <span class="text-[13px] font-mono w-12 text-right" style="color: var(--foreground);">{{ form.sample_size }}</span>
            </div>
          </div>

          <!-- Confidence -->
          <div>
            <label class="field-label">Confidence Threshold <span style="color: var(--muted-foreground); font-weight: 400;">(최소 신뢰도)</span></label>
            <div class="flex items-center gap-3">
              <input v-model="form.confidence_threshold" type="range" min="0.1" max="1.0" step="0.05" class="flex-1" style="accent-color: var(--primary);" />
              <span class="text-[13px] font-mono w-12 text-right" style="color: var(--primary);">{{ form.confidence_threshold.toFixed(2) }}</span>
            </div>
          </div>

          <!-- Target schemas -->
          <div>
            <label class="field-label">Target Schemas <span style="color: var(--muted-foreground); font-weight: 400;">(비우면 전체 스캔)</span></label>
            <input v-model="form.target_schemas" type="text" placeholder="schema1, schema2, ..." class="field-input" />
            <p class="text-[11px] mt-1" style="color: var(--muted-foreground);">쉼표로 구분. 특정 스키마만 스캔하려면 입력하세요.</p>
          </div>

          <div class="flex items-start gap-2 p-3 rounded-xl border"
            style="background: color-mix(in oklch, var(--primary) 4%, transparent); border-color: color-mix(in oklch, var(--primary) 15%, transparent);">
            <AlertTriangle class="w-4 h-4 flex-shrink-0 mt-0.5" style="color: var(--primary);" />
            <p class="text-[12px]" style="color: var(--primary);">
              {{ form.scan_type === 'scheduled' ? '스케줄 등록 후 지정된 시간에 자동으로 실행됩니다.' : '스캔은 백그라운드에서 실행됩니다. 대용량 DB는 시간이 걸릴 수 있습니다.' }}
            </p>
          </div>

          <p v-if="formError" class="text-[12px] flex items-center gap-1.5" style="color: #dc2626;">
            <XCircle class="w-3.5 h-3.5" /> {{ formError }}
          </p>
        </div>

        <div class="px-6 py-4 flex items-center justify-end gap-3" style="border-top: 1px solid var(--border);">
          <button @click="drawerOpen = false" class="btn-ghost">Cancel</button>
          <button @click="startScan" :disabled="saving" class="btn-primary flex items-center gap-2"
            :style="form.scan_type === 'scheduled' ? 'background: #7c3aed;' : ''">
            <Loader2 v-if="saving" class="w-4 h-4 animate-spin" />
            <CalendarClock v-else-if="form.scan_type === 'scheduled'" class="w-4 h-4" />
            <Play v-else class="w-4 h-4" />
            {{ saving ? 'Saving...' : form.scan_type === 'scheduled' ? 'Register Schedule' : 'Start Scan' }}
          </button>
        </div>
      </div>
    </Transition>

    <!-- ── Schedule Modal ────────────────────────────────────────────────── -->
    <Transition name="fade">
      <div v-if="scheduleModalScan" class="fixed inset-0 z-50 flex items-center justify-center px-4" @click.self="scheduleModalScan = null">
        <div class="w-[420px] rounded-2xl shadow-2xl flex flex-col" style="background: var(--card); border: 1px solid var(--border);">
          <div class="flex items-center justify-between px-6 py-4" style="border-bottom: 1px solid var(--border);">
            <h3 class="font-display font-bold text-[16px]" style="color: var(--foreground);">Schedule Scan #{{ scheduleModalScan.id }}</h3>
            <button class="icon-btn" @click="scheduleModalScan = null"><X class="w-4 h-4" /></button>
          </div>
          <div class="px-6 py-5 space-y-4">
            <div>
              <label class="field-label">반복 주기 프리셋</label>
              <div class="grid grid-cols-2 gap-2">
                <button v-for="p in cronPresets" :key="p.cron"
                  class="cron-preset-btn text-left"
                  :class="scheduleModalCron === p.cron ? 'cron-preset-active' : ''"
                  @click="scheduleModalCron = p.cron">
                  <div class="text-[12px] font-semibold" style="color: var(--foreground);">{{ p.label }}</div>
                  <div class="text-[11px]" style="color: var(--muted-foreground);">{{ p.desc }}</div>
                </button>
              </div>
            </div>
            <div>
              <label class="field-label">Cron 표현식</label>
              <input v-model="scheduleModalCron" type="text" placeholder="0 9 * * *" class="field-input font-mono" />
              <p v-if="scheduleModalCron" class="text-[11px] mt-1 flex items-center gap-1" style="color: #7c3aed;">
                <Repeat2 class="w-3 h-3" /> {{ describeCron(scheduleModalCron) }}
              </p>
            </div>
          </div>
          <div class="px-6 py-4 flex items-center justify-end gap-3" style="border-top: 1px solid var(--border);">
            <button class="btn-ghost" @click="scheduleModalScan = null">Cancel</button>
            <button class="btn-primary flex items-center gap-2" style="background: #7c3aed;"
              :disabled="schedulingId !== null" @click="applySchedule">
              <Loader2 v-if="schedulingId !== null" class="w-4 h-4 animate-spin" />
              <CalendarClock v-else class="w-4 h-4" />
              Apply Schedule
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.btn-primary { height: 36px; padding: 0 16px; border-radius: 9px; font-size: 13px; font-weight: 700; background: var(--primary); color: white; transition: opacity 0.15s; }
.btn-primary:hover { opacity: 0.88; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost { height: 36px; padding: 0 14px; border-radius: 9px; font-size: 13px; font-weight: 600; color: var(--muted-foreground); transition: background 0.12s; }
.btn-ghost:hover { background: var(--muted); }
.icon-btn { width: 28px; height: 28px; border-radius: 7px; display: flex; align-items: center; justify-content: center; color: var(--muted-foreground); transition: background 0.12s, color 0.12s; }
.icon-btn:hover { background: var(--muted); color: var(--foreground); }

.scan-card { transition: border-color 0.15s, box-shadow 0.15s; }
.scan-card:hover { border-color: var(--primary) !important; box-shadow: 0 2px 8px oklch(0.577 0.218 257 / 6%); }

.action-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; border-radius: 7px; font-size: 11px; font-weight: 600;
  border: 1px solid var(--border); color: var(--muted-foreground);
  transition: all 0.12s; white-space: nowrap;
}
.action-btn:hover { border-color: var(--primary); color: var(--primary); background: color-mix(in oklch, var(--primary) 5%, transparent); }
.action-btn-danger:hover { border-color: #fecaca; color: #dc2626; background: #fef2f2; }
.action-btn-purple:hover { border-color: #ddd6fe; color: #7c3aed; background: #f5f3ff; }

.field-label { display: block; font-size: 12px; font-weight: 600; color: var(--foreground); margin-bottom: 6px; }
.field-input { width: 100%; height: 38px; padding: 0 12px; border-radius: 9px; border: 1px solid var(--border); background: var(--background); color: var(--foreground); font-size: 13px; outline: none; transition: border-color 0.15s, box-shadow 0.15s; }
.field-input:focus { border-color: color-mix(in oklch, var(--primary) 60%, transparent); box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 12%, transparent); }
.field-input::placeholder { color: var(--muted-foreground); opacity: 0.6; }

.type-btn {
  display: flex; align-items: center; gap: 10px; padding: 12px;
  border-radius: 12px; border: 1px solid var(--border);
  background: var(--background); color: var(--muted-foreground);
  transition: all 0.15s; text-align: left;
}
.type-btn-active { border-color: var(--primary); background: color-mix(in oklch, var(--primary) 6%, transparent); color: var(--primary); }
.type-btn-purple { border-color: #ddd6fe; background: #f5f3ff; color: #7c3aed; }

.cron-preset-btn {
  padding: 10px 12px; border-radius: 10px; border: 1px solid var(--border);
  background: var(--background); transition: all 0.12s;
}
.cron-preset-btn:hover { border-color: #ddd6fe; background: #f5f3ff; }
.cron-preset-active { border-color: #7c3aed; background: #f5f3ff; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.18s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-right-enter-active, .slide-right-leave-active { transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1); }
.slide-right-enter-from, .slide-right-leave-to { transform: translateX(100%); }
</style>
