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
  masterClear: (root_path, dry_run = false) =>
    post('/api/master/clear', { root_path, dry_run }),
  combinedList: (root_path) => post('/api/combined/list', { root_path }),
  split: (root_path, combined_file, force_overwrite = false, dry_run = false) =>
    post('/api/split', { root_path, combined_file, force_overwrite, dry_run }),
  listOpen: (root_path) => post('/api/list/open', { root_path }),
  listAutoCreate: (root_path, source, combined_file, dry_run = false) =>
    post('/api/list/auto-create', { root_path, source, combined_file, dry_run }),
  listParse: (root_path) => post('/api/list/parse', { root_path }),
  combine: (root_path, output_filename, include_evidence_table = false, dry_run = false) =>
    post('/api/combine', { root_path, output_filename, include_evidence_table, dry_run }),
  caseParse: (case_file) => post('/api/case/parse', { case_file }),
  caseBuildCombined: (
    root_path,
    case_file,
    output_filename,
    table_data = [],
    dry_run = false,
    force_continue = false,
  ) =>
    post('/api/case/build-combined', {
      root_path,
      case_file,
      output_filename,
      table_data,
      dry_run,
      force_continue,
    }),
  openBackup: (root_path) => post('/api/backup/open', { root_path }),
};
