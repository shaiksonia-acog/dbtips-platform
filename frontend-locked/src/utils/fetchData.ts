export async function fetchData<T = any>(
  payload: unknown,
  endpoint: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${import.meta.env.VITE_API_URI}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    ...init,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let errorMessage: string;
    try {
      // Try to parse as JSON
      const errorData = JSON.parse(text);
      errorMessage = errorData.message || JSON.stringify(errorData);
    } catch {
      // Fallback to plain text if not JSON
      errorMessage = text || `Request failed with status ${res.status}`;
    }
    throw new Error(errorMessage);
  }

  // Return blob for '/export' endpoint, otherwise JSON
  return endpoint === "/export" ? (res.blob() as Promise<T>) : (res.json() as Promise<T>);
}