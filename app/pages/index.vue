<script setup lang="ts">
import { Activity, Database as DbIcon, ScanSearch as ScanIcon, Shield, AlertTriangle, Users as UsersIcon } from 'lucide-vue-next'

interface TrendPoint { date: string; total: number; high: number; medium: number; low: number }

interface Summary {
  total_connections: number; total_scans: number; pii_columns: number; high_risk: number
  scans_completed: number; scans_pending: number; scans_cancelled: number
  recent_scans: Array<{ id: number; connection_id: number; status: string; created_at: string }>
}
interface ActivityItem {
  id: number; action: string; entity_type: string | null
  entity_id: number | null; details: string | null; created_at: string
}

const summary = ref<Summary>({ total_connections: 0, total_scans: 0, pii_columns: 0, high_risk: 0, scans_completed: 0, scans_pending: 0, scans_cancelled: 0, recent_scans: [] })
const { users: allUsers, lockedUsers, activeUsers, inactiveUsers, initLockedEvents } = useUsers()
onMounted(() => initLockedEvents())
const activity = ref<ActivityItem[]>([])
type TrendMode = '1h' | '1d' | '7d' | '14d' | '30d'
const TREND_MODES: TrendMode[] = ['1h', '1d', '7d', '14d', '30d']
function trendApiParams(mode: TrendMode) {
  if (mode === '1h') return 'hours=1'
  if (mode === '1d') return 'hours=24'
  return `days=${mode.replace('d', '')}`
}

const trendData = ref<TrendPoint[]>([])
const trendMode = ref<TrendMode>('30d')
const loading = ref(true)
const loadingTrend = ref(false)

async function loadTrend() {
  loadingTrend.value = true
  trendData.value = await $fetch<TrendPoint[]>(`/api/reports/daily-trend?${trendApiParams(trendMode.value)}`).catch(() => [])
  loadingTrend.value = false
}
async function setTrendMode(m: TrendMode) {
  trendMode.value = m
  await loadTrend()
}

const actionColor: Record<string, string> = {
  'connection.created': '#16a34a', 'connection.deleted': '#dc2626',
  'scan.created': '#2563eb', 'scan.failed': '#dc2626',
}

const statCards = computed(() => [
  { label: 'Connections', value: summary.value.total_connections, icon: DbIcon,
    bg: 'color-mix(in oklch, var(--primary) 8%, transparent)',
    iconColor: 'var(--primary)', bar: 'color-mix(in oklch, var(--primary) 40%, transparent)',
    to: '/connections', sub: null },
  { label: 'Total Scans', value: summary.value.total_scans, icon: ScanIcon,
    bg: '#fff7ed', iconColor: '#ea580c', bar: '#fed7aa',
    to: '/scans',
    sub: [
      { label: '완료', value: summary.value.scans_completed, color: '#16a34a' },
      { label: '예정', value: summary.value.scans_pending, color: '#2563eb' },
      { label: '취소', value: summary.value.scans_cancelled, color: '#6b7280' },
    ] },
  { label: 'PII Columns', value: summary.value.pii_columns, icon: Shield,
    bg: '#f0fdf4', iconColor: '#16a34a', bar: '#bbf7d0',
    to: '/reports', sub: null },
  { label: 'High Risk', value: summary.value.high_risk, icon: AlertTriangle,
    bg: '#fef2f2', iconColor: '#dc2626', bar: '#fecaca',
    to: '/reports', sub: null },
  { label: 'Users', value: allUsers.value.length, icon: UsersIcon,
    bg: '#f5f3ff', iconColor: '#7c3aed', bar: '#ddd6fe',
    to: '/users',
    sub: [
      { label: '활성', value: activeUsers.value.length, color: '#16a34a' },
      { label: '비활성', value: inactiveUsers.value.length, color: '#6b7280' },
      { label: '잠금', value: lockedUsers.value.length, color: '#be123c' },
    ] },
])

onMounted(async () => {
  const [s, a] = await Promise.all([
    $fetch<Summary>('/api/dashboard/summary').catch(() => ({ total_connections: 0, total_scans: 0, pii_columns: 0, high_risk: 0, recent_scans: [] })),
    $fetch<ActivityItem[]>('/api/dashboard/recent-activity').catch(() => []),
  ])
  summary.value = s
  activity.value = a
  loading.value = false
  loadTrend()
})
</script>

<template>
  <div class="p-6 h-full">
    <div class="mb-5">
      <h1 class="font-display text-2xl font-bold tracking-tight" style="color: var(--foreground);">Dashboard</h1>
      <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">PII detection overview across all connected databases</p>
    </div>

    <!-- Stat cards -->
    <div class="grid grid-cols-2 xl:grid-cols-5 gap-3 mb-5">
      <NuxtLink v-for="stat in statCards" :key="stat.label"
        :to="stat.to"
        class="stat-card relative rounded-xl overflow-hidden block"
        style="border: 1px solid var(--border); background: var(--card); text-decoration: none;">
        <div class="absolute top-0 left-0 right-0 h-px"
          :style="`background: linear-gradient(to right, transparent, ${stat.bar}, transparent);`" />
        <div class="p-5 relative">
          <div class="absolute top-4 right-4 w-9 h-9 rounded-lg flex items-center justify-center"
            :style="`background: ${stat.bg};`">
            <component :is="stat.icon" class="w-4 h-4" :style="`color: ${stat.iconColor};`" />
          </div>
          <p class="text-[11px] uppercase tracking-widest mb-2 pr-11" style="color: var(--muted-foreground); font-family: var(--font-mono);">{{ stat.label }}</p>
          <p class="text-3xl font-display font-bold tabular-nums" style="color: var(--foreground);">{{ loading && !stat.sub ? '…' : stat.value }}</p>
          <!-- Sub-stats (e.g. Users active/locked) -->
          <div v-if="stat.sub" class="grid grid-cols-3 gap-1 mt-3 w-full">
            <div v-for="s in stat.sub" :key="s.label" class="flex flex-col items-center py-1 rounded-lg" :style="{ background: s.color + '12' }">
              <span class="text-[14px] font-bold tabular-nums leading-none" :style="{ color: s.color }">{{ s.value }}</span>
              <span class="text-[9px] font-medium mt-0.5 leading-none" style="color: var(--muted-foreground);">{{ s.label }}</span>
            </div>
          </div>
        </div>
      </NuxtLink>
    </div>

    <!-- Recent Activity -->
    <div v-if="activity.length > 0" class="mb-5">
      <h3 class="text-[11px] uppercase tracking-widest mb-3 flex items-center gap-2" style="color: var(--muted-foreground);">
        <Activity class="w-3.5 h-3.5" /> Recent Activity
      </h3>
      <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border); background: var(--card);">
        <div v-for="(a, i) in activity.slice(0, 8)" :key="a.id"
          class="activity-row flex items-center gap-3 px-4 py-2.5"
          :style="i > 0 ? 'border-top: 1px solid var(--border);' : ''">
          <div class="w-1.5 h-1.5 rounded-full flex-shrink-0"
            :style="{ background: actionColor[a.action] || 'var(--muted-foreground)' }" />
          <span class="text-[12px] font-mono"
            :style="{ color: actionColor[a.action] || 'var(--muted-foreground)' }">{{ a.action }}</span>
          <span v-if="a.entity_id" class="text-[11px]" style="color: var(--muted-foreground);">#{{ a.entity_id }}</span>
          <span class="ml-auto text-[11px]" style="color: var(--muted-foreground);">{{ new Date(a.created_at).toLocaleString('ko-KR') }}</span>
        </div>
      </div>
    </div>

    <!-- Daily Trend Chart -->
    <div v-if="!loading" class="mb-5">
      <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border); background: var(--card);">
        <div class="px-5 pt-4 pb-3 flex items-center justify-between" style="border-bottom: 1px solid var(--border);">
          <h3 class="text-[11px] uppercase tracking-widest flex items-center gap-2" style="color: var(--muted-foreground);">
            <Activity class="w-3.5 h-3.5" /> Daily Trend
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
        <div class="px-4 py-3">
          <div v-if="loadingTrend" class="h-[200px] rounded-lg animate-pulse" style="background: var(--border);" />
          <ReportsTrendChart v-else :data="trendData" />
        </div>
      </div>
    </div>

    <!-- Empty state when no data -->
    <div v-if="!loading && summary.total_scans === 0"
      class="rounded-xl p-12 text-center"
      style="border: 1px dashed var(--border);">
      <div class="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4"
        style="background: color-mix(in oklch, var(--primary) 8%, transparent); border: 1px solid color-mix(in oklch, var(--primary) 20%, transparent);">
        <ScanIcon class="w-5 h-5" style="color: var(--primary); opacity: 0.6;" />
      </div>
      <h3 class="font-display font-semibold mb-1" style="color: var(--foreground);">No scan data yet</h3>
      <p class="text-[13px] max-w-sm mx-auto" style="color: var(--muted-foreground);">Add a database connection and run your first scan.</p>
      <NuxtLink to="/connections/new"
        class="inline-flex items-center gap-2 mt-5 px-4 py-2 rounded-lg text-[13px] font-semibold transition-colors"
        style="background: var(--primary); color: white;">
        Add Connection
      </NuxtLink>
    </div>
  </div>
</template>

<style scoped>
.stat-card { transition: box-shadow 0.15s, transform 0.15s; cursor: pointer; }
.stat-card:hover {
  box-shadow: 0 4px 16px oklch(0.128 0.018 257 / 10%);
  transform: translateY(-1px);
}

.activity-row { transition: background 0.1s; }
.activity-row:hover { background: color-mix(in oklch, var(--primary) 3%, transparent); }

.trend-day-btn {
  height: 24px; padding: 0 9px; border-radius: 6px;
  font-size: 11px; font-weight: 600; font-family: var(--font-mono);
  color: var(--muted-foreground); transition: background 0.1s, color 0.1s;
}
.trend-day-btn:hover { background: var(--muted); color: var(--foreground); }
.trend-day-btn-active {
  background: color-mix(in oklch, var(--primary) 10%, transparent);
  color: var(--primary);
}
</style>
