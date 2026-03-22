export function useApi() {
  const get = <T>(url: string, options?: object) =>
    $fetch<T>(`/api${url}`, { method: 'GET', ...options })
  const post = <T>(url: string, body: unknown) =>
    $fetch<T>(`/api${url}`, { method: 'POST', body })
  const put = <T>(url: string, body: unknown) =>
    $fetch<T>(`/api${url}`, { method: 'PUT', body })
  const del = <T>(url: string) =>
    $fetch<T>(`/api${url}`, { method: 'DELETE' })
  return { get, post, put, del }
}
