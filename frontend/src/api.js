const BASE = 'http://127.0.0.1:8765';

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  });
  let data = null;
  try {
    data = await res.json();
  } catch (_) {
    /* ignore */
  }
  if (!res.ok) {
    const detail = (data && (data.detail || data.message)) || `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return data;
}

export const api = {
  setup: (root_path) => post('/api/setup', { root_path }),
  masterList: (root_path) => post('/api/master/list', { root_path }),
  masterClear: (root_path) => post('/api/master/clear', { root_path }),
  combinedList: (root_path) => post('/api/combined/list', { root_path }),
  split: (root_path, combined_file, force_overwrite = false) =>
    post('/api/split', { root_path, combined_file, force_overwrite }),
  listOpen: (root_path) => post('/api/list/open', { root_path }),
  listAutoCreate: (root_path, source, combined_filename) =>
    post('/api/list/auto-create', { root_path, source, combined_filename }),
  listParse: (root_path) => post('/api/list/parse', { root_path }),
  combine: (root_path, output_filename, include_evidence_table = false) =>
    post('/api/combine', { root_path, output_filename, include_evidence_table }),
  caseParse: (case_file) => post('/api/case/parse', { case_file }),
  caseBuildCombined: (root_path, case_file, output_filename, table_data = []) =>
    post('/api/case/build-combined', {
      root_path,
      case_file,
      output_filename,
      table_data,
    }),
};
