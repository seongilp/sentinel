export const useTheme = () => {
  const isDark = useState('theme-is-dark', () => false)

  const _apply = (dark: boolean) => {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', dark)
    }
  }

  const toggle = () => {
    isDark.value = !isDark.value
    _apply(isDark.value)
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('sentinel-theme', isDark.value ? 'dark' : 'light')
    }
  }

  const init = () => {
    if (typeof window === 'undefined') return
    const saved = localStorage.getItem('sentinel-theme')
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    isDark.value = saved !== null ? saved === 'dark' : prefersDark
    _apply(isDark.value)
  }

  return { isDark: readonly(isDark), toggle, init }
}
