# PDF编辑服务器

这是一个基于Web的PDF编辑工具，目前支持从PDF文件中删除指定页面。使用Celery任务队列处理PDF文件，适合多用户并发场景。

## 功能特点

- 简洁美观的用户界面
- 支持拖放上传PDF文件
- 实时显示处理进度
- 支持范围选择页面（例如：1,3,5-7）
- 安全的文件处理机制
- 自动清理过期文件
- 使用Celery任务队列，支持高并发处理

## 技术栈

- 后端：Flask (Python)
- 前端：HTML, JavaScript, Tailwind CSS
- PDF处理：PyPDF2
- 任务队列：Celery
- 消息代理：Redis

## 安装与运行

### 前提条件

- Python 3.7+
- pip (Python包管理器)
- Redis服务器

### 安装步骤

1. 克隆或下载本仓库

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 启动Redis服务器
   ```bash
   # 如果使用Docker
   docker run -d -p 6379:6379 redis
   
   # 或者使用本地安装的Redis
   redis-server
   ```

4. 配置环境变量（可选）
   创建`.env`文件，添加以下内容：
   ```
   REDIS_URL=redis://localhost:6379/0
   CLEAN_PASSWORD=your_secure_password
   ```

5. 启动Celery Worker
   ```bash
   # 在项目根目录下运行
   celery -A pdfeditserver.celery_app worker --loglevel=info
   ```

6. 启动Celery Beat（用于定时任务）
   ```bash
   celery -A pdfeditserver.celery_app beat --loglevel=info
   ```

7. 运行Flask应用
   ```bash
   python -m pdfeditserver.app
   ```

8. 在浏览器中访问
   ```
   http://localhost:9000
   ```

## 使用方法

1. 上传PDF文件（支持拖放或点击上传）
2. 输入要删除的页面号（例如：1,3,5-7）
3. 点击"处理文件"按钮
4. 等待处理完成
5. 下载处理后的文件

## 生产环境部署

对于生产环境，建议：

1. 使用Gunicorn或uWSGI作为WSGI服务器
2. 使用Nginx作为反向代理
3. 使用Supervisor管理Celery Worker和Beat进程
4. 使用专用的Redis实例作为消息代理
5. 考虑使用Redis或数据库存储任务状态，而不是内存字典

示例Supervisor配置：
```ini
[program:pdfedit_worker]
command=/path/to/venv/bin/celery -A pdfeditserver.celery_app worker --loglevel=info
directory=/path/to/pdfeditserver
user=www-data
numprocs=1
stdout_logfile=/var/log/pdfedit_worker.log
stderr_logfile=/var/log/pdfedit_worker_error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600

[program:pdfedit_beat]
command=/path/to/venv/bin/celery -A pdfeditserver.celery_app beat --loglevel=info
directory=/path/to/pdfeditserver
user=www-data
numprocs=1
stdout_logfile=/var/log/pdfedit_beat.log
stderr_logfile=/var/log/pdfedit_beat_error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=10
```

## 注意事项

- 上传文件大小限制为16MB
- 仅支持PDF文件格式
- 页面号从1开始计数
- 处理后的文件会在24小时后自动删除
- 确保Redis服务器正常运行，否则任务队列将无法工作

## 未来计划

- 添加更多PDF编辑功能（合并、分割、旋转等）
- 支持PDF预览
- 添加用户认证系统
- 提供API接口
- 使用数据库存储任务状态，提高可靠性

## 许可证

MIT 