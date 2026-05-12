const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiCall<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers as Record<string, string> || {}) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw { status: res.status, message: err.detail || "Request failed", data: err };
  }
  return res.json();
}

export const api = {
  analyzeText: (text: string, keyword?: string, contentType?: string, _unused?: any, keywords?: string[], brief?: string) =>
    apiCall("/analyze/text", { method: "POST", body: JSON.stringify({ text, target_keyword: keyword, content_type: contentType, target_keywords: keywords, user_brief: brief }) }),

  analyzeUrl: (url: string, keyword?: string, contentType?: string, _unused?: any, keywords?: string[], brief?: string) =>
    apiCall("/analyze/url", { method: "POST", body: JSON.stringify({ url, target_keyword: keyword, content_type: contentType, target_keywords: keywords, user_brief: brief }) }),

  analyzeDocument: (file: File, keyword?: string, contentType?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (keyword) form.append("target_keyword", keyword);
    if (contentType) form.append("content_type", contentType);
    return fetch(`${API_BASE}/analyze/document`, { method: "POST", body: form }).then(r => r.json());
  },

  getAnalysis: (id: string) => apiCall<any>(`/analyze/${id}`),
  getHistory:  (page = 1)  => apiCall<any>(`/analyze/history/all?page=${page}`),

  downloadDocx: (id: string) => fetch(`${API_BASE}/analyze/${id}/download`),

  runAudit: (url: string) =>
    apiCall<any>("/audit", { method: "POST", body: JSON.stringify({ url }) }),

  clusterKeywords: (keyword: string, url?: string) =>
    apiCall<any>("/keywords/cluster", { method: "POST", body: JSON.stringify({ topic: keyword, url }) }),

  generateBrief: (keyword: string, contentType?: string) =>
    apiCall<any>("/keywords/brief", { method: "POST", body: JSON.stringify({ primary_keyword: keyword, content_type: contentType }) }),

  writeArticle: (competitorUrls: string[], targetKeywords: string[], topicPrompt?: string, userTone?: string) =>
    apiCall<any>("/writer/create", { method: "POST", body: JSON.stringify({ competitor_urls: competitorUrls, target_keywords: targetKeywords.length ? targetKeywords : undefined, topic_prompt: topicPrompt, user_tone_prompt: userTone }) }),

  compareUrls: (yourUrl: string, competitorUrl: string) =>
    apiCall<any>("/compare", { method: "POST", body: JSON.stringify({ your_url: yourUrl, competitor_url: competitorUrl }) }),

  // AEO endpoints
  aeoCitationAudit: (url: string, keywords: string[]) =>
    apiCall<any>("/aeo/citation-audit", { method: "POST", body: JSON.stringify({ url, keywords }) }),

  aeoScore: (content: string, contentProfile?: Record<string, any>) =>
    apiCall<any>("/aeo/score", { method: "POST", body: JSON.stringify({ content, content_profile: contentProfile }) }),

  aeoFactDensity: (content: string) =>
    apiCall<any>("/aeo/fact-density", { method: "POST", body: JSON.stringify({ content }) }),

  aeoEntityMap: (content: string, topic: string) =>
    apiCall<any>("/aeo/entity-map", { method: "POST", body: JSON.stringify({ content, topic }) }),

  aeoCitableClaims: (content: string, topic: string, keywords?: string[]) =>
    apiCall<any>("/aeo/citable-claims", { method: "POST", body: JSON.stringify({ content, topic, keywords }) }),

  aeoQueryPlan: (topic: string, keywords?: string[]) =>
    apiCall<any>("/aeo/query-plan", { method: "POST", body: JSON.stringify({ topic, keywords }) }),

  aeoFullAudit: (content: string, topic: string, keywords?: string[], url?: string) =>
    apiCall<any>("/aeo/full-audit", { method: "POST", body: JSON.stringify({ content, topic, keywords, url }) }),
};
