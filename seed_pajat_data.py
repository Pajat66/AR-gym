import json
import random

from werkzeug.security import generate_password_hash

from app import get_db_connection, test_db_connection, init_database

# 目标测试用户用户名
TEST_USERNAME = "pajat"

# 当前系统中已有的健身动作类型（与前端/后端保持一致）
EXERCISE_TYPES = [
    "pushup",               # 俯卧撑计数
    "squat",                # 蹲起
    "reverse_crunch",       # 反向卷腹
    "barbell_curl_left",    # 左侧杠铃弯举
    "barbell_curl_right",   # 右侧杠铃弯举
    "barbell_sit_left",     # 左侧杠铃坐姿
    "barbell_sit_right",    # 右侧杠铃坐姿
]


def ensure_test_user():
    """确保 argym_users 中存在测试用户 pajat，返回其 id。

    如果不存在，则创建一个密码为 "pajat_test_password" 的测试账号。
    """
    conn = get_db_connection()
    if not conn:
        raise RuntimeError("数据库连接失败，请检查 app.py 中的 DB_CONFIG 配置")

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM argym_users WHERE username = %s", (TEST_USERNAME,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
                print(f"已找到测试用户 {TEST_USERNAME}，id = {user_id}")
                return user_id

            print(f"未找到测试用户 {TEST_USERNAME}，正在创建...")
            password_hash = generate_password_hash("pajat_test_password")
            cursor.execute(
                "INSERT INTO argym_users (username, password, created_at) VALUES (%s, %s, NOW())",
                (TEST_USERNAME, password_hash),
            )
            user_id = cursor.lastrowid

        conn.commit()
        print(f"已创建测试用户 {TEST_USERNAME}，id = {user_id}")
        return user_id
    finally:
        conn.close()


def insert_random_exercise_data(user_id: int, record_count: int = 15):
    """为指定用户插入随机的运动记录和对应的统计数据。

    会向 exercise_records 中插入 record_count 条记录，
    并同步更新 exercise_stats，保证统计数据与历史记录总量一致（通过累加 count/duration）。
    """
    conn = get_db_connection()
    if not conn:
        raise RuntimeError("数据库连接失败，请检查 app.py 中的 DB_CONFIG 配置")

    try:
        with conn.cursor() as cursor:
            for i in range(record_count):
                exercise_type = random.choice(EXERCISE_TYPES)
                count = random.randint(5, 30)          # 本次训练次数
                duration = random.randint(60, 600)     # 本次训练时长（秒）
                # 伪造一些角度数据
                angle_data = [random.randint(30, 160) for _ in range(10)]

                # 1) 插入历史记录表 exercise_records
                cursor.execute(
                    """
                    INSERT INTO exercise_records
                        (user_id, exercise_type, count, duration, angle_data)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (str(user_id), exercise_type, count, duration, json.dumps(angle_data)),
                )

                # 2) 同步更新统计表 exercise_stats
                #    与 app.py 中 /api/save_exercise 的逻辑保持一致：累加 total_count / total_duration
                cursor.execute(
                    """
                    INSERT INTO exercise_stats
                        (user_id, exercise_type, total_count, total_duration, last_exercise_date)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        total_count = total_count + %s,
                        total_duration = total_duration + %s,
                        last_exercise_date = NOW()
                    """,
                    (str(user_id), exercise_type, count, duration, count, duration),
                )

                print(
                    f"第 {i + 1} 条: user_id={user_id}, type={exercise_type}, "
                    f"count={count}, duration={duration} 秒",
                )

        conn.commit()
        print(f"已为用户 {TEST_USERNAME} 插入 {record_count} 条运动记录并更新统计数据。")
    finally:
        conn.close()


if __name__ == "__main__":
    # 先通过 app.py 中的 test_db_connection 自动选择可用的数据库配置
    print("正在测试数据库连接并初始化表结构...")
    if not test_db_connection():
        raise RuntimeError("无法连接到数据库，请确认 DB_CONFIG/DB_CONFIG_ROOT 等配置是否正确")
    init_database()

    uid = ensure_test_user()
    insert_random_exercise_data(uid, record_count=15)
