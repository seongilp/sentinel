<script setup lang="ts">
import {
  Plus, Database, Trash2, Edit2, Zap,
  CheckCircle2, XCircle, Loader2, Eye, EyeOff,
  X, ServerCrash, ChevronDown, ChevronUp, Table2, FlaskConical
} from 'lucide-vue-next'

interface Connection {
  id: number; name: string; db_type: string
  host: string; port: number; database: string; username: string
  created_at: string; updated_at: string
}
interface FormData {
  name: string; db_type: string; host: string; port: number | ''
  database: string; username: string; password: string
}

const DB_TYPES = {
  mysql:      { label: 'MySQL',      defaultPort: 3306,  color: '#ea580c', bg: 'rgba(234,88,12,0.08)',  dbLabel: 'Database Name',      dbPlaceholder: 'mydb'    },
  oracle:     { label: 'Oracle',     defaultPort: 1521,  color: '#dc2626', bg: 'rgba(220,38,38,0.08)',  dbLabel: 'Service Name / SID', dbPlaceholder: 'ORCL'    },
  mongodb:    { label: 'MongoDB',    defaultPort: 27017, color: '#16a34a', bg: 'rgba(22,163,74,0.08)',  dbLabel: 'Database Name',      dbPlaceholder: 'admin'   },
  clickhouse: { label: 'ClickHouse', defaultPort: 8123,  color: '#d97706', bg: 'rgba(217,119,6,0.08)',  dbLabel: 'Database Name',      dbPlaceholder: 'default' },
  impala:     { label: 'Impala',     defaultPort: 21050, color: '#0369a1', bg: 'rgba(3,105,161,0.08)',  dbLabel: 'Database Name',      dbPlaceholder: 'default' },
  rds:        { label: 'AWS RDS',    defaultPort: 3306,  color: '#f59e0b', bg: 'rgba(245,158,11,0.08)', dbLabel: 'Database Name',      dbPlaceholder: 'mydb'    },
} as const
type DbType = keyof typeof DB_TYPES

const connections = ref<Connection[]>([])
const loading = ref(false)
const drawerOpen = ref(false)
const editingId = ref<number | null>(null)
const showPassword = ref(false)
const testStatus = ref<Record<number, 'idle'|'testing'|'ok'|'fail'>>({})
const deletingId = ref<number | null>(null)
const saving = ref(false)
const formError = ref('')
const testResult = ref<{ success: boolean; message: string } | null>(null)
const testing = ref(false)

interface ConnInfo {
  schemas: number; tables: number
  schema_details: Array<{ schema: string; tables: number; table_names: string[] }>
}
const infoMap = ref<Record<number, ConnInfo | null>>({})
const infoLoading = ref<Record<number, boolean>>({})
const expandedInfo = ref<Record<number, boolean>>({})

async function fetchInfo(id: number) {
  infoLoading.value[id] = true
  try {
    infoMap.value[id] = await $fetch<ConnInfo>(`/api/connections/${id}/info`)
  } catch {
    infoMap.value[id] = null
  } finally {
    infoLoading.value[id] = false
  }
}

function toggleInfo(id: number) {
  if (!infoMap.value[id] && !infoLoading.value[id]) {
    fetchInfo(id)
  }
  expandedInfo.value[id] = !expandedInfo.value[id]
}

const form = ref<FormData>({ name: '', db_type: 'mysql', host: '', port: 3306, database: '', username: '', password: '' })
const selectedDbMeta = computed(() => DB_TYPES[form.value.db_type as DbType] ?? DB_TYPES.mysql)

function selectDbType(type: DbType) {
  form.value.db_type = type
  form.value.port = DB_TYPES[type].defaultPort
  testResult.value = null
}

async function loadConnections() {
  loading.value = true
  try { connections.value = await $fetch<Connection[]>('/api/connections') }
  finally { loading.value = false }
}

function openDrawer(conn?: Connection) {
  formError.value = ''; testResult.value = null; showPassword.value = false
  if (conn) {
    editingId.value = conn.id
    form.value = { name: conn.name, db_type: conn.db_type, host: conn.host, port: conn.port, database: conn.database, username: conn.username, password: '' }
  } else {
    editingId.value = null
    form.value = { name: '', db_type: 'mysql', host: '', port: 3306, database: '', username: '', password: '' }
  }
  drawerOpen.value = true
}
function closeDrawer() { drawerOpen.value = false; testResult.value = null }

async function testConnection() {
  if (!form.value.host || !form.value.username) { formError.value = 'Host와 Username을 먼저 입력하세요.'; return }
  formError.value = ''; testing.value = true; testResult.value = null
  try {
    testResult.value = await $fetch<{ success: boolean; message: string }>('/api/connections/check', {
      method: 'POST',
      body: { name: form.value.name || 'test', db_type: form.value.db_type, host: form.value.host, port: Number(form.value.port), database: form.value.database, username: form.value.username, password: form.value.password || null },
    })
  } catch { testResult.value = { success: false, message: '연결 테스트 중 오류가 발생했습니다.' } }
  finally { testing.value = false }
}

async function saveConnection() {
  formError.value = ''
  if (!form.value.name || !form.value.host || !form.value.port || !form.value.username) {
    formError.value = '이름, Host, Port, Username은 필수입니다.'; return
  }
  saving.value = true
  try {
    const body = { name: form.value.name, db_type: form.value.db_type, host: form.value.host, port: Number(form.value.port), database: form.value.database, username: form.value.username, password: form.value.password || null }
    if (editingId.value) await $fetch(`/api/connections/${editingId.value}`, { method: 'PUT', body })
    else await $fetch('/api/connections', { method: 'POST', body })
    closeDrawer(); await loadConnections()
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    formError.value = err?.data?.detail ?? '저장 중 오류가 발생했습니다.'
  } finally { saving.value = false }
}

async function deleteConnection(id: number) {
  deletingId.value = id
  try { await $fetch(`/api/connections/${id}`, { method: 'DELETE' }); connections.value = connections.value.filter(c => c.id !== id) }
  finally { deletingId.value = null }
}

async function testSavedConnection(id: number) {
  testStatus.value[id] = 'testing'
  try {
    const result = await $fetch<{ success: boolean }>(`/api/connections/${id}/test`, { method: 'POST' })
    testStatus.value[id] = result.success ? 'ok' : 'fail'
  } catch { testStatus.value[id] = 'fail' }
  setTimeout(() => { testStatus.value[id] = 'idle' }, 3000)
}

onMounted(loadConnections)
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="px-8 pt-8 pb-6 flex items-start justify-between">
      <div>
        <h1 class="font-display text-2xl font-bold tracking-tight" style="color: var(--foreground);">Connections</h1>
        <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">PII 스캔 대상 데이터베이스 연결을 관리합니다.</p>
      </div>
      <button class="btn-primary flex items-center gap-2" @click="openDrawer()">
        <Plus class="w-4 h-4" /> Add Connection
      </button>
    </div>

    <div class="flex-1 overflow-auto px-8 pb-8">
      <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div v-for="i in 3" :key="i" class="h-36 rounded-xl animate-pulse" style="background: var(--border);" />
      </div>

      <div v-else-if="connections.length === 0" class="flex flex-col items-center justify-center py-24 text-center">
        <div class="w-14 h-14 rounded-full flex items-center justify-center mb-4"
          style="background: var(--muted); border: 1px solid var(--border);">
          <ServerCrash class="w-6 h-6" style="color: var(--muted-foreground);" />
        </div>
        <h3 class="font-display font-semibold mb-1" style="color: var(--foreground);">연결된 DB가 없습니다</h3>
        <p class="text-[13px] max-w-xs mb-5" style="color: var(--muted-foreground);">Oracle, MySQL, MongoDB, ClickHouse 연결을 추가하고 PII 스캔을 시작하세요.</p>
        <button class="btn-primary flex items-center gap-2" @click="openDrawer()">
          <Plus class="w-4 h-4" /> Add Connection
        </button>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div v-for="conn in connections" :key="conn.id"
          class="conn-card relative rounded-xl border p-5 group"
          style="background: var(--card); border-color: var(--border);">
          <div class="flex items-start justify-between mb-4">
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold"
              :style="{ color: DB_TYPES[conn.db_type as DbType]?.color || 'var(--primary)', background: DB_TYPES[conn.db_type as DbType]?.bg || 'transparent' }">
              {{ conn.db_type.toUpperCase() }}
            </span>
            <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button class="icon-btn"
                :style="testStatus[conn.id] === 'ok' ? 'color: #16a34a' : testStatus[conn.id] === 'fail' ? 'color: #dc2626' : ''"
                title="Test connection" @click="testSavedConnection(conn.id)">
                <Loader2 v-if="testStatus[conn.id] === 'testing'" class="w-3.5 h-3.5 animate-spin" />
                <CheckCircle2 v-else-if="testStatus[conn.id] === 'ok'" class="w-3.5 h-3.5" />
                <XCircle v-else-if="testStatus[conn.id] === 'fail'" class="w-3.5 h-3.5" />
                <Zap v-else class="w-3.5 h-3.5" />
              </button>
              <button class="icon-btn" @click="openDrawer(conn)"><Edit2 class="w-3.5 h-3.5" /></button>
              <button class="icon-btn icon-btn-danger" @click="deleteConnection(conn.id)">
                <Loader2 v-if="deletingId === conn.id" class="w-3.5 h-3.5 animate-spin" />
                <Trash2 v-else class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
          <h3 class="font-display font-semibold text-[15px] mb-1 truncate" style="color: var(--foreground);">{{ conn.name }}</h3>
          <p class="text-[12px] font-mono truncate" style="color: var(--muted-foreground);">{{ conn.host }}:{{ conn.port }}</p>
          <p class="text-[12px] mt-0.5 truncate" style="color: var(--muted-foreground);">{{ conn.database || '전체 DB' }} · {{ conn.username }}</p>

          <!-- Info summary (when loaded) -->
          <div v-if="infoMap[conn.id]" class="mt-3 flex items-center gap-3">
            <span class="info-chip"><Database class="w-3 h-3" /> {{ infoMap[conn.id]!.schemas }} schemas</span>
            <span class="info-chip" style="color: var(--primary); background: color-mix(in oklch, var(--primary) 8%, transparent);">
              <Table2 class="w-3 h-3" /> {{ infoMap[conn.id]!.tables }} tables
            </span>
          </div>

          <!-- Info expand toggle -->
          <button v-if="infoMap[conn.id]" class="mt-2 flex items-center gap-1 text-[11px] transition-colors info-toggle"
            @click.stop="expandedInfo[conn.id] = !expandedInfo[conn.id]">
            <component :is="expandedInfo[conn.id] ? ChevronUp : ChevronDown" class="w-3 h-3" />
            {{ expandedInfo[conn.id] ? '접기' : '상세 보기' }}
          </button>

          <!-- Schema detail breakdown -->
          <div v-if="expandedInfo[conn.id] && infoMap[conn.id]" class="mt-2 space-y-1.5">
            <div v-for="s in infoMap[conn.id]!.schema_details" :key="s.schema"
              class="rounded-lg px-3 py-2" style="background: var(--background); border: 1px solid var(--border);">
              <div class="flex items-center justify-between mb-1">
                <span class="text-[11px] font-mono font-semibold" style="color: var(--foreground);">{{ s.schema }}</span>
                <span class="text-[10px]" style="color: var(--muted-foreground);">{{ s.tables }} tables</span>
              </div>
              <div class="flex flex-wrap gap-1">
                <span v-for="t in s.table_names" :key="t"
                  class="text-[10px] font-mono px-1.5 py-0.5 rounded"
                  style="background: var(--muted); color: var(--muted-foreground);">
                  {{ t }}
                </span>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-between mt-3">
            <p class="text-[11px]" style="color: var(--muted-foreground);">
              Added {{ new Date(conn.created_at).toLocaleDateString('ko-KR') }}
            </p>
            <button class="dryrun-btn flex items-center gap-1.5" @click.stop="toggleInfo(conn.id)">
              <Loader2 v-if="infoLoading[conn.id]" class="w-3 h-3 animate-spin" />
              <FlaskConical v-else class="w-3 h-3" />
              {{ infoLoading[conn.id] ? 'Scanning...' : infoMap[conn.id] ? 'Re-run' : 'Dry Run' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <Transition name="fade">
      <div v-if="drawerOpen" class="fixed inset-0 z-40" style="background: oklch(0.128 0.018 257 / 40%);" @click="closeDrawer" />
    </Transition>

    <Transition name="slide-right">
      <div v-if="drawerOpen" class="fixed right-0 top-0 h-full w-[480px] z-50 flex flex-col shadow-2xl"
        style="background: var(--card); border-left: 1px solid var(--border);" @click.stop>
        <div class="flex items-center justify-between px-6 py-5" style="border-bottom: 1px solid var(--border);">
          <div>
            <h2 class="font-display font-bold text-[17px]" style="color: var(--foreground);">{{ editingId ? 'Edit Connection' : 'New Connection' }}</h2>
            <p class="text-[12px] mt-0.5" style="color: var(--muted-foreground);">DB 연결 정보를 입력하세요.</p>
          </div>
          <button class="icon-btn" @click="closeDrawer"><X class="w-4 h-4" /></button>
        </div>

        <div class="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          <div>
            <label class="field-label">Database Type</label>
            <div class="grid grid-cols-2 gap-2">
              <button v-for="(meta, type) in DB_TYPES" :key="type"
                class="db-type-btn flex items-center gap-3 p-3 rounded-xl border text-left transition-all"
                :style="form.db_type === type
                  ? `border-color: ${meta.color}; background: ${meta.bg}; color: ${meta.color};`
                  : 'border-color: var(--border); color: var(--muted-foreground); background: var(--background);'"
                @click="selectDbType(type as DbType)">
                <div class="w-8 h-8 rounded-lg flex items-center justify-center"
                  :style="{ background: form.db_type === type ? meta.bg : 'var(--muted)' }">
                  <Database class="w-4 h-4" :style="{ color: form.db_type === type ? meta.color : 'var(--muted-foreground)' }" />
                </div>
                <div>
                  <div class="text-[13px] font-semibold">{{ meta.label }}</div>
                  <div class="text-[11px] opacity-60">:{{ meta.defaultPort }}</div>
                </div>
              </button>
            </div>
          </div>

          <div>
            <label class="field-label">Connection Name</label>
            <input v-model="form.name" type="text" placeholder="예: Production MySQL" class="field-input" />
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div class="col-span-2">
              <label class="field-label">Host / IP</label>
              <input v-model="form.host" type="text" placeholder="192.168.1.1" class="field-input" />
            </div>
            <div>
              <label class="field-label">Port</label>
              <input v-model="form.port" type="number" class="field-input text-right" />
            </div>
          </div>
          <div>
            <label class="field-label">
              {{ selectedDbMeta.dbLabel }}
              <span style="color: var(--muted-foreground); font-weight: 400;">(선택)</span>
            </label>
            <input v-model="form.database" type="text" :placeholder="selectedDbMeta.dbPlaceholder" class="field-input" />
            <p class="text-[11px] mt-1" style="color: var(--muted-foreground);">비우면 접근 가능한 전체 DB를 대상으로 스캔합니다.</p>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="field-label">Username</label>
              <input v-model="form.username" type="text" placeholder="root" class="field-input" />
            </div>
            <div>
              <label class="field-label">Password <span v-if="editingId" style="color: var(--muted-foreground); font-weight: 400;">(변경 시에만 입력)</span></label>
              <div class="relative">
                <input v-model="form.password" :type="showPassword ? 'text' : 'password'" :placeholder="editingId ? '변경하지 않으려면 비워두세요' : '••••••••'" class="field-input pr-10" />
                <button type="button" class="absolute right-3 top-1/2 -translate-y-1/2" style="color: var(--muted-foreground);" @click="showPassword = !showPassword">
                  <EyeOff v-if="showPassword" class="w-4 h-4" />
                  <Eye v-else class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          <Transition name="fade">
            <div v-if="testResult" class="flex items-start gap-2.5 p-3 rounded-xl border text-[13px]"
              :style="testResult.success ? 'background: #f0fdf4; border-color: #bbf7d0; color: #16a34a;' : 'background: #fef2f2; border-color: #fecaca; color: #dc2626;'">
              <CheckCircle2 v-if="testResult.success" class="w-4 h-4 mt-0.5 flex-shrink-0" />
              <XCircle v-else class="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{{ testResult.message }}</span>
            </div>
          </Transition>
          <p v-if="formError" class="text-[12px] flex items-center gap-1.5" style="color: #dc2626;">
            <XCircle class="w-3.5 h-3.5" /> {{ formError }}
          </p>
        </div>

        <div class="px-6 py-4 flex items-center gap-3" style="border-top: 1px solid var(--border);">
          <button class="btn-outline flex items-center gap-2" :disabled="testing" @click="testConnection">
            <Loader2 v-if="testing" class="w-4 h-4 animate-spin" />
            <Zap v-else class="w-4 h-4" /> Test
          </button>
          <div class="flex-1" />
          <button class="btn-ghost" @click="closeDrawer">Cancel</button>
          <button class="btn-primary flex items-center gap-2" :disabled="saving" @click="saveConnection">
            <Loader2 v-if="saving" class="w-4 h-4 animate-spin" />
            {{ editingId ? 'Update' : 'Save' }}
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.btn-primary {
  height: 36px; padding: 0 16px; border-radius: 9px;
  font-size: 13px; font-weight: 700;
  background: var(--primary); color: white;
  transition: opacity 0.15s;
}
.btn-primary:hover { opacity: 0.88; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-outline {
  height: 36px; padding: 0 14px; border-radius: 9px;
  font-size: 13px; font-weight: 600;
  border: 1px solid var(--border); color: var(--foreground);
  background: transparent; transition: border-color 0.12s;
}
.btn-outline:hover { border-color: var(--primary); }
.btn-outline:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-ghost {
  height: 36px; padding: 0 14px; border-radius: 9px;
  font-size: 13px; font-weight: 600;
  color: var(--muted-foreground); background: transparent;
  transition: background 0.12s;
}
.btn-ghost:hover { background: var(--muted); }

.icon-btn {
  width: 28px; height: 28px; border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  color: var(--muted-foreground); transition: background 0.12s, color 0.12s;
}
.icon-btn:hover { background: var(--muted); color: var(--foreground); }
.icon-btn-danger:hover { background: #fef2f2; color: #dc2626; }

.conn-card { transition: border-color 0.15s, box-shadow 0.15s; }
.conn-card:hover { border-color: var(--primary) !important; box-shadow: 0 2px 8px oklch(0.577 0.218 257 / 8%); }

.field-label { display: block; font-size: 12px; font-weight: 600; color: var(--foreground); margin-bottom: 6px; }
.field-input {
  width: 100%; height: 38px; padding: 0 12px;
  border-radius: 9px; border: 1px solid var(--border);
  background: var(--background); color: var(--foreground);
  font-size: 13px; outline: none; transition: border-color 0.15s, box-shadow 0.15s;
}
.field-input:focus {
  border-color: color-mix(in oklch, var(--primary) 60%, transparent);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 12%, transparent);
}
.field-input::placeholder { color: var(--muted-foreground); opacity: 0.6; }

.info-chip {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10px; font-weight: 600; font-family: var(--font-mono);
  padding: 2px 7px; border-radius: 20px;
  background: var(--muted); color: var(--muted-foreground);
}
.info-toggle {
  color: var(--muted-foreground);
}
.info-toggle:hover { color: var(--foreground); }

.dryrun-btn {
  font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 7px;
  color: var(--primary); border: 1px solid color-mix(in oklch, var(--primary) 35%, transparent);
  background: color-mix(in oklch, var(--primary) 6%, transparent);
  transition: border-color 0.12s, background 0.12s, opacity 0.12s;
}
.dryrun-btn:hover {
  background: color-mix(in oklch, var(--primary) 12%, transparent);
  border-color: var(--primary);
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.18s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-right-enter-active, .slide-right-leave-active { transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1); }
.slide-right-enter-from, .slide-right-leave-to { transform: translateX(100%); }
</style>
