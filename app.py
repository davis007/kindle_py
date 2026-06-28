import glob
import hashlib
import os
import sqlite3
import subprocess
import unicodedata
from datetime import datetime

from flask import Flask, abort, render_template, request, send_file, url_for
from pdf2image import convert_from_path

app = Flask(__name__)

@app.template_filter('basename')
def basename_filter(path):
    return os.path.basename(path)

@app.template_filter('dirname')
def dirname_filter(path):
    return os.path.dirname(path)

BASE_DIR = '/Volumes/ARSTH-2TB/kindle本/'
DB_PATH = 'kindle_library.db'


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
    normalized = unicodedata.normalize('NFC', text.lower())
    return unicodedata.normalize('NFKC', normalized)


def search_with_grep(search_query):
    normalized_query = normalize_japanese(search_query)
    cmd = (
        f'find {BASE_DIR} -name "*.pdf" | python3 -c "'
        f'import sys, os, unicodedata; '
        f'print(\'\\n\'.join([f for f in sys.stdin.read().splitlines() '
        f'if unicodedata.normalize(\'NFKC\', unicodedata.normalize(\'NFC\', os.path.basename(f).lower()))'
        f'.find(\'{normalized_query}\') != -1]))"'
    )
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if not result.stdout:
            return []
        return [
            os.path.relpath(f, BASE_DIR)
            for f in result.stdout.strip().split('\n') if f
        ]
    except Exception:
        return []


def search_pdfs(query):
    """DB検索（部分一致→AND→OR）→ 結果なければ grep フォールバック"""
    normalized = normalize_japanese(query)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        'SELECT path FROM pdf_files WHERE normalized_filename LIKE ? ORDER BY filename',
        (f'%{normalized}%',)
    )
    results = [row[0] for row in cursor.fetchall()]

    if not results and ' ' in normalized:
        terms = normalized.split()
        conditions = ' AND '.join(['normalized_filename LIKE ?' for _ in terms])
        cursor.execute(
            f'SELECT path FROM pdf_files WHERE {conditions} ORDER BY filename',
            [f'%{t}%' for t in terms]
        )
        results = [row[0] for row in cursor.fetchall()]

        if len(results) < 5:
            seen = set(results)
            for term in terms:
                cursor.execute(
                    'SELECT path FROM pdf_files WHERE normalized_filename LIKE ? ORDER BY filename',
                    (f'%{term}%',)
                )
                for row in cursor.fetchall():
                    if row[0] not in seen:
                        results.append(row[0])
                        seen.add(row[0])

    conn.close()

    if not results:
        results = search_with_grep(query)
    return results


def get_pdf_files(path):
    """指定フォルダのPDFファイルを取得"""
    folder = '/' if path == '' else path
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT path FROM pdf_files WHERE folder = ? ORDER BY filename',
        (folder,)
    )
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results


@app.route('/')
@app.route('/<path:folder_path>')
def index(folder_path=''):
    folder_structure = get_folder_structure()
    search_query = request.args.get('search', '')
    current_path = request.args.get('current_path', folder_path)

    if search_query:
        pdfs = search_pdfs(search_query)
    else:
        pdfs = get_pdf_files(folder_path)

    return render_template('index.html',
                           current_path=current_path if search_query else folder_path,
                           folder_structure=folder_structure,
                           pdfs=pdfs,
                           search_query=search_query)


@app.route('/thumbnail/<path:filename>')
def thumbnail(filename):
    full_path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(full_path):
        default_thumb = "thumbnails/default.png"
        if os.path.exists(default_thumb):
            return send_file(default_thumb, mimetype='image/png')
        abort(404)

    base_filename = os.path.basename(filename)
    filename_hash = hashlib.md5(base_filename.encode('utf-8')).hexdigest()
    thumb_path = f"thumbnails/{filename_hash}.png"

    if not os.path.exists(thumb_path):
        try:
            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
            images = convert_from_path(full_path, first_page=0, last_page=1)
            images[0].save(thumb_path, 'PNG')
        except Exception as e:
            print(f"サムネイル生成エラー: {e}")
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


def cleanup_old_kindle_lists(keep_filename):
    """最新1件を除いて古い kindleList.txt ファイルを削除する"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(script_dir, '*_kindleList.txt')
    for f in sorted(glob.glob(pattern)):
        if os.path.basename(f) != os.path.basename(keep_filename):
            os.remove(f)
            print(f"古いリストを削除しました: {f}")


def generate_kindle_list(base_dir):
    output_filename = f"{datetime.now().strftime('%Y-%m-%d')}_kindleList.txt"
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(output_filename, 'w', encoding='utf-8') as f:
        for root, dirs, files in os.walk(base_dir):
            level = root.replace(base_dir, '').count(os.sep)
            folder_path = root.replace(base_dir, '') or '/'

            indent = ' ' * 4 * level
            f.write(f'{indent}{os.path.basename(root)}/\n')
            dirs.sort()

            sub_indent = ' ' * 4 * (level + 1)
            for file in sorted(files):
                if not file.startswith('.') and file.lower().endswith('.pdf'):
                    f.write(f'{sub_indent}{file}\n')
                    normalized_filename = normalize_japanese(file)
                    relative_path = os.path.relpath(os.path.join(root, file), base_dir)
                    cursor.execute(
                        'INSERT INTO pdf_files (filename, normalized_filename, path, folder) VALUES (?, ?, ?, ?)',
                        (file, normalized_filename, relative_path, folder_path)
                    )

    conn.commit()
    conn.close()

    print(f"Kindleリストが {output_filename} に保存されました。")
    print(f"データベース {DB_PATH} を更新しました。")
    cleanup_old_kindle_lists(output_filename)


@app.route('/generate_list')
def generate_list():
    generate_kindle_list(BASE_DIR)
    return "Kindleリストが生成されました。"


if __name__ == '__main__':
    generate_kindle_list(BASE_DIR)
    app.run(debug=True, host='127.0.0.1', port=8000)
