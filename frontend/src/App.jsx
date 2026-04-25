import React, { useCallback, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  FolderOpen,
  Hourglass,
  Layers,
  ListChecks,
  Pencil,
  RefreshCcw,
  Scissors,
  Settings,
  Sparkles,
  Trash2,
  Wand2,
  XCircle,
} from 'lucide-react';
import { api } from './api.js';

function nowStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

const ICONS = {
  info: <Hourglass className="w-4 h-4 text-amber-500" />,
  ok: <CheckCircle2 className="w-4 h-4 text-emerald-600" />,
  err: <XCircle className="w-4 h-4 text-rose-600" />,
};

function useLog() {
  const [log, setLog] = useState([]);
  const push = useCallback((kind, msg) => {
    setLog((prev) => [...prev, { kind, msg, time: nowStamp() }].slice(-200));
  }, []);
  return { log, push, clear: () => setLog([]) };
}

function Section({ title, icon: Icon, children }) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-3">
      <h2 className="flex items-center gap-2 text-base font-bold text-slate-800">
        {Icon ? <Icon className="w-4 h-4 text-slate-600" /> : null}
        {title}
      </h2>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function Btn({ children, onClick, disabled, kind = 'primary', icon: Icon }) {
  const base =
    'inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed';
  const styles = {
    primary: 'bg-slate-900 text-white hover:bg-slate-700',
    secondary: 'bg-white text-slate-800 border border-slate-300 hover:bg-slate-50',
    danger: 'bg-rose-600 text-white hover:bg-rose-500',
    accent: 'bg-emerald-600 text-white hover:bg-emerald-500',
  };
  return (
    <button onClick={onClick} disabled={disabled} className={`${base} ${styles[kind]}`}>
      {Icon ? <Icon className="w-4 h-4" /> : null}
      {children}
    </button>
  );
}

function ConfirmModal({ open, title, body, onCancel, onConfirm, confirmLabel = '実行' }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/40 z-40 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-5 space-y-4">
        <div className="flex items-center gap-2 text-amber-600">
          <AlertTriangle className="w-5 h-5" />
          <h3 className="font-bold">{title}</h3>
        </div>
        <div className="text-sm text-slate-700 whitespace-pre-line">{body}</div>
        <div className="flex justify-end gap-2 pt-2">
          <Btn kind="secondary" onClick={onCancel}>
            キャンセル
          </Btn>
          <Btn kind="danger" onClick={onConfirm}>
            {confirmLabel}
          </Btn>
        </div>
      </div>
    </div>
  );
}

function EvidenceTableEditor({ rows, onChange }) {
  if (!rows.length) return null;
  const updateCell = (idx, key, value) => {
    const next = rows.map((r, i) => (i === idx ? { ...r, [key]: value } : r));
    onChange(next);
  };
  return (
    <div className="overflow-x-auto border border-slate-200 rounded-lg">
      <table className="w-full text-sm">
        <thead className="bg-slate-100 text-slate-700">
          <tr>
            {['号証', '標目', '作成年月日', '作成者', '立証趣旨'].map((h) => (
              <th key={h} className="px-3 py-2 text-left font-semibold border-b border-slate-200">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.label} className="even:bg-slate-50">
              <td className="px-3 py-1.5 font-mono whitespace-nowrap border-b border-slate-100">
                {r.label}
              </td>
              {['title', 'date', 'author', 'purpose'].map((k) => (
                <td key={k} className="px-1 py-1 border-b border-slate-100">
                  <input
                    className="w-full px-2 py-1 rounded border border-transparent focus:border-slate-300 focus:bg-white"
                    value={r[k] ?? ''}
                    onChange={(e) => updateCell(i, k, e.target.value)}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const { log, push, clear: clearLog } = useLog();
  const [rootPath, setRootPath] = useState('');
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState({ masterCount: 0, listCount: 0 });

  const [combinedFiles, setCombinedFiles] = useState([]);
  const [selectedCombined, setSelectedCombined] = useState('');

  const [listLabels, setListLabels] = useState([]);
  const [listSource, setListSource] = useState('master');

  const [combineFilename, setCombineFilename] = useState('結合甲号証.docx');
  const [includeTable, setIncludeTable] = useState(false);

  const [caseFile, setCaseFile] = useState('');
  const [caseLabels, setCaseLabels] = useState([]);
  const [caseTableRows, setCaseTableRows] = useState([]);
  const [caseOutput, setCaseOutput] = useState('結合甲号証_完成.docx');

  const [splitConfirm, setSplitConfirm] = useState(false);
  const [pendingSplit, setPendingSplit] = useState(null);

  const ensureRoot = useCallback(() => {
    if (!rootPath) {
      push('err', 'ルートフォルダを指定してください。');
      return false;
    }
    return true;
  }, [rootPath, push]);

  const run = useCallback(
    async (label, fn) => {
      setBusy(true);
      push('info', `${label} を開始しました。`);
      try {
        const result = await fn();
        push('ok', `${label} が完了しました。`);
        return result;
      } catch (e) {
        push('err', `${label} に失敗: ${e.message}`);
        throw e;
      } finally {
        setBusy(false);
      }
    },
    [push],
  );

  const refreshSummary = useCallback(
    async (path = rootPath) => {
      if (!path) return;
      const [m, c, l] = await Promise.all([
        api.masterList(path),
        api.combinedList(path),
        api.listParse(path),
      ]);
      setSummary({ masterCount: m.files.length, listCount: l.count });
      setCombinedFiles(c.files);
      setSelectedCombined((prev) => (c.files.includes(prev) ? prev : c.files[0] ?? ''));
      setListLabels(l.labels);
    },
    [rootPath],
  );

  const handleSetup = async () => {
    if (!ensureRoot()) return;
    await run('設定・構成確認', async () => {
      const res = await api.setup(rootPath);
      res.messages.forEach((m) => push('ok', m));
      await refreshSummary();
    });
  };

  const handleSplitClick = async () => {
    if (!ensureRoot()) return;
    if (!selectedCombined) {
      push('err', '分解する結合甲号証ファイルを選択してください。');
      return;
    }
    await run('結合甲号証の分解', async () => {
      const master = await api.masterList(rootPath);
      if (!master.is_empty) {
        setPendingSplit({ combined: selectedCombined });
        setSplitConfirm(true);
        push('info', '個別マスタが空ではありません。確認モーダルで選択してください。');
        return;
      }
      const res = await api.split(rootPath, selectedCombined, true);
      res.extracted.forEach((e) => push('ok', `→ ${e.label}`));
      await refreshSummary();
    });
  };

  const confirmSplit = async () => {
    setSplitConfirm(false);
    const target = pendingSplit?.combined;
    setPendingSplit(null);
    if (!target) return;
    await run('個別マスタを消去して分解', async () => {
      const res = await api.split(rootPath, target, true);
      res.extracted.forEach((e) => push('ok', `→ ${e.label}`));
      await refreshSummary();
    });
  };

  const handleListOpen = async () => {
    if (!ensureRoot()) return;
    await run('甲号証リストを Word で開く', () => api.listOpen(rootPath));
  };

  const handleListAutoCreate = async () => {
    if (!ensureRoot()) return;
    if (listSource === 'combined' && !selectedCombined) {
      push('err', '結合甲号証ファイルを選択してください。');
      return;
    }
    await run('甲号証リストの自動作成', async () => {
      const res = await api.listAutoCreate(
        rootPath,
        listSource,
        listSource === 'combined' ? selectedCombined : undefined,
      );
      push('ok', `${res.count} 件のラベルを書き出しました。`);
      await refreshSummary();
    });
  };

  const handleCombine = async () => {
    if (!ensureRoot()) return;
    if (!combineFilename.trim()) {
      push('err', '出力ファイル名を入力してください。');
      return;
    }
    await run('個別マスタの結合', async () => {
      const res = await api.combine(rootPath, combineFilename.trim(), includeTable);
      push('ok', `保存先: ${res.output_path}`);
      if (res.missing.length)
        push('err', `不足ファイル: ${res.missing.join(', ')}`);
      await refreshSummary();
    });
  };

  const handleCaseParse = async () => {
    if (!caseFile.trim()) {
      push('err', '案件ファイルのパスを入力してください。');
      return;
    }
    await run('案件ファイル解析', async () => {
      const res = await api.caseParse(caseFile.trim());
      setCaseLabels(res.labels);
      setCaseTableRows(
        res.labels.map((label) => ({
          label,
          title: '',
          date: '',
          author: '',
          purpose: '',
        })),
      );
      push('ok', `${res.labels.length} 件の号証を抽出しました。`);
    });
  };

  const handleCaseBuild = async () => {
    if (!ensureRoot()) return;
    if (!caseFile.trim()) {
      push('err', '案件ファイルを指定してください。');
      return;
    }
    if (!caseOutput.trim()) {
      push('err', '出力ファイル名を入力してください。');
      return;
    }
    await run('案件ファイル基準の結合甲号証作成', async () => {
      const res = await api.caseBuildCombined(
        rootPath,
        caseFile.trim(),
        caseOutput.trim(),
        caseTableRows,
      );
      push('ok', `保存先: ${res.output_path}`);
      if (res.missing.length)
        push('err', `不足ファイル: ${res.missing.join(', ')}`);
      await refreshSummary();
    });
  };

  const handleClearMaster = async () => {
    if (!ensureRoot()) return;
    if (!window.confirm('個別マスタの全ファイルを削除します。よろしいですか？')) return;
    await run('個別マスタを空にする', async () => {
      await api.masterClear(rootPath);
      await refreshSummary();
    });
  };

  const summaryNode = useMemo(
    () => (
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
        <div className="rounded bg-slate-50 border border-slate-200 px-3 py-2">
          個別マスタ: <span className="font-bold">{summary.masterCount}</span> 件
        </div>
        <div className="rounded bg-slate-50 border border-slate-200 px-3 py-2">
          リスト行数: <span className="font-bold">{summary.listCount}</span>
        </div>
        <div className="rounded bg-slate-50 border border-slate-200 px-3 py-2">
          結合甲号証ファイル数: <span className="font-bold">{combinedFiles.length}</span>
        </div>
      </div>
    ),
    [summary, combinedFiles],
  );

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="bg-slate-900 text-white px-6 py-4 shadow">
        <h1 className="text-lg font-bold flex items-center gap-2">
          <FileText className="w-5 h-5" />
          甲号証管理アプリ
        </h1>
        <p className="text-xs text-slate-300 mt-0.5">
          訴訟用 甲号証 の結合・分解・一覧表作成を半自動化します。
        </p>
      </header>

      <main className="max-w-6xl mx-auto p-4 lg:p-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Section title="① ルートフォルダ設定" icon={Settings}>
          <input
            className="w-full px-3 py-2 rounded border border-slate-300 text-sm font-mono"
            placeholder="例: I:\マイドライブ\令和8年（ワ）第131号"
            value={rootPath}
            onChange={(e) => setRootPath(e.target.value)}
          />
          <div className="flex gap-2 flex-wrap">
            <Btn icon={Settings} onClick={handleSetup} disabled={busy}>
              設定・構成確認
            </Btn>
            <Btn kind="secondary" icon={RefreshCcw} onClick={() => refreshSummary()} disabled={busy || !rootPath}>
              情報を再取得
            </Btn>
          </div>
          {summaryNode}
        </Section>

        <Section title="② 結合甲号証 → 個別マスタ" icon={Scissors}>
          <label className="block text-xs text-slate-600">
            分解対象（結合甲号証フォルダ内）
          </label>
          <select
            className="w-full px-3 py-2 rounded border border-slate-300 text-sm"
            value={selectedCombined}
            onChange={(e) => setSelectedCombined(e.target.value)}
            disabled={busy || !combinedFiles.length}
          >
            {combinedFiles.length === 0 && <option value="">（ファイルなし）</option>}
            {combinedFiles.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
          <div className="flex gap-2 flex-wrap">
            <Btn icon={Scissors} onClick={handleSplitClick} disabled={busy || !selectedCombined}>
              結合甲号証の分解
            </Btn>
            <Btn kind="danger" icon={Trash2} onClick={handleClearMaster} disabled={busy || !rootPath}>
              個別マスタを空にする
            </Btn>
          </div>
        </Section>

        <Section title="③ 甲号証リスト操作" icon={ListChecks}>
          <div className="flex gap-2 flex-wrap items-center">
            <Btn kind="secondary" icon={FolderOpen} onClick={handleListOpen} disabled={busy || !rootPath}>
              甲号証リストを Word で開く
            </Btn>
            <select
              className="px-2 py-1.5 rounded border border-slate-300 text-sm"
              value={listSource}
              onChange={(e) => setListSource(e.target.value)}
              disabled={busy}
            >
              <option value="master">個別マスタから自動作成</option>
              <option value="combined">結合甲号証から自動作成</option>
            </select>
            <Btn icon={Wand2} onClick={handleListAutoCreate} disabled={busy || !rootPath}>
              リスト自動作成
            </Btn>
          </div>
          <div className="border border-slate-200 rounded p-2 max-h-40 overflow-auto bg-slate-50">
            {listLabels.length ? (
              <ol className="list-decimal pl-5 text-sm space-y-0.5">
                {listLabels.map((l) => (
                  <li key={l} className="font-mono">
                    {l}
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-xs text-slate-500">甲号証リストは空です。</p>
            )}
          </div>
        </Section>

        <Section title="④ 個別マスタ → 結合甲号証" icon={Layers}>
          <div className="flex gap-2 flex-wrap items-center">
            <input
              className="flex-1 min-w-[12rem] px-3 py-2 rounded border border-slate-300 text-sm"
              value={combineFilename}
              onChange={(e) => setCombineFilename(e.target.value)}
              placeholder="出力ファイル名 (例: 結合甲号証.docx)"
            />
            <label className="text-xs text-slate-700 flex items-center gap-1">
              <input
                type="checkbox"
                checked={includeTable}
                onChange={(e) => setIncludeTable(e.target.checked)}
              />
              証拠説明書テーブルを先頭に追加
            </label>
          </div>
          <Btn icon={Layers} onClick={handleCombine} disabled={busy || !rootPath}>
            個別マスタの結合
          </Btn>
        </Section>

        <Section title="⑤ 案件ファイル基準で結合 + 証拠説明書" icon={Sparkles}>
          <div className="space-y-2">
            <label className="block text-xs text-slate-600">案件ファイル (.docx) のパス</label>
            <input
              className="w-full px-3 py-2 rounded border border-slate-300 text-sm font-mono"
              placeholder="例: C:\\path\\to\\訴状.docx"
              value={caseFile}
              onChange={(e) => setCaseFile(e.target.value)}
            />
            <div className="flex gap-2 flex-wrap">
              <Btn kind="secondary" icon={Pencil} onClick={handleCaseParse} disabled={busy || !caseFile}>
                号証を抽出
              </Btn>
              <input
                className="flex-1 min-w-[12rem] px-3 py-2 rounded border border-slate-300 text-sm"
                value={caseOutput}
                onChange={(e) => setCaseOutput(e.target.value)}
                placeholder="出力ファイル名"
              />
              <Btn
                kind="accent"
                icon={Sparkles}
                onClick={handleCaseBuild}
                disabled={busy || !rootPath || !caseFile}
              >
                結合甲号証を作成
              </Btn>
            </div>
            {caseLabels.length > 0 && (
              <p className="text-xs text-slate-600">
                抽出された号証: {caseLabels.length} 件 — 下のテーブルで証拠説明書を編集できます。
              </p>
            )}
            <EvidenceTableEditor rows={caseTableRows} onChange={setCaseTableRows} />
          </div>
        </Section>

        <Section title="⑥ ログ" icon={ListChecks}>
          <div className="flex justify-end">
            <Btn kind="secondary" onClick={clearLog} disabled={busy}>
              ログをクリア
            </Btn>
          </div>
          <div className="border border-slate-200 rounded h-64 overflow-auto bg-slate-50 p-3 text-sm font-mono space-y-1">
            {log.length === 0 ? (
              <p className="text-slate-400">まだ操作はありません。</p>
            ) : (
              log.map((entry, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-2 ${
                    entry.kind === 'err' ? 'text-rose-600' : 'text-slate-700'
                  }`}
                >
                  <span className="text-slate-400">[{entry.time}]</span>
                  {ICONS[entry.kind]}
                  <span className="break-words">{entry.msg}</span>
                </div>
              ))
            )}
          </div>
        </Section>
      </main>

      <ConfirmModal
        open={splitConfirm}
        title="個別マスタを上書きします"
        body={`現在、個別マスタには ${summary.masterCount} 件のファイルが存在します。\n分解を続けるとこれらは すべて削除 されます。よろしいですか？`}
        onCancel={() => {
          setSplitConfirm(false);
          setPendingSplit(null);
        }}
        onConfirm={confirmSplit}
        confirmLabel="消去して分解を実行"
      />
    </div>
  );
}
