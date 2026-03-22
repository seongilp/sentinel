<script setup lang="ts">
import { Shield, Eye, EyeOff, Loader2, Lock } from 'lucide-vue-next'

definePageMeta({ layout: false })

const { isDark, toggle, init } = useTheme()
const { logoData, appName, load: loadBranding } = useBranding()

onMounted(() => { init(); loadBranding() })

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  if (!username.value || !password.value) {
    error.value = '아이디와 비밀번호를 입력하세요.'
    return
  }
  loading.value = true
  error.value = ''
  // Dummy auth — always succeeds for now
  await new Promise(r => setTimeout(r, 800))
  loading.value = false
  // TODO: integrate real auth (LDAP / SAML SSO)
  navigateTo('/')
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center px-4"
    style="background: var(--background);">

    <!-- Theme toggle -->
    <button
      @click="toggle"
      class="absolute top-5 right-5 w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
      style="background: var(--muted);"
    >
      <component :is="isDark ? 'svg' : 'svg'" />
      <span class="text-[13px]">{{ isDark ? '☀️' : '🌙' }}</span>
    </button>

    <div class="w-full max-w-[380px]">

      <!-- Brand -->
      <div class="flex flex-col items-center mb-10">
        <div class="w-14 h-14 rounded-2xl flex items-center justify-center mb-4 shadow-lg"
          style="background: var(--primary);">
          <img v-if="logoData" :src="logoData" alt="logo" class="w-8 h-8 object-contain" />
          <Shield v-else class="w-7 h-7" style="color: white;" />
        </div>
        <h1 class="font-display font-bold text-[26px] tracking-tight" style="color: var(--foreground); letter-spacing: -0.04em;">
          {{ appName }}
        </h1>
        <p class="text-[13px] mt-1" style="color: var(--muted-foreground);">PII 탐지 시스템에 로그인하세요</p>
      </div>

      <!-- Card -->
      <div class="rounded-2xl p-7 shadow-xl"
        style="background: var(--card); border: 1px solid var(--border);">

        <form @submit.prevent="handleLogin" class="space-y-4">
          <!-- Username -->
          <div>
            <label class="block text-[12px] font-semibold mb-1.5" style="color: var(--foreground);">사용자 아이디</label>
            <input
              v-model="username"
              type="text"
              placeholder="username"
              autocomplete="username"
              class="field-input w-full"
              :disabled="loading"
            />
          </div>

          <!-- Password -->
          <div>
            <label class="block text-[12px] font-semibold mb-1.5" style="color: var(--foreground);">비밀번호</label>
            <div class="relative">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="••••••••"
                autocomplete="current-password"
                class="field-input w-full pr-10"
                :disabled="loading"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2"
                style="color: var(--muted-foreground);"
              >
                <EyeOff v-if="showPassword" class="w-4 h-4" />
                <Eye v-else class="w-4 h-4" />
              </button>
            </div>
          </div>

          <!-- Error -->
          <Transition name="fade">
            <div v-if="error"
              class="flex items-center gap-2 px-3 py-2.5 rounded-lg text-[12px]"
              style="background: #fef2f2; border: 1px solid #fecaca; color: #dc2626;">
              <Lock class="w-3.5 h-3.5 flex-shrink-0" />
              {{ error }}
            </div>
          </Transition>

          <!-- Submit -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full py-2.5 rounded-xl text-[13px] font-bold flex items-center justify-center gap-2 transition-opacity"
            style="background: var(--primary); color: white;"
            :style="{ opacity: loading ? '0.75' : '1' }"
          >
            <Loader2 v-if="loading" class="w-4 h-4 animate-spin" />
            <span>{{ loading ? '로그인 중...' : '로그인' }}</span>
          </button>
        </form>

        <!-- SSO divider -->
        <div class="flex items-center gap-3 my-5">
          <div class="flex-1 h-px" style="background: var(--border);" />
          <span class="text-[11px]" style="color: var(--muted-foreground);">또는</span>
          <div class="flex-1 h-px" style="background: var(--border);" />
        </div>

        <!-- SSO button -->
        <button
          type="button"
          class="w-full py-2.5 rounded-xl text-[13px] font-semibold flex items-center justify-center gap-2 transition-colors"
          style="background: var(--muted); color: var(--foreground); border: 1px solid var(--border);"
          @click="error = 'SSO 연동은 Settings > SSO에서 설정 후 이용 가능합니다.'"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          SSO로 로그인
        </button>
      </div>

      <!-- Footer -->
      <p class="text-center text-[11px] mt-6" style="color: var(--muted-foreground);">
        Sentinel v0.1.0 · 관리자에게 계정을 요청하세요
      </p>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.field-input {
  height: 36px; padding: 0 12px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--background);
  color: var(--foreground); font-size: 13px; outline: none;
  transition: border-color 0.12s; width: 100%;
}
.field-input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 12%, transparent);
}
.field-input::placeholder { color: var(--muted-foreground); }
.field-input:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
