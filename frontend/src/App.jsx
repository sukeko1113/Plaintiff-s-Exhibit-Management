import React, { useState, useCallback, useEffect } from 'react';
import {
  FolderOpen,
  FileBox,
  Split,
  Combine,
  ListOrdered,
  FileSignature,
  AlertTriangle,
  CheckCircle,
  Settings,
  FileText,
  RefreshCw,
} from 'lucide-react';
import { api } from './api.js';

const DEFAULT_ROOT =
  'I:\\マイドライブ\\2026年度\\学園案件\\訴訟用・懲戒請求共通資料作成\\令和8年（ワ）第131号';

export default function App() {
  const [rootPath, setRootPath] = useState(DEFAULT_ROOT);
  const [logs, setLogs] = useState([]);
  const [busy, setBusy] = useState(false);

  // データ
  const [combinedFiles, setCombinedFiles] = useState([]);
  const [selectedCombined, setSelectedCombined] = useState('');
  const [tableRows, setTableRows] = useState([]);
  const [caseFile, setCaseFile] = useState('');
  const [listSource, setListSource] = useState('master');
  const [addSummary, setAddSummary] = useState(true);

  // モーダル
  const [confirm, setConfirm] = useState(null);
  // confirm 形: { title, message, confirmLabel, onConfirm }

  const addLog = useCallback((message, level = 'info') => {
    const time = new Date().toLocaleTimeString();
    setLogs(prev => [{ time, message, level }, ...prev]);
  }, []);

  const formatError = (e) =>
    e?.message
      ? `${e.message}${e.detail ? ` (${e.detail})` : ''}`
      : String(e);

  const runAction = useCallback(async (label, fn) => {
    setBusy(true);
    addLog(`⏳ ${label}`, 'pending');
    try {
      const result = await fn();
      addLog(`✅ ${label} 完了`, 'success');
      return result;
    } catch (e) {
      addLog(`❌ ${label} 失敗: ${formatError(e)}`, 'error');
      throw e;
    } finally {
      setBusy(false);
    }
  }, [addLog]);

  // ---- ハンドラ ---------------------------------------------------

  const handleSetup = async () => {
    try {
      const result = await runAction('ルートフォルダ初期化', () => api.setup(rootPath));
      if (result.created.length) {
        addLog(`作成: ${result.created.join(', ')}`);
      }
      if (result.existed.length) {
        addLog(`既存: ${result.existed.join(', ')}`);
      }
      await refreshData();
    } catch { /* ログ出力済み */ }
  };

  const refreshData = useCallback(async () => {
    if (!rootPath) return;
    try {
      const [combined, table] = await Promise.all([
        api.combinedList(rootPath).catch(() => ({ files: [] })),
        api.masterTable(rootPath).catch(() => ({ rows: [] })),
      ]);
      setCombinedFiles(combined.files || []);
      setTableRows(table.rows || []);
      if ((combined.files || []).length && !selectedCombined) {
        setSelectedCombined(combined.files[0].path);
      }
    } catch (e) {
      addLog(`データ取得失敗: ${formatError(e)}`, 'error');
    }
  }, [rootPath, selectedCombined, addLog]);

  const handleSplit = async () => {
    if (!selectedCombined) {
      addLog('結合甲号証ファイルを選択してください', 'error');
      return;
    }
    let preview;
    try {
      preview = await runAction('分解 dry-run', () =>
        api.split(rootPath, selectedCombined, { dryRun: true }),
      );
    } catch { return; }

    addLog(`生成予定: ${preview.preview_files.length} 件`);

    const proceed = async (overwrite) => {
      try {
        const result = await runAction('結合甲号証を分解', () =>
          api.split(rootPath, selectedCombined, { overwrite }),
        );
        addLog(`生成: ${result.produced_files.length} 件`);
        if (result.backup_path) addLog(`バックアップ: ${result.backup_path}`);
        await refreshData();
      } catch { /* */ }
    };

    if (preview.existing_files_in_target.length > 0) {
      setConfirm({
        title: '個別マスタの上書き',
        message:
          `「個別マスタ」フォルダに既に ${preview.existing_files_in_target.length} 件のファイルがあります。\n` +
          'すべてバックアップ後に削除して、結合甲号証の分解を実行しますか？',
        confirmLabel: '消去して分解を実行',
        onConfirm: () => {
          setConfirm(null);
          proceed(true);
        },
      });
    } else {
      proceed(false);
    }
  };

  const handleCombine = async () => {
    try {
      const result = await runAction('個別マスタを結合', () =>
        api.combine(rootPath, { addSummaryTable: addSummary }),
      );
      addLog(`出力: ${result.output_file}`);
      addLog(`ソースファイル: ${result.source_count} 件`);
      await refreshData();
    } catch { /* */ }
  };

  const handleListOpen = async () => {
    try {
      const result = await runAction('甲号証リストを Word で開く', () =>
        api.listOpen(rootPath),
      );
      if (!result.opened) {
        addLog('OS 既定アプリで開けませんでした（Windows 以外の可能性）', 'error');
      } else {
        addLog(`開いたファイル: ${result.list_path}`);
      }
    } catch { /* */ }
  };

  const handleListBuild = async () => {
    try {
      if (listSource === 'master') {
        const result = await runAction('甲号証リスト自動作成（個別マスタから）', () =>
          api.listFromMaster(rootPath),
        );
        addLog(`ラベル数: ${result.labels.length}`);
        if (result.backup_path) addLog(`バックアップ: ${result.backup_path}`);
      } else {
        if (!selectedCombined) {
          addLog('結合甲号証ファイルを選択してください', 'error');
          return;
        }
        const result = await runAction('甲号証リスト自動作成（結合甲号証から）', () =>
          api.listFromCombined(rootPath, [selectedCombined]),
        );
        addLog(`ラベル数: ${result.labels.length}`);
        if (result.backup_path) addLog(`バックアップ: ${result.backup_path}`);
      }
    } catch { /* */ }
  };

  const handleEvidencePack = async () => {
    if (!caseFile) {
      addLog('案件ファイルのパスを入力してください', 'error');
      return;
    }
    let dry;
    try {
      dry = await runAction('案件ファイル解析（dry-run）', () =>
        api.evidencePack(rootPath, caseFile, { dryRun: true, addSummaryTable: addSummary }),
      );
    } catch { return; }

    addLog(`使用号証: ${dry.used_labels.length} 件 / 不足: ${dry.missing_labels.length} 件`);
    if (dry.missing_labels.length > 0) {
      addLog(`不足ラベル: ${dry.missing_labels.join(', ')}`, 'error');
      setConfirm({
        title: '個別マスタに不足あり',
        message:
          `案件ファイルが要求する号証のうち、個別マスタに無いものが ${dry.missing_labels.length} 件あります。\n` +
          `不足: ${dry.missing_labels.join(', ')}\n\n` +
          '存在する号証のみで結合を続行しますか？',
        confirmLabel: '続行',
        onConfirm: async () => {
          setConfirm(null);
          await runEvidencePack();
        },
      });
    } else {
      await runEvidencePack();
    }
  };

  const runEvidencePack = async () => {
    try {
      const result = await runAction('証拠説明書付き結合甲号証の作成', () =>
        api.evidencePack(rootPath, caseFile, { addSummaryTable: addSummary }),
      );
      addLog(`出力: ${result.output_file}`);
      await refreshData();
    } catch { /* */ }
  };

  // 初回ロード時にデータ取得
  useEffect(() => {
    refreshData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- レンダリング ----------------------------------------------

  return (
    <div className="min-h-screen bg-gray-50 p-6 font-sans text-gray-800">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* ヘッダー */}
        <header className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <FileSignature className="w-8 h-8 text-blue-600" />
            <h1 className="text-2xl font-bold text-gray-900">甲号証管理システム</h1>
          </div>
          <div className="text-sm text-gray-500 flex items-center">
            <Settings className="w-4 h-4 mr-1" />
            {busy ? '処理中…' : 'バックエンド: localhost:8765'}
          </div>
        </header>

        {/* ルートフォルダ設定 */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h2 className="text-lg font-semibold mb-4 flex items-center">
            <FolderOpen className="w-5 h-5 mr-2 text-blue-500" />
            ルートフォルダの設定
          </h2>
          <div className="flex space-x-2">
            <input
              type="text"
              value={rootPath}
              onChange={(e) => setRootPath(e.target.value)}
              className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none font-mono text-sm"
              placeholder="例: I:\\マイドライブ\\..."
              disabled={busy}
            />
            <button
              onClick={handleSetup}
              disabled={busy || !rootPath}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium whitespace-nowrap disabled:opacity-50"
            >
              設定・構成確認
            </button>
            <button
              onClick={refreshData}
              disabled={busy}
              title="一覧を再取得"
              className="bg-gray-200 text-gray-700 px-4 py-3 rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* 左側：操作パネル */}
          <div className="lg:col-span-2 space-y-6">

            {/* メインアクション */}
            <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h2 className="text-lg font-semibold mb-4 text-gray-800 border-b pb-2">証拠ファイルの操作</h2>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  対象の結合甲号証ファイル
                </label>
                <select
                  value={selectedCombined}
                  onChange={(e) => setSelectedCombined(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-lg text-sm bg-white"
                  disabled={busy}
                >
                  <option value="">— 結合甲号証フォルダから選択 —</option>
                  {combinedFiles.map((f) => (
                    <option key={f.path} value={f.path}>{f.name}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <button
                  onClick={handleSplit}
                  disabled={busy || !selectedCombined}
                  className="flex flex-col items-start p-4 border border-orange-200 bg-orange-50 rounded-lg hover:bg-orange-100 transition-colors disabled:opacity-50"
                >
                  <div className="flex items-center mb-2 text-orange-700 font-medium">
                    <Split className="w-5 h-5 mr-2" />
                    結合甲号証の分解
                  </div>
                  <p className="text-sm text-left text-orange-600/80">
                    結合ファイルを分解し「個別マスタ」に保存します。
                  </p>
                </button>

                <button
                  onClick={handleCombine}
                  disabled={busy}
                  className="flex flex-col items-start p-4 border border-blue-200 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50"
                >
                  <div className="flex items-center mb-2 text-blue-700 font-medium">
                    <Combine className="w-5 h-5 mr-2" />
                    個別マスタの結合
                  </div>
                  <p className="text-sm text-left text-blue-600/80">
                    番号順に個別マスタを結合します。
                  </p>
                </button>
              </div>

              <label className="mt-3 flex items-center text-sm text-gray-600">
                <input
                  type="checkbox"
                  checked={addSummary}
                  onChange={(e) => setAddSummary(e.target.checked)}
                  className="mr-2"
                />
                結合時に証拠説明書テーブルを先頭に挿入する
              </label>
            </section>

            {/* リスト・テーブル操作 */}
            <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h2 className="text-lg font-semibold mb-4 text-gray-800 border-b pb-2">
                リスト・証拠説明書の作成
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <button
                  onClick={handleListOpen}
                  disabled={busy}
                  className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                >
                  <FileText className="w-5 h-5 mr-3 text-gray-500" />
                  <span className="font-medium text-gray-700">甲号証リストを Word で開く</span>
                </button>

                <div className="flex border border-gray-200 rounded-lg overflow-hidden">
                  <select
                    value={listSource}
                    onChange={(e) => setListSource(e.target.value)}
                    className="bg-gray-50 px-3 border-r border-gray-200 text-sm focus:outline-none"
                    disabled={busy}
                  >
                    <option value="master">個別マスタから</option>
                    <option value="combined">結合甲号証から</option>
                  </select>
                  <button
                    onClick={handleListBuild}
                    disabled={busy}
                    className="flex-1 bg-white hover:bg-gray-50 px-4 py-3 font-medium text-gray-700 transition-colors text-left disabled:opacity-50"
                  >
                    リスト自動作成
                  </button>
                </div>
              </div>

              <div className="mb-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  案件ファイル（申立書等）の絶対パス
                </label>
                <input
                  type="text"
                  value={caseFile}
                  onChange={(e) => setCaseFile(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-lg font-mono text-sm"
                  placeholder="例: I:\\...\\申立書.docx"
                  disabled={busy}
                />
              </div>

              <button
                onClick={handleEvidencePack}
                disabled={busy || !caseFile}
                className="w-full flex items-center justify-center p-4 border border-green-200 bg-green-50 rounded-lg hover:bg-green-100 transition-colors text-green-700 font-medium disabled:opacity-50"
              >
                <ListOrdered className="w-5 h-5 mr-2" />
                【案件ファイル基準】証拠説明書付き結合甲号証の作成
              </button>
            </section>

            {/* プレビューエリア（証拠説明書） */}
            <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <h2 className="text-lg font-semibold mb-4 text-gray-800 flex items-center">
                <FileBox className="w-5 h-5 mr-2 text-indigo-500" />
                証拠説明書（一覧テーブル）プレビュー
                <span className="text-xs font-normal text-gray-500 ml-2">
                  個別マスタ {tableRows.length} 件
                </span>
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse border border-gray-300">
                  <thead className="bg-gray-100 text-gray-700">
                    <tr>
                      <th className="border border-gray-300 p-2 whitespace-nowrap">号証</th>
                      <th className="border border-gray-300 p-2 min-w-[200px]">標目</th>
                      <th className="border border-gray-300 p-2 whitespace-nowrap">作成年月日</th>
                      <th className="border border-gray-300 p-2 whitespace-nowrap">作成者</th>
                      <th className="border border-gray-300 p-2 min-w-[300px]">立証趣旨</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tableRows.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="border border-gray-300 p-3 text-center text-gray-400">
                          個別マスタが空、またはルートフォルダ未設定です。
                        </td>
                      </tr>
                    ) : (
                      tableRows.map((row, idx) => (
                        <tr key={idx} className="bg-white hover:bg-gray-50">
                          <td className="border border-gray-300 p-2 font-medium">{row.display_label}</td>
                          <td className="border border-gray-300 p-2">{row['標目']}</td>
                          <td className="border border-gray-300 p-2">{row['作成年月日']}</td>
                          <td className="border border-gray-300 p-2">{row['作成者']}</td>
                          <td className="border border-gray-300 p-2">{row['立証趣旨']}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          {/* 右側：実行ログ */}
          <div className="lg:col-span-1">
            <section className="bg-gray-900 rounded-xl shadow-sm overflow-hidden h-[600px] flex flex-col">
              <div className="p-4 bg-gray-800 border-b border-gray-700 flex justify-between items-center">
                <h2 className="text-sm font-semibold text-gray-200">システムログ</h2>
                <button
                  onClick={() => setLogs([])}
                  className="text-xs text-gray-400 hover:text-white"
                >
                  クリア
                </button>
              </div>
              <div className="p-4 flex-1 overflow-y-auto font-mono text-xs space-y-2">
                {logs.length === 0 ? (
                  <span className="text-gray-500">待機中...</span>
                ) : (
                  logs.map((log, i) => (
                    <div
                      key={i}
                      className={
                        log.level === 'error'
                          ? 'text-red-300 break-all'
                          : log.level === 'success'
                          ? 'text-blue-300 break-all'
                          : log.level === 'pending'
                          ? 'text-yellow-300 break-all'
                          : 'text-green-400 break-all'
                      }
                    >
                      [{log.time}] {log.message}
                    </div>
                  ))
                )}
              </div>
            </section>

            {/* 表記ゆれ補正ルールの説明パネル */}
            <div className="mt-4 p-4 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-800">
              <h3 className="font-bold mb-2 flex items-center">
                <CheckCircle className="w-4 h-4 mr-1" />
                自動補正ルール
              </h3>
              <ul className="list-disc pl-4 space-y-1 opacity-80">
                <li>甲号証の番号は <code>全角3桁</code> に統一されます。<br />例: <code>甲第1号証</code> → <code>甲第００１号証</code></li>
                <li>枝番（その / の / 枝）も認識し、<code>その全角</code> に正規化します。</li>
                <li>分解の区切りは段落単位の <code>【甲第xxx号証】</code> マーカー。</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* モーダル */}
      {confirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-xl max-w-md w-full">
            <div className="flex items-center text-orange-600 mb-4">
              <AlertTriangle className="w-6 h-6 mr-2" />
              <h3 className="text-lg font-bold">{confirm.title}</h3>
            </div>
            <p className="text-gray-700 mb-6 text-sm whitespace-pre-line">{confirm.message}</p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setConfirm(null)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium"
              >
                キャンセル
              </button>
              <button
                onClick={confirm.onConfirm}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 font-medium"
              >
                {confirm.confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
