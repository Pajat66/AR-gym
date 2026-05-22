from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import pymysql
from datetime import datetime
import json
import base64
import hashlib
import hmac
import os
import ssl
from pathlib import Path
from time import mktime
from urllib.parse import unquote, urlencode, urljoin, urlparse
from wsgiref.handlers import format_date_time
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 请在生产环境中更改（生产环境请使用环境变量或配置文件）
CORS(app)

# 数据库配置
# 根据MySQL用户列表，project@% 用户有远程访问权限
DB_CONFIG = {
    'host': '10.31.44.117',
    'port': 3306,
    'user': 'project',  # 使用project用户（有%权限，可从任何主机连接）
    'password': 'Zbp42682600',
    'database': 'exercise',
    'charset': 'utf8mb4'
}

# 备用配置1：尝试使用Zbp42682600用户（如果存在）
DB_CONFIG_ZBP = {
    'host': '10.31.44.117',
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

SPARK_CONFIG = {
    'appid': os.environ.get('SPARK_APPID', 'b13faa35'),
    'api_secret': os.environ.get('SPARK_API_SECRET', 'MmNlYmU4NGQ3NWIzYzdkN2I2ZTMxNjU4'),
    'api_key': os.environ.get('SPARK_API_KEY', '2156fa2aed34b9247b9e553202d17508'),
    'host': 'spark-api.xf-yun.com',
    # Spark Lite 固定使用 v1.1/chat + lite，避免被旧环境变量覆盖成 v3.5/generalv3.5。
    'path': '/v1.1/chat',
    'domain': 'lite'
}

FAILED_OSS_HOSTS = {'exercise-image.oss-cn-beijing.aliyuncs.com'}

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

def build_spark_auth_url():
    """生成讯飞星火 WebSocket 鉴权地址。"""
    request_url = f"wss://{SPARK_CONFIG['host']}{SPARK_CONFIG['path']}"
    parsed_url = urlparse(request_url)
    # 讯飞示例使用 RFC1123 时间戳，保持签名串完全一致。
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    signature_origin = f"host: {parsed_url.netloc}\ndate: {date}\nGET {parsed_url.path} HTTP/1.1"
    signature_sha = hmac.new(
        SPARK_CONFIG['api_secret'].encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode('utf-8')
    authorization_origin = (
        f'api_key="{SPARK_CONFIG["api_key"]}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
    query = urlencode({
        'authorization': authorization,
        'date': date,
        'host': parsed_url.netloc
    })
    return f"{request_url}?{query}"

def ask_spark_coach(messages):
    """调用讯飞星火 Lite WebSocket 接口并返回完整文本回复。"""
    try:
        import websocket
    except ImportError as exc:
        raise RuntimeError('缺少 websocket-client 依赖，请先执行 pip install -r requirements.txt') from exc

    system_prompts = [item.get('content', '') for item in messages if item.get('role') == 'system']
    spark_messages = []
    for item in messages:
        role = item.get('role')
        content = (item.get('content') or '').strip()
        if role not in ('user', 'assistant') or not content:
            continue
        spark_messages.append({'role': role, 'content': content})

    if system_prompts and spark_messages:
        spark_messages[0]['content'] = f"{' '.join(system_prompts)}\n\n用户问题：{spark_messages[0]['content']}"

    payload = {
        'header': {
            'app_id': SPARK_CONFIG['appid'],
            'uid': 'argym_user'
        },
        'parameter': {
            'chat': {
                'domain': SPARK_CONFIG['domain'],
                'temperature': 0.5,
                'max_tokens': 4096,
                'top_k': 4
            }
        },
        'payload': {
            'message': {
                'text': spark_messages
            }
        }
    }

    ws = None
    try:
        websocket.enableTrace(False)
        ws = websocket.create_connection(
            build_spark_auth_url(),
            timeout=30,
            sslopt={'cert_reqs': ssl.CERT_NONE}
        )
        ws.send(json.dumps(payload, ensure_ascii=False))

        answer_parts = []
        while True:
            response = json.loads(ws.recv())
            header = response.get('header', {})
            code = header.get('code', 0)
            if code != 0:
                raise RuntimeError(f"讯飞星火WebSocket Lite错误 {code}: {header.get('message') or response}")

            choices = response.get('payload', {}).get('choices', {})
            for item in choices.get('text', []):
                answer_parts.append(item.get('content', ''))

            if choices.get('status') == 2:
                break

        answer = ''.join(answer_parts).strip()
        if not answer:
            raise RuntimeError('讯飞星火没有返回有效内容')
        return answer
    finally:
        if ws:
            ws.close()

def normalize_media_name(value):
    return ''.join(ch.lower() for ch in value if ch.isalnum())

def find_local_static_media_url(title, original_url, media_type):
    media_config = {
        'video': ('videos', {'.mp4', '.webm', '.mov', '.m4v'}),
        'image': ('images', {'.jpg', '.jpeg', '.png', '.webp'})
    }
    static_folder, extensions = media_config.get(media_type, media_config['video'])
    static_dir = Path(app.root_path) / 'static' / static_folder
    if not static_dir.exists():
        return ''

    parsed = urlparse(original_url)
    original_name = unquote(Path(parsed.path).name)
    original_path = static_dir / original_name
    if original_name and original_path.exists():
        return urljoin(request.host_url, f'static/{static_folder}/{original_name}')

    title_key = normalize_media_name(Path(str(title or '')).stem)
    for file_path in static_dir.iterdir():
        if not file_path.is_file() or file_path.suffix.lower() not in extensions:
            continue
        stem_key = normalize_media_name(file_path.stem)
        if title_key and (title_key == stem_key or title_key in stem_key or stem_key in title_key):
            return urljoin(request.host_url, f'static/{static_folder}/{file_path.name}')

    return ''

def normalize_media_url(value, media_type='video', title=''):
    """把数据库里的视频/封面地址规范成浏览器可直接请求的 URL。"""
    if value is None:
        return ''

    url = str(value).strip()
    if not url:
        return ''

    if url.startswith(('http://', 'https://')):
        parsed = urlparse(url)
        if parsed.netloc in FAILED_OSS_HOSTS:
            return find_local_static_media_url(title, url, media_type)
        return url

    if url.startswith(('data:', 'blob:')):
        return url

    if url.startswith('//'):
        return f'https:{url}'

    if url.startswith(('www.', 'm.', 'static.')):
        return f'https://{url}'

    # 兼容数据库中保存 videos/xxx、images/xxx、static/xxx 或 /static/xxx 这类相对路径的情况。
    normalized_path = url.replace('\\', '/')
    normalized_without_slash = normalized_path.lstrip('/')
    if normalized_without_slash.startswith(('videos/', 'images/')):
        normalized_path = f'static/{normalized_without_slash}'
    return urljoin(request.host_url, normalized_path.lstrip('/'))

def normalize_video_record(record):
    if not record:
        return record

    title = record.get('Title') or ''
    record['Video_URL'] = normalize_media_url(record.get('Video_URL'), 'video', title)
    record['Video_Image_URL'] = normalize_media_url(record.get('Video_Image_URL'), 'image', title)
    record['Video_ID'] = record.get('Video_ID') or record.get('Vid') or record.get('id')
    record['Estimated_Time'] = record.get('Estimated_Time') or 0
    record['Estimated_Calories'] = record.get('Estimated_Calories') or 0
    record['StarCount'] = record.get('StarCount') or 0
    record['Content'] = record.get('Content') or ''
    record['Suitable_People'] = record.get('Suitable_People') or '所有人'
    record['Coach_Name'] = record.get('Coach_Name') or ''
    return record

def get_table_columns(cursor, table_name):
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
    return {row['Field'] for row in cursor.fetchall()}

def pick_column(columns, *candidates):
    for name in candidates:
        if name in columns:
            return name
    return None

def build_video_select(columns):
    """兼容 Vid/Video_ID 等不同字段命名，避免某个可选字段缺失导致整页视频加载失败。"""
    mapping = {
        'Video_ID': pick_column(columns, 'Video_ID', 'Vid', 'id'),
        'Title': pick_column(columns, 'Title', 'title', 'Name', 'Video_Title'),
        'Content': pick_column(columns, 'Content', 'content', 'Description', 'Video_Content'),
        'Video_URL': pick_column(columns, 'Video_URL', 'video_url', 'Url', 'URL'),
        'Video_Image_URL': pick_column(columns, 'Video_Image_URL', 'video_image_url', 'Image_URL', 'Cover_URL'),
        'Estimated_Time': pick_column(columns, 'Estimated_Time', 'estimated_time', 'Duration'),
        'Estimated_Calories': pick_column(columns, 'Estimated_Calories', 'estimated_calories', 'Calories'),
        'Suitable_People': pick_column(columns, 'Suitable_People', 'suitable_people'),
        'StarCount': pick_column(columns, 'StarCount', 'star_count', 'Stars'),
        'Completion_Rate': pick_column(columns, 'Completion_Rate', 'completion_rate'),
        'Created_Time': pick_column(columns, 'Created_Time', 'created_time', 'created_at')
    }

    required = ['Video_ID', 'Title', 'Video_URL']
    missing = [name for name in required if not mapping[name]]
    if missing:
        raise RuntimeError(f"视频表缺少必要字段: {', '.join(missing)}")

    select_parts = []
    for alias, column in mapping.items():
        if column:
            select_parts.append(f"`{column}` AS `{alias}`")
        else:
            select_parts.append(f"NULL AS `{alias}`")

    order_column = mapping.get('StarCount') or mapping.get('Created_Time') or mapping['Video_ID']
    return ',\n                    '.join(select_parts), mapping['Video_ID'], order_column, mapping['Video_URL']

def fetch_video_rows(cursor, limit):
    """根据真实表字段动态读取教学视频列表。"""
    columns = get_table_columns(cursor, 'teachingvideos_teaching_video')
    select_sql, _, order_column, video_url_column = build_video_select(columns)
    sql = f"""
        SELECT
            {select_sql}
        FROM teachingvideos_teaching_video
        WHERE `{video_url_column}` IS NOT NULL AND `{video_url_column}` <> ''
        ORDER BY `{order_column}` DESC
        LIMIT %s
    """
    cursor.execute(sql, (limit,))
    return cursor.fetchall()

def fetch_video_row(cursor, video_id):
    """根据真实表字段动态读取单条教学视频。"""
    columns = get_table_columns(cursor, 'teachingvideos_teaching_video')
    select_sql, id_column, _, _ = build_video_select(columns)
    sql = f"""
        SELECT
            {select_sql}
        FROM teachingvideos_teaching_video
        WHERE `{id_column}` = %s
    """
    cursor.execute(sql, (video_id,))
    return cursor.fetchone()

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

@app.route('/api/ai_coach', methods=['POST'])
def ai_coach():
    """AI虚拟教练对话接口，服务端代理讯飞星火，避免密钥暴露到前端。"""
    try:
        data = request.json or {}
        message = (data.get('message') or '').strip()
        history = data.get('history') or []

        if not message:
            return jsonify({'success': False, 'error': '请输入想咨询的问题'}), 400

        system_prompt = (
            '你是 AR健身教练 应用里的AI虚拟教练。请用中文回答，语气专业、简洁、鼓励但不过度夸张。'
            '你的建议应围绕健身动作规范、训练计划、热身拉伸、训练安全和恢复。'
            '涉及疼痛、损伤、疾病或高风险症状时，提醒用户停止训练并咨询医生。'
        )
        messages = [{'role': 'system', 'content': system_prompt}]

        for item in history[-8:]:
            role = item.get('role')
            content = (item.get('content') or '').strip()
            if role in ('user', 'assistant') and content:
                messages.append({'role': role, 'content': content[:1200]})

        messages.append({'role': 'user', 'content': message[:2000]})
        reply = ask_spark_coach(messages)
        return jsonify({'success': True, 'data': {'reply': reply}})
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
            videos = fetch_video_rows(cursor, limit)
            for video in videos:
                normalize_video_record(video)
        
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
            video = fetch_video_row(cursor, video_id)
            normalize_video_record(video)
        
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

