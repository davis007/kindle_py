import os
import sqlite3
import subprocess
from flask import Flask, render_template, request, send_file, abort, url_for
from pdf2image import convert_from_path
from datetime import datetime
import unicodedata
import urllib.parse

app = Flask(__name__)

# テンプレート用のフィルタを追加
@app.template_filter('basename')
def basename_filter(path):
    return os.path.basename(path)
    
@app.template_filter('dirname')
def dirname_filter(path):
    return os.path.dirname(path)
    
BASE_DIR = '/Volumes/ARSTH-2TB/kindle本/'
DB_PATH = 'kindle_library.db'

def init_db():
    """データベースを初期化し、必要なテーブルを作成する"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # PDFファイル情報を保存するテーブルを作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pdf_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        normalized_filename TEXT NOT NULL,
        path TEXT NOT NULL,
        folder TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 既存のデータを削除（再構築のため）
    cursor.execute('DELETE FROM pdf_files')
    conn.commit()

    conn.close()

def get_folder_structure(path=''):
    full_path = os.path.join(BASE_DIR, path)
    structure = []
    for item in sorted(os.listdir(full_path)):
        if item.startswith('.'):
            continue
        item_path = os.path.join(full_path, item)
        if os.path.isdir(item_path):
            structure.append({
                'name': item,
                'path': os.path.join(path, item),
                'children': get_folder_structure(os.path.join(path, item))
            })
    return structure

def normalize_japanese(text):
    # まず NFC 正規化を行う（文字を合成形式にする）
    normalized = unicodedata.normalize('NFC', text.lower())
    # さらに NFKC 正規化を行い、互換性のある文字を標準形式に変換
    normalized = unicodedata.normalize('NFKC', normalized)
    print(f"Debug: Normalizing '{text}' to '{normalized}'")
    return normalized

def get_pdf_files(path, search_query=None):
    """SQLiteデータベースを使用してPDFファイルを検索する"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    pdfs = []
    print(f"Debug: Searching for PDFs in {path}")
    print(f"Debug: Search query: {search_query}")

    if search_query and search_query.strip():
        normalized_query = normalize_japanese(search_query)
        print(f"Debug: Normalized query: {normalized_query}")

        # 検索戦略を改善:
        # 1. 単純な部分一致検索（キーワードを含むファイル）
        # 2. 複数キーワード検索（すべてのキーワードを含むファイル）
        # 3. キーワード個別検索（いずれかのキーワードを含むファイル）

        results = []

        # 1. まず単純な部分一致検索を試みる（前方一致と部分一致を統合）
        print(f"Debug: Executing simple partial match query: %{normalized_query}%")
        cursor.execute('''
        SELECT id, path FROM pdf_files
        WHERE lower(normalized_filename) LIKE ?
        ORDER BY filename
        ''', (f'%{normalized_query}%',))

        partial_results = cursor.fetchall()
        print(f"Debug: Found {len(partial_results)} PDFs with partial match")
        print(f"Debug: Partial match results: {partial_results}")
        for row in partial_results:
            results.append(row[1])  # pathを追加

        # 2. 複数キーワードによる検索
        if ' ' in normalized_query:
            search_terms = normalized_query.split()
            print(f"Debug: Multiple search terms: {search_terms}")

            # 2a. すべてのキーワードを含むファイルを検索
            query_conditions = []
            query_params = []

            for term in search_terms:
                query_conditions.append("lower(normalized_filename) LIKE ?")
                query_params.append(f"%{term}%")

            # 検索条件を「AND」で結合
            conditions_sql = " AND ".join(query_conditions)

            print(f"Debug: Multi-keyword SQL query: {conditions_sql}")
            print(f"Debug: Query params: {query_params}")

            cursor.execute(f'''
            SELECT id, path FROM pdf_files
            WHERE {conditions_sql}
            ORDER BY filename
            ''', query_params)

            multi_results = cursor.fetchall()
            print(f"Debug: Found {len(multi_results)} PDFs with all keywords")
            print(f"Debug: Multi-keyword results: {multi_results}")

            # 重複を除外して追加
            for row in multi_results:
                if row[1] not in results:  # filenameで重複チェック
                    results.append(row[1])

            # 2b. 検索結果が少ない場合、各単語での検索も試す
            if len(results) < 5:
                print(f"Debug: Few results, trying individual keyword search")
                for term in search_terms:
                    print(f"Debug: Searching for individual term: {term}")
                    cursor.execute('''
                    SELECT id, path FROM pdf_files
                    WHERE lower(normalized_filename) LIKE ?
                    ORDER BY filename
                    ''', (f'%{term}%',))

                    term_results = cursor.fetchall()
                    print(f"Debug: Found {len(term_results)} PDFs with term '{term}'")

                    for row in term_results:
                        if row[1] not in results:  # filenameで重複チェック
                            results.append(row[1])

                print(f"Debug: Found {len(results)} total PDFs after individual keyword search")
    else:
        # 検索クエリがない場合は、指定されたパスのすべてのPDFを取得
        if path == '':
            # ルートディレクトリの場合
            cursor.execute('''
            SELECT path FROM pdf_files
            WHERE folder = ?
            ORDER BY filename
            ''', ('/'),)
        else:
            # サブディレクトリの場合
            cursor.execute('''
            SELECT path FROM pdf_files
            WHERE folder = ?
            ORDER BY filename
            ''', (path,))

        results = cursor.fetchall()

    for row in results:
        pdfs.append(row[0])
        print(f"Debug: Added PDF: {row[0]}")

    conn.close()

    print(f"Debug: Found total {len(pdfs)} PDFs for query '{search_query}'")
    return pdfs

def search_with_grep(search_query):
    """
    grepコマンドを使用してファイルシステムから直接PDFファイルを検索する
    """
    print(f"Debug: Using grep to search for '{search_query}'")

    try:
        # 検索クエリを正規化
        normalized_query = normalize_japanese(search_query)
        print(f"Debug: Normalized search query: {normalized_query}")

        # 検索クエリをURLエンコード
        encoded_query = urllib.parse.quote(normalized_query)
        print(f"Debug: URL-encoded search query: {encoded_query}")

        # ファイル内容を正規化して検索するためのコマンド
        # 注意: 実際のPDFファイル内容の検索は難しいため、ファイル名のみを対象とする
        cmd = f'find {BASE_DIR} -name "*.pdf" | python3 -c "import sys, os, unicodedata; print(\'\n\'.join([f for f in sys.stdin.read().splitlines() if unicodedata.normalize(\'NFKC\', unicodedata.normalize(\'NFC\', os.path.basename(f).lower())).find(\'{normalized_query}\') != -1]))"'
        print(f"Debug: Executing command: {cmd}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode != 0 and not result.stdout:
            print(f"Debug: grep search failed or found no results")
            return []

        # 結果を処理
        files = result.stdout.strip().split('\n')
        pdfs = []

        for file_path in files:
            if file_path:  # 空行をスキップ
                # ベースディレクトリからの相対パスを取得
                relative_path = os.path.relpath(file_path, BASE_DIR)
                pdfs.append(relative_path)  # ファイル名ではなく相対パスを追加
                print(f"Debug: grep found: {relative_path}")

        return pdfs
    except Exception as e:
        print(f"Debug: Error in grep search: {str(e)}")
        return []

@app.route('/')
@app.route('/<path:folder_path>')
def index(folder_path=''):
    folder_structure = get_folder_structure()

    # URLパラメータのエンコーディング問題を解決
    search_query = request.args.get('search', '')

    # 検索クエリをURLエンコードして処理
    if search_query:
        # デバッグ用に元のクエリを出力
        print(f"Debug: Original search query: {search_query}")

        # URLエンコードされた検索クエリを作成
        encoded_query = urllib.parse.quote(search_query)
        print(f"Debug: URL-encoded search query: {encoded_query}")

        # 検索クエリの取得
        print(f"Debug: Raw search query: {search_query}")





    # 検索クエリのエンコーディングを確認
    print(f"Debug: Raw search query: {search_query}")
    print(f"Debug: Request args: {request.args}")

    # 日本語検索キーワードに対する特別な処理
    if search_query:
        # 日本語文字が含まれているかチェック
        def contains_japanese(text):
            for ch in text:
                # Unicode ranges for Japanese characters:
                # Hiragana (3040-309F), Katakana (30A0-30FF), 
                # CJK Unified Ideographs/Kanji (4E00-9FFF)
                if ('\u3040' <= ch <= '\u309F' or  # Hiragana
                    '\u30A0' <= ch <= '\u30FF' or  # Katakana
                    '\u4E00' <= ch <= '\u9FFF'):   # Kanji
                    return True
            return False
        
        is_special_search = contains_japanese(search_query) or '\\u' in repr(search_query)
        
        if is_special_search:
            print(f"Debug: Special handling for Japanese terms like 'アドラー'")
            
            # 正規化された検索語を用意
            normalized_query = normalize_japanese(search_query)
            
            # デバッグ情報
            print(f"Debug: Original query: {search_query}")
            print(f"Debug: Normalized query: {normalized_query}")
            
            # 直接データベースに問い合わせ
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # LIKE句で検索
            cursor.execute('''
            SELECT id, path FROM pdf_files
            WHERE normalized_filename LIKE ?
            ORDER BY filename
            ''', (f'%{normalized_query}%',))
            
            direct_results = cursor.fetchall()
            conn.close()
            
            if direct_results:
                print(f"Debug: Direct search found {len(direct_results)} results")
                pdfs = [row[1] for row in direct_results]
                current_path = request.args.get('current_path', folder_path)
                
                # デバッグ情報 - PDFのパスを出力
                print("Debug: PDFs that will be displayed:")
                for pdf in pdfs:
                    print(f"  - {pdf} (type: {type(pdf)})")
                
                # 検索結果を表示
                return render_template('index.html',
                                    current_path=current_path,
                                    folder_structure=folder_structure,
                                    pdfs=pdfs,
                                    search_query=search_query)
            else:
                print(f"Debug: No results found in direct search, trying grep")
                # データベースで見つからない場合、grepを使用して検索
                pdfs = search_with_grep(search_query)
                if pdfs:
                    print(f"Debug: grep found {len(pdfs)} results")
                    current_path = request.args.get('current_path', folder_path)
                    
                    # デバッグ情報 - PDFのパスを出力
                    print("Debug: PDFs that will be displayed:")
                    for pdf in pdfs:
                        print(f"  - {pdf} (type: {type(pdf)})")
                    
                    return render_template('index.html',
                                        current_path=current_path,
                                        folder_structure=folder_structure,
                                        pdfs=pdfs,
                                        search_query=search_query)

    current_path = request.args.get('current_path', folder_path)

    print(f"Debug: Search query from request: {search_query}")
    print(f"Debug: Current path from request: {current_path}")

    # 通常の検索処理
    if search_query:
        pdfs = get_pdf_files(current_path, search_query)

        # 検索結果が見つからない場合、grepを使用して検索
        if not pdfs:
            print(f"Debug: No results found in database for '{search_query}', trying grep")
            pdfs = search_with_grep(search_query)
    else:
        pdfs = get_pdf_files(folder_path, search_query)

    print(f"Debug: Rendering template with {len(pdfs)} PDFs")
    print(f"Debug: Current path: {current_path if search_query else folder_path}")
    print(f"Debug: Search query: {search_query}")
    
    # デバッグ情報 - PDFのパスを出力
    print("Debug: PDFs that will be displayed:")
    for pdf in pdfs:
        print(f"  - {pdf} (type: {type(pdf)})")
    
    return render_template('index.html',
                           current_path=current_path if search_query else folder_path,
                           folder_structure=folder_structure,
                           pdfs=pdfs,
                           search_query=search_query)

@app.route('/thumbnail/<path:filename>')
def thumbnail(filename):
    full_path = os.path.join(BASE_DIR, filename)
    print(f"Debug: Thumbnail requested for {filename}")
    print(f"Debug: Full path: {full_path}")
    print(f"Debug: File exists: {os.path.exists(full_path)}")

    if not os.path.exists(full_path):
        print(f"Debug: File not found at {full_path}")
        # ファイルが見つからない場合はデフォルトのサムネイルを返す
        default_thumb = "thumbnails/default.png"
        if os.path.exists(default_thumb):
            return send_file(default_thumb, mimetype='image/png')
        abort(404)

    # ファイル名のみを使用してサムネイルを生成
    # パスではなくファイル名だけを使用することで、パスの問題を回避
    base_filename = os.path.basename(filename)

    # ファイル名をハッシュ化して一意のIDを生成
    import hashlib
    filename_hash = hashlib.md5(base_filename.encode('utf-8')).hexdigest()

    # サムネイルのパスを生成
    thumb_path = f"thumbnails/{filename_hash}.png"

    print(f"Debug: Base filename: {base_filename}")
    print(f"Debug: Filename hash: {filename_hash}")
    print(f"Debug: Thumbnail path: {thumb_path}")

    if not os.path.exists(thumb_path):
        print(f"Debug: Creating thumbnail at {thumb_path}")
        try:
            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
            images = convert_from_path(full_path, first_page=0, last_page=1)
            images[0].save(thumb_path, 'PNG')
            print(f"Debug: Thumbnail created successfully")
        except Exception as e:
            print(f"Debug: Error creating thumbnail: {str(e)}")
            # エラーが発生した場合はデフォルトのサムネイルを返す
            default_thumb = "thumbnails/default.png"
            if os.path.exists(default_thumb):
                return send_file(default_thumb, mimetype='image/png')
            abort(500)

    return send_file(thumb_path, mimetype='image/png')

@app.route('/view/<path:filename>')
def view_pdf(filename):
    full_path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(full_path):
        abort(404)
    pdf_url = url_for('get_pdf', filename=filename)
    return render_template('pdf_viewer.html', pdf_url=pdf_url)

@app.route('/get_pdf/<path:filename>')
def get_pdf(filename):
    full_path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(full_path):
        abort(404)
    return send_file(full_path, mimetype='application/pdf')

def generate_kindle_list(base_dir):
    """
    Kindleライブラリのリストを生成し、テキストファイルとSQLiteデータベースに保存する
    """
    output_filename = f"{datetime.now().strftime('%Y-%m-%d')}_kindleList.txt"

    # データベースを初期化（既存データを削除）
    init_db()

    # データベース接続
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(output_filename, 'w', encoding='utf-8') as f:
        for root, dirs, files in os.walk(base_dir):
            level = root.replace(base_dir, '').count(os.sep)
            folder_path = root.replace(base_dir, '')
            if folder_path == '':
                folder_path = '/'

            indent = ' ' * 4 * level
            f.write(f'{indent}{os.path.basename(root)}/\n')

            # サブディレクトリがあれば辞書順にソート
            dirs.sort()

            sub_indent = ' ' * 4 * (level + 1)
            for file in sorted(files):  # ファイル名を辞書順にソート
                if not file.startswith('.') and file.lower().endswith('.pdf'):
                    f.write(f'{sub_indent}{file}\n')

                    # ファイル名を正規化
                    normalized_filename = normalize_japanese(file)
                    print(f"Debug: Normalizing filename '{file}' to '{normalized_filename}'")

                    # PDFファイル情報をデータベースに保存
                    relative_path = os.path.relpath(os.path.join(root, file), base_dir)
                    cursor.execute('''
                    INSERT INTO pdf_files (filename, normalized_filename, path, folder)
                    VALUES (?, ?, ?, ?)
                    ''', (file, normalized_filename, relative_path, folder_path))

    conn.commit()
    conn.close()

    print(f"Kindleリストが {output_filename} に保存されました。")
    print(f"Kindleリストがデータベース {DB_PATH} に保存されました。")

@app.route('/generate_list')
def generate_list():
    generate_kindle_list(BASE_DIR)
    return "Kindleリストが生成されました。サーバーのログを確認してください。"

# アプリケーション起動時にDBを初期化し、書籍リストを生成
if __name__ == '__main__':
    # 起動時に必ずデータベース初期化と書籍リスト生成を実行
    generate_kindle_list(BASE_DIR)
    app.run(debug=True, host='127.0.0.1', port=8000)
