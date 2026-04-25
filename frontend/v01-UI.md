// v01-UI.md — Gemini 製 UI モック（リファレンス用、クリーン版）
//
// チャットで受領した内容から markdown エスケープ (`\[` `\]` `\=\>` 等) と
// 自動リンク化 (`[e.target](http://e.target).value` 等) を除去したもの。
// このファイル自体は実装では使われない。本実装は frontend/src/App.jsx を参照。

import React, { useState } from 'react';
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
  FileText
} from 'lucide-react';

export default function App() {
  const [rootPath, setRootPath] = useState('I:\\マイドライブ\\2026年度\\学園案件\\訴訟用・懲戒請求共通資料作成\\令和8年（ワ）第131号');
  const [logs, setLogs] = useState([]);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [modalAction, setModalAction] = useState(null);

  // モック用のテーブルデータ
  const mockTableData = [
    { id: '甲第００１号証', name: '令和〇年〇月〇日付 保護者説明会配布資料', date: '令和8年4月1日', author: '被告（〇〇学園）', purpose: '保護者に対して事前の説明を行っていた事実の証明' },
    { id: '甲第００２号証の１', name: '〇〇会議議事録（前半）', date: '令和8年5月10日', author: '原告', purpose: '5月10日の会議において、〇〇について合意がなされたこと' },
    { id: '甲第００２号証の２', name: '〇〇会議議事録（後半）', date: '令和8年5月10日', author: '原告', purpose: '同上' },
  ];

  const addLog = (message, type = 'info') => {
    const time = new Date().toLocaleTimeString();
    setLogs(prev => [`[${time}] ${message}`, ...prev]);
  };

  const handleSetPath = () => {
    addLog(`ルートフォルダを設定しました: ${rootPath}`, 'success');
    addLog('フォルダ構成をチェックしています...');
    addLog('✅ 「甲号証リスト.docx」を確認/作成しました。');
    addLog('✅ 「個別マスタ」フォルダを確認/作成しました。');
    addLog('✅ 「結合甲号証」フォルダを確認/作成しました。');
  };

  const executeAction = (actionName, description) => {
    addLog(`⏳ 処理開始: ${actionName}`);
    addLog(`詳細: ${description}`);
    // モック処理の完了をシミュレート
    setTimeout(() => {
      addLog(`✅ 処理完了: ${actionName}`, 'success');
    }, 1500);
  };

  const handleSplitConfirm = () => {
    setShowConfirmModal(true);
    setModalAction(() => () => {
      executeAction('結合甲号証の分解', '結合ファイルを解析し、「甲第xxx号証」の区切りでWordファイルを分割。表記ゆれを全角3桁に統一し「個別マスタ」に保存します。');
      setShowConfirmModal(false);
    });
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
            ローカルファイルモード (Simulation)
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

          {/* 左側：操作パネル */}
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
                  onClick={() => executeAction('甲号証リストに従って結合', '甲号証リストの順序に従い、個別マスタ内のファイルを結合して新しい結合ファイルを作成します。')}
                  className="flex flex-col items-start p-4 border border-blue-200 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  <div className="flex items-center mb-2 text-blue-700 font-medium">
                    <Combine className="w-5 h-5 mr-2" />
                    個別マスタの結合
                  </div>
                  <p className="text-sm text-left text-blue-600/80">リストに従い、個別ファイルを一つに結合します。</p>
                </button>
              </div>
            </section>

            {/* リスト・テーブル操作 */}
            <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h2 className="text-lg font-semibold mb-4 text-gray-800 border-b pb-2">リスト・証拠説明書の作成</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <button
                  onClick={() => executeAction('甲号証リストの編集', 'Wordアプリケーションを起動し、「甲号証リスト.docx」を開きます。')}
                  className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <FileText className="w-5 h-5 mr-3 text-gray-500" />
                  <span className="font-medium text-gray-700">甲号証リストをWordで開く</span>
                </button>

                <div className="flex border border-gray-200 rounded-lg overflow-hidden">
                  <select className="bg-gray-50 px-3 border-r border-gray-200 text-sm focus:outline-none" id="listSource">
                    <option value="master">個別マスタから</option>
                    <option value="combined">結合甲号証から</option>
                  </select>
                  <button
                    onClick={() => {
                      const source = document.getElementById('listSource').value;
                      executeAction('甲号証リストの自動作成', `${source === 'master' ? '個別マスタ' : '結合甲号証'} の内容を解析し、リストを自動生成します。`);
                    }}
                    className="flex-1 bg-white hover:bg-gray-50 px-4 py-3 font-medium text-gray-700 transition-colors text-left"
                  >
                    リスト自動作成
                  </button>
                </div>
              </div>

              <button
                onClick={() => executeAction('証拠一覧テーブル付き結合ファイルの作成', '案件ファイルから号証を抽出し、証拠説明書（一覧テーブル）を先頭に付与した完全な結合甲号証を作成します。')}
                className="w-full flex items-center justify-center p-4 border border-green-200 bg-green-50 rounded-lg hover:bg-green-100 transition-colors text-green-700 font-medium"
              >
                <ListOrdered className="w-5 h-5 mr-2" />
                【案件ファイル基準】一覧テーブル付き結合甲号証の作成
              </button>
            </section>

            {/* プレビューエリア（証拠説明書） */}
            <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <h2 className="text-lg font-semibold mb-4 text-gray-800 flex items-center">
                <FileBox className="w-5 h-5 mr-2 text-indigo-500" />
                証拠説明書（一覧テーブル）プレビュー
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse border border-gray-300">
                  <thead className="bg-gray-100 text-gray-700">
                    <tr>
                      <th className="border border-gray-300 p-2 whitespace-nowrap">号証</th>
                      <th className="border border-gray-300 p-2 min-w-[200px]">標目（証拠の名称）</th>
                      <th className="border border-gray-300 p-2 whitespace-nowrap">作成年月日</th>
                      <th className="border border-gray-300 p-2 whitespace-nowrap">作成者</th>
                      <th className="border border-gray-300 p-2 min-w-[300px]">立証趣旨（証明事項）</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mockTableData.map((row, idx) => (
                      <tr key={idx} className="bg-white hover:bg-gray-50">
                        <td className="border border-gray-300 p-2 font-medium">{row.id}</td>
                        <td className="border border-gray-300 p-2">{row.name}</td>
                        <td className="border border-gray-300 p-2">{row.date}</td>
                        <td className="border border-gray-300 p-2">{row.author}</td>
                        <td className="border border-gray-300 p-2">{row.purpose}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          {/* 右側：実行ログ */}
          <div className="lg:col-span-1">
            <section className="bg-gray-900 rounded-xl shadow-sm overflow-hidden h-[600px] flex flex-col">
              <div className="p-4 bg-gray-800 border-b border-gray-700 flex justify-between items-center">
                <h2 className="text-sm font-semibold text-gray-200 flex items-center">
                  システムログ
                </h2>
                <button
                  onClick={() => setLogs([])}
                  className="text-xs text-gray-400 hover:text-white"
                >
                  クリア
                </button>
              </div>
              <div className="p-4 flex-1 overflow-y-auto font-mono text-xs text-green-400 space-y-2">
                {logs.length === 0 ? (
                  <span className="text-gray-500">待機中...</span>
                ) : (
                  logs.map((log, i) => (
                    <div key={i} className={`${log.includes('✅') ? 'text-blue-300' : log.includes('⏳') ? 'text-yellow-300' : 'text-green-400'} break-all`}>
                      {log}
                    </div>
                  ))
                )}
              </div>
            </section>

            {/* 表記ゆれ補正ルールの説明パネル */}
            <div className="mt-4 p-4 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-800">
              <h3 className="font-bold mb-2 flex items-center">
                <CheckCircle className="w-4 h-4 mr-1" />
                自動補正ルール (バックエンド仕様)
              </h3>
              <ul className="list-disc pl-4 space-y-1 opacity-80">
                <li>甲第〇〇号証の番号は「全角数字3桁」に強制統一されます。<br/>例: <code>甲第1号証</code> → <code>甲第００１号証</code></li>
                <li>枝番も認識し処理します。<br/>例: <code>その1</code>, <code>の１</code> → <code>の１</code></li>
                <li>分解時の区切りはページ先頭の「甲第xxx号証」の行単位で判別します。</li>
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
              「個別マスタ」フォルダ内に既にファイルが存在します。<br/>
              結合甲号証を分解して保存すると、既存のファイルはすべて消去・上書きされますがよろしいですか？
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
                消去して分解を実行
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
