<script setup lang="ts">
import {
  LayoutDashboard,
  Database,
  ScanSearch,
  ShieldCheck,
  Tags,
  BarChart3,
  Settings2,
  ScrollText,
  ChevronRight,
  Shield,
  Sun,
  Moon,
  Microscope,
  Users,
  UserCog,
  X,
} from 'lucide-vue-next'

const route = useRoute()
const { isDark, toggle, init } = useTheme()
const { logoData, appName, load: loadBranding } = useBranding()
const { persona, isPersonaMode, exitPersona, canWrite, ROLE_CONFIG } = usePersona()

onMounted(() => { init(); loadBranding() })

const routeToMenuKey = (path: string): string => {
  if (path === '/') return 'dashboard'
  if (path.startsWith('/connections')) return 'connections'
  if (path.startsWith('/scans')) return 'scans'
  if (path.startsWith('/deep-inspect')) return 'deep-inspect'
  if (path.startsWith('/rules')) return 'rules'
  if (path.startsWith('/classification')) return 'classification'
  if (path.startsWith('/reports')) return 'reports'
  if (path.startsWith('/users')) return 'users'
  if (path.startsWith('/settings')) return 'settings'
  if (path.startsWith('/audit-log')) return 'audit-log'
  return 'dashboard'
}

const currentMenuKey = computed(() => routeToMenuKey(route.path))
const isReadOnly = computed(() => isPersonaMode.value && !canWrite(currentMenuKey.value))

const showBlockedToast = ref(false)
function handleBlockedClick() {
  showBlockedToast.value = true
  setTimeout(() => { showBlockedToast.value = false }, 2000)
}

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, to: '/', description: 'Overview' },
  { label: 'Connections', icon: Database, to: '/connections', description: 'DB Sources' },
  { label: 'Scans', icon: ScanSearch, to: '/scans', description: 'PII Detection' },
  { label: 'Deep Inspect', icon: Microscope, to: '/deep-inspect', description: 'Full Scan' },
  { label: 'Rules', icon: ShieldCheck, to: '/rules', description: 'Detection Rules' },
  { label: 'Classification', icon: Tags, to: '/classification', description: 'Data Tagging' },
  { label: 'Reports', icon: BarChart3, to: '/reports', description: 'Analytics' },
  { label: 'Users', icon: Users, to: '/users', description: 'User Management' },
  { label: 'Settings', icon: Settings2, to: '/settings', description: 'Configuration' },
  { label: 'Audit Log', icon: ScrollText, to: '/audit-log', description: 'Activity' },
]

const isActive = (to: string) => {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}

const currentPage = computed(() =>
  navItems.find(n => isActive(n.to))?.label ?? 'Dashboard'
)
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-background relative">

    <!-- Sidebar -->
    <aside
      class="w-[220px] flex-shrink-0 flex flex-col relative z-10"
      style="background: var(--sidebar); border-right: 1px solid var(--sidebar-border); box-shadow: 1px 0 0 var(--sidebar-border);"
    >

      <!-- Logo -->
      <div class="h-[60px] flex items-center px-5" style="border-bottom: 1px solid var(--sidebar-border);">
        <div class="flex items-center gap-2.5">
          <!-- Custom logo image -->
          <img
            v-if="logoData"
            :src="logoData"
            alt="logo"
            class="w-7 h-7 rounded-lg object-contain flex-shrink-0"
            style="background: var(--primary);"
          />
          <!-- Default Shield icon -->
          <div
            v-else
            class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
            style="background: var(--primary);"
          >
            <Shield class="w-3.5 h-3.5" style="color: white;" />
          </div>
          <span
            class="font-display font-bold text-[15px] tracking-tight truncate"
            style="color: var(--foreground); letter-spacing: -0.03em;"
          >{{ appName }}</span>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 px-2.5 py-3 space-y-0.5 overflow-y-auto">
        <NuxtLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="group flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[13px] font-semibold transition-all duration-150 relative"
          :style="isActive(item.to)
            ? 'background: color-mix(in oklch, var(--primary) 8%, transparent); color: var(--primary-active);'
            : 'color: var(--muted-foreground);'"
        >
          <component
            :is="item.icon"
            class="w-[15px] h-[15px] flex-shrink-0 transition-colors"
            :style="isActive(item.to)
              ? 'color: var(--primary);'
              : 'color: var(--muted-foreground);'"
          />
          <span class="flex-1 truncate">{{ item.label }}</span>
        </NuxtLink>
      </nav>

      <!-- Footer -->
      <div class="px-4 py-3.5" style="border-top: 1px solid var(--sidebar-border);">
        <div class="flex items-center gap-2">
          <div class="w-1.5 h-1.5 rounded-full animate-pulse-glow" style="background: oklch(0.65 0.18 145);" />
          <span class="text-[11px]" style="font-family: var(--font-mono); color: var(--muted-foreground);">v0.1.0 · ready</span>
          <div v-if="isPersonaMode" class="ml-auto flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold"
            :style="{ background: ROLE_CONFIG[persona].bg, color: ROLE_CONFIG[persona].color }">
            <UserCog class="w-2.5 h-2.5" />
            {{ ROLE_CONFIG[persona].label }}
          </div>
        </div>
      </div>
    </aside>

    <!-- Main area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden relative z-10">

      <!-- Top bar -->
      <header
        class="h-[60px] flex items-center px-6 flex-shrink-0"
        style="background: var(--sidebar); border-bottom: 1px solid var(--sidebar-border);"
      >
        <div class="flex items-center gap-1.5 text-[13px]">
          <span style="color: var(--muted-foreground); font-weight: 500;">{{ appName }}</span>
          <ChevronRight class="w-3.5 h-3.5" style="color: var(--muted-foreground); opacity: 0.4;" />
          <span style="font-weight: 700; color: var(--foreground); letter-spacing: -0.01em;">{{ currentPage }}</span>
        </div>

        <div class="ml-auto flex items-center gap-2.5">
          <!-- PII Scanner badge -->
          <div
            class="h-6 px-2.5 rounded-full flex items-center gap-1.5"
            style="border: 1px solid color-mix(in oklch, var(--primary) 25%, transparent); background: color-mix(in oklch, var(--primary) 7%, transparent);"
          >
            <div class="w-1.5 h-1.5 rounded-full" style="background: var(--primary);" />
            <span
              class="text-[11px] font-semibold"
              style="font-family: var(--font-mono); color: var(--primary-active);"
            >PII Scanner</span>
          </div>

          <!-- Theme toggle -->
          <button
            @click="toggle"
            class="w-7 h-7 rounded-lg flex items-center justify-center transition-colors"
            style="background: transparent;"
            :style="{ background: 'transparent' }"
            :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
            @mouseenter="($event.currentTarget as HTMLElement).style.background = 'var(--muted)'"
            @mouseleave="($event.currentTarget as HTMLElement).style.background = 'transparent'"
          >
            <Sun v-if="isDark" class="w-3.5 h-3.5" style="color: var(--muted-foreground);" />
            <Moon v-else class="w-3.5 h-3.5" style="color: var(--muted-foreground);" />
          </button>
        </div>
      </header>

      <!-- Persona Mode Banner -->
      <div v-if="isPersonaMode"
        class="flex items-center gap-3 px-5 py-2 text-[12px] font-semibold flex-shrink-0"
        :style="{ background: ROLE_CONFIG[persona].bg, borderBottom: `1px solid ${ROLE_CONFIG[persona].color}30` }">
        <UserCog class="w-3.5 h-3.5 flex-shrink-0" :style="{ color: ROLE_CONFIG[persona].color }" />
        <span :style="{ color: ROLE_CONFIG[persona].color }">
          Persona 모드 — <strong>{{ ROLE_CONFIG[persona].label }}</strong> 권한으로 보는 중
          <span class="font-normal opacity-70 ml-1">{{ ROLE_CONFIG[persona].description }}</span>
        </span>
        <button
          @click="exitPersona"
          class="ml-auto flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold transition-opacity hover:opacity-70"
          :style="{ background: ROLE_CONFIG[persona].color, color: 'white' }">
          <X class="w-3 h-3" /> Admin으로 돌아가기
        </button>
      </div>

      <!-- Page content -->
      <main class="flex-1 overflow-auto relative">
        <div class="animate-slide-in">
          <slot />
        </div>

        <!-- Read-only overlay for persona mode -->
        <div v-if="isReadOnly"
          class="absolute inset-0 z-40 cursor-not-allowed"
          style="background: transparent;"
          @click.capture.prevent="handleBlockedClick"
        />

        <!-- Blocked toast -->
        <Transition name="toast">
          <div v-if="showBlockedToast"
            class="absolute bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl text-[13px] font-semibold shadow-lg"
            :style="{ background: ROLE_CONFIG[persona].color, color: 'white' }">
            <UserCog class="w-3.5 h-3.5" />
            {{ ROLE_CONFIG[persona].label }} 권한으로는 수정할 수 없습니다
          </div>
        </Transition>
      </main>
    </div>
  </div>
</template>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: opacity 0.2s, transform 0.2s; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(8px); }
</style>
