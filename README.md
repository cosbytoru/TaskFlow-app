Dockerized ToDo App (Flask, PostgreSQL, Docker-Compose)
FlaskとPostgreSQLで作成したWeb ToDoアプリを、Docker Composeで完全にコンテナ化したプロジェクトです。

docker compose upコマンド一発で、アプリケーションとデータベースが起動します。
開発環境のセットアップが非常に簡単で、誰でも同じ環境を再現できます。
Flask-Migrateを導入し、データベースのスキーマ変更をコードで管理しています。
動作環境
Docker
Docker Compose (Docker Engineのプラグインとして)
セットアップ & 実行手順
1. リポジトリをクローン
Bash

git clone git@github.com:あなたのユーザー名/docker-todo-app.git
cd docker-todo-app
2. コンテナのビルドと起動
以下のコマンドで、Dockerコンテナをビルドし、バックグラウンドで起動します。

Bash

docker compose up --build -d
3. データベースの初期化
初回起動時のみ、以下のコマンドを実行してデータベース内にテーブルを作成します。（別のターミナルを開いて実行する必要はありません）

Bash

docker compose exec web flask db upgrade
これでセットアップは完了です！
ブラウザで http://localhost:5001 にアクセスしてください。

データベースの更新方法（開発者向け）
app.py内のモデル（UserクラスやTaskクラスなど）に変更を加えた場合は、以下のコマンドでデータベースのスキーマを更新します。

マイグレーションファイルの自動生成
モデルの変更点を検出し、更新用の指示書（マイグレーションファイル）を作成します。

Bash

docker compose exec web flask db migrate -m "変更内容の要約（例: Add due_date to Task）"
データベースへの適用
生成された指示書を元に、データベースのテーブル構造を更新します。

Bash

docker compose exec web flask db upgrade