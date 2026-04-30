import React, { useState, useEffect } from 'react';
import {
  FolderOpen,
  FileBox,
  Split,
  Combine,
  FileSignature,
  AlertTriangle,
  CheckCircle,
  Settings,
  Edit3,
  Sparkles,
  Save,
  Loader2
} from 'lucide-react';

export default function App() {
  const [rootPath, setRootPath] = useState('');
  const [logs, setLogs] = useState([]);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [modalAction, setModalAction] = useState(null);
  const [tableEntries, setTableEntries] = useState([]);
  const [isConfigured, setIsConfigured] = useState(false);

  // メタデータ状態
  // normalized_key → { title, created_date, author, purpose, dirty, extracting, saving, error }
  const [metadata, setMetadata] = useState({});

  // ログ追加ヘルパー
  const addLog = (message, type = 'info') => {
    const time = new Date().toLocaleTimeString();
    setLogs(prev => [{ time, message, type }, ...prev]);
  };

  // 行のメタデータを取得(無ければデフォルト)
  const getRow = (key) => metadata[key] || {
    title: '',
    created_date: '',
    author: '',
    purpose: '',
    dirty: false,
    extracting: false,
    saving: false,
    error: false
  };

  // 構成確認(モック)
  const handleSetPath = () => {
    if (!rootPath.trim()) {
      addLog('ルートフォルダを入力してください。', 'warn');
      return;
    }
    addLog('フォルダ構成をチェックしています...', 'info');
    setTimeout(() => {
      addLog('✅ 個別マスタのディレクトリ構成を確認しました。', 'ok');
      setIsConfigured(true);
      // モックデータ(.docx に修正、枝番表記を「その」に統一 — SPEC.md §7.1.4 準拠)
      setTableEntries([
        { id: '甲第００１号証', filename: '甲第００１号証.docx' },
        { id: '甲第００２号証その１', filename: '甲第００２号証その１.docx' },
        { id: '甲第００２号証その２', filename: '甲第００２号証その２.docx' }
      ]);
      // GET /api/metadata で取得した確定値で初期化(モック:空)
      setMetadata({});
    }, 500);
  };

  // 分解処理(モック)
  const handleSplitConfirm = () => {
    if (!isConfigured) {
      addLog('先にルートフォルダを設定してください。', 'warn');
      return;
    }
    setShowConfirmModal(true);
    setModalAction(() => () => {
      addLog('処理開始: 結合甲号証の分解', 'info');
      setTimeout(() => {
        addLog('✅ 新規作成 3 件: 甲第００１号証.docx、甲第００２号証その１.docx、甲第００２号証その２.docx', 'ok');
        addLog('✅ 処理完了: 結合甲号証の分解', 'ok');
        setShowConfirmModal(false);
      }, 1000);
    });
  };

  // 結合処理(モック)
  const handleMerge = () => {
    if (!isConfigured) {
      addLog('先にルートフォルダを設定してください。', 'warn');
      return;
    }
    addLog('処理開始: 個別マスタの結合', 'info');
    setTimeout(() => {
      addLog('結合ファイル: I:\\マイドライブ\\...\\結合甲号証.docx', 'ok');
      addLog('結合 3 件: 甲第００１号証.docx、甲第００２号証その１.docx、甲第００２号証その２.docx', 'ok');
      addLog('✅ 処理完了: 個別マスタの結合', 'ok');
    }, 1500);
  };

  // ===== 証拠説明書テーブル: 新規ハンドラ =====

  // フィールド変更
  const handleFieldChange = (key, field, value) => {
    setMetadata(prev => ({
      ...prev,
      [key]: { ...getRow(key), [field]: value, dirty: true, error: false }
    }));
  };

  // 編集ボタン: ファイルを既定アプリで開く
  // 実装時:POST /api/master/open に置き換え
  const handleEditFile = (key) => {
    addLog(`Word を起動: ${key}`, 'info');
    setTimeout(() => {
      addLog(`✅ ファイルを開きました: ${key}`, 'ok');
    }, 300);
  };

  // 自動入力ボタン: AI 抽出
  // 実装時:POST /api/metadata/extract に置き換え。
  // 下書きを取得してフォームにプリフィル(保存はしない、ユーザーが「保存」を押す)
  const handleExtract = (key) => {
    setMetadata(prev => ({
      ...prev,
      [key]: { ...getRow(key), extracting: true, error: false }
    }));
    addLog(`処理開始: ${key} の自動入力`, 'info');
    setTimeout(() => {
      // モック応答(本番は §10.5.2 の JSON を受け取る)
      const mockDraft = {
        title: `(下書き)${key} の標目`,
        created_date: '令和○年○月○日',
        author: '(下書き)作成者',
        purpose: `(下書き)${key} に基づき、被告の○○の事実を立証する。`
      };
      setMetadata(prev => ({
        ...prev,
        [key]: { ...getRow(key), ...mockDraft, dirty: true, extracting: false, error: false }
      }));
      addLog(`✅ 自動入力完了: ${key}(内容を確認して保存してください)`, 'ok');
    }, 1200);
  };

  // 保存ボタン: 1 行分のメタデータを保存
  // 実装時:PUT /api/metadata/{normalized_key} に置き換え
  const handleSaveRow = (key) => {
    const row = getRow(key);
    if (!row.dirty) return;
    setMetadata(prev => ({
      ...prev,
      [key]: { ...row, saving: true, error: false }
    }));
    addLog(`処理開始: ${key} の保存`, 'info');
    setTimeout(() => {
      setMetadata(prev => ({
        ...prev,
        [key]: { ...prev[key], saving: false, dirty: false, error: false }
      }));
      addLog(`✅ 保存完了: ${key}`, 'ok');
    }, 600);
  };

  // 行の左端ボーダー色を状態から決定
  const getRowBorderClass = (row) => {
    if (row.error) return 'border-l-4 border-l-red-500';
    if (row.dirty) return 'border-l-4 border-l-orange-400';
    return 'border-l-4 border-l-transparent';
  };

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
            ローカルファイルモード
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
              placeholder="例: I:\マイドライブ\..."
            />
            <button
              onClick={handleSetPath}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium whitespace-nowrap"
            >
              設定・構成確認
            </button>
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* 左側:操作パネル */}
          <div className="lg:col-span-2 space-y-6">

            {/* メインアクション */}
            <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h2 className="text-lg font-semibold mb-4 text-gray-800 border-b pb-2">証拠ファイルの操作</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                <button
                  onClick={handleSplitConfirm}
                  className="flex flex-col items-start p-4 border border-orange-200 bg-orange-50 rounded-lg hover:bg-orange-100 transition-colors"
                >
                  <div className="flex items-center mb-2 text-orange-700 font-medium">
                    <Split className="w-5 h-5 mr-2" />
                    結合甲号証の分解
                  </div>
                  <p className="text-sm text-left text-orange-600/80">結合ファイルを分解し「個別マスタ」に保存します。</p>
                </button>

                <button
                  onClick={handleMerge}
                  className="flex flex-col items-start p-4 border border-blue-200 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  <div className="flex items-center mb-2 text-blue-700 font-medium">
                    <Combine className="w-5 h-5 mr-2" />
                    個別マスタの結合
                  </div>
                  <p className="text-sm text-left text-blue-600/80">個別マスタ内のファイルを番号順に一つに結合します。</p>
                </button>
              </div>
            </section>

            {/* 証拠説明書(一覧テーブル) — 編集機能付き */}
            <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800 flex items-center">
                  <FileBox className="w-5 h-5 mr-2 text-indigo-500" />
                  証拠説明書(一覧テーブル)
                </h2>
                <button className="text-xs text-gray-500 hover:text-gray-700" onClick={handleSetPath}>
                  再読込
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead className="bg-gray-100 text-gray-700">
                    <tr>
                      <th className="border border-gray-300 p-2 whitespace-nowrap text-center w-16">編集</th>
                      <th className="border border-gray-300 p-2 whitespace-nowrap text-center w-20">自動入力</th>
                      <th className="border border-gray-300 p-2 whitespace-nowrap">号証</th>
                      <th className="border border-gray-300 p-2 min-w-[180px]">標目</th>
                      <th className="border border-gray-300 p-2 whitespace-nowrap min-w-[140px]">作成年月日</th>
                      <th className="border border-gray-300 p-2 whitespace-nowrap min-w-[140px]">作成者</th>
                      <th className="border border-gray-300 p-2 min-w-[280px]">立証趣旨</th>
                      <th className="border border-gray-300 p-2 whitespace-nowrap text-center w-16">保存</th>
                    </tr>
                  </thead>
                  <tbody>
                    {!isConfigured ? (
                      <tr>
                        <td colSpan="8" className="border border-gray-300 p-3 text-center text-gray-500">
                          ルートフォルダを設定してください。
                        </td>
                      </tr>
                    ) : tableEntries.length === 0 ? (
                      <tr>
                        <td colSpan="8" className="border border-gray-300 p-3 text-center text-gray-500">
                          個別マスタにファイルがありません。
                        </td>
                      </tr>
                    ) : (
                      tableEntries.map((row) => {
                        const meta = getRow(row.id);
                        return (
                          <tr key={row.id} className={`bg-white hover:bg-gray-50 ${getRowBorderClass(meta)}`}>
                            {/* 編集ボタン */}
                            <td className="border border-gray-300 p-2 text-center">
                              <button
                                onClick={() => handleEditFile(row.id)}
                                className="p-2 rounded hover:bg-blue-50 text-blue-600 transition-colors"
                                title="Word で開く"
                              >
                                <Edit3 className="w-4 h-4" />
                              </button>
                            </td>

                            {/* 自動入力ボタン */}
                            <td className="border border-gray-300 p-2 text-center">
                              <button
                                onClick={() => handleExtract(row.id)}
                                disabled={meta.extracting}
                                className="p-2 rounded hover:bg-indigo-50 text-indigo-600 disabled:opacity-50 disabled:hover:bg-transparent transition-colors"
                                title="AI で自動入力(下書きを生成。確認後に保存ボタンで確定)"
                              >
                                {meta.extracting ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <Sparkles className="w-4 h-4" />
                                )}
                              </button>
                            </td>

                            {/* 号証 */}
                            <td className="border border-gray-300 p-2 font-medium whitespace-nowrap">{row.id}</td>

                            {/* 標目 */}
                            <td className="border border-gray-300 p-1">
                              <input
                                type="text"
                                value={meta.title}
                                onChange={(e) => handleFieldChange(row.id, 'title', e.target.value)}
                                className="w-full p-1 border border-transparent hover:border-gray-300 focus:border-blue-400 focus:outline-none rounded"
                              />
                            </td>

                            {/* 作成年月日 */}
                            <td className="border border-gray-300 p-1">
                              <input
                                type="text"
                                value={meta.created_date}
                                onChange={(e) => handleFieldChange(row.id, 'created_date', e.target.value)}
                                className="w-full p-1 border border-transparent hover:border-gray-300 focus:border-blue-400 focus:outline-none rounded"
                              />
                            </td>

                            {/* 作成者 */}
                            <td className="border border-gray-300 p-1">
                              <input
                                type="text"
                                value={meta.author}
                                onChange={(e) => handleFieldChange(row.id, 'author', e.target.value)}
                                className="w-full p-1 border border-transparent hover:border-gray-300 focus:border-blue-400 focus:outline-none rounded"
                              />
                            </td>

                            {/* 立証趣旨(複数行) */}
                            <td className="border border-gray-300 p-1">
                              <textarea
                                value={meta.purpose}
                                onChange={(e) => handleFieldChange(row.id, 'purpose', e.target.value)}
                                rows={3}
                                className="w-full p-1 border border-transparent hover:border-gray-300 focus:border-blue-400 focus:outline-none rounded resize-y"
                              />
                            </td>

                            {/* 保存ボタン */}
                            <td className="border border-gray-300 p-2 text-center">
                              <button
                                onClick={() => handleSaveRow(row.id)}
                                disabled={!meta.dirty || meta.saving}
                                className="p-2 rounded hover:bg-green-50 text-green-600 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                                title={meta.dirty ? "保存" : "変更がないため保存不要"}
                              >
                                {meta.saving ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <Save className="w-4 h-4" />
                                )}
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* 凡例 */}
              {isConfigured && tableEntries.length > 0 && (
                <div className="mt-3 flex items-center space-x-4 text-xs text-gray-500">
                  <span className="flex items-center">
                    <span className="inline-block w-1 h-3 bg-orange-400 mr-1"></span>
                    未保存の編集あり
                  </span>
                  <span className="flex items-center">
                    <span className="inline-block w-1 h-3 bg-red-500 mr-1"></span>
                    エラー
                  </span>
                </div>
              )}
            </section>

          </div>

          {/* 右側:実行ログ */}
          <div className="lg:col-span-1">
            <section className="bg-gray-900 rounded-xl shadow-sm overflow-hidden h-[600px] flex flex-col">
              <div className="p-4 bg-gray-800 border-b border-gray-700 flex justify-between items-center">
                <h2 className="text-sm font-semibold text-gray-200">
                  システムログ
                </h2>
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
                  logs.map((log, i) => {
                    let cls = "text-green-400";
                    if (log.type === "ok") cls = "text-blue-300";
                    else if (log.type === "warn") cls = "text-yellow-300";
                    else if (log.type === "err") cls = "text-red-400";
                    return (
                      <div key={i} className={`${cls} break-all`}>
                        [{log.time}] {log.message}
                      </div>
                    );
                  })
                )}
              </div>
            </section>

            {/* 自動補正ルールの説明パネル(SPEC.md §6.2.3 と整合する形に修正) */}
            <div className="mt-4 p-4 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-800">
              <h3 className="font-bold mb-2 flex items-center">
                <CheckCircle className="w-4 h-4 mr-1" />
                自動補正ルール (バックエンド仕様)
              </h3>
              <ul className="list-disc pl-4 space-y-1 opacity-80">
                <li>甲第〇〇号証の番号は「全角数字3桁」に強制統一されます。<br />例: <code>甲第1号証</code> → <code>甲第００１号証</code></li>
                <li>枝番も認識し処理します。<br />例: <code>その1</code>、<code>の１</code> → <code>その１</code></li>
                <li>分解時の区切りは、<strong>ページ先頭にある</strong>「【甲第〇〇〇号証】」<strong>のみ</strong>を区切りとして判定します(本文中の引用は対象外)。</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* モーダル */}
      {showConfirmModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-xl max-w-md w-full">
            <div className="flex items-center text-orange-600 mb-4">
              <AlertTriangle className="w-6 h-6 mr-2" />
              <h3 className="text-lg font-bold">警告: 個別マスタの上書き</h3>
            </div>
            <p className="text-gray-700 mb-6 text-sm">
              「個別マスタ」フォルダ内に既にファイルが存在します。<br />
              結合甲号証を分解して保存すると、既存のファイルはすべて上書きされますがよろしいですか?
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium"
              >
                キャンセル
              </button>
              <button
                onClick={modalAction}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 font-medium"
              >
                上書きして分解を実行
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
