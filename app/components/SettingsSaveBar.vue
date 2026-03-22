<script setup lang="ts">
import { Save, Check, Loader2, AlertCircle } from 'lucide-vue-next'

defineProps<{
  saving: boolean
  status: 'idle' | 'success' | 'error'
  error?: string
}>()

defineEmits<{
  save: []
}>()
</script>

<template>
  <div class="mt-10 flex items-center justify-between pt-6 border-t border-border">
    <p v-if="status === 'error'" class="flex items-center gap-1.5 text-[12px] text-red-400">
      <AlertCircle class="w-3.5 h-3.5" />
      {{ error || '저장 중 오류가 발생했습니다.' }}
    </p>
    <p v-else-if="status === 'success'" class="flex items-center gap-1.5 text-[12px] text-emerald-400">
      <Check class="w-3.5 h-3.5" />
      저장되었습니다.
    </p>
    <span v-else />

    <button
      class="flex items-center gap-2 px-4 py-2 rounded-md text-[13px] font-semibold transition-all"
      :class="saving
        ? 'bg-amber-500/50 text-zinc-900/50 cursor-not-allowed'
        : 'bg-amber-500 hover:bg-amber-400 text-zinc-900'"
      :disabled="saving"
      @click="$emit('save')"
    >
      <Loader2 v-if="saving" class="w-4 h-4 animate-spin" />
      <Save v-else class="w-4 h-4" />
      {{ saving ? 'Saving...' : 'Save Changes' }}
    </button>
  </div>
</template>
