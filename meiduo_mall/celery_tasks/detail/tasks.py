from django.shortcuts import render
from goods.models import SKU
from meiduo_mall.utils.category import get_category
from meiduo_mall.utils.breadcrumb import get_breadcrumb
import os
from django.conf import settings
from celery_tasks.main import celery_app


@celery_app.task(name='generate_static_detail_html')
def generate_static_detail_html(sku_id):
    try:
        sku = SKU.objects.get(pk=sku_id)
    except:
        return render(None, '404.html')

    # - 频道分类
    categories = get_category()

    # 面包屑导航
    category3 = sku.category
    breadcrumb = get_breadcrumb(category3)

    # - 库存商品对象(根据主键查询)

    # 标准商品对象
    spu = sku.spu

    # - 规格选项
    # 当前库存商品的选项，如当前库存商品为15号，则当前规格选项信息为：[16,20]===>6,7
    # list1=sku.specs.order_by('spec_id')
    # option_current=[]
    # for info in list1:
    #     option_current.append(info.option_id)
    option_current = [info.option_id for info in sku.specs.order_by('spec_id')]

    # 查询所有的库存商品与选项信息
    skus = spu.sku_set.filter(is_launched=True)
    '''
    当前数据，需要包含：库存商品编号，选项列表
    当前已知：选项列表，找：库存商品编号
    {
        选项列表：库存商品编号
    }
    dict1[键]===>值
    '''
    sku_option_dict = {}
    for sku_temp in skus:
        option_list = [info.option_id for info in sku_temp.specs.order_by('spec_id')]
        sku_option_dict[tuple(option_list)] = sku_temp.id
    '''
    {
        (13,20):9,
        (13,21):10,
        ...
    }
    '''

    # 规格==》选项===》链接
    # 查询指定标准商品的所有规格
    specs = spu.specs.all()  # 6===>0,7=====>1
    spec_list = []
    for index, spec in enumerate(specs):  # [20,5,8,39]
        spec_dict = {
            'name': spec.name,
            'options': []
        }
        # 查询指定规格的所有选项
        options = spec.options.all()
        # 遍历，加入规格字典的列表中
        for option in options:
            # 根据当前选项获取新的完整选项，即保持其它规格的选项不变，只替换本规格的选项
            option_current_temp = option_current[:]
            option_current_temp[index] = option.id  # [16,20]==>[13,20]===>16--->13
            sku_id = sku_option_dict.get(tuple(option_current_temp), 0)

            spec_dict['options'].append({
                'name': option.value,
                'selected': option.id in option_current,
                'sku_id': sku_id
            })

        spec_list.append(spec_dict)

    # - 热销排行

    context = {
        'categories': categories,
        'breadcrumb': breadcrumb,
        'sku': sku,
        'spu': spu,
        'category_id': category3.id,
        'spec_list': spec_list
    }
    response = render(None, 'detail.html', context)
    html_str = response.content.decode()

    file_path = os.path.join(settings.BASE_DIR, 'static/details/%d.html' % sku.id)
    with open(file_path, 'w') as f1:
        f1.write(html_str)
