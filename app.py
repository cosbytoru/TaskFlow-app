# app.py

import os # <-- 追加
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a_default_fallback_secret_key') # <-- 変更: 環境変数から読み込む

# --- データベース接続情報 ---
DB_USER = os.environ.get("POSTGRES_USER", "postgres") # <-- 変更
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "mysecretpassword") # <-- 変更
DB_HOST = os.environ.get("DB_HOST", "db") # <-- 変更 (通常はdocker-composeのサービス名)
DB_PORT = os.environ.get("DB_PORT", "5432") # <-- 変更
DB_NAME = os.environ.get("POSTGRES_DB", "postgres") # <-- 変更
# SQLAlchemyのデータベースURIを構築
DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- Flask-SQLAlchemyとFlask-Migrateの設定 ---
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # 推奨設定
db = SQLAlchemy(app) # <-- SQLAlchemyのインスタンスを作成
migrate = Migrate(app, db) # <-- Migrateのインスタンスを作成

# --- Flask-Loginの設定 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- データベースモデル（ここからがORMの核心です） ---

# usersテーブルに対応するモデル
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # Taskモデルとのリレーションシップを定義
    tasks = db.relationship('Task', backref='owner', lazy=True, cascade="all, delete-orphan")

# tasksテーブルに対応するモデル
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    due_date = db.Column(db.Date, nullable=True) # <-- 追加
    priority = db.Column(db.Integer, nullable=True, default=2) # <-- 追加 (1:低, 2:中, 3:高)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # SubTaskモデルとのリレーションシップを定義 (一対多)
    subtasks = db.relationship('SubTask', backref='task', lazy=True, cascade="all, delete-orphan")

class SubTask(db.Model):
    __tablename__ = 'subtasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# 優先度表示用のヘルパー関数
def get_priority_display(priority_val):
    if priority_val == 1:
        return "低"
    if priority_val == 3:
        return "高"
    return "中"


# --- ルーティング ---
@app.route('/')
@login_required
def index():
    try:
        # ベースとなるクエリ
        query = Task.query.filter_by(owner=current_user)

        # 絞り込み (フィルタリング)
        filter_status = request.args.get('filter_status')
        if filter_status == 'completed':
            query = query.filter_by(completed=True)
        elif filter_status == 'incomplete':
            query = query.filter_by(completed=False)
        # 'all' または指定なしの場合は、全てのタスクを表示

        # 検索機能
        search_term = request.args.get('search_term')
        if search_term:
            query = query.filter(Task.title.ilike(f'%{search_term}%')) # 大文字・小文字を区別しない検索

        # 並び替え機能
        sort_by = request.args.get('sort_by', 'id') # デフォルトはID順
        sort_order = request.args.get('sort_order', 'asc') # デフォルトは昇順

        if sort_by == 'priority':
            # 優先度 (1:低, 2:中, 3:高)。昇順なら低→高、降順なら高→低。
            # 優先度が同じ場合はID順で安定ソート
            if sort_order == 'desc':
                query = query.order_by(Task.priority.desc(), Task.id.asc())
            else:
                query = query.order_by(Task.priority.asc(), Task.id.asc())
        elif sort_by == 'due_date':
            # 期限日。期限日がないタスク (NULL) の扱いを考慮
            # 期限日が同じ場合はID順で安定ソート
            if sort_order == 'desc':
                # 降順の場合、NULLを先頭 (nullsfirst) または末尾 (nullslast) に表示
                query = query.order_by(Task.due_date.desc().nullsfirst(), Task.id.asc())
            else:
                # 昇順の場合、NULLを末尾に表示
                query = query.order_by(Task.due_date.asc().nullslast(), Task.id.asc())
        else: # 'id' または未定義のキー
            sort_by = 'id' # 正規化
            if sort_order == 'desc':
                query = query.order_by(Task.id.desc())
            else:
                query = query.order_by(Task.id.asc())

        tasks = query.all()
    except Exception as error:
        flash(f"タスクの読み込み中にエラー: {error}", "danger")
        tasks = [] # エラー時は空のリスト
    return render_template('index.html', tasks=tasks, current_sort_by=sort_by, 
                           current_sort_order=sort_order, current_filter_status=filter_status, 
                           current_search_term=search_term)


@app.route('/add', methods=['POST'])
@login_required
def add_task():
    if request.is_json:
        data = request.get_json()
        title = data.get('title')
        due_date_str = data.get('due_date')
        priority = data.get('priority', 2)
    else:
        title = request.form.get('title')
        due_date_str = request.form.get('due_date')
        priority = request.form.get('priority', type=int, default=2)

    if not title: # タイトルが空の場合にエラーとする
        message = "タスクのタイトルを入力してください。"
        if request.is_json:
            return jsonify({'status': 'error', 'message': message}), 400
        else:
            flash(message, "warning")
            return redirect(url_for('index'))

    try:
        new_task = Task(title=title, owner=current_user, priority=int(priority))
        if due_date_str:
            new_task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        db.session.add(new_task)
        db.session.commit()
        message = f"タスク「{title}」を追加しました。"
        if request.is_json:
            task_data = {
                'id': new_task.id, 'title': new_task.title, 'completed': new_task.completed,
                'due_date': new_task.due_date.strftime('%Y-%m-%d') if new_task.due_date else None,
                'priority': new_task.priority,
                'priority_display': get_priority_display(new_task.priority)
            }
            return jsonify({'status': 'success', 'message': message, 'task': task_data})
        else:
            flash(message, "success")
    except Exception as error:
        print("タスクの追加中にエラーが発生しました:", error)
        db.session.rollback()
        message = "タスクの追加中にエラーが発生しました。"
        if request.is_json:
            return jsonify({'status': 'error', 'message': message}), 500
        else:
            flash(message, "danger")
    # HTMLフォームからのリクエストの場合、ソート等のパラメータを引き継ぐ
    # フォームから送信されたソート情報を取得 (デフォルト値を設定)
    redirect_sort_by = request.form.get('current_sort_by', 'id')
    redirect_sort_order = request.form.get('current_sort_order', 'asc')
    redirect_filter_status = request.form.get('current_filter_status')
    redirect_search_term = request.form.get('current_search_term')
    return redirect(url_for(
        'index',
        sort_by=redirect_sort_by,
        sort_order=redirect_sort_order,
        filter_status=redirect_filter_status,
        search_term=redirect_search_term
    ))


@app.route('/complete/<int:task_id>')
@login_required
def complete_task(task_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    try:
        task = Task.query.filter_by(id=task_id, owner=current_user).first()
        if task:
            task.completed = True
            db.session.commit()
            message = f"タスクID {task_id} を完了にしました。"
            if is_ajax:
                task_data = {
                    'id': task.id, 'title': task.title, 'completed': task.completed,
                    'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else None,
                    'priority': task.priority, 'priority_display': get_priority_display(task.priority)
                }
                return jsonify({'status': 'success', 'message': message, 'task': task_data})
            else:
                flash(message, "success")
        else:
            message = f"タスクID {task_id} が見つからないか、権限がありません。"
            if is_ajax:
                return jsonify({'status': 'error', 'message': message}), 404 if not task else 403
            else:
                flash(message, "warning")
    except Exception as error:
        print("タスクの完了中にエラーが発生しました:", error)
        db.session.rollback()
        message = f"タスクID {task_id} の完了処理中にエラーが発生しました。"
        if is_ajax:
            return jsonify({'status': 'error', 'message': message}), 500
        else:
            flash(message, "danger")
    return redirect(url_for('index'))


# タスクの削除
@app.route('/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    try:
        task = Task.query.filter_by(id=task_id, owner=current_user).first()
        if task:
            db.session.delete(task)
            db.session.commit()
            message = f"タスクID {task_id} を削除しました。"
            if is_ajax:
                return jsonify({'status': 'success', 'message': message})
            else:
                flash(message, "success")
        else:
            message = f"タスクID {task_id} が見つからないか、権限がありません。"
            if is_ajax:
                return jsonify({'status': 'error', 'message': message}), 404 if not task else 403
            else:
                flash(message, "warning")
    except Exception as error:
        print(f"タスク {task_id} の削除中にエラーが発生しました:", error)
        db.session.rollback()
        message = f"タスクID {task_id} の削除中にエラーが発生しました。"
        if is_ajax:
            return jsonify({'status': 'error', 'message': message}), 500
        else:
            flash(message, "danger")
    return redirect(url_for('index'))


@app.route('/reactivate/<int:task_id>')
@login_required
def reactivate_task(task_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    try:
        task = Task.query.filter_by(id=task_id, owner=current_user).first()
        if task:
            task.completed = False
            db.session.commit()
            message = f"タスクID {task_id} を未完了に戻しました。"
            if is_ajax:
                task_data = {
                    'id': task.id, 'title': task.title, 'completed': task.completed,
                    'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else None,
                    'priority': task.priority, 'priority_display': get_priority_display(task.priority)
                }
                return jsonify({'status': 'success', 'message': message, 'task': task_data})
            else:
                flash(message, "success")
        else:
            message = f"タスクID {task_id} が見つからないか、権限がありません。"
            if is_ajax:
                return jsonify({'status': 'error', 'message': message}), 404 if not task else 403
            else:
                flash(message, "warning")
    except Exception as error:
        print("タスクの再活性化中にエラーが発生しました:", error)
        db.session.rollback()
        message = f"タスクID {task_id} の再活性化中にエラーが発生しました。"
        if is_ajax:
            return jsonify({'status': 'error', 'message': message}), 500
        else:
            flash(message, "danger")
    return redirect(url_for('index'))


@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task_to_edit = Task.query.filter_by(id=task_id, owner=current_user).first_or_404()
    if request.method == 'POST':
        new_title = request.form.get('title')
        new_due_date_str = request.form.get('due_date')
        new_priority = request.form.get('priority', type=int, default=task_to_edit.priority) # 編集時に指定がなければ既存の値

        if new_title:
            try:
                task_to_edit.title = new_title # <-- 修正: task -> task_to_edit
                if new_due_date_str:
                    task_to_edit.due_date = datetime.strptime(new_due_date_str, '%Y-%m-%d').date()
                else:
                    task_to_edit.due_date = None # 日付が空の場合はNoneを設定
                task_to_edit.priority = new_priority
                db.session.commit()
                flash(f"タスクID {task_id} のタイトルを「{new_title}」に更新しました。", "success")
            except Exception as error:
                print(f"タスクID {task_id} の更新中にエラーが発生しました: {error}")
                db.session.rollback()
                flash(f"タスクID {task_id} の更新中にエラーが発生しました。", "danger")
        else:
            flash("新しいタスクのタイトルを入力してください。", "warning")
        return redirect(url_for('index'))

    # GETリクエストでは、取得したtask_to_editオブジェクトをテンプレートに渡す
    return render_template('edit.html', task=task_to_edit)

# --- サブタスク関連のルート ---
@app.route('/subtask/add/<int:task_id>', methods=['POST'])
@login_required
def add_subtask(task_id):
    task = Task.query.filter_by(id=task_id, owner=current_user).first_or_404()
    title = request.form.get('subtask_title')

    if not title:
        flash("サブタスクのタイトルを入力してください。", "warning")
        return redirect(url_for('index', _anchor=f'task-{task.id}'))

    try:
        new_subtask = SubTask(title=title, task_id=task.id)
        db.session.add(new_subtask)
        db.session.commit()
        flash(f"サブタスク「{title}」をタスク「{task.title}」に追加しました。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"サブタスクの追加中にエラーが発生しました: {e}", "danger")
    return redirect(url_for('index', _anchor=f'task-{task.id}'))


@app.route('/subtask/toggle/<int:subtask_id>', methods=['POST'])
@login_required
def toggle_subtask(subtask_id):
    subtask = SubTask.query.get_or_404(subtask_id)
    if subtask.task.owner != current_user:
        flash("権限がありません。", "danger")
        # AJAXリクエストの場合、適切なエラーコードを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': '権限がありません。'}), 403
        return redirect(url_for('index'))

    try:
        subtask.completed = not subtask.completed
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'success',
                'message': f"サブタスク「{subtask.title}」の状態を更新しました。",
                'subtask': {'id': subtask.id, 'title': subtask.title, 'completed': subtask.completed}
            })
        flash(f"サブタスク「{subtask.title}」の状態を更新しました。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"サブタスクの状態更新中にエラーが発生しました: {e}", "danger")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': f"サブタスクの状態更新中にエラー: {e}"}), 500
    return redirect(url_for('index', _anchor=f'task-{subtask.task_id}'))

# --- 認証ルート ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user_exists = User.query.filter_by(username=username).first()

        if user_exists:
            flash("そのユーザー名は既に使用されています。", "warning")
            return redirect(url_for('signup'))

        try:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("アカウントが作成されました。ログインしてください。", "success")
            return redirect(url_for('login'))
        except Exception as error:
            print(f"ユーザー登録中にエラーが発生しました: {error}")
            db.session.rollback()
            flash("アカウント作成中にエラーが発生しました。", "danger")
            return redirect(url_for('signup'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user) # Flask-Loginのlogin_user関数
            flash("ログインしました。", "success")
            return redirect(url_for('index'))
        else:
            flash("ユーザー名またはパスワードが正しくありません。", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("ログアウトしました。", "info")
    return redirect(url_for('login'))

# --- プロファイル編集ルート ---
@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        # 現在のパスワードを確認
        if not check_password_hash(current_user.password_hash, current_password):
            flash('現在のパスワードが正しくありません。', 'danger')
            return redirect(url_for('edit_profile'))

        # 新しいパスワードが入力されているか確認
        if not new_password:
            flash('新しいパスワードを入力してください。', 'warning')
            return redirect(url_for('edit_profile'))

        # 新しいパスワードと確認用パスワードが一致するか確認
        if new_password != confirm_new_password:
            flash('新しいパスワードと確認用パスワードが一致しません。', 'danger')
            return redirect(url_for('edit_profile'))

        try:
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('パスワードが正常に更新されました。', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'パスワード更新中にエラーが発生しました: {e}', 'danger')
    return render_template('edit_profile.html')


if __name__ == '__main__':
    # from datetime import datetime # グローバルスコープに移動したため削除
    app.run(debug=True, host='0.0.0.0', port=5001)
