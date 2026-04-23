import axios from "axios";

const API = "https://openfintel.onrender.com";

export const uploadFile = (formData: FormData) =>
  axios.post(`${API}/api/upload`, formData);

export const getDashboard = () =>
  axios.get(`${API}/api/dashboard`);

export const getFiles = () =>
  axios.get(`${API}/api/files`);

export const getCoverage = () =>
  axios.get(`${API}/api/coverage`);