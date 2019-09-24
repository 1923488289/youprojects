def get_breadcrumb(category3):
    # 1.二级分类
    category2 = category3.parent
    # 2.一级分类
    category1 = category2.parent
    # 3.构造页面需要的字典
    breadcrumb = {
        'cat1': {
            'name': category1.name,
            'url': category1.goodschannel_set.all()[0].url
        },
        'cat2': category2,
        'cat3': category3
    }
    return breadcrumb
