<script setup lang="ts">
import {
  Plus, ShieldCheck, Trash2, X, XCircle, Loader2, Lock,
  ToggleLeft, ToggleRight, FlaskConical, CheckCircle2, AlertCircle
} from 'lucide-vue-next'

interface Rule {
  id: number; name: string; pii_type: string; detection_method: string
  column_patterns: string | null; data_patterns: string | null
  is_builtin: boolean; is_active: boolean; created_at: string
}

interface RegexResult { pattern: string; matches: string[]; valid: boolean; error?: string }

const rules = ref<Rule[]>([])
const loading = ref(false)
const modalOpen = ref(false)
const saving = ref(false)
const formError = ref('')
const deletingId = ref<number | null>(null)
const togglingId = ref<number | null>(null)
const isCreating = ref(false)
const editingId = ref<number | null>(null)

const form = ref({
  name: '', pii_type: '', detection_method: 'both',
  column_patterns: '', data_patterns: '', is_active: true
})

// ── Regex tester ─────────────────────────────────────────────
const regexInput = ref('')
const regexResults = ref<RegexResult[]>([])
const tested = ref(false)

const SAMPLES_BY_PII: Record<string, string> = {
  email:          `hong.gildong@company.co.kr\ntest.user@example.com\nadmin@sentinel.internal\nuser123@naver.com\ninfo@test.org`,
  phone:          `010-1234-5678\n010-9876-5432\n02-3456-7890\n031-123-4567\n010 8765 4321`,
  resident_id:    `901201-1234567\n850515-2876543\n001115-3456789\n720303-1234567`,
  credit_card:    `4532-1234-5678-9012\n5412 7534 1234 5678\n372348 123456789\n4111111111111111`,
  account_number: `110-234-567890\n352-0012-3456-78\n123456-01-123456\n020-12-345678`,
  passport:       `M12345678\nAB1234567\nM98765432\nC12345678`,
  driver_license: `11-22-334455-66\n06-08-123456-78\n12-34-567890-12`,
  ip_address:     `192.168.1.100\n10.0.0.1\n172.16.254.3\n255.255.255.0\n8.8.8.8`,
  name:           `홍길동\n김철수\n이영희\n박민준\nJohn Doe`,
  birth_date:     `1990-01-15\n1985/05/22\n2000.11.30\n19901015`,
  password:       `P@ssw0rd!\nqwerty123\nsecret$2024\nAbcd1234!`,
  ssn:            `123-45-6789\n987-65-4321\n000-12-3456`,
  address:        `서울시 강남구 테헤란로 123\n경기도 성남시 분당구 판교역로 235\n부산시 해운대구 해운대로 10`,
}
const SAMPLE_FALLBACK = `홍길동 (hong@company.co.kr)\n010-1234-5678\n901201-1234567\n4532-1234-5678-9012\n110-234-567890`

function insertSample() {
  regexInput.value = SAMPLES_BY_PII[form.value.pii_type] ?? SAMPLE_FALLBACK
}

function runRegexTest() {
  const raw = form.value.data_patterns.trim()
  if (!raw) return
  const patterns = raw.split('\n').map(s => s.trim()).filter(Boolean)
  regexResults.value = patterns.map(pattern => {
    try {
      const regex = new RegExp(pattern, 'g')
      const matches = [...regexInput.value.matchAll(regex)].map(m => m[0])
      return { pattern, matches, valid: true }
    } catch {
      return { pattern, matches: [], valid: false, error: '유효하지 않은 정규식' }
    }
  })
  tested.value = true
}

// ── Helpers ───────────────────────────────────────────────────
const PII_TYPES = [
  'email','phone','resident_id','name','address','birth_date',
  'credit_card','account_number','passport','driver_license','password','ssn','ip_address'
]
const methodLabel: Record<string, string> = {
  column_name: '컬럼명만', regex: '정규식만', both: '둘 다'
}
const piiColor: Record<string, string> = {
  email: '#2563eb', phone: '#16a34a', resident_id: '#dc2626',
  credit_card: '#7c3aed', name: '#d97706', address: '#ea580c',
  password: '#b91c1c', account_number: '#db2777', passport: '#0891b2',
  driver_license: '#0d9488', ssn: '#9333ea', ip_address: '#4f46e5',
}

function parseColPatterns(json: string | null): string {
  if (!json) return ''
  try { const a = JSON.parse(json); return Array.isArray(a) ? a.join(', ') : json }
  catch { return json }
}
function parseDataPatterns(json: string | null): string {
  if (!json) return ''
  try { const a = JSON.parse(json); return Array.isArray(a) ? a.join('\n') : json }
  catch { return json }
}

// ── Data ──────────────────────────────────────────────────────
async function loadRules() {
  loading.value = true
  try { rules.value = await $fetch<Rule[]>('/api/rules') }
  finally { loading.value = false }
}

async function toggleActive(rule: Rule) {
  togglingId.value = rule.id
  try {
    await $fetch(`/api/rules/${rule.id}`, { method: 'PUT', body: { is_active: !rule.is_active } })
    rule.is_active = !rule.is_active
  } finally { togglingId.value = null }
}

async function deleteRule(id: number) {
  deletingId.value = id
  try {
    await $fetch(`/api/rules/${id}`, { method: 'DELETE' })
    rules.value = rules.value.filter(r => r.id !== id)
  } finally { deletingId.value = null }
}

async function saveRule() {
  if (!form.value.name || !form.value.pii_type) {
    formError.value = '이름과 PII 유형은 필수입니다.'
    return
  }
  saving.value = true; formError.value = ''
  const colPatterns = form.value.column_patterns.split(',').map(s => s.trim()).filter(Boolean)
  const dataPatterns = form.value.data_patterns.split('\n').map(s => s.trim()).filter(Boolean)
  try {
    if (isCreating.value) {
      await $fetch('/api/rules', {
        method: 'POST',
        body: { name: form.value.name, pii_type: form.value.pii_type,
          detection_method: form.value.detection_method,
          column_patterns: colPatterns, data_patterns: dataPatterns,
          is_active: form.value.is_active }
      })
    } else {
      await $fetch(`/api/rules/${editingId.value}`, {
        method: 'PUT',
        body: { name: form.value.name, pii_type: form.value.pii_type,
          detection_method: form.value.detection_method,
          column_patterns: colPatterns, data_patterns: dataPatterns,
          is_active: form.value.is_active }
      })
    }
    modalOpen.value = false
    await loadRules()
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    formError.value = err?.data?.detail ?? '저장 실패'
  } finally { saving.value = false }
}

function openCreate() {
  isCreating.value = true; editingId.value = null
  form.value = { name: '', pii_type: '', detection_method: 'both',
    column_patterns: '', data_patterns: '', is_active: true }
  formError.value = ''; regexInput.value = ''; regexResults.value = []; tested.value = false
  modalOpen.value = true
}

function openEdit(rule: Rule) {
  isCreating.value = false; editingId.value = rule.id
  form.value = {
    name: rule.name, pii_type: rule.pii_type,
    detection_method: rule.detection_method,
    column_patterns: parseColPatterns(rule.column_patterns),
    data_patterns: parseDataPatterns(rule.data_patterns),
    is_active: rule.is_active
  }
  formError.value = ''; regexInput.value = ''; regexResults.value = []; tested.value = false
  modalOpen.value = true
}

const builtinRules = computed(() => rules.value.filter(r => r.is_builtin))
const customRules = computed(() => rules.value.filter(r => !r.is_builtin))
const showDataPatterns = computed(() => ['regex', 'both'].includes(form.value.detection_method))
const showColPatterns = computed(() => ['column_name', 'both'].includes(form.value.detection_method))

onMounted(loadRules)
</script>

<template>
  <div class="h-full flex flex-col">

    <!-- Header -->
    <div class="px-8 pt-8 pb-6 flex items-start justify-between">
      <div>
        <h1 class="font-display text-2xl font-bold tracking-tight" style="color: var(--foreground);">Rules</h1>
        <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">PII 탐지 규칙을 관리합니다. 내장 규칙도 패턴을 수정할 수 있습니다.</p>
      </div>
      <button @click="openCreate" class="btn-primary flex items-center gap-2">
        <Plus class="w-4 h-4" /> New Rule
      </button>
    </div>

    <div class="flex-1 overflow-auto px-8 pb-8 space-y-8">

      <!-- Built-in rules -->
      <div>
        <h2 class="section-title flex items-center gap-2 mb-3">
          <Lock class="w-3 h-3" /> BUILT-IN RULES ({{ builtinRules.length }})
        </h2>
        <div class="rule-card">
          <div v-for="(rule, i) in builtinRules" :key="rule.id"
            class="rule-row group cursor-pointer"
            :class="i > 0 ? 'border-t' : ''"
            style="border-color: var(--border);"
            @click="openEdit(rule)">
            <!-- Left: status icon -->
            <ShieldCheck class="w-4 h-4 flex-shrink-0"
              :style="{ color: rule.is_active ? '#16a34a' : 'var(--muted-foreground)' }" />
            <!-- Middle: info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[13px] font-semibold" style="color: var(--foreground);">{{ rule.name }}</span>
                <span class="badge-builtin">builtin</span>
                <span class="badge-pii" :style="{ color: piiColor[rule.pii_type] || 'var(--primary)', background: (piiColor[rule.pii_type] || 'var(--primary)') + '14' }">
                  {{ rule.pii_type }}
                </span>
              </div>
              <div class="text-[11px] mt-0.5" style="color: var(--muted-foreground);">
                {{ methodLabel[rule.detection_method] }}
              </div>
            </div>
            <!-- Right: actions -->
            <div class="flex items-center gap-1" @click.stop>
              <button @click="toggleActive(rule)" :disabled="togglingId === rule.id"
                class="icon-btn" :title="rule.is_active ? '비활성화' : '활성화'">
                <Loader2 v-if="togglingId === rule.id" class="w-3.5 h-3.5 animate-spin" />
                <ToggleRight v-else-if="rule.is_active" class="w-4 h-4" style="color: #16a34a;" />
                <ToggleLeft v-else class="w-4 h-4" style="color: var(--muted-foreground);" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Custom rules -->
      <div>
        <h2 class="section-title mb-3">CUSTOM RULES ({{ customRules.length }})</h2>
        <div v-if="customRules.length === 0"
          class="rounded-xl border-2 border-dashed p-10 text-center"
          style="border-color: var(--border);">
          <p class="text-[13px]" style="color: var(--muted-foreground);">
            커스텀 규칙이 없습니다.
            <button @click="openCreate" class="font-semibold hover:underline" style="color: var(--primary);">새 규칙을 추가</button>하세요.
          </p>
        </div>
        <div v-else class="rule-card">
          <div v-for="(rule, i) in customRules" :key="rule.id"
            class="rule-row group cursor-pointer"
            :class="i > 0 ? 'border-t' : ''"
            style="border-color: var(--border);"
            @click="openEdit(rule)">
            <ShieldCheck class="w-4 h-4 flex-shrink-0"
              :style="{ color: rule.is_active ? 'var(--primary)' : 'var(--muted-foreground)' }" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[13px] font-semibold" style="color: var(--foreground);">{{ rule.name }}</span>
                <span class="badge-pii" :style="{ color: piiColor[rule.pii_type] || 'var(--primary)', background: (piiColor[rule.pii_type] || 'var(--primary)') + '14' }">
                  {{ rule.pii_type }}
                </span>
              </div>
              <div class="text-[11px] mt-0.5" style="color: var(--muted-foreground);">
                {{ methodLabel[rule.detection_method] }}
              </div>
            </div>
            <div class="flex items-center gap-1" @click.stop>
              <button @click="toggleActive(rule)" :disabled="togglingId === rule.id" class="icon-btn">
                <Loader2 v-if="togglingId === rule.id" class="w-3.5 h-3.5 animate-spin" />
                <ToggleRight v-else-if="rule.is_active" class="w-4 h-4" style="color: #16a34a;" />
                <ToggleLeft v-else class="w-4 h-4" style="color: var(--muted-foreground);" />
              </button>
              <button @click="deleteRule(rule.id)" :disabled="deletingId === rule.id"
                class="icon-btn hover:!text-red-500" style="color: var(--muted-foreground);" title="삭제">
                <Loader2 v-if="deletingId === rule.id" class="w-3.5 h-3.5 animate-spin" />
                <Trash2 v-else class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Modal backdrop ── -->
    <Transition name="fade">
      <div v-if="modalOpen" class="fixed inset-0 z-40 flex items-center justify-center p-4"
        style="background: oklch(0.128 0.018 257 / 40%); backdrop-filter: blur(2px);"
        @click.self="modalOpen = false">

        <!-- Modal panel -->
        <div class="modal-panel w-full max-w-[520px] flex flex-col max-h-[90vh]"
          @click.stop>
          <!-- Modal header -->
          <div class="flex items-center justify-between px-6 py-5" style="border-bottom: 1px solid var(--border);">
            <div>
              <h2 class="font-display font-bold text-[17px]" style="color: var(--foreground); letter-spacing: -0.02em;">
                {{ isCreating ? 'New Rule' : '규칙 편집' }}
              </h2>
              <p v-if="!isCreating" class="text-[12px] mt-0.5" style="color: var(--muted-foreground);">
                builtin 규칙도 패턴 수정이 가능합니다.
              </p>
            </div>
            <button @click="modalOpen = false" class="icon-btn">
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- Modal body -->
          <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">

            <!-- Name -->
            <div>
              <label class="field-label">Rule Name *</label>
              <input v-model="form.name" class="field-input" placeholder="예: Korean Phone Number" />
            </div>

            <!-- PII Type -->
            <div>
              <label class="field-label">PII Type *</label>
              <select v-model="form.pii_type" class="field-input">
                <option value="" disabled>선택하세요</option>
                <option v-for="t in PII_TYPES" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>

            <!-- Detection Method -->
            <div>
              <label class="field-label">Detection Method</label>
              <div class="flex gap-2">
                <button v-for="m in ['column_name','regex','both']" :key="m"
                  @click="form.detection_method = m"
                  class="flex-1 py-2 rounded-lg border text-[12px] font-semibold transition-all"
                  :style="form.detection_method === m
                    ? 'border-color: var(--primary); background: color-mix(in oklch, var(--primary) 8%, transparent); color: var(--primary-active);'
                    : 'border-color: var(--border); color: var(--muted-foreground); background: transparent;'">
                  {{ methodLabel[m] }}
                </button>
              </div>
            </div>

            <!-- Column patterns -->
            <div v-if="showColPatterns">
              <label class="field-label">컬럼명 패턴 <span style="color: var(--muted-foreground); font-weight: 400;">(쉼표로 구분)</span></label>
              <input v-model="form.column_patterns" class="field-input" placeholder="email, e_mail, 이메일, email_addr" />
            </div>

            <!-- Data patterns (regex) -->
            <div v-if="showDataPatterns">
              <label class="field-label">정규식 패턴 <span style="color: var(--muted-foreground); font-weight: 400;">(줄바꿈으로 구분)</span></label>
              <textarea v-model="form.data_patterns" class="field-input field-textarea"
                placeholder="[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}&#10;다른 패턴..." />

              <!-- Regex Tester -->
              <div class="regex-tester mt-3">
                <div class="flex items-center gap-2 mb-3">
                  <FlaskConical class="w-3.5 h-3.5" style="color: var(--primary);" />
                  <span class="text-[12px] font-semibold" style="color: var(--foreground);">정규식 테스터</span>
                </div>
                <textarea v-model="regexInput" class="field-input field-textarea"
                  placeholder="테스트할 샘플 데이터를 입력하세요&#10;예: 홍길동의 이메일은 hong@example.com 입니다." />
                <div class="mt-2 flex items-center gap-2">
                  <button @click="runRegexTest"
                    class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-colors"
                    style="background: color-mix(in oklch, var(--primary) 10%, transparent); color: var(--primary-active); border: 1px solid color-mix(in oklch, var(--primary) 20%, transparent);">
                    <FlaskConical class="w-3.5 h-3.5" /> 테스트 실행
                  </button>
                  <button @click="insertSample"
                    class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-colors"
                    style="color: var(--muted-foreground); border: 1px solid var(--border); background: var(--background);">
                    샘플 데이터 삽입
                  </button>
                </div>

                <!-- Test Results -->
                <div v-if="tested" class="mt-3 space-y-2">
                  <!-- Summary banner -->
                  <div class="flex items-center gap-2 px-3 py-2 rounded-lg text-[12px] font-semibold"
                    :style="regexResults.some(r => r.matches.length > 0)
                      ? 'background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0;'
                      : 'background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca;'">
                    <CheckCircle2 v-if="regexResults.some(r => r.matches.length > 0)" class="w-3.5 h-3.5 flex-shrink-0" />
                    <AlertCircle v-else class="w-3.5 h-3.5 flex-shrink-0" />
                    <span v-if="regexResults.some(r => r.matches.length > 0)">
                      테스트 통과 — {{ regexResults.reduce((s, r) => s + r.matches.length, 0) }}건 매칭됨
                    </span>
                    <span v-else>테스트 실패 — 패턴과 일치하는 데이터 없음</span>
                  </div>
                  <!-- Per-pattern detail -->
                  <div v-for="r in regexResults" :key="r.pattern" class="regex-result-row">
                    <div class="flex items-center gap-2">
                      <code class="pattern-code flex-1">{{ r.pattern }}</code>
                      <span v-if="r.valid && r.matches.length > 0" class="text-[10px] font-bold px-1.5 py-0.5 rounded" style="background: #f0fdf4; color: #15803d;">PASS</span>
                      <span v-else-if="r.valid" class="text-[10px] font-bold px-1.5 py-0.5 rounded" style="background: #fef2f2; color: #b91c1c;">FAIL</span>
                      <span v-else class="text-[10px] font-bold px-1.5 py-0.5 rounded" style="background: #fef9c3; color: #a16207;">ERROR</span>
                    </div>
                    <div v-if="!r.valid" class="result-error">
                      <AlertCircle class="w-3 h-3 flex-shrink-0" /> {{ r.error }}
                    </div>
                    <div v-else-if="r.matches.length === 0" class="result-none">
                      일치 없음
                    </div>
                    <div v-else class="result-matches">
                      <CheckCircle2 class="w-3 h-3 flex-shrink-0 mt-0.5" style="color: #16a34a;" />
                      <div class="flex flex-wrap gap-1">
                        <span v-for="m in r.matches" :key="m" class="match-chip">{{ m }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Active toggle -->
            <div class="flex items-center justify-between py-1">
              <label class="field-label mb-0">활성화</label>
              <button @click="form.is_active = !form.is_active"
                class="transition-colors"
                :style="form.is_active ? 'color: #16a34a' : 'color: var(--muted-foreground)'">
                <ToggleRight v-if="form.is_active" class="w-6 h-6" />
                <ToggleLeft v-else class="w-6 h-6" />
              </button>
            </div>

            <p v-if="formError" class="text-[12px] flex items-center gap-1.5" style="color: #dc2626;">
              <XCircle class="w-3.5 h-3.5 flex-shrink-0" /> {{ formError }}
            </p>
          </div>

          <!-- Modal footer -->
          <div class="px-6 py-4 flex justify-end gap-3" style="border-top: 1px solid var(--border);">
            <button @click="modalOpen = false" class="btn-ghost">취소</button>
            <button @click="saveRule" :disabled="saving" class="btn-primary flex items-center gap-2">
              <Loader2 v-if="saving" class="w-4 h-4 animate-spin" />
              {{ isCreating ? '생성' : '저장' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
/* ── Section title ── */
.section-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted-foreground);
}

/* ── Rule card & rows ── */
.rule-card {
  border-radius: 12px;
  border: 1px solid var(--border);
  overflow: hidden;
  background: var(--card);
  box-shadow: 0 1px 3px oklch(0.128 0.018 257 / 5%);
}
.rule-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  transition: background 0.12s;
  cursor: default;
}
.rule-row:hover {
  background: color-mix(in oklch, var(--primary) 4%, transparent);
}

/* ── Badges ── */
.badge-builtin {
  font-size: 10px;
  font-family: var(--font-mono);
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid var(--border);
  color: var(--muted-foreground);
  background: var(--muted);
}
.badge-pii {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 20px;
  font-family: var(--font-mono);
}

/* ── Icon button ── */
.icon-btn {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted-foreground);
  transition: background 0.12s, color 0.12s;
}
.icon-btn:hover {
  background: var(--muted);
  color: var(--foreground);
}

/* ── Buttons ── */
.btn-primary {
  height: 36px;
  padding: 0 16px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 700;
  background: var(--primary);
  color: white;
  transition: opacity 0.15s;
}
.btn-primary:hover { opacity: 0.88; }
.btn-primary:disabled { opacity: 0.5; }

.btn-ghost {
  height: 36px;
  padding: 0 14px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted-foreground);
  transition: background 0.12s;
}
.btn-ghost:hover { background: var(--muted); }

/* ── Modal ── */
.modal-panel {
  background: var(--card);
  border-radius: 16px;
  border: 1px solid var(--border);
  box-shadow: 0 24px 64px oklch(0.128 0.018 257 / 20%), 0 4px 12px oklch(0.128 0.018 257 / 8%);
}

/* ── Form fields ── */
.field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--foreground);
  margin-bottom: 6px;
}
.field-input {
  width: 100%;
  height: 38px;
  padding: 0 12px;
  border-radius: 9px;
  border: 1px solid var(--border);
  background: var(--background);
  color: var(--foreground);
  font-size: 13px;
  font-family: var(--font-sans);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field-input:focus {
  border-color: color-mix(in oklch, var(--primary) 60%, transparent);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 12%, transparent);
}
.field-input::placeholder { color: var(--muted-foreground); opacity: 0.7; }
.field-textarea {
  height: auto;
  min-height: 80px;
  padding: 10px 12px;
  resize: vertical;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
}
select.field-input { cursor: pointer; }

/* ── Regex tester ── */
.regex-tester {
  padding: 14px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--background);
}
.regex-result-row {
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--card);
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pattern-code {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--muted-foreground);
  word-break: break-all;
}
.result-error {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #dc2626;
}
.result-none {
  font-size: 11px;
  color: var(--muted-foreground);
}
.result-matches {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 11px;
}
.match-chip {
  background: color-mix(in oklch, #16a34a 10%, transparent);
  color: #15803d;
  border: 1px solid color-mix(in oklch, #16a34a 20%, transparent);
  border-radius: 4px;
  padding: 1px 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
}

/* ── Transitions ── */
.fade-enter-active, .fade-leave-active { transition: opacity 0.18s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
