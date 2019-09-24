from django.db import models
from meiduo_mall.utils.models import BaseModel
from orders.models import OrderInfo


class AlipayInfo(BaseModel):
    # 订单
    order = models.ForeignKey(OrderInfo, related_name='alipays')
    # 支付宝流水号
    alipay_id = models.CharField(max_length=100)

    class Meta:
        db_table = 'tb_alipay'
