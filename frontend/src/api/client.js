import axios from "axios";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const wsBaseUrl =
  import.meta.env.VITE_WS_BASE_URL ||
  apiBaseUrl.replace("https://", "wss://").replace("http://", "ws://");

const api = axios.create({ baseURL: apiBaseUrl });

export const generatePCB = async (description, options = {}) => (await api.post("/api/generate", { description, ...options })).data;
export const getJobStatus = async (jobId) => (await api.get(`/api/jobs/${jobId}`)).data;
export const connectToLogs = (jobId, onMessage) => {
  const socket = new WebSocket(`${wsBaseUrl}/ws/logs/${jobId}`);
  socket.onmessage = (event) => onMessage(JSON.parse(event.data));
  return socket;
};
export const validatePCB = async (filePath, fabTarget) => (await api.post("/api/validate", { pcb_file_path: filePath, fab_target: fabTarget })).data;
export const exportGerbers = async (filePath, options = {}) => (await api.post("/api/export", { pcb_file: filePath, options })).data;
export const getConfig = async () => (await api.get("/api/config")).data;
export const updateConfig = async (settings) => (await api.post("/api/config", { values: settings })).data;
export const getHealth = async () => (await api.get("/api/health")).data;
export const getDesigns = async () => (await api.get("/api/designs")).data;
