<script setup lang="ts">
import {
  ScanSearch, Bell, Settings2, Info,
  ChevronRight,
  Slack, Mail, Database,
  Clock, Layers, Filter, Trash2,
  ShieldCheck, Lock, Server, Key, Loader2,
  Radio, BarChart2, Palette, Upload, X, ImageIcon,
  Globe, Copy, CheckCheck, AlertCircle, Users2, Check, Crown, Eye, UserCog, LogIn
} from 'lucide-vue-next'

type SettingKey = string
type SettingsMap = Record<SettingKey, string>

const activeSection = ref<'scanning' | 'notifications' | 'ldap' | 'sso' | 'kafka' | 'splunk' | 'branding' | 'database' | 'system' | 'rbac' | 'about'>('scanning')

const sections = [
  { id: 'scanning',      label: 'Scanning',        icon: ScanSearch,  description: 'PII detection config' },
  { id: 'notifications', label: 'Notifications',   icon: Bell,        description: 'Alerts & webhooks' },
  { id: 'ldap',          label: 'LDAP',            icon: ShieldCheck, description: 'Directory authentication' },
  { id: 'sso',           label: 'SSO / SAML',      icon: Globe,       description: 'Single Sign-On' },
  { id: 'kafka',         label: 'Kafka',           icon: Radio,       description: 'Event streaming' },
  { id: 'splunk',        label: 'Splunk / Syslog', icon: BarChart2,   description: 'Log forwarding' },
  { id: 'branding',      label: 'Branding',        icon: Palette,     description: 'Logo & app name' },
  { id: 'database',      label: 'Database',        icon: Database,    description: 'Storage backend' },
  { id: 'system',        label: 'System',          icon: Settings2,   description: 'Data & retention' },
  { id: 'rbac',          label: 'RBAC',            icon: Users2,      description: 'Role-based access control' },
  { id: 'about',         label: 'About',           icon: Info,        description: 'Version info' },
] as const

const { persona, isPersonaMode, enterPersona, exitPersona, ROLE_CONFIG } = usePersona()

const allMenus = [
  { key: 'dashboard',       label: 'Dashboard' },
  { key: 'connections',     label: 'Connections' },
  { key: 'scans',           label: 'Scans' },
  { key: 'rules',           label: 'Rules' },
  { key: 'classification',  label: 'Data Classification' },
  { key: 'reports',         label: 'Reports' },
  { key: 'deep-inspect',    label: 'Deep Inspect' },
  { key: 'audit-log',       label: 'Audit Log' },
  { key: 'users',           label: 'Users' },
  { key: 'settings',        label: 'Settings' },
]
const analystWrite = ['scans', 'rules']

const settings = ref<SettingsMap>({})
const loading = ref(false)
const saving = ref(false)
const saveStatus = ref<'idle' | 'success' | 'error'>('idle')
const saveError = ref('')

async function loadSettings() {
  loading.value = true
  try {
    const list = await $fetch<Array<{ key: string; value: string | null }>>('/api/settings')
    const map: SettingsMap = {}
    for (const s of list) map[s.key] = s.value ?? ''
    settings.value = map
  } finally {
    loading.value = false
  }
}

async function saveSection(keys: string[]) {
  saving.value = true
  saveStatus.value = 'idle'
  saveError.value = ''
  try {
    const payload: Record<string, string> = {}
    for (const k of keys) payload[k] = settings.value[k] ?? ''
    await $fetch('/api/settings/bulk', { method: 'POST', body: payload })
    saveStatus.value = 'success'
    setTimeout(() => { saveStatus.value = 'idle' }, 2500)
  } catch (e: unknown) {
    saveStatus.value = 'error'
    const err = e as { data?: { detail?: string } }
    saveError.value = err?.data?.detail ?? '저장 실패'
  } finally {
    saving.value = false
  }
}

const scanKeys = [
  'scan.default_sample_size',
  'scan.confidence_threshold',
  'scan.timeout_seconds',
  'scan.max_concurrent_tables',
  'scan.exclude_system_schemas',
]

const notifKeys = [
  'notification.slack_webhook_url',
  'notification.email_recipients',
  'notification.notify_on_scan_complete',
  'notification.notify_on_high_risk',
]

const systemKeys = [
  'system.data_retention_days',
  'system.max_scan_history',
]

const dbKeys = [
  'database.type',
  'database.mysql_host',
  'database.mysql_port',
  'database.mysql_database',
  'database.mysql_username',
  'database.mysql_password',
]

const ldapKeys = [
  'ldap.enabled',
  'ldap.host',
  'ldap.port',
  'ldap.use_ssl',
  'ldap.use_starttls',
  'ldap.base_dn',
  'ldap.bind_dn',
  'ldap.bind_password',
  'ldap.user_search_filter',
  'ldap.user_attr_username',
  'ldap.user_attr_email',
]

const ssoKeys = [
  'sso.enabled',
  'sso.provider',
  'sso.idp_entity_id',
  'sso.idp_sso_url',
  'sso.idp_slo_url',
  'sso.idp_certificate',
  'sso.sp_entity_id',
  'sso.name_id_format',
  'sso.attr_username',
  'sso.attr_email',
  'sso.attr_display_name',
  'sso.attr_role',
  'sso.auto_provision',
  'sso.default_role',
]

const copiedField = ref('')
async function copyToClipboard(text: string, field: string) {
  await navigator.clipboard.writeText(text)
  copiedField.value = field
  setTimeout(() => { copiedField.value = '' }, 2000)
}

const kafkaKeys = [
  'kafka.enabled',
  'kafka.brokers',
  'kafka.topic',
  'kafka.security_protocol',
  'kafka.sasl_mechanism',
  'kafka.sasl_username',
  'kafka.sasl_password',
  'kafka.ssl_ca_location',
  'kafka.client_id',
]

const splunkKeys = [
  'splunk.enabled',
  'splunk.mode',
  'splunk.hec_url',
  'splunk.hec_token',
  'splunk.hec_index',
  'splunk.hec_source',
  'splunk.syslog_host',
  'splunk.syslog_port',
  'splunk.syslog_protocol',
]

const brandingKeys = ['system.app_name', 'system.logo_data']
const { update: updateBranding } = useBranding()
const logoPreview = ref('')
const isDragOver = ref(false)

function initLogoPreview() {
  logoPreview.value = settings.value['system.logo_data'] ?? ''
}

function handleLogoFile(file: File) {
  if (!file.type.startsWith('image/')) return
  if (file.size > 512 * 1024) {
    alert('이미지 크기는 512KB 이하여야 합니다.')
    return
  }
  const reader = new FileReader()
  reader.onload = (e) => {
    const data = e.target?.result as string
    logoPreview.value = data
    settings.value['system.logo_data'] = data
  }
  reader.readAsDataURL(file)
}

function onFileInput(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) handleLogoFile(file)
}

function onDrop(e: DragEvent) {
  isDragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleLogoFile(file)
}

function clearLogo() {
  logoPreview.value = ''
  settings.value['system.logo_data'] = ''
}

async function saveBranding() {
  await saveSection(brandingKeys)
  updateBranding(settings.value['system.logo_data'] ?? '', settings.value['system.app_name'] ?? 'Sentinel')
}

// Keep logoPreview in sync when settings load
watch(() => settings.value['system.logo_data'], (v) => {
  if (v !== undefined) logoPreview.value = v
})

const kafkaTestStatus = ref<'idle' | 'testing' | 'ok' | 'fail'>('idle')
const kafkaTestMsg = ref('')
async function testKafka() {
  kafkaTestStatus.value = 'testing'
  kafkaTestMsg.value = ''
  try {
    await $fetch('/api/settings/kafka/test', { method: 'POST', body: {
      brokers: settings.value['kafka.brokers'],
      security_protocol: settings.value['kafka.security_protocol'],
      sasl_mechanism: settings.value['kafka.sasl_mechanism'],
      sasl_username: settings.value['kafka.sasl_username'],
      sasl_password: settings.value['kafka.sasl_password'],
    }})
    kafkaTestStatus.value = 'ok'
    kafkaTestMsg.value = 'Kafka 브로커에 성공적으로 연결되었습니다.'
  } catch (e: unknown) {
    kafkaTestStatus.value = 'fail'
    const err = e as { data?: { detail?: string } }
    kafkaTestMsg.value = err?.data?.detail ?? '연결에 실패했습니다.'
  }
  setTimeout(() => { kafkaTestStatus.value = 'idle'; kafkaTestMsg.value = '' }, 4000)
}

const splunkTestStatus = ref<'idle' | 'testing' | 'ok' | 'fail'>('idle')
const splunkTestMsg = ref('')
async function testSplunk() {
  splunkTestStatus.value = 'testing'
  splunkTestMsg.value = ''
  try {
    await $fetch('/api/settings/splunk/test', { method: 'POST', body: {
      mode: settings.value['splunk.mode'],
      hec_url: settings.value['splunk.hec_url'],
      hec_token: settings.value['splunk.hec_token'],
      syslog_host: settings.value['splunk.syslog_host'],
      syslog_port: Number(settings.value['splunk.syslog_port'] || 514),
      syslog_protocol: settings.value['splunk.syslog_protocol'],
    }})
    splunkTestStatus.value = 'ok'
    splunkTestMsg.value = '연결 테스트가 성공했습니다.'
  } catch (e: unknown) {
    splunkTestStatus.value = 'fail'
    const err = e as { data?: { detail?: string } }
    splunkTestMsg.value = err?.data?.detail ?? '연결에 실패했습니다.'
  }
  setTimeout(() => { splunkTestStatus.value = 'idle'; splunkTestMsg.value = '' }, 4000)
}

const ldapTestStatus = ref<'idle' | 'testing' | 'ok' | 'fail'>('idle')
const ldapTestMsg = ref('')
async function testLdap() {
  ldapTestStatus.value = 'testing'
  ldapTestMsg.value = ''
  try {
    await $fetch('/api/settings/ldap/test', { method: 'POST', body: {
      host: settings.value['ldap.host'],
      port: Number(settings.value['ldap.port'] || 389),
      use_ssl: settings.value['ldap.use_ssl'] === 'true',
      bind_dn: settings.value['ldap.bind_dn'],
      bind_password: settings.value['ldap.bind_password'],
    }})
    ldapTestStatus.value = 'ok'
    ldapTestMsg.value = 'LDAP 서버에 성공적으로 연결되었습니다.'
  } catch (e: unknown) {
    ldapTestStatus.value = 'fail'
    const err = e as { data?: { detail?: string } }
    ldapTestMsg.value = err?.data?.detail ?? '연결에 실패했습니다.'
  }
  setTimeout(() => { ldapTestStatus.value = 'idle'; ldapTestMsg.value = '' }, 4000)
}

onMounted(loadSettings)
</script>

<template>
  <div class="flex h-full min-h-0">

    <!-- Left: Section tabs -->
    <aside class="w-56 flex-shrink-0 p-4 space-y-1" style="border-right: 1px solid var(--border);">
      <p class="text-[10px] uppercase tracking-widest px-3 mb-3" style="color: var(--muted-foreground);">Settings</p>
      <button
        v-for="s in sections"
        :key="s.id"
        class="nav-btn w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150 text-left group"
        :class="activeSection === s.id ? 'nav-active' : 'nav-inactive'"
        @click="activeSection = s.id as typeof activeSection"
      >
        <component :is="s.icon" class="w-4 h-4 flex-shrink-0 transition-colors"
          :style="activeSection === s.id ? 'color: var(--primary);' : 'color: var(--muted-foreground);'" />
        <div class="flex-1 min-w-0">
          <div>{{ s.label }}</div>
          <div class="text-[11px] truncate mt-0.5" style="color: var(--muted-foreground);">{{ s.description }}</div>
        </div>
        <ChevronRight v-if="activeSection === s.id" class="w-3 h-3 flex-shrink-0" style="color: var(--primary);" />
      </button>
    </aside>

    <!-- Right: Form content -->
    <div class="flex-1 overflow-auto">
      <div class="max-w-2xl p-8">

        <!-- Loading skeleton -->
        <div v-if="loading" class="space-y-4">
          <div v-for="i in 4" :key="i" class="h-16 rounded-xl animate-pulse" style="background: var(--border);" />
        </div>

        <!-- SCANNING -->
        <template v-else-if="activeSection === 'scanning'">
          <div class="mb-8">
            <h2 class="text-xl font-bold tracking-tight" style="color: var(--foreground);">Scanning</h2>
            <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">PII 탐지 엔진의 동작 방식을 제어합니다.</p>
          </div>

          <div class="space-y-6">
            <!-- Sample Size -->
            <div class="flex items-center justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Layers class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>Sample Size</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">컬럼당 최대 샘플링 행 수. 높을수록 정확하지만 느림.</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <input v-model="settings['scan.default_sample_size']"
                  type="number" min="10" max="10000" step="10"
                  class="field-input w-32 text-right" />
                <span class="text-[12px]" style="color: var(--muted-foreground);">rows</span>
              </div>
            </div>

            <!-- Confidence Threshold -->
            <div class="flex items-center justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Filter class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>Confidence Threshold</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">이 값 이상인 탐지 결과만 저장. 범위: 0.0 ~ 1.0</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <input v-model="settings['scan.confidence_threshold']"
                  type="number" min="0" max="1" step="0.05"
                  class="field-input w-28 text-right" />
                <div class="w-24 h-1.5 rounded-full overflow-hidden" style="background: var(--border);">
                  <div class="h-full rounded-full transition-all" style="background: var(--primary);"
                    :style="`width: ${Math.min(100, Number(settings['scan.confidence_threshold'] ?? 0) * 100)}%`" />
                </div>
              </div>
            </div>

            <!-- Timeout -->
            <div class="flex items-center justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Clock class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>Query Timeout</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">DB 연결 및 쿼리의 최대 대기 시간.</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <input v-model="settings['scan.timeout_seconds']"
                  type="number" min="5" max="300" step="5"
                  class="field-input w-28 text-right" />
                <span class="text-[12px]" style="color: var(--muted-foreground);">seconds</span>
              </div>
            </div>

            <!-- Concurrent Tables -->
            <div class="flex items-center justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Database class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>Concurrent Tables</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">동시에 스캔할 최대 테이블 수. 높으면 부하 증가.</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <input v-model="settings['scan.max_concurrent_tables']"
                  type="number" min="1" max="20" step="1"
                  class="field-input w-28 text-right" />
                <span class="text-[12px]" style="color: var(--muted-foreground);">tables</span>
              </div>
            </div>

            <!-- Exclude System Schemas -->
            <div class="flex items-center justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Filter class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>Exclude System Schemas</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">information_schema, pg_catalog 등 시스템 스키마를 제외합니다.</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <button class="toggle-btn"
                  :class="settings['scan.exclude_system_schemas'] === 'true' ? 'toggle-on' : 'toggle-off'"
                  @click="settings['scan.exclude_system_schemas'] = settings['scan.exclude_system_schemas'] === 'true' ? 'false' : 'true'">
                  <span class="toggle-thumb"
                    :class="settings['scan.exclude_system_schemas'] === 'true' ? 'translate-x-5' : 'translate-x-1'" />
                </button>
                <span class="text-[12px]"
                  :style="settings['scan.exclude_system_schemas'] === 'true' ? 'color: var(--primary);' : 'color: var(--muted-foreground);'">
                  {{ settings['scan.exclude_system_schemas'] === 'true' ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
            </div>
          </div>

          <SettingsSaveBar :saving="saving" :status="saveStatus" :error="saveError" @save="saveSection(scanKeys)" />
        </template>

        <!-- NOTIFICATIONS -->
        <template v-else-if="activeSection === 'notifications'">
          <div class="mb-8">
            <h2 class="text-xl font-bold tracking-tight" style="color: var(--foreground);">Notifications</h2>
            <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">스캔 완료 및 PII 탐지 시 알림 채널을 설정합니다.</p>
          </div>

          <div class="space-y-6">
            <!-- Slack Webhook -->
            <div class="flex flex-col items-start gap-3">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Slack class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>Slack Webhook URL</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">Slack App의 Incoming Webhook URL을 입력하세요.</p>
              </div>
              <input v-model="settings['notification.slack_webhook_url']"
                type="url" placeholder="https://hooks.slack.com/services/..."
                class="field-input w-full font-mono text-[12px]" />
            </div>

            <!-- Email -->
            <div class="flex flex-col items-start gap-3">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Mail class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>Email Recipients</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">알림을 받을 이메일 주소. 쉼표로 여러 주소 입력 가능.</p>
              </div>
              <input v-model="settings['notification.email_recipients']"
                type="text" placeholder="admin@company.com, security@company.com"
                class="field-input w-full" />
            </div>

            <!-- Toggles -->
            <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border);">
              <div class="flex items-center justify-between gap-4 px-4 py-4" style="border-bottom: 1px solid var(--border);">
                <div class="flex-1 min-w-0">
                  <span class="text-[13px] font-medium" style="color: var(--foreground);">Notify on Scan Complete</span>
                  <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">스캔 작업이 완료되면 알림을 보냅니다.</p>
                </div>
                <button class="toggle-btn"
                  :class="settings['notification.notify_on_scan_complete'] === 'true' ? 'toggle-on' : 'toggle-off'"
                  @click="settings['notification.notify_on_scan_complete'] = settings['notification.notify_on_scan_complete'] === 'true' ? 'false' : 'true'">
                  <span class="toggle-thumb"
                    :class="settings['notification.notify_on_scan_complete'] === 'true' ? 'translate-x-5' : 'translate-x-1'" />
                </button>
              </div>
              <div class="flex items-center justify-between gap-4 px-4 py-4">
                <div class="flex-1 min-w-0">
                  <span class="text-[13px] font-medium" style="color: var(--foreground);">Notify on High Risk Detection</span>
                  <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">High Risk PII가 탐지되면 즉시 알림을 보냅니다.</p>
                </div>
                <button class="toggle-btn"
                  :class="settings['notification.notify_on_high_risk'] === 'true' ? 'toggle-on' : 'toggle-off'"
                  @click="settings['notification.notify_on_high_risk'] = settings['notification.notify_on_high_risk'] === 'true' ? 'false' : 'true'">
                  <span class="toggle-thumb"
                    :class="settings['notification.notify_on_high_risk'] === 'true' ? 'translate-x-5' : 'translate-x-1'" />
                </button>
              </div>
            </div>
          </div>

          <SettingsSaveBar :saving="saving" :status="saveStatus" :error="saveError" @save="saveSection(notifKeys)" />
        </template>

        <!-- LDAP -->
        <template v-else-if="activeSection === 'ldap'">
          <div class="mb-8">
            <h2 class="text-xl font-bold tracking-tight" style="color: var(--foreground);">LDAP Authentication</h2>
            <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">LDAP/Active Directory 디렉토리 서버를 통해 사용자 인증을 설정합니다.</p>
          </div>

          <div class="space-y-6">
            <!-- Enable toggle -->
            <div class="flex items-center justify-between gap-4 px-4 py-4 rounded-xl" style="border: 1px solid var(--border); background: var(--card);">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <ShieldCheck class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>LDAP 인증 활성화</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">활성화 시 로그인에 LDAP 디렉토리 서버를 사용합니다.</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <button class="toggle-btn"
                  :class="settings['ldap.enabled'] === 'true' ? 'toggle-on' : 'toggle-off'"
                  @click="settings['ldap.enabled'] = settings['ldap.enabled'] === 'true' ? 'false' : 'true'">
                  <span class="toggle-thumb"
                    :class="settings['ldap.enabled'] === 'true' ? 'translate-x-5' : 'translate-x-1'" />
                </button>
                <span class="text-[12px]"
                  :style="settings['ldap.enabled'] === 'true' ? 'color: var(--primary);' : 'color: var(--muted-foreground);'">
                  {{ settings['ldap.enabled'] === 'true' ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
            </div>

            <!-- Server connection -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3 flex items-center gap-2" style="color: var(--muted-foreground);">
                <Server class="w-3.5 h-3.5" /> 서버 연결
              </p>
              <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border);">
                <!-- Host + Port -->
                <div class="flex items-center gap-4 px-4 py-3.5" style="border-bottom: 1px solid var(--border);">
                  <div class="flex-1 min-w-0">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Host</label>
                    <input v-model="settings['ldap.host']"
                      type="text" placeholder="ldap.company.com"
                      class="field-input w-full font-mono text-[12px]" />
                  </div>
                  <div class="w-28 flex-shrink-0">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Port</label>
                    <input v-model="settings['ldap.port']"
                      type="number" placeholder="389"
                      class="field-input w-full text-right" />
                  </div>
                </div>
                <!-- SSL / StartTLS toggles -->
                <div class="flex items-center gap-6 px-4 py-3.5" style="border-bottom: 1px solid var(--border);">
                  <div class="flex items-center gap-2">
                    <button class="toggle-btn"
                      :class="settings['ldap.use_ssl'] === 'true' ? 'toggle-on' : 'toggle-off'"
                      @click="settings['ldap.use_ssl'] = settings['ldap.use_ssl'] === 'true' ? 'false' : 'true'">
                      <span class="toggle-thumb"
                        :class="settings['ldap.use_ssl'] === 'true' ? 'translate-x-5' : 'translate-x-1'" />
                    </button>
                    <span class="text-[12px] font-medium" style="color: var(--foreground);">SSL (LDAPS)</span>
                    <span class="text-[11px]" style="color: var(--muted-foreground);">— 포트 636</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <button class="toggle-btn"
                      :class="settings['ldap.use_starttls'] === 'true' ? 'toggle-on' : 'toggle-off'"
                      @click="settings['ldap.use_starttls'] = settings['ldap.use_starttls'] === 'true' ? 'false' : 'true'">
                      <span class="toggle-thumb"
                        :class="settings['ldap.use_starttls'] === 'true' ? 'translate-x-5' : 'translate-x-1'" />
                    </button>
                    <span class="text-[12px] font-medium" style="color: var(--foreground);">StartTLS</span>
                  </div>
                </div>
                <!-- Base DN -->
                <div class="px-4 py-3.5">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Base DN</label>
                  <input v-model="settings['ldap.base_dn']"
                    type="text" placeholder="dc=company,dc=com"
                    class="field-input w-full font-mono text-[12px]" />
                  <p class="text-[11px] mt-1" style="color: var(--muted-foreground);">사용자 검색의 루트 DN</p>
                </div>
              </div>
            </div>

            <!-- Bind credentials -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3 flex items-center gap-2" style="color: var(--muted-foreground);">
                <Key class="w-3.5 h-3.5" /> Bind 계정
              </p>
              <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border);">
                <div class="px-4 py-3.5" style="border-bottom: 1px solid var(--border);">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Bind DN</label>
                  <input v-model="settings['ldap.bind_dn']"
                    type="text" placeholder="cn=sentinel,ou=service,dc=company,dc=com"
                    class="field-input w-full font-mono text-[12px]" />
                  <p class="text-[11px] mt-1" style="color: var(--muted-foreground);">디렉토리 검색에 사용할 서비스 계정 DN</p>
                </div>
                <div class="px-4 py-3.5">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Bind Password</label>
                  <input v-model="settings['ldap.bind_password']"
                    type="password" placeholder="••••••••"
                    class="field-input w-full" />
                </div>
              </div>
            </div>

            <!-- User mapping -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3 flex items-center gap-2" style="color: var(--muted-foreground);">
                <Lock class="w-3.5 h-3.5" /> 사용자 매핑
              </p>
              <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border);">
                <div class="px-4 py-3.5" style="border-bottom: 1px solid var(--border);">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">User Search Filter</label>
                  <input v-model="settings['ldap.user_search_filter']"
                    type="text" placeholder="(sAMAccountName={username})"
                    class="field-input w-full font-mono text-[12px]" />
                  <p class="text-[11px] mt-1" style="color: var(--muted-foreground);">{username} 은 로그인 시 입력한 사용자명으로 대체됩니다.</p>
                </div>
                <div class="flex gap-4 px-4 py-3.5">
                  <div class="flex-1">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Username Attribute</label>
                    <input v-model="settings['ldap.user_attr_username']"
                      type="text" placeholder="sAMAccountName"
                      class="field-input w-full font-mono text-[12px]" />
                  </div>
                  <div class="flex-1">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Email Attribute</label>
                    <input v-model="settings['ldap.user_attr_email']"
                      type="text" placeholder="mail"
                      class="field-input w-full font-mono text-[12px]" />
                  </div>
                </div>
              </div>
            </div>

            <!-- Test connection result -->
            <div v-if="ldapTestStatus !== 'idle'" class="flex items-center gap-2 px-4 py-3 rounded-xl text-[13px]"
              :style="ldapTestStatus === 'ok' ? 'border:1px solid #bbf7d0; background:#f0fdf4; color:#16a34a;' :
                      ldapTestStatus === 'fail' ? 'border:1px solid #fecaca; background:#fef2f2; color:#dc2626;' :
                      'border:1px solid var(--border); background:var(--card); color:var(--muted-foreground);'">
              <Loader2 v-if="ldapTestStatus === 'testing'" class="w-4 h-4 animate-spin" />
              <ShieldCheck v-else-if="ldapTestStatus === 'ok'" class="w-4 h-4" />
              <span v-else class="w-4 h-4 text-center font-bold">✕</span>
              {{ ldapTestStatus === 'testing' ? 'LDAP 서버에 연결 중...' : ldapTestMsg }}
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-3 pt-2">
              <button @click="testLdap" :disabled="ldapTestStatus === 'testing'"
                class="flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-semibold transition-colors test-btn">
                <ShieldCheck class="w-3.5 h-3.5" />
                연결 테스트
              </button>
            </div>
          </div>

          <SettingsSaveBar :saving="saving" :status="saveStatus" :error="saveError" @save="saveSection(ldapKeys)" />
        </template>

        <!-- KAFKA -->
        <template v-else-if="activeSection === 'kafka'">
          <div class="mb-8">
            <h2 class="text-xl font-bold tracking-tight" style="color: var(--foreground);">Kafka Integration</h2>
            <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">PII 탐지 이벤트를 Kafka 토픽으로 스트리밍합니다.</p>
          </div>

          <div class="space-y-6">
            <!-- Enable -->
            <div class="flex items-center justify-between gap-4 px-4 py-4 rounded-xl" style="border: 1px solid var(--border); background: var(--card);">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Radio class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>Kafka 연동 활성화</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">활성화 시 스캔 완료·PII 탐지 이벤트를 Kafka로 발행합니다.</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <button class="toggle-btn"
                  :class="settings['kafka.enabled'] === 'true' ? 'toggle-on' : 'toggle-off'"
                  @click="settings['kafka.enabled'] = settings['kafka.enabled'] === 'true' ? 'false' : 'true'">
                  <span class="toggle-thumb"
                    :class="settings['kafka.enabled'] === 'true' ? 'translate-x-5' : 'translate-x-1'" />
                </button>
                <span class="text-[12px]"
                  :style="settings['kafka.enabled'] === 'true' ? 'color: var(--primary);' : 'color: var(--muted-foreground);'">
                  {{ settings['kafka.enabled'] === 'true' ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
            </div>

            <!-- Broker & Topic -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3 flex items-center gap-2" style="color: var(--muted-foreground);">
                <Server class="w-3.5 h-3.5" /> 브로커 연결
              </p>
              <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border);">
                <div class="px-4 py-3.5" style="border-bottom: 1px solid var(--border);">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Bootstrap Brokers</label>
                  <input v-model="settings['kafka.brokers']"
                    type="text" placeholder="broker1:9092,broker2:9092"
                    class="field-input w-full font-mono text-[12px]" />
                  <p class="text-[11px] mt-1" style="color: var(--muted-foreground);">쉼표로 여러 브로커를 입력할 수 있습니다.</p>
                </div>
                <div class="flex gap-4 px-4 py-3.5">
                  <div class="flex-1">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Topic</label>
                    <input v-model="settings['kafka.topic']"
                      type="text" placeholder="sentinel.pii-events"
                      class="field-input w-full font-mono text-[12px]" />
                  </div>
                  <div class="flex-1">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Client ID</label>
                    <input v-model="settings['kafka.client_id']"
                      type="text" placeholder="sentinel"
                      class="field-input w-full font-mono text-[12px]" />
                  </div>
                </div>
              </div>
            </div>

            <!-- Security -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3 flex items-center gap-2" style="color: var(--muted-foreground);">
                <Lock class="w-3.5 h-3.5" /> 보안 설정
              </p>
              <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border);">
                <div class="flex gap-4 px-4 py-3.5" style="border-bottom: 1px solid var(--border);">
                  <div class="flex-1">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Security Protocol</label>
                    <select v-model="settings['kafka.security_protocol']" class="field-input w-full">
                      <option value="PLAINTEXT">PLAINTEXT</option>
                      <option value="SSL">SSL</option>
                      <option value="SASL_PLAINTEXT">SASL_PLAINTEXT</option>
                      <option value="SASL_SSL">SASL_SSL</option>
                    </select>
                  </div>
                  <div class="flex-1">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">SASL Mechanism</label>
                    <select v-model="settings['kafka.sasl_mechanism']" class="field-input w-full">
                      <option value="">없음</option>
                      <option value="PLAIN">PLAIN</option>
                      <option value="SCRAM-SHA-256">SCRAM-SHA-256</option>
                      <option value="SCRAM-SHA-512">SCRAM-SHA-512</option>
                    </select>
                  </div>
                </div>
                <div class="flex gap-4 px-4 py-3.5" style="border-bottom: 1px solid var(--border);">
                  <div class="flex-1">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">SASL Username</label>
                    <input v-model="settings['kafka.sasl_username']"
                      type="text" placeholder="kafka-user"
                      class="field-input w-full font-mono text-[12px]" />
                  </div>
                  <div class="flex-1">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">SASL Password</label>
                    <input v-model="settings['kafka.sasl_password']"
                      type="password" placeholder="••••••••"
                      class="field-input w-full" />
                  </div>
                </div>
                <div class="px-4 py-3.5">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">SSL CA Certificate Path</label>
                  <input v-model="settings['kafka.ssl_ca_location']"
                    type="text" placeholder="/etc/ssl/certs/ca-certificates.crt"
                    class="field-input w-full font-mono text-[12px]" />
                  <p class="text-[11px] mt-1" style="color: var(--muted-foreground);">SSL 사용 시 CA 인증서 경로 (선택)</p>
                </div>
              </div>
            </div>

            <!-- Test result -->
            <div v-if="kafkaTestStatus !== 'idle'" class="flex items-center gap-2 px-4 py-3 rounded-xl text-[13px]"
              :style="kafkaTestStatus === 'ok' ? 'border:1px solid #bbf7d0; background:#f0fdf4; color:#16a34a;' :
                      kafkaTestStatus === 'fail' ? 'border:1px solid #fecaca; background:#fef2f2; color:#dc2626;' :
                      'border:1px solid var(--border); background:var(--card); color:var(--muted-foreground);'">
              <Loader2 v-if="kafkaTestStatus === 'testing'" class="w-4 h-4 animate-spin" />
              <Radio v-else-if="kafkaTestStatus === 'ok'" class="w-4 h-4" />
              <span v-else class="w-4 h-4 text-center font-bold">✕</span>
              {{ kafkaTestStatus === 'testing' ? 'Kafka 브로커에 연결 중...' : kafkaTestMsg }}
            </div>

            <div class="flex items-center gap-3 pt-2">
              <button @click="testKafka" :disabled="kafkaTestStatus === 'testing'"
                class="flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-semibold transition-colors test-btn">
                <Radio class="w-3.5 h-3.5" />
                연결 테스트
              </button>
            </div>
          </div>

          <SettingsSaveBar :saving="saving" :status="saveStatus" :error="saveError" @save="saveSection(kafkaKeys)" />
        </template>

        <!-- SPLUNK / SYSLOG -->
        <template v-else-if="activeSection === 'splunk'">
          <div class="mb-8">
            <h2 class="text-xl font-bold tracking-tight" style="color: var(--foreground);">Splunk / Syslog</h2>
            <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">PII 탐지 로그를 Splunk HEC 또는 Syslog 서버로 전송합니다.</p>
          </div>

          <div class="space-y-6">
            <!-- Enable -->
            <div class="flex items-center justify-between gap-4 px-4 py-4 rounded-xl" style="border: 1px solid var(--border); background: var(--card);">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <BarChart2 class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>로그 포워딩 활성화</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">활성화 시 감사 이벤트를 Splunk / Syslog로 전송합니다.</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <button class="toggle-btn"
                  :class="settings['splunk.enabled'] === 'true' ? 'toggle-on' : 'toggle-off'"
                  @click="settings['splunk.enabled'] = settings['splunk.enabled'] === 'true' ? 'false' : 'true'">
                  <span class="toggle-thumb"
                    :class="settings['splunk.enabled'] === 'true' ? 'translate-x-5' : 'translate-x-1'" />
                </button>
                <span class="text-[12px]"
                  :style="settings['splunk.enabled'] === 'true' ? 'color: var(--primary);' : 'color: var(--muted-foreground);'">
                  {{ settings['splunk.enabled'] === 'true' ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
            </div>

            <!-- Mode selector -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3" style="color: var(--muted-foreground);">전송 방식</p>
              <div class="flex gap-3">
                <button
                  v-for="mode in [{ value: 'hec', label: 'Splunk HEC', sub: 'HTTP Event Collector' }, { value: 'syslog', label: 'Syslog', sub: 'RFC 5424 / UDP / TCP' }]"
                  :key="mode.value"
                  @click="settings['splunk.mode'] = mode.value"
                  class="flex-1 px-4 py-3 rounded-xl text-left transition-all"
                  :style="settings['splunk.mode'] === mode.value
                    ? 'border: 1.5px solid var(--primary); background: color-mix(in oklch, var(--primary) 6%, transparent);'
                    : 'border: 1px solid var(--border); background: var(--card);'">
                  <p class="text-[13px] font-semibold" :style="settings['splunk.mode'] === mode.value ? 'color: var(--primary);' : 'color: var(--foreground);'">
                    {{ mode.label }}
                  </p>
                  <p class="text-[11px] mt-0.5" style="color: var(--muted-foreground);">{{ mode.sub }}</p>
                </button>
              </div>
            </div>

            <!-- Splunk HEC settings -->
            <div v-if="settings['splunk.mode'] !== 'syslog'">
              <p class="text-[11px] uppercase tracking-widest mb-3 flex items-center gap-2" style="color: var(--muted-foreground);">
                <Server class="w-3.5 h-3.5" /> Splunk HEC
              </p>
              <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border);">
                <div class="px-4 py-3.5" style="border-bottom: 1px solid var(--border);">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">HEC URL</label>
                  <input v-model="settings['splunk.hec_url']"
                    type="url" placeholder="https://splunk.company.com:8088/services/collector"
                    class="field-input w-full font-mono text-[12px]" />
                </div>
                <div class="px-4 py-3.5" style="border-bottom: 1px solid var(--border);">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">HEC Token</label>
                  <input v-model="settings['splunk.hec_token']"
                    type="password" placeholder="••••••••-••••-••••-••••-••••••••••••"
                    class="field-input w-full font-mono text-[12px]" />
                </div>
                <div class="flex gap-4 px-4 py-3.5">
                  <div class="flex-1">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Index</label>
                    <input v-model="settings['splunk.hec_index']"
                      type="text" placeholder="sentinel"
                      class="field-input w-full font-mono text-[12px]" />
                  </div>
                  <div class="flex-1">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Source</label>
                    <input v-model="settings['splunk.hec_source']"
                      type="text" placeholder="sentinel:pii"
                      class="field-input w-full font-mono text-[12px]" />
                  </div>
                </div>
              </div>
            </div>

            <!-- Syslog settings -->
            <div v-if="settings['splunk.mode'] === 'syslog'">
              <p class="text-[11px] uppercase tracking-widest mb-3 flex items-center gap-2" style="color: var(--muted-foreground);">
                <Server class="w-3.5 h-3.5" /> Syslog 서버
              </p>
              <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border);">
                <div class="flex items-end gap-4 px-4 py-3.5" style="border-bottom: 1px solid var(--border);">
                  <div class="flex-1">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Host</label>
                    <input v-model="settings['splunk.syslog_host']"
                      type="text" placeholder="syslog.company.com"
                      class="field-input w-full font-mono text-[12px]" />
                  </div>
                  <div class="w-28 flex-shrink-0">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Port</label>
                    <input v-model="settings['splunk.syslog_port']"
                      type="number" placeholder="514"
                      class="field-input w-full text-right" />
                  </div>
                  <div class="w-28 flex-shrink-0">
                    <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">Protocol</label>
                    <select v-model="settings['splunk.syslog_protocol']" class="field-input w-full">
                      <option value="UDP">UDP</option>
                      <option value="TCP">TCP</option>
                      <option value="TLS">TLS</option>
                    </select>
                  </div>
                </div>
                <div class="px-4 py-3 flex items-start gap-2">
                  <Info class="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style="color: var(--muted-foreground);" />
                  <p class="text-[11px]" style="color: var(--muted-foreground);">RFC 5424 포맷으로 전송됩니다. Splunk Universal Forwarder에서 수신하도록 설정하세요.</p>
                </div>
              </div>
            </div>

            <!-- Test result -->
            <div v-if="splunkTestStatus !== 'idle'" class="flex items-center gap-2 px-4 py-3 rounded-xl text-[13px]"
              :style="splunkTestStatus === 'ok' ? 'border:1px solid #bbf7d0; background:#f0fdf4; color:#16a34a;' :
                      splunkTestStatus === 'fail' ? 'border:1px solid #fecaca; background:#fef2f2; color:#dc2626;' :
                      'border:1px solid var(--border); background:var(--card); color:var(--muted-foreground);'">
              <Loader2 v-if="splunkTestStatus === 'testing'" class="w-4 h-4 animate-spin" />
              <BarChart2 v-else-if="splunkTestStatus === 'ok'" class="w-4 h-4" />
              <span v-else class="w-4 h-4 text-center font-bold">✕</span>
              {{ splunkTestStatus === 'testing' ? '연결 테스트 중...' : splunkTestMsg }}
            </div>

            <div class="flex items-center gap-3 pt-2">
              <button @click="testSplunk" :disabled="splunkTestStatus === 'testing'"
                class="flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-semibold transition-colors test-btn">
                <BarChart2 class="w-3.5 h-3.5" />
                연결 테스트
              </button>
            </div>
          </div>

          <SettingsSaveBar :saving="saving" :status="saveStatus" :error="saveError" @save="saveSection(splunkKeys)" />
        </template>

        <!-- BRANDING -->
        <template v-else-if="activeSection === 'branding'">
          <div class="mb-8">
            <h2 class="text-xl font-bold tracking-tight" style="color: var(--foreground);">Branding</h2>
            <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">사이드바에 표시되는 로고와 앱 이름을 커스터마이즈합니다.</p>
          </div>

          <div class="space-y-6">
            <!-- App Name -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3 flex items-center gap-2" style="color: var(--muted-foreground);">
                <Palette class="w-3.5 h-3.5" /> 앱 이름
              </p>
              <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border);">
                <div class="px-4 py-3.5">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">표시 이름</label>
                  <input v-model="settings['system.app_name']"
                    type="text" placeholder="Sentinel"
                    class="field-input w-full text-[14px] font-semibold" />
                  <p class="text-[11px] mt-1.5" style="color: var(--muted-foreground);">사이드바 상단과 브레드크럼에 표시됩니다.</p>
                </div>
              </div>
            </div>

            <!-- Logo Upload -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3 flex items-center gap-2" style="color: var(--muted-foreground);">
                <ImageIcon class="w-3.5 h-3.5" /> 로고 이미지
              </p>

              <!-- Current preview + clear -->
              <div v-if="logoPreview" class="flex items-start gap-4 mb-4">
                <div class="w-16 h-16 rounded-xl flex items-center justify-center overflow-hidden flex-shrink-0"
                  style="border: 1px solid var(--border); background: var(--background);">
                  <img :src="logoPreview" alt="logo preview" class="w-full h-full object-contain" />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-[13px] font-semibold" style="color: var(--foreground);">현재 로고</p>
                  <p class="text-[11px] mt-0.5" style="color: var(--muted-foreground);">사이드바에 이 이미지가 표시됩니다.</p>
                  <button @click="clearLogo"
                    class="mt-2 flex items-center gap-1.5 text-[12px] font-semibold px-3 py-1 rounded-lg transition-colors"
                    style="color: #dc2626; border: 1px solid #fecaca;"
                    onmouseover="this.style.background='#fef2f2'" onmouseout="this.style.background=''">
                    <X class="w-3 h-3" /> 로고 제거
                  </button>
                </div>
              </div>

              <!-- Drop zone -->
              <label
                class="drop-zone flex flex-col items-center justify-center gap-3 cursor-pointer rounded-xl transition-all"
                :class="isDragOver ? 'drop-zone-active' : ''"
                @dragover.prevent="isDragOver = true"
                @dragleave="isDragOver = false"
                @drop.prevent="onDrop">
                <input type="file" accept="image/*" class="hidden" @change="onFileInput" />
                <div class="w-10 h-10 rounded-xl flex items-center justify-center"
                  :style="isDragOver ? 'background: color-mix(in oklch, var(--primary) 15%, transparent);' : 'background: var(--border);'">
                  <Upload class="w-5 h-5"
                    :style="isDragOver ? 'color: var(--primary);' : 'color: var(--muted-foreground);'" />
                </div>
                <div class="text-center">
                  <p class="text-[13px] font-semibold" style="color: var(--foreground);">
                    {{ logoPreview ? '새 로고로 교체' : '로고 업로드' }}
                  </p>
                  <p class="text-[12px] mt-0.5" style="color: var(--muted-foreground);">클릭하거나 드래그하여 업로드 · PNG, JPG, SVG · 최대 512KB</p>
                </div>
              </label>
            </div>

            <!-- Live preview -->
            <div v-if="logoPreview || settings['system.app_name']">
              <p class="text-[11px] uppercase tracking-widest mb-3" style="color: var(--muted-foreground);">사이드바 미리보기</p>
              <div class="rounded-xl overflow-hidden inline-flex items-center gap-2.5 px-4 py-3"
                style="border: 1px solid var(--border); background: var(--sidebar);">
                <img v-if="logoPreview" :src="logoPreview" alt="logo"
                  class="w-7 h-7 rounded-lg object-contain flex-shrink-0"
                  style="background: var(--primary);" />
                <div v-else class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                  style="background: var(--primary);">
                  <ShieldCheck class="w-3.5 h-3.5" style="color: white;" />
                </div>
                <span class="font-display font-bold text-[15px]" style="color: var(--foreground); letter-spacing: -0.03em;">
                  {{ settings['system.app_name'] || 'Sentinel' }}
                </span>
              </div>
            </div>
          </div>

          <SettingsSaveBar :saving="saving" :status="saveStatus" :error="saveError" @save="saveBranding" />
        </template>

        <!-- DATABASE -->
        <template v-else-if="activeSection === 'database'">
          <div class="mb-8">
            <h2 class="text-xl font-bold tracking-tight" style="color: var(--foreground);">Database</h2>
            <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">스토리지 백엔드를 설정합니다. 현재 개발 환경에서는 SQLite를 사용합니다.</p>
          </div>

          <div class="space-y-6">
            <!-- DB Type selector -->
            <div>
              <div class="text-[13px] font-medium mb-3" style="color: var(--foreground);">Storage Backend</div>
              <div class="flex gap-3">
                <label v-for="opt in [{ value: 'sqlite', label: 'SQLite', desc: '개발 환경 권장' }, { value: 'mysql', label: 'MySQL', desc: '프로덕션 배포용' }]"
                  :key="opt.value"
                  class="flex-1 flex items-start gap-3 p-4 rounded-xl cursor-pointer transition-all"
                  :style="settings['database.type'] === opt.value
                    ? 'border: 1.5px solid var(--primary); background: color-mix(in oklch, var(--primary) 5%, transparent);'
                    : 'border: 1px solid var(--border); background: var(--card);'">
                  <input type="radio" :value="opt.value" v-model="settings['database.type']" class="mt-0.5 accent-[var(--primary)]" />
                  <div>
                    <div class="text-[13px] font-semibold" style="color: var(--foreground);">{{ opt.label }}</div>
                    <div class="text-[11px] mt-0.5" style="color: var(--muted-foreground);">{{ opt.desc }}</div>
                  </div>
                </label>
              </div>
            </div>

            <!-- MySQL fields (shown when MySQL selected) -->
            <template v-if="settings['database.type'] === 'mysql'">
              <div class="rounded-xl p-5 space-y-4" style="border: 1px solid var(--border); background: var(--card);">
                <div class="text-[12px] font-semibold uppercase tracking-widest mb-1" style="color: var(--muted-foreground);">MySQL Connection</div>
                <div class="grid grid-cols-3 gap-4">
                  <div class="col-span-2">
                    <label class="field-label">Host</label>
                    <input v-model="settings['database.mysql_host']" type="text" placeholder="localhost" class="field-input w-full" />
                  </div>
                  <div>
                    <label class="field-label">Port</label>
                    <input v-model="settings['database.mysql_port']" type="number" placeholder="3306" class="field-input w-full" />
                  </div>
                </div>
                <div>
                  <label class="field-label">Database Name</label>
                  <input v-model="settings['database.mysql_database']" type="text" placeholder="sentinel" class="field-input w-full" />
                </div>
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="field-label">Username</label>
                    <input v-model="settings['database.mysql_username']" type="text" placeholder="sentinel_user" class="field-input w-full" />
                  </div>
                  <div>
                    <label class="field-label">Password</label>
                    <input v-model="settings['database.mysql_password']" type="password" placeholder="••••••••" class="field-input w-full" />
                  </div>
                </div>
              </div>
            </template>

            <!-- Dev note -->
            <div class="flex items-start gap-3 p-4 rounded-xl" style="background: #fffbeb; border: 1px solid #fde68a;">
              <span class="text-[14px] mt-0.5">⚠️</span>
              <p class="text-[12px] leading-relaxed" style="color: #92400e;">
                현재 개발 환경에서는 SQLite를 사용합니다. MySQL 설정은 프로덕션 배포 시 백엔드 환경변수(<code class="font-mono bg-amber-100 px-1 rounded">DATABASE_URL</code>)에 반영되어 적용됩니다.
              </p>
            </div>
          </div>

          <SettingsSaveBar :saving="saving" :status="saveStatus" :error="saveError" @save="saveSection(dbKeys)" />
        </template>

        <!-- SYSTEM -->
        <template v-else-if="activeSection === 'system'">
          <div class="mb-8">
            <h2 class="text-xl font-bold tracking-tight" style="color: var(--foreground);">System</h2>
            <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">데이터 보관 정책 및 시스템 리소스를 설정합니다.</p>
          </div>

          <div class="space-y-6">
            <div class="flex items-center justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Clock class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>Data Retention</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">스캔 결과를 보관할 기간. 이후 자동 삭제.</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <input v-model="settings['system.data_retention_days']"
                  type="number" min="7" max="3650" step="1"
                  class="field-input w-28 text-right" />
                <span class="text-[12px]" style="color: var(--muted-foreground);">days</span>
              </div>
            </div>

            <div class="flex items-center justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Layers class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>Max Scan History</span>
                </div>
                <p class="text-[12px] mt-0.5 leading-relaxed" style="color: var(--muted-foreground);">보관할 최대 스캔 이력 수. 초과 시 오래된 순으로 삭제.</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <input v-model="settings['system.max_scan_history']"
                  type="number" min="10" max="10000" step="10"
                  class="field-input w-28 text-right" />
                <span class="text-[12px]" style="color: var(--muted-foreground);">records</span>
              </div>
            </div>

            <!-- Danger Zone -->
            <div class="mt-10">
              <div class="flex items-center gap-2 mb-4">
                <div class="h-px flex-1" style="background: #fecaca;" />
                <span class="text-[11px] uppercase tracking-widest" style="color: #ef4444; opacity: 0.7;">Danger Zone</span>
                <div class="h-px flex-1" style="background: #fecaca;" />
              </div>
              <div class="rounded-xl p-4" style="border: 1px solid #fecaca;">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="text-[13px] font-medium flex items-center gap-2" style="color: var(--foreground);">
                      <Trash2 class="w-4 h-4" style="color: #dc2626;" />
                      Reset All Settings
                    </p>
                    <p class="text-[12px] mt-1" style="color: var(--muted-foreground);">모든 설정을 기본값으로 초기화합니다. 이 작업은 되돌릴 수 없습니다.</p>
                  </div>
                  <button class="flex-shrink-0 px-3 py-1.5 rounded-lg text-[12px] transition-colors"
                    style="border: 1px solid #fecaca; color: #dc2626;"
                    onmouseover="this.style.background='#fef2f2'" onmouseout="this.style.background=''">
                    Reset
                  </button>
                </div>
              </div>
            </div>
          </div>

          <SettingsSaveBar :saving="saving" :status="saveStatus" :error="saveError" @save="saveSection(systemKeys)" />
        </template>

        <!-- SSO / SAML -->
        <template v-else-if="activeSection === 'sso'">
          <div class="mb-8">
            <h2 class="text-xl font-bold tracking-tight" style="color: var(--foreground);">SSO / SAML 2.0</h2>
            <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">SAML 2.0 기반 싱글 사인온(SSO)을 구성합니다. IdP 메타데이터를 등록하여 연동을 활성화하세요.</p>
          </div>

          <div class="space-y-6">
            <!-- Enable -->
            <div class="flex items-center justify-between gap-4 px-4 py-4 rounded-xl" style="border: 1px solid var(--border); background: var(--card);">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Globe class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>SSO 활성화</span>
                </div>
                <p class="text-[12px] mt-0.5" style="color: var(--muted-foreground);">활성화 시 로그인 페이지에 SSO 버튼이 표시됩니다.</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <button class="toggle-btn"
                  :class="settings['sso.enabled'] === 'true' ? 'toggle-on' : 'toggle-off'"
                  @click="settings['sso.enabled'] = settings['sso.enabled'] === 'true' ? 'false' : 'true'">
                  <span class="toggle-thumb" :class="settings['sso.enabled'] === 'true' ? 'translate-x-5' : 'translate-x-1'" />
                </button>
                <span class="text-[12px]" :style="settings['sso.enabled'] === 'true' ? 'color: var(--primary);' : 'color: var(--muted-foreground);'">
                  {{ settings['sso.enabled'] === 'true' ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
            </div>

            <!-- Provider type -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3" style="color: var(--muted-foreground);">프로토콜</p>
              <div class="flex gap-3">
                <button
                  v-for="p in [{ value: 'saml2', label: 'SAML 2.0', sub: 'Okta, Azure AD, ADFS' }, { value: 'oidc', label: 'OIDC', sub: 'Google, Keycloak' }]"
                  :key="p.value"
                  @click="settings['sso.provider'] = p.value"
                  class="flex-1 px-4 py-3 rounded-xl text-left transition-all"
                  :style="settings['sso.provider'] === p.value
                    ? 'border: 1.5px solid var(--primary); background: color-mix(in oklch, var(--primary) 6%, transparent);'
                    : 'border: 1px solid var(--border); background: var(--card);'">
                  <p class="text-[13px] font-semibold" :style="settings['sso.provider'] === p.value ? 'color: var(--primary);' : 'color: var(--foreground);'">{{ p.label }}</p>
                  <p class="text-[11px] mt-0.5" style="color: var(--muted-foreground);">{{ p.sub }}</p>
                </button>
              </div>
            </div>

            <!-- SP Info (read-only) -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3" style="color: var(--muted-foreground);">서비스 프로바이더 (SP) 정보</p>
              <div class="rounded-xl overflow-hidden divide-y" style="border: 1px solid var(--border); background: var(--card);">
                <div v-for="spField in [
                  { label: 'SP Entity ID', key: 'sp_entity_id', value: 'https://sentinel.internal/saml/metadata' },
                  { label: 'ACS URL', key: 'acs_url', value: 'https://sentinel.internal/saml/acs' },
                  { label: 'SLO URL (SP)', key: 'slo_url', value: 'https://sentinel.internal/saml/slo' },
                ]" :key="spField.key" class="flex items-center justify-between gap-3 px-4 py-3">
                  <div class="min-w-0">
                    <p class="text-[11px] font-medium mb-0.5" style="color: var(--muted-foreground);">{{ spField.label }}</p>
                    <p class="text-[12px] font-mono truncate" style="color: var(--foreground);">{{ spField.value }}</p>
                  </div>
                  <button
                    @click="copyToClipboard(spField.value, spField.key)"
                    class="flex-shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-colors"
                    style="border: 1px solid var(--border); color: var(--muted-foreground);"
                    :style="copiedField === spField.key ? 'color: var(--primary); border-color: var(--primary);' : ''"
                  >
                    <CheckCheck v-if="copiedField === spField.key" class="w-3 h-3" />
                    <Copy v-else class="w-3 h-3" />
                    {{ copiedField === spField.key ? 'Copied' : 'Copy' }}
                  </button>
                </div>
              </div>
              <p class="text-[11px] mt-2 flex items-center gap-1" style="color: var(--muted-foreground);">
                <AlertCircle class="w-3 h-3" />
                IdP 설정 시 위 URL을 등록하세요.
              </p>
            </div>

            <!-- IdP config -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3" style="color: var(--muted-foreground);">아이덴티티 프로바이더 (IdP) 설정</p>
              <div class="rounded-xl overflow-hidden divide-y" style="border: 1px solid var(--border); background: var(--card);">
                <div class="px-4 py-3">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">IdP Entity ID</label>
                  <input v-model="settings['sso.idp_entity_id']" type="text"
                    placeholder="https://idp.example.com/saml/metadata"
                    class="field-input w-full font-mono text-[12px]" />
                </div>
                <div class="px-4 py-3">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">SSO URL <span class="font-normal" style="color: var(--muted-foreground);">(IdP redirect)</span></label>
                  <input v-model="settings['sso.idp_sso_url']" type="text"
                    placeholder="https://idp.example.com/saml/sso"
                    class="field-input w-full font-mono text-[12px]" />
                </div>
                <div class="px-4 py-3">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">SLO URL <span class="font-normal" style="color: var(--muted-foreground);">(선택, Single Logout)</span></label>
                  <input v-model="settings['sso.idp_slo_url']" type="text"
                    placeholder="https://idp.example.com/saml/slo"
                    class="field-input w-full font-mono text-[12px]" />
                </div>
                <div class="px-4 py-3">
                  <label class="text-[12px] font-medium block mb-1" style="color: var(--foreground);">IdP X.509 인증서 <span class="font-normal" style="color: var(--muted-foreground);">(PEM 형식)</span></label>
                  <textarea v-model="settings['sso.idp_certificate']"
                    placeholder="-----BEGIN CERTIFICATE-----&#10;MIICxDCCAaygAwIBAgIGAXXXXXXXXX...&#10;-----END CERTIFICATE-----"
                    rows="6"
                    class="w-full px-3 py-2 rounded-lg text-[11px] font-mono resize-none"
                    style="border: 1px solid var(--border); background: var(--background); color: var(--foreground); outline: none; transition: border-color 0.12s;"
                    onfocus="this.style.borderColor='var(--primary)'"
                    onblur="this.style.borderColor='var(--border)'"
                  />
                </div>
              </div>
            </div>

            <!-- Name ID format -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3" style="color: var(--muted-foreground);">Name ID 포맷</p>
              <div class="flex gap-2 flex-wrap">
                <button
                  v-for="fmt in [
                    { value: 'emailAddress', label: 'Email Address' },
                    { value: 'unspecified', label: 'Unspecified' },
                    { value: 'transient', label: 'Transient' },
                    { value: 'persistent', label: 'Persistent' },
                  ]"
                  :key="fmt.value"
                  @click="settings['sso.name_id_format'] = fmt.value"
                  class="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all"
                  :style="settings['sso.name_id_format'] === fmt.value
                    ? 'background: color-mix(in oklch, var(--primary) 10%, transparent); color: var(--primary); border: 1.5px solid var(--primary);'
                    : 'border: 1px solid var(--border); color: var(--muted-foreground); background: var(--card);'"
                >{{ fmt.label }}</button>
              </div>
            </div>

            <!-- Attribute mappings -->
            <div>
              <p class="text-[11px] uppercase tracking-widest mb-3" style="color: var(--muted-foreground);">속성 매핑</p>
              <div class="rounded-xl overflow-hidden divide-y" style="border: 1px solid var(--border); background: var(--card);">
                <div v-for="attr in [
                  { key: 'sso.attr_username', label: 'Username', placeholder: 'uid' },
                  { key: 'sso.attr_email', label: 'Email', placeholder: 'mail' },
                  { key: 'sso.attr_display_name', label: 'Display Name', placeholder: 'displayName' },
                  { key: 'sso.attr_role', label: 'Role', placeholder: 'memberOf' },
                ]" :key="attr.key" class="flex items-center gap-3 px-4 py-2.5">
                  <span class="w-28 text-[12px] flex-shrink-0" style="color: var(--muted-foreground);">{{ attr.label }}</span>
                  <span class="text-[12px]" style="color: var(--border);">→</span>
                  <input v-model="settings[attr.key]" type="text" :placeholder="attr.placeholder"
                    class="flex-1 field-input font-mono text-[12px]" />
                </div>
              </div>
            </div>

            <!-- Auto-provision -->
            <div class="flex items-center justify-between gap-4 px-4 py-4 rounded-xl" style="border: 1px solid var(--border); background: var(--card);">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13px] font-medium" style="color: var(--foreground);">
                  <Key class="w-4 h-4" style="color: var(--muted-foreground);" />
                  <span>자동 계정 생성 (Auto-provision)</span>
                </div>
                <p class="text-[12px] mt-0.5" style="color: var(--muted-foreground);">최초 SSO 로그인 시 사용자 계정을 자동으로 생성합니다.</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <button class="toggle-btn"
                  :class="settings['sso.auto_provision'] === 'true' ? 'toggle-on' : 'toggle-off'"
                  @click="settings['sso.auto_provision'] = settings['sso.auto_provision'] === 'true' ? 'false' : 'true'">
                  <span class="toggle-thumb" :class="settings['sso.auto_provision'] === 'true' ? 'translate-x-5' : 'translate-x-1'" />
                </button>
                <span class="text-[12px]" :style="settings['sso.auto_provision'] === 'true' ? 'color: var(--primary);' : 'color: var(--muted-foreground);'">
                  {{ settings['sso.auto_provision'] === 'true' ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
            </div>

            <!-- Default role -->
            <div class="px-4 py-3 rounded-xl" style="border: 1px solid var(--border); background: var(--card);">
              <label class="text-[12px] font-medium block mb-1.5" style="color: var(--foreground);">신규 사용자 기본 권한</label>
              <div class="flex gap-2">
                <button
                  v-for="role in [{ value: 'viewer', label: 'Viewer' }, { value: 'analyst', label: 'Analyst' }, { value: 'admin', label: 'Admin' }]"
                  :key="role.value"
                  @click="settings['sso.default_role'] = role.value"
                  class="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all"
                  :style="settings['sso.default_role'] === role.value
                    ? 'background: color-mix(in oklch, var(--primary) 10%, transparent); color: var(--primary); border: 1.5px solid var(--primary);'
                    : 'border: 1px solid var(--border); color: var(--muted-foreground); background: var(--background);'"
                >{{ role.label }}</button>
              </div>
              <p class="text-[11px] mt-2" style="color: var(--muted-foreground);">Auto-provision 시 새 사용자에게 부여할 권한</p>
            </div>
          </div>

          <SettingsSaveBar :saving="saving" :status="saveStatus" :error="saveError" @save="saveSection(ssoKeys)" />
        </template>

        <!-- RBAC -->
        <template v-else-if="activeSection === 'rbac'">
          <div class="mb-8">
            <h2 class="text-[18px] font-bold mb-1" style="color: var(--foreground);">Role-Based Access Control</h2>
            <p class="text-[13px]" style="color: var(--muted-foreground);">역할별 메뉴 및 기능 접근 권한을 정의합니다.</p>
          </div>

          <!-- Persona Mode Active Banner -->
          <div v-if="isPersonaMode" class="rounded-xl px-4 py-3 flex items-center gap-3 mb-2"
            :style="{ background: ROLE_CONFIG[persona].bg, border: `1px solid ${ROLE_CONFIG[persona].color}40` }">
            <UserCog class="w-4 h-4 flex-shrink-0" :style="{ color: ROLE_CONFIG[persona].color }" />
            <span class="text-[13px] font-semibold" :style="{ color: ROLE_CONFIG[persona].color }">
              현재 <strong>{{ ROLE_CONFIG[persona].label }}</strong> Persona 모드로 테스트 중
            </span>
            <button @click="exitPersona"
              class="ml-auto text-[11px] font-bold px-3 py-1 rounded-lg transition-opacity hover:opacity-70"
              :style="{ background: ROLE_CONFIG[persona].color, color: 'white' }">
              Admin으로 복귀
            </button>
          </div>

          <div class="space-y-4">
            <!-- Admin -->
            <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border); background: var(--card);">
              <div class="px-5 py-4 flex items-center gap-3" style="border-bottom: 1px solid var(--border); background: color-mix(in oklch, #7c3aed 4%, transparent);">
                <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background: #7c3aed20;">
                  <Crown class="w-4 h-4" style="color: #7c3aed;" />
                </div>
                <div>
                  <p class="text-[14px] font-bold" style="color: var(--foreground);">Admin</p>
                  <p class="text-[12px]" style="color: var(--muted-foreground);">모든 메뉴 접근 및 전체 권한</p>
                </div>
                <span class="ml-auto text-[11px] font-semibold px-2.5 py-1 rounded-full" style="background: #7c3aed20; color: #7c3aed;">Full Access</span>
              </div>
              <div class="px-5 py-4">
                <div class="grid grid-cols-2 gap-2">
                  <div v-for="item in allMenus" :key="item.key" class="flex items-center gap-2 text-[13px]" style="color: var(--foreground);">
                    <Check class="w-3.5 h-3.5 flex-shrink-0" style="color: #16a34a;" />
                    <span>{{ item.label }}</span>
                    <span class="text-[11px] ml-auto" style="color: var(--muted-foreground);">읽기 + 쓰기</span>
                  </div>
                </div>
                <div class="mt-3 pt-3" style="border-top: 1px solid var(--border);">
                  <span class="text-[12px]" style="color: var(--muted-foreground);">현재 로그인된 역할입니다.</span>
                </div>
              </div>
            </div>

            <!-- Analyst -->
            <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border); background: var(--card);">
              <div class="px-5 py-4 flex items-center gap-3" style="border-bottom: 1px solid var(--border); background: color-mix(in oklch, #2563eb 4%, transparent);">
                <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background: #2563eb20;">
                  <Users2 class="w-4 h-4" style="color: #2563eb;" />
                </div>
                <div>
                  <p class="text-[14px] font-bold" style="color: var(--foreground);">Analyst</p>
                  <p class="text-[12px]" style="color: var(--muted-foreground);">스캔 및 규칙 편집 가능, 나머지 읽기 전용</p>
                </div>
                <span class="ml-auto text-[11px] font-semibold px-2.5 py-1 rounded-full" style="background: #2563eb20; color: #2563eb;">Limited Write</span>
              </div>
              <div class="px-5 py-4">
                <div class="grid grid-cols-2 gap-2">
                  <div v-for="item in allMenus" :key="item.key" class="flex items-center gap-2 text-[13px]" style="color: var(--foreground);">
                    <Check v-if="analystWrite.includes(item.key)" class="w-3.5 h-3.5 flex-shrink-0" style="color: #16a34a;" />
                    <Eye v-else class="w-3.5 h-3.5 flex-shrink-0" style="color: #6b7280;" />
                    <span>{{ item.label }}</span>
                    <span class="text-[11px] ml-auto" :style="{ color: analystWrite.includes(item.key) ? '#16a34a' : '#6b7280' }">
                      {{ analystWrite.includes(item.key) ? '읽기 + 쓰기' : '읽기 전용' }}
                    </span>
                  </div>
                </div>
                <div class="mt-3 pt-3 flex items-center justify-between" style="border-top: 1px solid var(--border);">
                  <span class="text-[12px]" style="color: var(--muted-foreground);">이 역할로 UI를 테스트합니다.</span>
                  <button
                    @click="persona === 'analyst' ? exitPersona() : enterPersona('analyst')"
                    class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-all"
                    :style="persona === 'analyst'
                      ? 'background: #2563eb; color: white;'
                      : 'background: #2563eb20; color: #2563eb; border: 1px solid #2563eb40;'">
                    <LogIn class="w-3 h-3" />
                    {{ persona === 'analyst' ? 'Persona 종료' : 'Analyst로 테스트' }}
                  </button>
                </div>
              </div>
            </div>

            <!-- Viewer -->
            <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border); background: var(--card);">
              <div class="px-5 py-4 flex items-center gap-3" style="border-bottom: 1px solid var(--border); background: color-mix(in oklch, #6b7280 4%, transparent);">
                <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background: #6b728020;">
                  <Eye class="w-4 h-4" style="color: #6b7280;" />
                </div>
                <div>
                  <p class="text-[14px] font-bold" style="color: var(--foreground);">Viewer</p>
                  <p class="text-[12px]" style="color: var(--muted-foreground);">모든 메뉴 읽기 전용, 수정 불가</p>
                </div>
                <span class="ml-auto text-[11px] font-semibold px-2.5 py-1 rounded-full" style="background: #6b728020; color: #6b7280;">Read Only</span>
              </div>
              <div class="px-5 py-4">
                <div class="grid grid-cols-2 gap-2">
                  <div v-for="item in allMenus" :key="item.key" class="flex items-center gap-2 text-[13px]" style="color: var(--foreground);">
                    <Eye class="w-3.5 h-3.5 flex-shrink-0" style="color: #6b7280;" />
                    <span>{{ item.label }}</span>
                    <span class="text-[11px] ml-auto" style="color: #6b7280;">읽기 전용</span>
                  </div>
                </div>
                <div class="mt-3 pt-3 flex items-center justify-between" style="border-top: 1px solid var(--border);">
                  <span class="text-[12px]" style="color: var(--muted-foreground);">이 역할로 UI를 테스트합니다.</span>
                  <button
                    @click="persona === 'viewer' ? exitPersona() : enterPersona('viewer')"
                    class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-all"
                    :style="persona === 'viewer'
                      ? 'background: #6b7280; color: white;'
                      : 'background: #6b728020; color: #6b7280; border: 1px solid #6b728040;'">
                    <LogIn class="w-3 h-3" />
                    {{ persona === 'viewer' ? 'Persona 종료' : 'Viewer로 테스트' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- ABOUT -->
        <template v-else-if="activeSection === 'about'">
          <div class="mb-8">
            <h2 class="text-xl font-bold tracking-tight" style="color: var(--foreground);">About Sentinel</h2>
            <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">시스템 정보 및 버전</p>
          </div>

          <div class="space-y-3">
            <div v-for="item in [
              { label: 'Version', value: '0.1.0' },
              { label: 'Frontend', value: 'Nuxt 4 + Vue 3 + Tailwind v4' },
              { label: 'Backend', value: 'Python FastAPI + SQLAlchemy' },
              { label: 'Database', value: 'SQLite (sentinel.db)' },
              { label: 'Supported DBs', value: 'MySQL · Oracle · MongoDB · ClickHouse' },
              { label: 'PII Rules', value: '10 built-in (Korean + Universal)' },
            ]" :key="item.label"
              class="flex items-center justify-between px-4 py-3 rounded-xl"
              style="border: 1px solid var(--border); background: var(--card);">
              <span class="text-[12px]" style="color: var(--muted-foreground);">{{ item.label }}</span>
              <span class="text-[13px] font-mono" style="color: var(--foreground);">{{ item.value }}</span>
            </div>
          </div>

          <div class="mt-8 p-4 rounded-xl" style="border: 1px solid color-mix(in oklch, var(--primary) 25%, transparent); background: color-mix(in oklch, var(--primary) 5%, transparent);">
            <p class="text-[12px]" style="color: var(--primary);">
              Sentinel은 데이터베이스 내 개인정보(PII)를 탐지하는 내부 보안 도구입니다.
              개인정보보호법(PIPA) 컴플라이언스를 위한 PII 인벤토리 구축에 활용하세요.
            </p>
          </div>
        </template>

      </div>
    </div>
  </div>
</template>

<style scoped>
.nav-btn { border-radius: 8px; border: 1px solid transparent; }
.nav-active {
  background: color-mix(in oklch, var(--primary) 8%, transparent);
  border-color: color-mix(in oklch, var(--primary) 20%, transparent);
  color: var(--primary);
}
.nav-inactive { color: var(--muted-foreground); }
.nav-inactive:hover {
  background: var(--muted);
  color: var(--foreground);
}

.field-input {
  height: 32px; padding: 0 10px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--background);
  color: var(--foreground); font-size: 13px; outline: none;
  transition: border-color 0.12s;
}
.field-input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 12%, transparent);
}
.field-input::placeholder { color: var(--muted-foreground); }

.toggle-btn {
  position: relative; display: inline-flex;
  height: 22px; width: 40px;
  align-items: center; border-radius: 9999px;
  transition: background 0.2s; focus: outline-none;
}
.toggle-on  { background: var(--primary); }
.toggle-off { background: var(--border); }
.toggle-thumb {
  display: inline-block; height: 16px; width: 16px;
  border-radius: 9999px; background: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: transform 0.15s;
}

.test-btn {
  border: 1px solid var(--border); background: var(--card);
  color: var(--foreground);
}
.test-btn:hover:not(:disabled) {
  border-color: var(--primary);
  background: color-mix(in oklch, var(--primary) 5%, transparent);
  color: var(--primary);
}
.test-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.drop-zone {
  border: 2px dashed var(--border);
  background: var(--background);
  padding: 32px 24px;
  transition: border-color 0.15s, background 0.15s;
}
.drop-zone:hover {
  border-color: var(--primary);
  background: color-mix(in oklch, var(--primary) 4%, transparent);
}
.drop-zone-active {
  border-color: var(--primary) !important;
  background: color-mix(in oklch, var(--primary) 8%, transparent) !important;
}
</style>
