<script setup lang="ts">
import { Users, UserPlus, Shield, Eye, Edit3, Trash2, Search, Crown, User, LockKeyhole, LockOpen, Link2, CheckCircle2, AlertCircle, X, Check } from 'lucide-vue-next'

const { users, isLocked, unlock, lock, daysSinceLogin, LOCK_DAYS, initLockedEvents } = useUsers()

onMounted(() => initLockedEvents())

const searchQuery = ref('')
const roleFilter = ref<'all' | 'admin' | 'analyst' | 'viewer'>('all')

const filteredUsers = computed(() => users.value.filter(u => {
  const matchSearch = !searchQuery.value || u.username.includes(searchQuery.value) || u.email.includes(searchQuery.value)
  const matchRole = roleFilter.value === 'all' || u.role === roleFilter.value
  return matchSearch && matchRole
}))

const roleConfig: Record<string, { label: string; color: string; bg: string; icon: any }> = {
  admin:   { label: 'Admin',   color: '#7c3aed', bg: '#f5f3ff', icon: Crown },
  analyst: { label: 'Analyst', color: '#0369a1', bg: '#f0f9ff', icon: Edit3 },
  viewer:  { label: 'Viewer',  color: '#374151', bg: '#f3f4f6', icon: Eye },
}

function formatDate(d: string) {
  return new Date(d).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatDaysAgo(d: string) {
  const days = daysSinceLogin(d)
  if (days === 0) return '오늘'
  if (days === 1) return '어제'
  return `${days}일 전`
}

// ── LDAP 상태 (dev: 연결된 상태로 시뮬레이션) ────────────────────────────────
const ldapConnected = ref(true) // dev 환경: 연결됨
const ldapConfig = ref({ url: 'ldap://ldap.sentinel.internal:389', bindDn: 'cn=admin,dc=sentinel,dc=internal', bindPassword: '', baseDn: 'ou=users,dc=sentinel,dc=internal' })
const ldapTesting = ref(false)
const ldapTestResult = ref<'ok' | 'fail' | null>(null)

async function testLdapConnect() {
  ldapTesting.value = true
  ldapTestResult.value = null
  await new Promise(r => setTimeout(r, 1200))
  ldapTestResult.value = 'ok'
  ldapConnected.value = true
  ldapTesting.value = false
}

// ── LDAP 사용자 불러오기 (mock) ────────────────────────────────────────────
interface LdapUser { dn: string; uid: string; cn: string; mail: string; ou: string }

const LDAP_MOCK: LdapUser[] = [
  { dn: 'uid=jkim,ou=users,...', uid: 'jkim', cn: '김지훈', mail: 'jkim@corp.internal', ou: 'Engineering' },
  { dn: 'uid=lpark,ou=users,...', uid: 'lpark', cn: '박민지', mail: 'lpark@corp.internal', ou: 'Security' },
  { dn: 'uid=cshin,ou=users,...', uid: 'cshin', cn: '신채원', mail: 'cshin@corp.internal', ou: 'Data' },
  { dn: 'uid=hwang,ou=users,...', uid: 'hwang', cn: '황준호', mail: 'hwang@corp.internal', ou: 'Engineering' },
  { dn: 'uid=ylee,ou=users,...', uid: 'ylee', cn: '이예진', mail: 'ylee@corp.internal', ou: 'Compliance' },
  { dn: 'uid=bchoi,ou=users,...', uid: 'bchoi', cn: '최병철', mail: 'bchoi@corp.internal', ou: 'Security' },
  { dn: 'uid=ahan,ou=users,...', uid: 'ahan', cn: '한아름', mail: 'ahan@corp.internal', ou: 'Data' },
  { dn: 'uid=skang,ou=users,...', uid: 'skang', cn: '강성민', mail: 'skang@corp.internal', ou: 'Engineering' },
]

// ── 모달 상태 ──────────────────────────────────────────────────────────────
const modalOpen = ref(false)
const modalView = ref<'ldap-setup' | 'ldap-import'>('ldap-import')
const ldapSearch = ref('')
const selectedUids = ref<string[]>([])
const assignRole = ref<Record<string, string>>({})

const ldapFiltered = computed(() =>
  LDAP_MOCK.filter(u => !ldapSearch.value
    || u.cn.includes(ldapSearch.value) || u.uid.includes(ldapSearch.value) || u.mail.includes(ldapSearch.value))
    // exclude already-added users
    .filter(u => !users.value.some(ex => ex.email === u.mail))
)

function openAddModal() {
  if (!ldapConnected.value) {
    modalView.value = 'ldap-setup'
  } else {
    modalView.value = 'ldap-import'
    selectedUids.value = []
    ldapSearch.value = ''
  }
  modalOpen.value = true
}

function toggleSelect(uid: string) {
  if (selectedUids.value.includes(uid)) {
    selectedUids.value = selectedUids.value.filter(u => u !== uid)
  } else {
    selectedUids.value = [...selectedUids.value, uid]
    if (!assignRole.value[uid]) assignRole.value = { ...assignRole.value, [uid]: 'viewer' }
  }
}

function addSelectedUsers() {
  // Add selected LDAP users to local users list (mock)
  const toAdd = LDAP_MOCK.filter(u => selectedUids.value.includes(u.uid))
  const now = new Date().toISOString()
  const newUsers = toAdd.map((u, i) => ({
    id: Date.now() + i,
    username: u.uid,
    email: u.mail,
    role: assignRole.value[u.uid] ?? 'viewer',
    status: 'active' as const,
    last_login: now,
    created_at: now.slice(0, 10),
  }))
  users.value = [...users.value, ...newUsers]
  modalOpen.value = false
}
</script>

<template>
  <div class="p-6">

    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="font-display font-bold text-[22px] tracking-tight" style="color: var(--foreground); letter-spacing: -0.03em;">Users</h1>
        <p class="text-[13px] mt-0.5" style="color: var(--muted-foreground);">사용자 계정 및 권한 관리</p>
      </div>
      <button
        @click="openAddModal"
        class="flex items-center gap-2 px-4 py-2 rounded-xl text-[13px] font-semibold transition-colors"
        style="background: var(--primary); color: white;"
      >
        <UserPlus class="w-4 h-4" />
        사용자 추가
      </button>
    </div>

    <!-- Notice -->
    <div class="flex items-start gap-3 px-4 py-3 rounded-xl mb-4"
      style="background: color-mix(in oklch, var(--primary) 6%, transparent); border: 1px solid color-mix(in oklch, var(--primary) 20%, transparent);">
      <Shield class="w-4 h-4 mt-0.5 flex-shrink-0" style="color: var(--primary);" />
      <p class="text-[12px]" style="color: var(--foreground);">
        현재 더미 데이터가 표시됩니다. 실제 인증 시스템(LDAP/SAML SSO) 연동 후 실제 사용자 목록이 표시됩니다.
      </p>
    </div>

    <!-- Filters -->
    <div class="flex items-center gap-3 mb-5">
      <!-- Search -->
      <div class="relative flex-1 max-w-xs">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style="color: var(--muted-foreground);" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="이름 또는 이메일 검색..."
          class="w-full pl-9 pr-3 h-9 rounded-lg text-[13px]"
          style="border: 1px solid var(--border); background: var(--background); color: var(--foreground); outline: none;"
        />
      </div>

      <!-- Role filter -->
      <div class="flex gap-1.5">
        <button
          v-for="r in ['all', 'admin', 'analyst', 'viewer'] as const"
          :key="r"
          @click="roleFilter = r"
          class="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all capitalize"
          :style="roleFilter === r
            ? 'background: color-mix(in oklch, var(--primary) 10%, transparent); color: var(--primary); border: 1.5px solid var(--primary);'
            : 'border: 1px solid var(--border); color: var(--muted-foreground); background: var(--card);'"
        >{{ r === 'all' ? '전체' : r }}</button>
      </div>

      <span class="ml-auto text-[12px]" style="color: var(--muted-foreground);">{{ filteredUsers.length }}명</span>
    </div>

    <!-- Table -->
    <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border);">
      <table class="w-full text-[13px]">
        <thead>
          <tr style="background: var(--muted); border-bottom: 1px solid var(--border);">
            <th class="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">사용자</th>
            <th class="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">권한</th>
            <th class="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">상태</th>
            <th class="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">마지막 로그인</th>
            <th class="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">가입일</th>
            <th class="text-center px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">잠금 해제</th>
            <th class="text-center px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wide" style="color: var(--muted-foreground);">액션</th>
          </tr>
        </thead>
        <tbody class="divide-y" style="--tw-divide-opacity: 1; border-color: var(--border);">
          <tr
            v-for="user in filteredUsers"
            :key="user.id"
            class="transition-colors"
            style="background: var(--card);"
            @mouseenter="($event.currentTarget as HTMLElement).style.background = 'var(--muted)'"
            @mouseleave="($event.currentTarget as HTMLElement).style.background = 'var(--card)'"
          >
            <!-- User info -->
            <td class="px-4 py-3">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                  :style="{ background: roleConfig[user.role]?.bg, color: roleConfig[user.role]?.color }">
                  <component :is="roleConfig[user.role]?.icon ?? User" class="w-4 h-4" />
                </div>
                <div>
                  <p class="font-semibold" style="color: var(--foreground);">{{ user.username }}</p>
                  <p class="text-[11px]" style="color: var(--muted-foreground);">{{ user.email }}</p>
                </div>
              </div>
            </td>

            <!-- Role badge -->
            <td class="px-4 py-3">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold"
                :style="{ background: roleConfig[user.role]?.bg, color: roleConfig[user.role]?.color }">
                <component :is="roleConfig[user.role]?.icon ?? User" class="w-3 h-3" />
                {{ roleConfig[user.role]?.label }}
              </span>
            </td>

            <!-- Status -->
            <td class="px-4 py-3">
              <div v-if="isLocked(user)" class="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[11px] font-semibold"
                style="background: #fff1f2; color: #be123c; border: 1px solid #fecdd3;">
                <LockKeyhole class="w-3 h-3" /> 잠금
              </div>
              <div v-else class="flex items-center gap-1.5">
                <div class="w-1.5 h-1.5 rounded-full"
                  :style="user.status === 'active' ? 'background: oklch(0.65 0.18 145)' : 'background: var(--muted-foreground)'" />
                <span class="text-[12px]" :style="user.status === 'active' ? 'color: oklch(0.55 0.18 145)' : 'color: var(--muted-foreground)'">
                  {{ user.status === 'active' ? '활성' : '비활성' }}
                </span>
              </div>
            </td>

            <!-- Last login -->
            <td class="px-4 py-3">
              <div>
                <span class="text-[12px]" style="color: var(--muted-foreground);">{{ formatDate(user.last_login) }}</span>
                <span v-if="daysSinceLogin(user.last_login) > 30"
                  class="ml-1.5 text-[11px]"
                  :style="daysSinceLogin(user.last_login) > LOCK_DAYS ? 'color: #be123c;' : 'color: var(--muted-foreground);'">
                  ({{ formatDaysAgo(user.last_login) }})
                </span>
              </div>
            </td>

            <!-- Created at -->
            <td class="px-4 py-3">
              <span class="text-[12px]" style="color: var(--muted-foreground);">{{ user.created_at }}</span>
            </td>

            <!-- Unlock column -->
            <td class="px-4 py-3 text-center">
              <button v-if="isLocked(user)"
                @click="unlock(user)"
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-colors"
                style="color: #be123c; border: 1px solid #fecdd3; background: #fff1f2;"
                @mouseenter="($event.currentTarget as HTMLElement).style.background = '#ffe4e6'"
                @mouseleave="($event.currentTarget as HTMLElement).style.background = '#fff1f2'">
                <LockOpen class="w-3 h-3" /> 잠금 해제
              </button>
              <button v-else
                @click="lock(user)"
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-colors"
                style="color: #6b7280; border: 1px solid #e5e7eb; background: #f9fafb;"
                @mouseenter="($event.currentTarget as HTMLElement).style.background = '#f3f4f6'"
                @mouseleave="($event.currentTarget as HTMLElement).style.background = '#f9fafb'">
                <LockKeyhole class="w-3 h-3" /> 잠금
              </button>
            </td>
            <!-- Actions column -->
            <td class="px-4 py-3">
              <div class="flex items-center justify-center gap-1">
                <button class="w-7 h-7 rounded-lg flex items-center justify-center transition-colors"
                  style="color: var(--muted-foreground);"
                  @mouseenter="($event.currentTarget as HTMLElement).style.background = 'var(--muted)'"
                  @mouseleave="($event.currentTarget as HTMLElement).style.background = 'transparent'">
                  <Edit3 class="w-3.5 h-3.5" />
                </button>
                <button class="w-7 h-7 rounded-lg flex items-center justify-center transition-colors"
                  style="color: var(--muted-foreground);"
                  @mouseenter="($event.currentTarget as HTMLElement).style.color = '#dc2626'; ($event.currentTarget as HTMLElement).style.background = '#fef2f2'"
                  @mouseleave="($event.currentTarget as HTMLElement).style.color = 'var(--muted-foreground)'; ($event.currentTarget as HTMLElement).style.background = 'transparent'">
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Empty state -->
      <div v-if="filteredUsers.length === 0" class="py-16 text-center">
        <Users class="w-10 h-10 mx-auto mb-3" style="color: var(--muted-foreground); opacity: 0.4;" />
        <p class="text-[13px]" style="color: var(--muted-foreground);">검색 결과가 없습니다.</p>
      </div>
    </div>

    <!-- Role legend -->
    <div class="flex items-center gap-6 mt-5 px-1">
      <p class="text-[11px] font-semibold uppercase tracking-wider" style="color: var(--muted-foreground);">권한 설명</p>
      <div v-for="(cfg, role) in roleConfig" :key="role" class="flex items-center gap-1.5">
        <component :is="cfg.icon" class="w-3 h-3" :style="{ color: cfg.color }" />
        <span class="text-[11px] font-medium" :style="{ color: cfg.color }">{{ cfg.label }}</span>
        <span class="text-[11px]" style="color: var(--muted-foreground);">—
          {{ role === 'admin' ? '전체 권한' : role === 'analyst' ? '스캔·규칙 편집' : '읽기 전용' }}
        </span>
      </div>
    </div>
  </div>

  <!-- ── Modal overlay ──────────────────────────────────────────────────── -->
  <Teleport to="body">
    <div v-if="modalOpen" class="modal-backdrop" @click.self="modalOpen = false">
      <div class="modal-box">

        <!-- LDAP Setup view -->
        <template v-if="modalView === 'ldap-setup'">
          <div class="flex items-center justify-between mb-5">
            <div>
              <h2 class="text-[15px] font-bold" style="color: var(--foreground);">LDAP 연결 설정</h2>
              <p class="text-[12px] mt-0.5" style="color: var(--muted-foreground);">사용자 추가를 위해 먼저 LDAP 서버를 연결하세요.</p>
            </div>
            <button @click="modalOpen = false" class="modal-close"><X class="w-4 h-4" /></button>
          </div>
          <div class="space-y-3">
            <div>
              <label class="field-label">LDAP Server URL</label>
              <input v-model="ldapConfig.url" class="field-input w-full" placeholder="ldap://ldap.example.com:389" />
            </div>
            <div>
              <label class="field-label">Bind DN</label>
              <input v-model="ldapConfig.bindDn" class="field-input w-full" placeholder="cn=admin,dc=example,dc=com" />
            </div>
            <div>
              <label class="field-label">Bind Password</label>
              <input v-model="ldapConfig.bindPassword" type="password" class="field-input w-full" placeholder="••••••••" />
            </div>
            <div>
              <label class="field-label">Base DN</label>
              <input v-model="ldapConfig.baseDn" class="field-input w-full" placeholder="ou=users,dc=example,dc=com" />
            </div>
          </div>
          <div v-if="ldapTestResult" class="flex items-center gap-2 mt-3 text-[12px]"
            :style="ldapTestResult === 'ok' ? 'color: #16a34a' : 'color: #dc2626'">
            <CheckCircle2 v-if="ldapTestResult === 'ok'" class="w-4 h-4" />
            <AlertCircle v-else class="w-4 h-4" />
            {{ ldapTestResult === 'ok' ? '연결 성공! 사용자를 불러올 수 있습니다.' : '연결 실패. 설정을 확인하세요.' }}
          </div>
          <div class="flex gap-2 mt-5">
            <button @click="testLdapConnect" :disabled="ldapTesting"
              class="flex-1 h-9 rounded-lg text-[13px] font-semibold transition-colors flex items-center justify-center gap-2"
              style="border: 1.5px solid var(--primary); color: var(--primary);">
              <Link2 class="w-3.5 h-3.5" />
              {{ ldapTesting ? '연결 중...' : '테스트 & 연결' }}
            </button>
            <button v-if="ldapTestResult === 'ok'" @click="modalView = 'ldap-import'"
              class="flex-1 h-9 rounded-lg text-[13px] font-semibold"
              style="background: var(--primary); color: white;">
              사용자 불러오기 →
            </button>
          </div>
        </template>

        <!-- LDAP Import view -->
        <template v-else>
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <div class="w-5 h-5 rounded-full flex items-center justify-center" style="background: #f0fdf4;">
                <CheckCircle2 class="w-3.5 h-3.5" style="color: #16a34a;" />
              </div>
              <div>
                <h2 class="text-[15px] font-bold" style="color: var(--foreground);">LDAP 사용자 추가</h2>
                <p class="text-[11px]" style="color: var(--muted-foreground);">{{ ldapConfig.url }}</p>
              </div>
            </div>
            <button @click="modalOpen = false" class="modal-close"><X class="w-4 h-4" /></button>
          </div>

          <!-- Search -->
          <div class="relative mb-3">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style="color: var(--muted-foreground);" />
            <input v-model="ldapSearch" type="text" placeholder="이름, ID, 이메일 검색..."
              class="w-full pl-9 pr-3 h-8 rounded-lg text-[12px]"
              style="border: 1px solid var(--border); background: var(--background); color: var(--foreground); outline: none;" />
          </div>

          <!-- User list -->
          <div class="ldap-list">
            <div v-if="ldapFiltered.length === 0" class="py-8 text-center text-[12px]" style="color: var(--muted-foreground);">
              불러올 수 있는 사용자가 없습니다.
            </div>
            <div v-for="u in ldapFiltered" :key="u.uid"
              @click="toggleSelect(u.uid)"
              class="ldap-row"
              :class="selectedUids.includes(u.uid) ? 'ldap-row-selected' : ''">
              <!-- Checkbox -->
              <div class="w-4 h-4 rounded flex-shrink-0 flex items-center justify-center transition-colors"
                :style="selectedUids.includes(u.uid)
                  ? 'background: var(--primary); border: 1.5px solid var(--primary);'
                  : 'border: 1.5px solid var(--border); background: var(--background);'">
                <Check v-if="selectedUids.includes(u.uid)" class="w-2.5 h-2.5" style="color: white;" />
              </div>
              <!-- Info -->
              <div class="flex-1 min-w-0">
                <p class="text-[13px] font-semibold truncate" style="color: var(--foreground);">{{ u.cn }} <span class="font-normal text-[11px]" style="color: var(--muted-foreground);">@{{ u.uid }}</span></p>
                <p class="text-[11px] truncate" style="color: var(--muted-foreground);">{{ u.mail }} · {{ u.ou }}</p>
              </div>
              <!-- Role selector -->
              <select v-if="selectedUids.includes(u.uid)"
                v-model="assignRole[u.uid]"
                @click.stop
                class="h-7 px-2 rounded-lg text-[11px] font-semibold"
                style="border: 1px solid var(--border); background: var(--card); color: var(--foreground); outline: none;">
                <option value="viewer">Viewer</option>
                <option value="analyst">Analyst</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-between mt-4 pt-4" style="border-top: 1px solid var(--border);">
            <span class="text-[12px]" style="color: var(--muted-foreground);">
              {{ selectedUids.length }}명 선택됨
            </span>
            <button @click="addSelectedUsers" :disabled="selectedUids.length === 0"
              class="flex items-center gap-2 px-4 h-9 rounded-lg text-[13px] font-semibold transition-colors"
              :style="selectedUids.length > 0
                ? 'background: var(--primary); color: white;'
                : 'background: var(--muted); color: var(--muted-foreground); cursor: not-allowed;'">
              <UserPlus class="w-4 h-4" /> 추가
            </button>
          </div>
        </template>

      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.35);
  display: flex; align-items: center; justify-content: center;
}
.modal-box {
  width: 480px; max-height: 80vh;
  background: var(--card); border: 1px solid var(--border);
  border-radius: 16px; padding: 24px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  display: flex; flex-direction: column;
}
.modal-close {
  width: 28px; height: 28px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: var(--muted-foreground);
  transition: background 0.1s;
}
.modal-close:hover { background: var(--muted); }

.field-label { display: block; font-size: 11px; font-weight: 600; color: var(--muted-foreground); margin-bottom: 4px; }
.field-input {
  height: 34px; padding: 0 10px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--background);
  color: var(--foreground); font-size: 12px; outline: none;
}
.field-input:focus { border-color: var(--primary); }

.ldap-list { flex: 1; overflow-y: auto; max-height: 320px; display: flex; flex-direction: column; gap: 2px; }
.ldap-row {
  display: flex; align-items: center; gap-3: gap; gap: 10px;
  padding: 8px 10px; border-radius: 10px; cursor: pointer;
  transition: background 0.1s;
  border: 1px solid transparent;
}
.ldap-row:hover { background: var(--muted); }
.ldap-row-selected { background: color-mix(in oklch, var(--primary) 6%, transparent); border-color: color-mix(in oklch, var(--primary) 25%, transparent); }
</style>
