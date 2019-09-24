from goods.models import GoodsChannel


def get_category():
    # 1.查询频道
    channels = GoodsChannel.objects.order_by('group_id', 'sequence')
    categories = {}
    # 2.遍历频道，获取一级分类、二级分类数据
    for channel in channels:
        # 3.判断频道是否存在
        if channel.group_id not in categories:
            # 如果不存在则新建频道字典
            categories[channel.group_id] = {
                'channels': [],  # 一级分类
                'sub_cats': []  # 二级分类
            }
        # 3.1获取频道字典
        channel_dict = categories[channel.group_id]
        # 4.向频道中添加一级分类
        channel_dict['channels'].append({
            'name': channel.category.name,  # 一级分类名称
            'url': channel.url  # 频道链接
        })
        # 5.向频道中添加二级分类
        catetory2s = channel.category.subs.all()
        # 6.遍历，逐个添加二级分类
        for catetory2 in catetory2s:
            channel_dict['sub_cats'].append({
                'name': catetory2.name,  # 二级分类名称
                'sub_cats': catetory2.subs.all()  # 三级分类
            })
        '''
        {
            1:{
                'channels':[手机,相机,数码],
                'sub_cats':[
                    {
                        'name':'手机通讯',
                        'sub_cats':[手机,游戏手机,..]
                    }，
                    {
                        。。。。
                    }
                ]
            }，
            2：{
                'channels':[电脑,办公],
                'sub_cats':[]
            }
        }
        '''

    return categories
