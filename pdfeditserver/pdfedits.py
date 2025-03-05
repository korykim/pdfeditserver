#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF页面删除工具

这个脚本用于从PDF文件中删除指定页面。
使用方法：
python pdfedits.py input.pdf 1 2 3
将会删除input.pdf中的第1,2,3页，并生成新文件input_edit.pdf
"""

import os
import sys
import argparse
from PyPDF2 import PdfReader, PdfWriter

def generate_output_path(input_path):
    """
    根据输入文件路径生成输出文件路径
    
    Args:
        input_path (str): 输入PDF文件的路径
    
    Returns:
        str: 输出PDF文件的路径
    """
    try:
        # 分离文件路径和扩展名
        base_path, ext = os.path.splitext(input_path)
        
        # 确保文件名中的特殊字符（包括中文）被正确处理
        # 使用os.path.basename和os.path.dirname来正确处理路径
        dir_path = os.path.dirname(base_path)
        file_name = os.path.basename(base_path)
        
        # 生成新的输出路径
        output_path = os.path.join(dir_path, f"{file_name}_edit{ext}")
        
        # 打印路径信息，便于调试
        print(f"输入路径: {input_path}")
        print(f"基础路径: {base_path}")
        print(f"目录路径: {dir_path}")
        print(f"文件名: {file_name}")
        print(f"输出路径: {output_path}")
        
        return output_path
    except Exception as e:
        # 记录错误信息
        print(f"生成输出路径时出错: {str(e)}")
        # 使用简单的方法作为备选
        return f"{input_path}_edit"

def delete_pdf_pages(input_path, pages_to_delete):
    """
    从PDF文件中删除指定页面
    
    Args:
        input_path (str): 输入PDF文件的路径
        pages_to_delete (list): 要删除的页面号列表（从1开始）
    
    Raises:
        FileNotFoundError: 当输入文件不存在时
        ValueError: 当页面号无效时
        Exception: 其他PDF处理错误
    """
    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到输入文件：{input_path}")
    
    try:
        # 生成输出文件路径
        output_path = generate_output_path(input_path)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建PDF读取器对象
        pdf_reader = PdfReader(input_path)
        # 创建PDF写入器对象
        pdf_writer = PdfWriter()
        
        # 获取总页数
        total_pages = len(pdf_reader.pages)
        
        # 检查要删除的页面是否有效
        for page_num in pages_to_delete:
            if page_num < 1 or page_num > total_pages:
                raise ValueError(f"页面号 {page_num} 无效。PDF总共有 {total_pages} 页")
        
        # 将不需要删除的页面添加到写入器
        pages_kept = 0
        for i in range(total_pages):
            if (i + 1) not in pages_to_delete:
                page = pdf_reader.pages[i]
                pdf_writer.add_page(page)
                pages_kept += 1
        
        # 写入新的PDF文件
        with open(output_path, 'wb') as output_file:
            pdf_writer.write(output_file)
        
        return output_path, total_pages, pages_kept
    
    except Exception as e:
        # 记录错误信息
        print(f"处理PDF时出错: {str(e)}")
        # 重新抛出异常
        raise

def main():
    """主函数：处理命令行参数并执行PDF页面删除"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description='从PDF文件中删除指定页面',
        formatter_class=argparse.RawDescriptionHelpFormatter  # 保留换行格式
    )
    parser.add_argument('input_pdf', nargs='?', help='输入PDF文件的路径')
    parser.add_argument('pages', type=int, nargs='*', help='要删除的页面号（从1开始）')
    
    # 添加使用示例
    parser.epilog = '''
    使用示例:
    python pdfedits.py input.pdf 1 2 3   # 删除 input.pdf 的第1、2、3页
    python pdfedits.py                    # 显示此帮助信息
    '''
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 如果没有提供输入文件或页码，显示帮助信息
    if args.input_pdf is None or not args.pages:
        parser.print_help()
        sys.exit(0)
    
    try:
        # 执行PDF页面删除
        output_path, total_pages, pages_kept = delete_pdf_pages(args.input_pdf, args.pages)
        
        # 打印处理结果
        print(f"\n处理完成！")
        print(f"原PDF总页数：{total_pages}")
        print(f"删除页数：{len(args.pages)}")
        print(f"保留页数：{pages_kept}")
        print(f"新文件已保存为：{output_path}")
        
    except FileNotFoundError as e:
        print(f"\n错误：{str(e)}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"\n错误：{str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n发生未知错误：{str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()