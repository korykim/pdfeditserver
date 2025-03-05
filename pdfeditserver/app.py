#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF编辑服务器 - 后端应用

这个Flask应用提供PDF页面删除功能的Web界面。
用户可以上传PDF文件，选择要删除的页面，然后下载处理后的文件。
使用Celery处理异步任务，适合多用户并发场景。
"""

import os
import uuid
import time
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import glob
import dotenv

# 加载环境变量
dotenv.load_dotenv()

# 使用相对导入
from . import pdfedits
from .tasks import process_pdf_task, task_store, cleanup_old_tasks
from .celery_app import celery_app

# 创建Flask应用
app = Flask(__name__)

# 配置
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 打印上传目录路径，便于调试
print(f"应用中的上传目录路径: {app.config['UPLOAD_FOLDER']}")

def allowed_file(filename):
    """检查文件扩展名是否允许上传"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传请求"""
    # 检查是否有文件部分
    if 'file' not in request.files:
        return jsonify({'error': '没有文件部分'}), 400
    
    file = request.files['file']
    
    # 检查文件名是否为空
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    # 检查文件类型是否允许
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件类型，仅支持PDF文件'}), 400
    
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 保存原始文件名（不使用secure_filename处理，以保留中文字符）
    original_filename = file.filename
    
    # 为了安全存储，使用UUID作为文件名
    unique_id = str(uuid.uuid4())
    _, ext = os.path.splitext(original_filename)
    unique_filename = f"{unique_id}{ext}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)
    
    # 创建任务ID并存储任务信息
    task_id = str(uuid.uuid4())
    task_store[task_id] = {
        'status': 'uploaded',
        'file_path': file_path,
        'original_filename': original_filename,
        'created_at': time.time()
    }
    
    return jsonify({
        'task_id': task_id,
        'status': 'uploaded',
        'message': '文件上传成功'
    })

@app.route('/process', methods=['POST'])
def process_file():
    """处理PDF编辑请求"""
    data = request.json
    
    # 验证请求数据
    if not data or 'task_id' not in data or 'pages_to_delete' not in data:
        return jsonify({'error': '无效的请求数据'}), 400
    
    task_id = data['task_id']
    pages_to_delete = data['pages_to_delete']
    
    # 检查任务是否存在
    if task_id not in task_store:
        return jsonify({'error': '任务不存在'}), 404
    
    # 检查页面号是否有效
    if not all(isinstance(page, int) and page > 0 for page in pages_to_delete):
        return jsonify({'error': '页面号必须是正整数'}), 400
    
    # 获取文件路径和原始文件名
    file_path = task_store[task_id]['file_path']
    original_filename = task_store[task_id]['original_filename']
    
    # 打印调试信息
    print(f"处理PDF请求: task_id={task_id}, pages_to_delete={pages_to_delete}")
    
    # 如果是空的pages_to_delete（即只是获取PDF信息），直接处理而不使用Celery
    if not pages_to_delete:
        print(f"这是一个PDF信息请求，直接处理")
        try:
            import PyPDF2
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)
                
                # 更新任务信息 - 直接设置为completed
                task_store[task_id].update({
                    'status': 'completed',
                    'total_pages': total_pages,
                    'pages_kept': total_pages,
                    'pages_deleted': 0
                })
                
                print(f"PDF信息获取完成，总页数: {total_pages}")
                
                # 构建响应
                response = {
                    'task_id': task_id,
                    'status': 'completed',
                    'message': 'PDF信息获取完成',
                    'total_pages': total_pages,
                    'pages_kept': total_pages,
                    'pages_deleted': 0
                }
                
                print(f"返回响应: {response}")
                return jsonify(response)
                
        except Exception as e:
            error_msg = f"获取PDF页数时出错: {str(e)}"
            print(error_msg)
            
            # 更新任务状态为失败
            task_store[task_id].update({
                'status': 'failed',
                'error': error_msg
            })
            
            return jsonify({
                'task_id': task_id,
                'status': 'failed',
                'error': error_msg
            }), 500
    
    # 对于实际的页面删除操作，使用Celery异步处理
    # 启动Celery任务处理PDF
    celery_task = process_pdf_task.delay(task_id, file_path, pages_to_delete, original_filename)
    
    # 更新任务信息
    task_store[task_id].update({
        'status': 'processing',
        'celery_task_id': celery_task.id,
        'pages_to_delete': pages_to_delete,
        'pages_count': len(pages_to_delete)
    })
    
    # 构建响应
    response = {
        'task_id': task_id,
        'status': 'processing',
        'message': 'PDF处理已开始',
        'pages_to_delete': pages_to_delete,
        'pages_count': len(pages_to_delete)
    }
    
    # 如果任务存储中已经有total_pages信息，添加到响应中
    if 'total_pages' in task_store[task_id]:
        response['total_pages'] = task_store[task_id]['total_pages']
        print(f"响应中包含总页数: {response['total_pages']}")
    
    print(f"返回响应: {response}")
    return jsonify(response)

@app.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """获取任务状态"""
    if task_id not in task_store:
        return jsonify({'error': '任务不存在'}), 404
    
    task = task_store[task_id]
    
    # 打印调试信息
    print(f"获取任务状态: {task_id}")
    print(f"任务信息: {task}")
    
    response = {
        'task_id': task_id,
        'status': task['status']
    }
    
    # 如果有total_pages信息，始终返回
    if 'total_pages' in task:
        response['total_pages'] = task['total_pages']
        print(f"响应中包含总页数: {response['total_pages']}")
    else:
        print(f"警告: 任务 {task_id} 中没有total_pages信息")
        
        # 尝试从文件中获取总页数
        if 'file_path' in task and os.path.exists(task['file_path']):
            try:
                import PyPDF2
                with open(task['file_path'], 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    total_pages = len(pdf_reader.pages)
                    
                    # 更新任务信息
                    task_store[task_id]['total_pages'] = total_pages
                    response['total_pages'] = total_pages
                    print(f"从文件中获取到总页数: {total_pages}")
            except Exception as e:
                print(f"尝试获取PDF页数时出错: {str(e)}")
    
    # 根据状态添加额外信息
    if task['status'] == 'completed':
        response.update({
            'pages_kept': task.get('pages_kept', 0),
            'pages_deleted': task.get('pages_deleted', 0),
            'download_url': f"/download/{task_id}"
        })
    elif task['status'] == 'failed':
        response.update({
            'error': task.get('error', '未知错误')
        })
    elif task['status'] == 'retrying':
        response.update({
            'error': task.get('error', '未知错误'),
            'retry_count': task.get('retry_count', 0)
        })
    
    print(f"返回响应: {response}")
    return jsonify(response)

@app.route('/download/<task_id>', methods=['GET'])
def download_file(task_id):
    """下载处理后的文件"""
    if task_id not in task_store or task_store[task_id]['status'] != 'completed':
        return jsonify({'error': '文件不可用'}), 404
    
    task = task_store[task_id]
    output_path = task['output_path']
    
    # 获取目录和文件名
    directory = os.path.dirname(output_path)
    filename = os.path.basename(output_path)
    
    # 设置下载的文件名（保留原始文件名但添加_edit后缀）
    original_name = task['original_filename']
    base, ext = os.path.splitext(original_name)
    download_name = f"{base}_edit{ext}"
    
    # 使用URL编码处理文件名
    import urllib.parse
    encoded_name = urllib.parse.quote(download_name)
    
    # 直接使用send_from_directory，不设置download_name参数
    response = send_from_directory(
        directory,
        filename,
        as_attachment=True
    )
    
    # 手动设置Content-Disposition头，使用RFC 5987编码
    response.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_name}"
    
    return response

@app.route('/cleanup', methods=['POST'])
def cleanup_old_tasks():
    """手动触发清理旧任务"""
    # 启动Celery任务进行清理
    result = cleanup_old_tasks.delay()
    
    return jsonify({
        'message': '清理任务已启动',
        'task_id': result.id
    })

@app.route('/delete_all_tasks', methods=['POST'])
def delete_all_tasks():
    """删除所有任务"""
    for task_id in list(task_store.keys()):
        delete_task(task_id)
    return jsonify({'message': '所有任务已删除'})

@app.route('/delete_task/<task_id>', methods=['POST'])
def delete_task(task_id):
    """删除指定任务"""
    if task_id in task_store:
        task = task_store[task_id]
        if 'file_path' in task and os.path.exists(task['file_path']):
            os.remove(task['file_path'])
            
        if 'output_path' in task and os.path.exists(task['output_path']):
            os.remove(task['output_path'])
            
        # 从任务字典中删除
        del task_store[task_id]
        
        return jsonify({'message': '任务已删除'})
    
    return jsonify({'error': '任务不存在'}), 404

@app.route('/clean', methods=['GET'])
def clean_uploads():
    """清理uploads目录下的所有PDF文件（需要密码验证）"""
    # 获取请求中的密码参数
    password = request.args.get('password', '')
    
    # 从环境变量获取正确的密码
    correct_password = os.environ.get('CLEAN_PASSWORD')
    
    # 如果环境变量中没有设置密码，返回错误
    if not correct_password:
        return jsonify({'error': '服务器未配置清理密码'}), 500
    
    # 验证密码
    if password != correct_password:
        return jsonify({'error': '密码错误，无权清理文件'}), 403
    
    try:
        # 获取uploads目录中的所有PDF文件
        pdf_files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], '*.pdf'))
        
        # 删除文件
        deleted_count = 0
        for file_path in pdf_files:
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                print(f"删除文件 {file_path} 时出错: {str(e)}")
        
        # 清空Redis中的任务信息
        tasks_cleared = task_store.clear()
        
        return jsonify({
            'success': True,
            'message': f'成功清理 {deleted_count} 个PDF文件，{tasks_cleared} 个任务记录',
            'deleted_count': deleted_count,
            'tasks_cleared': tasks_cleared
        })
    except Exception as e:
        return jsonify({
            'error': f'清理文件时出错: {str(e)}'
        }), 500

# 设置定时任务，每天自动清理过期任务
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # 每天午夜执行清理任务
    sender.add_periodic_task(
        86400.0,  # 24小时 = 86400秒
        cleanup_old_tasks.s(),
        name='每天清理过期任务'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True) 