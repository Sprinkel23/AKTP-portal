import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("aktp_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !err.config?.url?.includes("/api/auth/login")) {
      sessionStorage.removeItem("aktp_token");
      sessionStorage.removeItem("aktp_user");
    }
    return Promise.reject(err);
  }
);

export function resolveAssetUrl(path) {
  if (!path) return "/ak-tuition-logo.png";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (path === "/assets/ak-tuition-logo.png") return "/ak-tuition-logo.png";
  return `${API_BASE_URL}${path}`;
}

export async function downloadAuthorizedFile(url, filename) {
  const response = await api.get(url, { responseType: "blob" });
  const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = blobUrl;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export default api;
