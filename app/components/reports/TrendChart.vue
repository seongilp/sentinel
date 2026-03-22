<script setup lang="ts">
interface TrendPoint { date: string; total: number; high: number; medium: number; low: number }

const props = defineProps<{ data: TrendPoint[] }>()

const WIDTH = 700
const HEIGHT = 200
const PAD = { top: 16, right: 16, bottom: 36, left: 40 }
const W = WIDTH - PAD.left - PAD.right
const H = HEIGHT - PAD.top - PAD.bottom

const maxVal = computed(() => {
  const m = Math.max(...props.data.map(d => d.total), 1)
  return Math.ceil(m / 5) * 5 || 5
})

function x(i: number) {
  return PAD.left + (i / (props.data.length - 1 || 1)) * W
}
function y(v: number) {
  return PAD.top + H - (v / maxVal.value) * H
}

function smoothPath(values: number[]) {
  if (values.length < 2) return ''
  const pts = values.map((v, i) => ({ x: x(i), y: y(v) }))
  let d = `M ${pts[0].x},${pts[0].y}`
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1]
    const curr = pts[i]
    const cx = (prev.x + curr.x) / 2
    d += ` C ${cx},${prev.y} ${cx},${curr.y} ${curr.x},${curr.y}`
  }
  return d
}

function areaPath(values: number[]) {
  if (values.length < 2) return ''
  const base = PAD.top + H
  const pts = values.map((v, i) => ({ x: x(i), y: y(v) }))
  let d = `M ${pts[0].x},${base} L ${pts[0].x},${pts[0].y}`
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1]
    const curr = pts[i]
    const cx = (prev.x + curr.x) / 2
    d += ` C ${cx},${prev.y} ${cx},${curr.y} ${curr.x},${curr.y}`
  }
  d += ` L ${pts[pts.length - 1].x},${base} Z`
  return d
}

// Y-axis ticks (5 steps)
const yTicks = computed(() => {
  const step = maxVal.value / 4
  return [0, 1, 2, 3, 4].map(i => ({ v: Math.round(step * i), y: y(step * i) }))
})

// "YYYY-MM-DD" → "MM-DD", anything shorter (e.g. "14:00") → as-is
function fmtLabel(d: string) { return d.length === 10 ? d.slice(5) : d }

// X-axis ticks (6 evenly spaced)
const xTicks = computed(() => {
  const n = props.data.length
  if (n === 0) return []
  const step = Math.ceil(n / 6)
  const ticks: { label: string; x: number }[] = []
  for (let i = 0; i < n; i += step) {
    ticks.push({ label: fmtLabel(props.data[i].date), x: x(i) })
  }
  // always include last
  const last = { label: fmtLabel(props.data[n - 1].date), x: x(n - 1) }
  if (!ticks.find(t => Math.abs(t.x - last.x) < 4)) ticks.push(last)
  return ticks
})

// Hover state
const hoverIdx = ref<number | null>(null)
const svgRef = ref<SVGSVGElement | null>(null)

function onMouseMove(e: MouseEvent) {
  if (!svgRef.value || props.data.length === 0) return
  const rect = svgRef.value.getBoundingClientRect()
  const scaleX = WIDTH / rect.width
  const mx = (e.clientX - rect.left) * scaleX
  // Find closest data point
  let best = 0
  let bestDist = Infinity
  for (let i = 0; i < props.data.length; i++) {
    const dist = Math.abs(x(i) - mx)
    if (dist < bestDist) { bestDist = dist; best = i }
  }
  hoverIdx.value = best
}
function onMouseLeave() { hoverIdx.value = null }

const hoverPoint = computed(() =>
  hoverIdx.value !== null ? props.data[hoverIdx.value] : null
)
const hoverX = computed(() =>
  hoverIdx.value !== null ? x(hoverIdx.value) : 0
)
</script>

<template>
  <div class="trend-wrap">
    <svg
      ref="svgRef"
      :viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
      class="w-full"
      :style="{ height: '200px' }"
      @mousemove="onMouseMove"
      @mouseleave="onMouseLeave"
    >
      <defs>
        <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--primary)" stop-opacity="0.18" />
          <stop offset="100%" stop-color="var(--primary)" stop-opacity="0" />
        </linearGradient>
      </defs>

      <!-- Grid lines -->
      <g>
        <line
          v-for="tick in yTicks" :key="tick.v"
          :x1="PAD.left" :y1="tick.y"
          :x2="PAD.left + W" :y2="tick.y"
          stroke="var(--border)" stroke-width="1"
        />
      </g>

      <!-- Y-axis labels -->
      <g>
        <text
          v-for="tick in yTicks" :key="'yl' + tick.v"
          :x="PAD.left - 6" :y="tick.y + 4"
          text-anchor="end"
          font-size="10"
          fill="var(--muted-foreground)"
          font-family="var(--font-mono)"
        >{{ tick.v }}</text>
      </g>

      <!-- X-axis labels -->
      <g>
        <text
          v-for="tick in xTicks" :key="tick.label"
          :x="tick.x" :y="PAD.top + H + 22"
          text-anchor="middle"
          font-size="10"
          fill="var(--muted-foreground)"
          font-family="var(--font-mono)"
        >{{ tick.label }}</text>
      </g>

      <!-- Area fill (total) -->
      <path
        v-if="data.length >= 2"
        :d="areaPath(data.map(d => d.total))"
        fill="url(#totalGrad)"
      />

      <!-- Lines -->
      <path
        v-if="data.length >= 2"
        :d="smoothPath(data.map(d => d.total))"
        fill="none"
        stroke="var(--primary)"
        stroke-width="2"
        stroke-linecap="round"
      />
      <path
        v-if="data.length >= 2"
        :d="smoothPath(data.map(d => d.high))"
        fill="none"
        stroke="#ef4444"
        stroke-width="1.5"
        stroke-linecap="round"
      />
      <path
        v-if="data.length >= 2"
        :d="smoothPath(data.map(d => d.medium))"
        fill="none"
        stroke="#f97316"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-dasharray="5 3"
      />

      <!-- Hover line + dots -->
      <template v-if="hoverIdx !== null && hoverPoint">
        <line
          :x1="hoverX" :y1="PAD.top"
          :x2="hoverX" :y2="PAD.top + H"
          stroke="var(--border)" stroke-width="1.5" stroke-dasharray="4 3"
        />
        <!-- total dot -->
        <circle
          :cx="hoverX" :cy="y(hoverPoint.total)"
          r="4" fill="var(--primary)" stroke="var(--card)" stroke-width="2"
        />
        <!-- high dot -->
        <circle v-if="hoverPoint.high > 0"
          :cx="hoverX" :cy="y(hoverPoint.high)"
          r="3.5" fill="#ef4444" stroke="var(--card)" stroke-width="2"
        />
        <!-- medium dot -->
        <circle v-if="hoverPoint.medium > 0"
          :cx="hoverX" :cy="y(hoverPoint.medium)"
          r="3.5" fill="#f97316" stroke="var(--card)" stroke-width="2"
        />
      </template>
    </svg>

    <!-- Hover tooltip -->
    <div v-if="hoverIdx !== null && hoverPoint" class="trend-tooltip">
      <div class="tooltip-date">{{ hoverPoint.date }}</div>
      <div class="tooltip-row">
        <span class="dot" style="background: var(--primary);" />
        <span>Total</span>
        <span class="tooltip-val">{{ hoverPoint.total }}</span>
      </div>
      <div class="tooltip-row">
        <span class="dot" style="background: #ef4444;" />
        <span>High</span>
        <span class="tooltip-val" style="color: #ef4444;">{{ hoverPoint.high }}</span>
      </div>
      <div class="tooltip-row">
        <span class="dot" style="background: #f97316;" />
        <span>Medium</span>
        <span class="tooltip-val" style="color: #f97316;">{{ hoverPoint.medium }}</span>
      </div>
      <div class="tooltip-row">
        <span class="dot" style="background: #22c55e;" />
        <span>Low</span>
        <span class="tooltip-val" style="color: #22c55e;">{{ hoverPoint.low }}</span>
      </div>
    </div>

    <!-- Legend -->
    <div class="trend-legend">
      <span class="legend-item"><span class="legend-dot" style="background: var(--primary);" /> Total</span>
      <span class="legend-item"><span class="legend-dot" style="background: #ef4444;" /> High</span>
      <span class="legend-item"><span class="legend-dot" style="background: #f97316;" /> Medium</span>
      <span class="legend-item"><span class="legend-dot" style="background: #22c55e;" /> Low</span>
    </div>
  </div>
</template>

<style scoped>
.trend-wrap { position: relative; }

.trend-tooltip {
  position: absolute;
  top: 8px; left: 8px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  box-shadow: 0 4px 16px oklch(0.128 0.018 257 / 12%);
  pointer-events: none;
  min-width: 130px;
  z-index: 10;
}
.tooltip-date {
  font-size: 11px; font-weight: 700; font-family: var(--font-mono);
  color: var(--muted-foreground); margin-bottom: 6px;
}
.tooltip-row {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--foreground); margin-bottom: 2px;
}
.tooltip-val { margin-left: auto; font-weight: 700; font-family: var(--font-mono); }
.dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

.trend-legend {
  display: flex; align-items: center; gap: 16px;
  justify-content: center; margin-top: 4px;
}
.legend-item {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; color: var(--muted-foreground);
}
.legend-dot { width: 8px; height: 8px; border-radius: 50%; }
</style>
