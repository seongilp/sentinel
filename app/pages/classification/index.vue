<script setup lang="ts">
import { Tags, Filter, Check, X, Microscope, ChevronRight } from 'lucide-vue-next'

interface Classification {
  id: number; scan_id: number; connection_id: number; schema_name: string; table_name: string
  column_name: string; data_type: string | null; pii_type: string
  confidence: number; sensitivity_level: string; status: string; created_at: string
}
interface Connection { id: number; name: string; db_type: string }

const items = ref<Classification[]>([])
const connections = ref<Connection[]>([])
const loading = ref(false)
const filterStatus = ref<string>('all')
const filterSensitivity = ref<string>('all')
const filterPiiType = ref<string>('all')
const filterConn = ref<string>('all')
const updatingId = ref<number | null>(null)

// Deep Inspect popover
const popoverItemId = ref<number | null>(null)
const popoverConnId = ref<number | null>(null)
const router = useRouter()

function openPopover(item: Classification) {
  // Auto-select the connection the scan came from; fall back to first connection
  const connId = connections.value.find(c => c.id === item.connection_id)?.id
    ?? connections.value[0]?.id
  if (connId) {
    router.push(`/deep-inspect?schema=${item.schema_name}&table=${item.table_name}&conn=${connId}&column=${item.column_name}`)
  } else {
    // No connection available — fall back to popover
    popoverItemId.value = popoverItemId.value === item.id ? null : item.id
    popoverConnId.value = null
  }
}
function closePopover() { popoverItemId.value = null }

function startDeepInspect(item: Classification) {
  closePopover()
  const connId = popoverConnId.value ?? connections.value[0]?.id
  if (!connId) return
  router.push(`/deep-inspect?schema=${item.schema_name}&table=${item.table_name}&conn=${connId}&column=${item.column_name}`)
}

const piiColor: Record<string, string> = {
  email: '#2563eb', phone: '#16a34a', resident_id: '#dc2626',
  credit_card: '#7c3aed', name: '#d97706', address: '#ea580c',
  password: '#b91c1c', account_number: '#db2777',
}

function getPiiColor(type: string) { return piiColor[type] || '#6b7280' }
function getConnName(id: number) { return connections.value.find(c => c.id === id)?.name ?? `DB #${id}` }

const piiTypes = computed(() => [...new Set(items.value.map(i => i.pii_type))].sort())

const filtered = computed(() => items.value.filter(i => {
  if (filterStatus.value !== 'all' && i.status !== filterStatus.value) return false
  if (filterSensitivity.value !== 'all' && i.sensitivity_level !== filterSensitivity.value) return false
  if (filterPiiType.value !== 'all' && i.pii_type !== filterPiiType.value) return false
  if (filterConn.value !== 'all' && String(i.connection_id) !== filterConn.value) return false
  return true
}))

async function updateItem(id: number, patch: { status?: string; sensitivity_level?: string }) {
  updatingId.value = id
  try {
    const updated = await $fetch<Classification>(`/api/classifications/${id}`, { method: 'PUT', body: patch })
    const idx = items.value.findIndex(i => i.id === id)
    if (idx >= 0) items.value[idx] = updated
  } finally { updatingId.value = null }
}

onMounted(async () => {
  document.addEventListener('click', closePopover)
  loading.value = true
  const [cls, conns] = await Promise.all([
    $fetch<Classification[]>('/api/classifications'),
    $fetch<Connection[]>('/api/connections').catch(() => []),
  ])
  items.value = cls
  connections.value = conns
  loading.value = false
})

onUnmounted(() => { document.removeEventListener('click', closePopover) })
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="px-8 pt-8 pb-6">
      <h1 class="font-display text-2xl font-bold tracking-tight" style="color: var(--foreground);">Data Classification</h1>
      <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">탐지된 PII 컬럼의 민감도를 지정하고 확인/기각합니다.</p>
    </div>

    <!-- Filters -->
    <div class="px-8 mb-4 flex items-center gap-3 flex-wrap">
      <div class="flex items-center gap-1.5 text-[12px]" style="color: var(--muted-foreground);">
        <Filter class="w-3.5 h-3.5" /> 필터:
      </div>
      <select v-model="filterStatus" class="filter-select">
        <option value="all">모든 상태</option>
        <option value="pending">Pending</option>
        <option value="confirmed">Confirmed</option>
        <option value="dismissed">Dismissed</option>
      </select>
      <select v-model="filterSensitivity" class="filter-select">
        <option value="all">모든 민감도</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
      </select>
      <select v-model="filterPiiType" class="filter-select">
        <option value="all">모든 PII 유형</option>
        <option v-for="t in piiTypes" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="filterConn" class="filter-select">
        <option value="all">모든 Connection</option>
        <option v-for="c in connections" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
      </select>
      <span class="ml-auto text-[12px]" style="color: var(--muted-foreground);">{{ filtered.length }}개 항목</span>
    </div>

    <!-- Table -->
    <div class="flex-1 overflow-auto px-8 pb-8">
      <div v-if="loading" class="space-y-2">
        <div v-for="i in 5" :key="i" class="h-12 rounded-xl animate-pulse" style="background: var(--border);" />
      </div>

      <div v-else-if="filtered.length === 0" class="section-card flex flex-col items-center py-20 text-center">
        <Tags class="w-10 h-10 mb-3" style="color: var(--border);" />
        <p class="text-[13px]" style="color: var(--muted-foreground);">탐지된 PII가 없거나 필터 조건에 맞지 않습니다.</p>
      </div>

      <div v-else class="section-card overflow-hidden !p-0">
        <table class="w-full border-collapse">
          <thead>
            <tr style="background: var(--background); border-bottom: 1px solid var(--border);">
              <th class="table-th px-5 py-3 text-left" style="width: 28%;">위치</th>
              <th class="table-th px-5 py-3 text-left" style="width: 15%;">PII 유형</th>
              <th class="table-th px-5 py-3 text-center" style="width: 10%;">신뢰도</th>
              <th class="table-th px-5 py-3 text-center" style="width: 15%;">민감도</th>
              <th class="table-th px-5 py-3 text-center" style="width: 8%;">Inspect</th>
              <th class="table-th px-5 py-3 text-center" style="width: 13%;">상태</th>
              <th class="table-th px-5 py-3 text-center" style="width: 11%;">액션</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in filtered" :key="item.id"
              class="table-body-row"
              :style="[
                i > 0 ? 'border-top: 1px solid var(--border);' : '',
                item.status === 'dismissed' ? 'opacity: 0.45;' : ''
              ].join(' ')">
              <!-- Location -->
              <td class="px-5 py-3">
                <div class="text-[10px] font-semibold uppercase tracking-wide mb-0.5"
                  style="color: var(--primary);">{{ getConnName(item.connection_id) }}</div>
                <div class="text-[11px] font-mono" style="color: var(--muted-foreground);">{{ item.schema_name }}.{{ item.table_name }}</div>
                <div class="text-[13px] font-mono font-semibold" style="color: var(--foreground);">{{ item.column_name }}</div>
              </td>
              <!-- PII type -->
              <td class="px-5 py-3">
                <span class="pii-badge"
                  :style="{ color: getPiiColor(item.pii_type), background: getPiiColor(item.pii_type) + '18' }">
                  {{ item.pii_type }}
                </span>
              </td>
              <!-- Confidence -->
              <td class="px-5 py-3 text-center">
                <span class="text-[12px] font-mono font-semibold"
                  :style="{ color: item.confidence >= 0.9 ? '#16a34a' : item.confidence >= 0.6 ? '#d97706' : 'var(--muted-foreground)' }">
                  {{ (item.confidence * 100).toFixed(0) }}%
                </span>
              </td>
              <!-- Sensitivity selector -->
              <td class="px-5 py-3 text-center">
                <select :value="item.sensitivity_level" :disabled="updatingId === item.id"
                  @change="updateItem(item.id, { sensitivity_level: ($event.target as HTMLSelectElement).value })"
                  class="sensitivity-select"
                  :class="{
                    'sel-high':   item.sensitivity_level === 'high',
                    'sel-medium': item.sensitivity_level === 'medium',
                    'sel-low':    item.sensitivity_level === 'low',
                  }">
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </td>
              <!-- Deep Inspect column -->
              <td class="px-3 py-3 text-center">
                <div v-if="item.sensitivity_level === 'high'" class="relative inline-block">
                  <button @click.stop="openPopover(item)" class="di-btn" title="Deep Inspect">
                    <Microscope class="w-3.5 h-3.5" />
                    <span class="di-pulse" />
                  </button>
                  <!-- Popover -->
                  <div v-if="popoverItemId === item.id" class="di-popover" @click.stop>
                    <div class="flex items-center gap-1.5 mb-2">
                      <Microscope class="w-3 h-3" style="color:#2563eb;" />
                      <span class="text-[11px] font-bold tracking-wide" style="color:var(--foreground);">Deep Inspect</span>
                    </div>
                    <div class="text-[10px] mb-2 font-mono" style="color:var(--muted-foreground);">
                      {{ item.schema_name }}.{{ item.table_name }}
                    </div>
                    <select v-if="connections.length > 0" v-model="popoverConnId" class="di-conn-select mb-2">
                      <option v-for="c in connections" :key="c.id" :value="c.id">{{ c.name }}</option>
                    </select>
                    <p v-else class="text-[10px] mb-2" style="color:#dc2626;">연결된 DB 없음</p>
                    <button @click="startDeepInspect(item)" :disabled="!popoverConnId" class="di-start-btn">
                      시작 <ChevronRight class="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </td>
              <!-- Status badge -->
              <td class="px-5 py-3 text-center">
                <span class="status-badge"
                  :class="{
                    'status-pending':   item.status === 'pending',
                    'status-confirmed': item.status === 'confirmed',
                    'status-dismissed': item.status === 'dismissed',
                  }">{{ item.status }}</span>
              </td>
              <!-- Actions -->
              <td class="px-5 py-3 text-center">
                <div class="flex items-center justify-center gap-1">
                  <button v-if="item.status !== 'confirmed'" @click="updateItem(item.id, { status: 'confirmed' })"
                    class="action-btn confirm-btn" title="Confirm">
                    <Check class="w-3.5 h-3.5" />
                  </button>
                  <button v-if="item.status !== 'dismissed'" @click="updateItem(item.id, { status: 'dismissed' })"
                    class="action-btn dismiss-btn" title="Dismiss">
                    <X class="w-3.5 h-3.5" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-select {
  height: 32px; padding: 0 8px; border-radius: 6px;
  border: 1px solid var(--border); background: var(--card);
  color: var(--foreground); font-size: 12px; outline: none;
}
.filter-select:focus { border-color: var(--primary); }

.section-card {
  border-radius: 12px; border: 1px solid var(--border);
  background: var(--card);
  box-shadow: 0 1px 3px oklch(0.128 0.018 257 / 4%);
}

.table-th {
  font-size: 11px; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--muted-foreground);
}
.table-body-row { transition: background 0.1s; }
.table-body-row:hover { background: color-mix(in oklch, var(--primary) 3%, transparent); }

.pii-badge {
  display: inline-block; font-size: 11px; font-weight: 600;
  font-family: var(--font-mono); padding: 2px 8px; border-radius: 20px;
}

.sensitivity-select {
  height: 26px; padding: 0 8px; border-radius: 20px;
  border: 1px solid transparent; font-size: 11px; font-weight: 700;
  outline: none; cursor: pointer; text-align: center;
}
.sel-high   { color: #dc2626; background: #fef2f2; border-color: #fecaca; }
.sel-medium { color: #ea580c; background: #fff7ed; border-color: #fed7aa; }
.sel-low    { color: #16a34a; background: #f0fdf4; border-color: #bbf7d0; }

.status-badge {
  display: inline-block; font-size: 11px; font-weight: 600;
  padding: 2px 9px; border-radius: 20px; text-transform: capitalize;
}
.status-pending   { color: #2563eb; background: #eff6ff; }
.status-confirmed { color: #16a34a; background: #f0fdf4; }
.status-dismissed { color: #6b7280; background: #f3f4f6; }

.action-btn {
  padding: 5px; border-radius: 6px; transition: background 0.1s, color 0.1s;
  color: var(--muted-foreground);
}
.confirm-btn:hover { color: #16a34a; background: #f0fdf4; }
.dismiss-btn:hover { color: #dc2626; background: #fef2f2; }

/* Deep Inspect button */
.di-btn {
  position: relative; width: 26px; height: 26px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: #2563eb; background: #eff6ff; border: 1px solid #bfdbfe;
  transition: background 0.15s, box-shadow 0.15s;
}
.di-btn:hover { background: #dbeafe; box-shadow: 0 0 0 3px rgba(37,99,235,0.12); }
.di-pulse {
  position: absolute; top: 3px; right: 3px;
  width: 5px; height: 5px; border-radius: 50%;
  background: #2563eb;
  animation: pulse-ring 1.8s ease-in-out infinite;
}
@keyframes pulse-ring {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.6); }
}

/* Popover */
.di-popover {
  position: absolute; top: calc(100% + 6px); right: 0; z-index: 50;
  width: 180px; padding: 10px;
  background: var(--card); border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06);
}
.di-conn-select {
  width: 100%; height: 28px; padding: 0 6px; border-radius: 6px;
  border: 1px solid var(--border); background: var(--background);
  color: var(--foreground); font-size: 11px; outline: none;
}
.di-start-btn {
  width: 100%; height: 28px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center; gap: 4px;
  font-size: 11px; font-weight: 700;
  background: #2563eb; color: white;
  transition: background 0.1s;
}
.di-start-btn:hover:not(:disabled) { background: #1d4ed8; }
.di-start-btn:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
