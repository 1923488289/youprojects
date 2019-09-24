from django.db import models
from django.contrib.auth.models import AbstractUser
from meiduo_mall.utils.models import BaseModel
from areas.models import Area


class User(AbstractUser):
    # 继承后，默认的属性、方法都有
    # 扩展新属性
    # 手机号
    mobile = models.CharField(max_length=11)
    # 邮箱激活状态
    email_active = models.BooleanField(default=False)
    # 默认收货地址
    default_address = models.ForeignKey('Address', related_name='users', null=True)

    class Meta:
        # 表名
        db_table = 'tb_users'


class Address(BaseModel):
    user = models.ForeignKey('User', related_name='addresses')  # 收货地址的用户
    title = models.CharField(max_length=10)  # 标题
    receiver = models.CharField(max_length=20)  # 收件人
    province = models.ForeignKey(Area, related_name='provinces')  # 省
    city = models.ForeignKey(Area, related_name='cities')  # 市
    district = models.ForeignKey(Area, related_name='districts')  # 区县
    detail = models.CharField(max_length=100)  # 详细地址
    mobile = models.CharField(max_length=11)  # 收件人的手机号
    tel = models.CharField(max_length=20, null=True)  # 固定电话，选填
    email = models.CharField(max_length=50, null=True)  # 邮箱，选填
    is_delete = models.BooleanField(default=False)  # 逻辑删除

    class Meta:
        db_table = 'tb_addresses'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'receiver': self.receiver,
            'province_id': self.province_id,
            'province': self.province.name,
            'city_id': self.city_id,
            'city': self.city.name,
            'district_id': self.district_id,
            'district': self.district.name,
            'place': self.detail,
            'mobile': self.mobile,
            'tel': self.tel,
            'email': self.email
        }
