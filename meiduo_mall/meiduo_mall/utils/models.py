from django.db import models


class BaseModel(models.Model):
    # 自动设置为添加时间
    create_time = models.DateTimeField(auto_now_add=True)
    # 自动设置为修改时间
    update_time = models.DateTimeField(auto_now=True)

    # 注意：定义模型类后，会生成表与之对象
    class Meta:
        # 当前模型类不会生成表，而是用于其它模型类的继承
        abstract = True
