from haystack import indexes
# 引入库存商品模块类，可修改
from .models import SKU


# 类的名称可修改，继承关系不可修改
class SKUIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        # 指定数据来源，可修改
        return SKU

    def index_queryset(self, using=None):
        # 指定搜索条件，可修改
        return self.get_model().objects.filter(is_launched=True)
