import psycopg2

# データベース接続情報
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "mysecretpassword"


def setup_database():
    """データベースに接続し、テーブルを作成する"""
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASS
        )
        cur = conn.cursor()

        # usersテーブルを作成
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL
        );
        """)
        print("テーブル 'users' の準備ができました。")

        # tasksテーブルを先に作成（これがないとALTER TABLEでエラーになるため）
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        print("テーブル 'tasks' の準備ができました。")

        # tasksテーブルにuser_idカラムを追加
        cur.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name='tasks' AND column_name='user_id';
        """)
        if cur.fetchone() is None:
            cur.execute("""
                ALTER TABLE tasks ADD COLUMN user_id INTEGER;
                ALTER TABLE tasks ADD CONSTRAINT fk_user
                    FOREIGN KEY(user_id) REFERENCES users(id);
            """)
            print("tasksテーブルにuser_idカラムを追加しました。")

        conn.commit()
        cur.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"データベースのセットアップ中にエラー: {error}")
    finally:
        if conn is not None:
            conn.close()


if __name__ == '__main__':
    setup_database()
