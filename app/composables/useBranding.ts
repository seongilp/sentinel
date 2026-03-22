export function useBranding() {
  const logoData = useState<string>('branding.logo', () => '')
  const appName = useState<string>('branding.name', () => 'Sentinel')
  const loaded = useState<boolean>('branding.loaded', () => false)

  async function load() {
    if (loaded.value) return
    const list = await $fetch<{ key: string; value: string | null }[]>('/api/settings').catch(() => [])
    for (const s of list) {
      if (s.key === 'system.logo_data') logoData.value = s.value ?? ''
      if (s.key === 'system.app_name') appName.value = s.value || 'Sentinel'
    }
    loaded.value = true
  }

  function update(logo: string, name: string) {
    logoData.value = logo
    appName.value = name || 'Sentinel'
  }

  return { logoData, appName, load, update }
}
