# AR健身教练 - Web版本

这是一个基于Web的智能健身动作检测系统，使用MediaPipe进行手部姿态检测和身体姿态检测。

## 功能特性

- 🎯 **手势识别导航** - 通过伸出手指选择不同的训练模式
- 💪 **多种训练模式**：
  - 上肢训练：杠铃弯举（左侧/右侧）、杠铃坐姿（左侧/右侧）
  - 下肢训练：俯卧撑计数、反向卷腹、蹲起
- 📊 **数据统计** - 记录训练次数、时长等数据
- 📈 **历史记录** - 查看历史训练记录
- 🎨 **现代化UI** - 美观的渐变设计和流畅的动画效果

## 技术栈

### 后端
- Flask - Web框架
- PyMySQL - MySQL数据库连接
- MySQL - 数据存储

### 前端
- HTML5/CSS3/JavaScript
- MediaPipe (JavaScript) - 手部和姿态检测
- WebRTC - 摄像头视频流

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

确保MySQL数据库已创建，并在 `app.py` 中配置正确的数据库连接信息：

```python
DB_CONFIG = {
    'host': '192.168.164.117',
    'port': 3306,
    'user': 'Zbp42682600',
    'password': 'Zbp42682600',
    'database': 'exercise',
    'charset': 'utf8mb4'
}
```

### 3. 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动。

### 4. 访问应用

在浏览器中打开 `http://localhost:5000`，允许浏览器访问摄像头权限。

## 使用说明

1. **首页导航**：
   - 伸出手指1：选择上肢训练
   - 伸出手指2：选择下肢训练
   - 保持手势3秒以确认选择

2. **训练模式**：
   - 选择训练类型后，根据提示选择具体的训练动作
   - 训练过程中会实时显示计数、角度和FPS
   - 点击"停止训练"返回主菜单
   - 点击"保存数据"将训练数据保存到数据库

3. **数据查看**：
   - 点击"数据统计"查看总体统计数据
   - 点击"历史记录"查看详细的历史训练记录

## 项目结构

```
.
├── app.py                 # Flask后端应用
├── templates/
│   └── index.html        # 主页面模板
├── static/
│   ├── css/
│   │   └── style.css     # 样式文件
│   └── js/
│       ├── main.js       # 主应用逻辑
│       ├── hand-detection.js  # 手部检测
│       └── pose-detection.js  # 姿态检测
├── src/                  # 原始项目代码（保留）
└── requirements.txt      # Python依赖

```

## 数据库表结构

应用会自动创建以下表：

- `exercise_records` - 运动记录表
- `exercise_stats` - 运动统计表
- `users` - 用户表

## 注意事项

1. **浏览器兼容性**：建议使用Chrome或Edge浏览器，以获得最佳的MediaPipe支持
2. **摄像头权限**：首次访问需要允许浏览器访问摄像头
3. **网络连接**：MediaPipe库需要从CDN加载，确保网络连接正常
4. **HTTPS**：某些浏览器可能要求HTTPS才能访问摄像头，本地开发可以使用 `http://localhost`

## 开发说明

- 前端使用原生JavaScript，无需构建工具
- MediaPipe通过CDN加载，无需本地安装
- 后端API使用RESTful风格
- 数据库操作使用PyMySQL

## 故障排除

1. **摄像头无法访问**：
   - 检查浏览器权限设置
   - 确保没有其他应用占用摄像头
   - 尝试使用HTTPS

2. **MediaPipe加载失败**：
   - 检查网络连接
   - 查看浏览器控制台错误信息
   - 尝试使用VPN或更换CDN源

3. **数据库连接失败**：
   - 检查数据库配置信息
   - 确保MySQL服务正在运行
   - 检查防火墙设置

## 许可证

本项目仅供学习和研究使用。

