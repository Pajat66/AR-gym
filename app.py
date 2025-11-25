from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import pymysql
from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 请在生产环境中更改（生产环境请使用环境变量或配置文件）
CORS(app)

# 数据库配置
# 根据MySQL用户列表，project@% 用户有远程访问权限
DB_CONFIG = {
    'host': '192.168.119.117',
    'port': 3306,
    'user': 'project',  # 使用project用户（有%权限，可从任何主机连接）
    'password': 'Zbp42682600',
    'database': 'exercise',
    'charset': 'utf8mb4'
}

# 备用配置1：尝试使用Zbp42682600用户（如果存在）
DB_CONFIG_ZBP = {
    'host': '192.168.119.117',
    'port': 3306,
    'user': 'Zbp42682600',
    'password': 'Zbp42682600',
    'database': 'exercise',
    'charset': 'utf8mb4'
}

# 备用配置2：尝试使用root用户（仅限localhost，如果从服务器本地运行）
DB_CONFIG_ROOT = {
    'host': 'localhost',  # root只能从localhost连接
    'port': 3306,
    'user': 'root',
    'password': 'Zbp42682600',
    'database': 'exercise',
    'charset': 'utf8mb4'
}

def get_db_connection():
    """获取数据库连接（使用测试成功的配置）"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        # 测试连接
        connection.ping(reconnect=True)
        return connection
    except pymysql.Error as e:
        error_code, error_msg = e.args
        print(f"数据库连接错误 [{error_code}]: {error_msg}")
        print(f"尝试连接: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        return None

def test_db_connection():
    """测试数据库连接"""
    global DB_CONFIG  # 在函数开始处声明global
    
    print("=" * 50)
    print("正在测试数据库连接...")
    print("=" * 50)
    
    # 配置列表，按优先级尝试
    configs = [
        ('project', DB_CONFIG, False),
        ('Zbp42682600', DB_CONFIG_ZBP, False),
        ('root (localhost)', DB_CONFIG_ROOT, True),
    ]
    
    for name, config, use_root in configs:
        print(f"\n尝试使用 {name} 用户连接...")
        try:
            connection = pymysql.connect(**config)
            connection.ping(reconnect=True)
            print(f"✓ 使用 {name} 用户连接成功！")
            connection.close()
            # 更新全局配置为成功的配置
            DB_CONFIG = config
            return True
        except pymysql.Error as e:
            error_code, error_msg = e.args
            print(f"✗ {name} 连接失败: [{error_code}] {error_msg}")
    
    print("\n" + "=" * 50)
    print("✗ 所有连接尝试都失败了")
    print("=" * 50)
    print("\n请检查：")
    print("1. MySQL服务是否正在运行")
    print("2. 用户名和密码是否正确")
    print("3. 用户是否有远程访问权限（host应该是%或192.168.164.117）")
    print("4. 防火墙是否允许3306端口")
    print("5. 数据库 'exercise' 是否存在")
    print("\n建议：")
    print("如果project用户密码不是Zbp42682600，请修改代码中的密码")
    print("或者创建新用户并授予远程访问权限：")
    print("  CREATE USER 'your_user'@'%' IDENTIFIED BY 'your_password';")
    print("  GRANT ALL PRIVILEGES ON exercise.* TO 'your_user'@'%';")
    print("  FLUSH PRIVILEGES;")
    return False

def init_database():
    """初始化数据库表"""
    connection = get_db_connection()
    if not connection:
        print("\n无法连接到数据库，跳过表初始化")
        print("如果表已存在，可以继续运行应用")
        return False
    
    try:
        with connection.cursor() as cursor:
            # 检查表是否已存在
            cursor.execute("SHOW TABLES LIKE 'exercise_records'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                print("检测到 exercise_records 表已存在，跳过创建")
            else:
                print("创建 exercise_records 表...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS exercise_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(50) DEFAULT 'default_user',
                        exercise_type VARCHAR(50) NOT NULL,
                        count INT DEFAULT 0,
                        duration INT DEFAULT 0,
                        angle_data TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_exercise (user_id, exercise_type),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            
            # 检查并创建新的用户表 argym_users（专供当前Web应用登录使用）
            cursor.execute("SHOW TABLES LIKE 'argym_users'")
            if not cursor.fetchone():
                print("创建用户表 argym_users...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS argym_users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_username (username)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            
            # 检查并创建运动统计表
            cursor.execute("SHOW TABLES LIKE 'exercise_stats'")
            if cursor.fetchone():
                print("检测到 exercise_stats 表已存在，跳过创建")
            else:
                print("创建 exercise_stats 表...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS exercise_stats (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(50) NOT NULL,
                        exercise_type VARCHAR(50) NOT NULL,
                        total_count INT DEFAULT 0,
                        total_duration INT DEFAULT 0,
                        last_exercise_date DATETIME,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_user_exercise (user_id, exercise_type),
                        INDEX idx_user (user_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            
        connection.commit()
        print("✓ 数据库表初始化完成")
        return True
    except Exception as e:
        print(f"✗ 数据库初始化错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        connection.close()

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    """用户注册，使用 users_users 表"""
    try:
        data = request.json or {}
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()

        if not username or not password:
            return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500

        try:
            with connection.cursor() as cursor:
                # 检查用户名是否已存在（使用新表 argym_users）
                cursor.execute("SELECT id FROM argym_users WHERE username = %s", (username,))
                if cursor.fetchone():
                    return jsonify({'success': False, 'error': '用户名已存在'}), 400

                # 生成密码哈希并写入 argym_users 表
                password_hash = generate_password_hash(password)
                cursor.execute(
                    "INSERT INTO argym_users (username, password, created_at) VALUES (%s, %s, NOW())",
                    (username, password_hash)
                )
                user_id = cursor.lastrowid

            connection.commit()
        finally:
            connection.close()

        # 将用户信息写入 session，实现后续接口按用户隔离
        session['user_id'] = user_id
        session['username'] = username

        return jsonify({'success': True, 'message': '注册成功', 'data': {'id': user_id, 'username': username}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录，使用 users_users 表"""
    try:
        data = request.json or {}
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()

        if not username or not password:
            return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500

        try:
            with connection.cursor() as cursor:
                # 从新表 argym_users 读取用户信息
                cursor.execute("SELECT id, password FROM argym_users WHERE username = %s", (username,))
                row = cursor.fetchone()

            if not row:
                return jsonify({'success': False, 'error': '用户名或密码错误'}), 401

            user_id, password_hash = row
            if not check_password_hash(password_hash, password):
                return jsonify({'success': False, 'error': '用户名或密码错误'}), 401
        finally:
            connection.close()

        # 登录成功，写入 session
        session['user_id'] = user_id
        session['username'] = username

        return jsonify({'success': True, 'message': '登录成功', 'data': {'id': user_id, 'username': username}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """用户退出登录"""
    session.clear()
    return jsonify({'success': True, 'message': '已退出登录'})

@app.route('/api/me', methods=['GET'])
def current_user():
    """获取当前登录用户信息"""
    user_id = session.get('user_id')
    username = session.get('username')
    if not user_id:
        return jsonify({'success': False, 'error': '未登录'}), 401
    return jsonify({'success': True, 'data': {'id': user_id, 'username': username}})

@app.route('/api/save_exercise', methods=['POST'])
def save_exercise():
    """保存运动记录（按当前登录用户）"""
    try:
        # 必须是已登录用户
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '用户未登录'}), 401

        data = request.json or {}
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500
        
        with connection.cursor() as cursor:
            # 插入运动记录（与当前用户绑定）
            sql = """
                INSERT INTO exercise_records 
                (user_id, exercise_type, count, duration, angle_data)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                str(user_id),
                data.get('exercise_type'),
                data.get('count', 0),
                data.get('duration', 0),
                json.dumps(data.get('angle_data', []))
            ))
            
            # 更新统计表（与当前用户绑定）
            sql_stats = """
                INSERT INTO exercise_stats 
                (user_id, exercise_type, total_count, total_duration, last_exercise_date)
                VALUES (%s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                total_count = total_count + %s,
                total_duration = total_duration + %s,
                last_exercise_date = NOW()
            """
            cursor.execute(sql_stats, (
                str(user_id),
                data.get('exercise_type'),
                data.get('count', 0),
                data.get('duration', 0),
                data.get('count', 0),
                data.get('duration', 0)
            ))
        
        connection.commit()
        connection.close()
        return jsonify({'success': True, 'message': '保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_stats', methods=['GET'])
def get_stats():
    """获取当前登录用户的运动统计"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '用户未登录'}), 401

        exercise_type = request.args.get('exercise_type', None)
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500
        
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            if exercise_type:
                sql = """
                    SELECT * FROM exercise_stats 
                    WHERE user_id = %s AND exercise_type = %s
                """
                cursor.execute(sql, (str(user_id), exercise_type))
            else:
                sql = """
                    SELECT * FROM exercise_stats 
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                """
                cursor.execute(sql, (str(user_id),))
            
            stats = cursor.fetchall()
        
        connection.close()
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_history', methods=['GET'])
def get_history():
    """获取当前登录用户的运动历史记录"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '用户未登录'}), 401

        exercise_type = request.args.get('exercise_type', None)
        limit = int(request.args.get('limit', 20))
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500
        
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            if exercise_type:
                sql = """
                    SELECT * FROM exercise_records 
                    WHERE user_id = %s AND exercise_type = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                cursor.execute(sql, (str(user_id), exercise_type, limit))
            else:
                sql = """
                    SELECT * FROM exercise_records 
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                cursor.execute(sql, (str(user_id), limit))
            
            records = cursor.fetchall()
            # 解析JSON数据
            for record in records:
                if record.get('angle_data'):
                    try:
                        record['angle_data'] = json.loads(record['angle_data'])
                    except:
                        record['angle_data'] = []
        
        connection.close()
        return jsonify({'success': True, 'data': records})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_videos', methods=['GET'])
def get_videos():
    """获取教学视频列表"""
    try:
        limit = int(request.args.get('limit', 20))
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500
        
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
                SELECT 
                    Video_ID,
                    Title,
                    Content,
                    Video_URL,
                    Video_Image_URL,
                    Estimated_Time,
                    Estimated_Calories,
                    Suitable_People,
                    StarCount,
                    Completion_Rate,
                    Created_Time
                FROM teachingvideos_teaching_video
                ORDER BY StarCount DESC, Created_Time DESC
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            videos = cursor.fetchall()
        
        connection.close()
        return jsonify({'success': True, 'data': videos})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_video/<int:video_id>', methods=['GET'])
def get_video(video_id):
    """获取单个视频详情"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500
        
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
                SELECT 
                    v.Video_ID,
                    v.Title,
                    v.Content,
                    v.Video_URL,
                    v.Video_Image_URL,
                    v.Estimated_Time,
                    v.Estimated_Calories,
                    v.Suitable_People,
                    v.StarCount,
                    v.Completion_Rate,
                    v.Created_Time,
                    c.Name as Coach_Name
                FROM teachingvideos_teaching_video v
                LEFT JOIN teachingvideos_coach c ON v.Coach_ID_id = c.Coach_ID
                WHERE v.Video_ID = %s
            """
            cursor.execute(sql, (video_id,))
            video = cursor.fetchone()
        
        connection.close()
        
        if video:
            return jsonify({'success': True, 'data': video})
        else:
            return jsonify({'success': False, 'error': '视频不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # 测试数据库连接
    if test_db_connection():
        # 初始化数据库表
        init_database()
    else:
        print("\n警告: 数据库连接失败，但应用仍会启动")
        print("某些功能可能无法正常工作\n")
    
    # 运行应用
    print("=" * 50)
    print("启动Flask应用...")
    print("访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)

