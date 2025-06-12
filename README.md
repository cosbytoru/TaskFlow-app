✨ 主な機能
ユーザー認証: 安全なサインアップ、ログイン、ログアウト機能

タスク管理 (CRUD): タスクの追加、一覧表示、編集、削除

タスク状態管理: タスクの完了・未完了の切り替え

データベースマイグレーション: Flask-Migrateによるスキーマ変更管理

🛠️ 技術スタック
バックエンド: Flask

フロントエンド: HTML, Tailwind CSS

データベース: PostgreSQL

コンテナ化: Docker, Docker Compose

CI: GitHub Actions

Pythonライブラリ: Flask-SQLAlchemy, Flask-Login, Flask-Migrateなど（詳細はrequirements.txtを参照）

🚀 セットアップ & 実行手順
前提条件
Docker

Docker Compose (Docker Desktopに含まれています)

1. リポジトリをクローン
git clone https://github.com/cosbytoru/taskflow-app.git
cd taskflow-app

2. コンテナのビルドと起動
以下のコマンドで、Dockerコンテナをビルドし、バックグラウンドで起動します。

docker compose up --build -d

初回起動時にはイメージのビルドに数分かかることがあります。

3. データベースの初期化
初回起動時のみ、以下のコマンドを実行してデータベース内にテーブルを作成します。

docker compose exec web flask db upgrade

セットアップは以上です！
ブラウザで http://localhost:5001 にアクセスしてください。

🔧 データベースの更新方法（開発者向け）
app.py内のモデル（UserクラスやTaskクラス）に変更を加えた場合は、以下のコマンドでデータベースのスキーマを更新します。

マイグレーションファイルの自動生成
モデルの変更点を検出し、更新用のマイグレーションファイルを生成します。

docker compose exec web flask db migrate -m "変更内容の要約（例: Add due_date to Task）"

データベースへの適用
生成されたファイルを元に、データベースのテーブル構造を更新します。

docker compose exec web flask db upgrade
