from django.shortcuts import render
from django.views import View
from goods.models import GoodsChannel, GoodsCategory
from meiduo_mall.utils.category import get_category
from .models import ContentCategory, Content


class IndexView(View):
    def get(self, request):
        # 频道分类信息
        categories = get_category()

        # 查询广告数据
        #1.查询广告位
        contents = ContentCategory.objects.all()
        content_dict = {}
        #2.遍历，查询每个位置的广告信息
        for content in contents:
            #3.将广告数据赋给指定的广告位
            content_dict[content.key] = content.content_set.filter(status=True).order_by('sequence')

        context = {
            'categories': categories,
            'contents': content_dict
        }
        return render(request, 'index.html', context)
