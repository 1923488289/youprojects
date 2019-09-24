from django.db import models


class Area(models.Model):
    # django自动创建名为id的主键，所以不需要定义
    # 地区名称
    name = models.CharField(max_length=30)
    # 父级地区对象，自关联
    parent = models.ForeignKey('self', null=True, related_name='subs')

    class Meta:
        db_table = 'tb_areas'
