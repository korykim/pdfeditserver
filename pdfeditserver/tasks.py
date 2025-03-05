#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Celery任务模块

这个模块定义了用于PDF处理的Celery任务。
"""

import os
import time
import logging
from celery.exceptions import MaxRetriesExceededError
from .celery_app import celery_app, task_store  # 从celery_app导入Redis任务存储
from .pdfedits import delete_pdf_pages
import PyPDF2

# 配置日志记录
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name='process_pdf', max_retries=3, default_retry_delay=5)
def process_pdf_task(self, task_id, file_path, pages_to_delete, original_filename):
    """
    处理PDF文件的Celery任务
    
    Args:
        task_id (str): 任务ID
        file_path (str): PDF文件路径
        pages_to_delete (list): 要删除的页面列表
        original_filename (str): 原始文件名
    """
    try:
        # 检查并初始化任务存储
        if task_id not in task_store:
            task_store[task_id] = {
                'status': 'processing',
                'file_path': file_path,
                'original_filename': original_filename,
                'created_at': time.time()
            }
        else:
            # 更新任务状态为处理中
            task_store[task_id]['status'] = 'processing'
            
        self.update_state(state='PROCESSING')
        
        # 记录任务信息
        logger.info(f"处理任务 {task_id}:")
        logger.info(f"  文件路径: {file_path}")
        logger.info(f"  要删除的页面: {pages_to_delete}")
        logger.info(f"  原始文件名: {original_filename}")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到文件: {file_path}")
        
        # 首先获取PDF的总页数并立即更新task_store
        total_pages = 0
        try:
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)
                
                # 立即更新task_store中的total_pages信息
                task_store.update(task_id, {
                    'status': 'processing',
                    'total_pages': total_pages
                })
                
                # 打印调试信息
                print(f"已获取PDF总页数: {total_pages}，已更新task_store[{task_id}]")
                logger.info(f"已获取PDF总页数: {total_pages}，已更新task_store[{task_id}]")
                
                # 打印当前task_store内容，用于调试
                print(f"当前task_store[{task_id}]内容: {task_store[task_id]}")
        except Exception as e:
            error_msg = f"获取PDF页数时出错: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            # 继续执行，不要因为获取页数失败而中断整个任务
            
        # 如果是空的pages_to_delete（即只是获取PDF信息），直接返回
        if not pages_to_delete:
            task_store.update(task_id, {
                'status': 'completed',
                'total_pages': total_pages,
                'pages_kept': total_pages,
                'pages_deleted': 0
            })
            print(f"PDF信息获取完成，总页数: {total_pages}")
            logger.info(f"PDF信息获取完成，总页数: {total_pages}")
            return {
                'status': 'completed',
                'total_pages': total_pages,
                'pages_kept': total_pages,
                'pages_deleted': 0
            }
        
        # 执行PDF页面删除
        output_path, total_pages, pages_kept = delete_pdf_pages(file_path, pages_to_delete)
        
        # 打印输出信息
        print(f"  处理完成:")
        print(f"  输出路径: {output_path}")
        print(f"  总页数: {total_pages}")
        print(f"  保留页数: {pages_kept}")
        
        try:
            # 更新任务状态为完成
            result = {
                'status': 'completed',
                'output_path': output_path,
                'total_pages': total_pages,
                'pages_kept': pages_kept,
                'pages_deleted': len(pages_to_delete)
            }
            
            # 更新任务存储并验证更新
            print(f"正在更新任务状态: {task_id}")
            updated_task = task_store.update(task_id, result)
            print(f"已更新任务状态，正在验证...")
            print(f"验证任务状态: {updated_task}")
            
            if updated_task.get('status') != 'completed':
                raise Exception(f"任务状态更新失败: {updated_task}")
                
            # 设置Celery任务状态
            self.update_state(state='SUCCESS', meta=result)
            print(f"Celery任务状态已更新为SUCCESS")
            
            return result
            
        except Exception as e:
            error_msg = f"更新任务状态时出错: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            raise
        
    except (FileNotFoundError, ValueError) as e:
        # 这些错误不需要重试，直接标记为失败
        error_message = str(e)
        print(f"处理PDF时出错 (不重试): {error_message}")
        
        # 更新任务状态为失败
        error_result = {
            'status': 'failed',
            'error': error_message
        }
        
        # 更新任务存储
        if task_id in task_store:
            task_store.update(task_id, error_result)
        
        # 将任务标记为失败
        self.update_state(state='FAILURE', meta=error_result)
        
        # 重新抛出异常
        raise
    except Exception as e:
        # 记录错误信息
        error_message = str(e)
        print(f"处理PDF时出错 (将重试): {error_message}")
        import traceback
        traceback.print_exc()
        
        # 更新任务状态
        retry_info = {
            'status': 'retrying',
            'error': error_message,
            'retry_count': self.request.retries
        }
        
        # 更新任务存储
        if task_id in task_store:
            task_store.update(task_id, retry_info)
        
        # 尝试重试任务
        try:
            # 重试任务，使用指数退避策略
            retry_delay = 5 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=retry_delay)
        except MaxRetriesExceededError:
            # 超过最大重试次数
            print(f"超过最大重试次数，任务失败: {task_id}")
            
            # 更新任务状态为失败
            final_error = {
                'status': 'failed',
                'error': f"处理失败，已重试 {self.request.retries} 次: {error_message}"
            }
            
            # 更新任务存储
            if task_id in task_store:
                task_store.update(task_id, final_error)
            
            # 将任务标记为失败
            self.update_state(state='FAILURE', meta=final_error)
            
            # 重新抛出异常
            raise

@celery_app.task(bind=True, max_retries=2)
def cleanup_old_tasks(self):
    """
    清理旧任务的定时任务
    """
    try:
        current_time = time.time()
        expired_tasks = []
        
        # 查找超过24小时的任务
        for task_id, task in list(task_store.items()):
            if current_time - task['created_at'] > 24 * 60 * 60:
                # 删除相关文件
                if 'file_path' in task and os.path.exists(task['file_path']):
                    try:
                        os.remove(task['file_path'])
                    except Exception as e:
                        print(f"删除文件 {task['file_path']} 时出错: {str(e)}")
                
                if 'output_path' in task and os.path.exists(task['output_path']):
                    try:
                        os.remove(task['output_path'])
                    except Exception as e:
                        print(f"删除文件 {task['output_path']} 时出错: {str(e)}")
                
                # 从任务字典中删除
                del task_store[task_id]
                expired_tasks.append(task_id)
        
        return {
            'message': f'已清理 {len(expired_tasks)} 个过期任务',
            'expired_tasks': expired_tasks
        }
    except Exception as e:
        print(f"清理任务时出错: {str(e)}")
        try:
            raise self.retry(exc=e, countdown=60)
        except MaxRetriesExceededError:
            print("清理任务失败，超过最大重试次数")
            raise 