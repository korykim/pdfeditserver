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
- Web服务器：Nginx + Gunicorn
- 容器化：Docker & Docker Compose
- 进程管理：Supervisor

## 安装与运行

### 方式一：Docker部署（推荐）

1. 确保安装了Docker和Docker Compose
   ```bash
   docker --version
   docker-compose --version
   ```

2. 克隆仓库
   ```bash
   git clone <repository-url>
   cd pdfeditserver
   ```

3. 创建环境变量文件
   ```bash
   cp pdfeditserver/.env.example pdfeditserver/.env
   # 编辑.env文件设置必要的环境变量
   ```

4. 构建和启动服务
   ```bash
   docker-compose build --no-cache

   docker-compose up -d
   ```

5. 访问服务
   ```
   http://localhost
   ```

6. 查看日志
   ```bash
   # 查看所有服务日志
   docker-compose logs -f
   
   # 查看特定服务日志
   docker-compose logs -f app
   docker-compose logs -f celery
   ```

7. 停止服务
   ```bash
   docker-compose down
   ```

### 方式二：传统部署

#### 前提条件

- Python 3.7+
- pip (Python包管理器)
- Redis服务器
- Nginx
- Supervisor

#### 安装步骤

1. 克隆仓库并安装依赖
   ```bash
   git clone <repository-url>
   cd pdfeditserver
   pip install -r requirements.txt
   ```

2. 配置环境变量
   ```bash
   cp pdfeditserver/.env.example pdfeditserver/.env
   # 编辑.env文件设置环境变量
   ```

3. 配置Nginx
   - 将`nginx.conf`复制到Nginx配置目录
   - 重启Nginx服务

4. 配置Supervisor
   - 将`supervisord.conf`复制到Supervisor配置目录
   - 更新配置中的路径
   - 重启Supervisor服务

5. 启动服务
   ```bash
   # Supervisor会自动管理Celery进程
   supervisorctl start all
   
   # 启动Gunicorn
   gunicorn --workers 4 --bind 0.0.0.0:8000 pdfeditserver.app:app
   ```

## 项目结构

```
pdfeditserver/
├── docker-compose.yml      # Docker编排配置
├── Dockerfile             # Docker构建文件
├── nginx.conf            # Nginx配置
├── supervisord.conf      # Supervisor配置
├── requirements.txt      # Python依赖
├── pdfeditserver/        # 主应用目录
│   ├── app.py           # Flask应用
│   ├── celery_app.py    # Celery配置
│   ├── tasks.py         # Celery任务
│   ├── pdfedits.py      # PDF处理逻辑
│   ├── static/          # 静态文件
│   ├── templates/       # HTML模板
│   └── uploads/         # 上传文件目录
└── .env                 # 环境变量
```

## 使用方法

1. 上传PDF文件（支持拖放或点击上传）
2. 输入要删除的页面号（例如：1,3,5-7）
3. 点击"处理文件"按钮
4. 等待处理完成
5. 下载处理后的文件

## 配置说明

### 环境变量

- `REDIS_URL`: Redis连接URL
- `CELERY_BROKER_URL`: Celery消息代理URL
- `CELERY_RESULT_BACKEND`: Celery结果后端URL
- `CLEAN_PASSWORD`: 清理API密码

### Docker服务

- `nginx`: 反向代理和静态文件服务
- `app`: Flask应用（Gunicorn）
- `redis`: 消息队列和结果存储
- `celery`: Celery worker和beat进程（Supervisor管理）

## 注意事项

- 上传文件大小限制为16MB
- 仅支持PDF文件格式
- 页面号从1开始计数
- 处理后的文件会在24小时后自动删除
- Docker部署会自动处理依赖和服务管理
- 生产环境部署建议：
  - 配置SSL证书
  - 调整Gunicorn和Nginx参数
  - 设置适当的日志轮转
  - 配置监控告警

## 未来计划

- 添加更多PDF编辑功能（合并、分割、旋转等）
- 支持PDF预览
- 添加用户认证系统
- 提供API接口
- 添加容器健康检查
- 集成CI/CD流程
- 添加Prometheus监控
- 支持水平扩展

## 故障排除

1. 容器无法启动
   ```bash
   # 检查容器日志
   docker-compose logs [service_name]
   ```

2. 文件上传失败
   - 检查nginx.conf中的client_max_body_size设置
   - 确认uploads目录权限正确

3. 任务处理失败
   - 检查Redis连接
   - 查看Celery worker日志
   - 确认文件权限设置

## 许可证

MIT 