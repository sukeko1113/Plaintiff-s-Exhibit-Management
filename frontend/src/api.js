// 仕様 §13 — バックエンド API ラッパ
// すべて Promise を返す。失敗時は { status, error, message, detail } を throw。

const BASE = 'http://localhost:8765/api';

async function request(path, { method = 'GET', body, params } = {}) {
  let url = `${BASE}${path}`;
  if (params) {
    const qs = new URLSearchParams(params).toString();
    if (qs) url += `?${qs}`;
  }
  const init = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) init.body = JSON.stringify(body);

  const res = await fetch(url, init);
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    const detail = data?.detail ?? data;
    const err = {
      status: res.status,
      error: detail?.error ?? `HTTP ${res.status}`,
      message: detail?.message ?? text,
      detail: detail?.detail ?? null,
    };
    throw err;
  }
  return data;
}

export const api = {
  setup: (rootPath) =>
    request('/setup', { method: 'POST', body: { root_path: rootPath } }),

  masterList: (rootPath) =>
    request('/master/list', { params: { root_path: rootPath } }),

  combinedList: (rootPath) =>
    request('/combined/list', { params: { root_path: rootPath } }),

  split: (rootPath, combinedFile, opts = {}) =>
    request('/split', {
      method: 'POST',
      body: {
        root_path: rootPath,
        combined_file: combinedFile,
        dry_run: !!opts.dryRun,
        overwrite: !!opts.overwrite,
      },
    }),

  combine: (rootPath, opts = {}) =>
    request('/combine', {
      method: 'POST',
      body: {
        root_path: rootPath,
        output_filename: opts.outputFilename ?? null,
        add_summary_table: !!opts.addSummaryTable,
        metadata_map: opts.metadataMap ?? null,
        dry_run: !!opts.dryRun,
      },
    }),

  listFromMaster: (rootPath, opts = {}) =>
    request('/list/from-master', {
      method: 'POST',
      body: { root_path: rootPath, dry_run: !!opts.dryRun },
    }),

  listFromCombined: (rootPath, combinedFiles, opts = {}) =>
    request('/list/from-combined', {
      method: 'POST',
      body: {
        root_path: rootPath,
        combined_files: combinedFiles,
        dry_run: !!opts.dryRun,
      },
    }),

  listOpen: (rootPath) =>
    request('/list/open', { method: 'POST', body: { root_path: rootPath } }),

  caseParse: (caseFile) =>
    request('/case/parse', { method: 'POST', body: { case_file: caseFile } }),

  evidencePack: (rootPath, caseFile, opts = {}) =>
    request('/evidence-pack', {
      method: 'POST',
      body: {
        root_path: rootPath,
        case_file: caseFile,
        add_summary_table: opts.addSummaryTable !== false,
        metadata_map: opts.metadataMap ?? null,
        dry_run: !!opts.dryRun,
      },
    }),

  masterTable: (rootPath) =>
    request('/master/table', { params: { root_path: rootPath } }),
};
