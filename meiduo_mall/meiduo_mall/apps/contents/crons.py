from django.shortcuts import render
from meiduo_mall.utils.category import get_category
from .models import ContentCategory
from django.conf import settings
import os


def generate_static_index_html():
    # 查询生成html字符串
    # 频道分类信息
    categories = get_category()
    # 查询广告数据
    # 1.查询广告位
    contents = ContentCategory.objects.all()
    content_dict = {}
    # 2.遍历，查询每个位置的广告信息
    for content in contents:
        # 3.将广告数据赋给指定的广告位
        content_dict[content.key] = content.content_set.filter(status=True).order_by('sequence')
    response = render(None, 'index.html', {
        'categories': categories,
        'contents': content_dict
    })
    html_str = response.content.decode()

    # 写文件
    file_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(file_path, 'w') as f1:
        f1.write(html_str)
