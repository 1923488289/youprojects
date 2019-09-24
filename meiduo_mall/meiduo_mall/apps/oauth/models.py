from django.db import models
from users.models import User
from meiduo_mall.utils.models import BaseModel


class OAuthQQUser(BaseModel):
    # class OAuthQQUser(models.Model):
    user = models.ForeignKey(User)
    openid = models.CharField(max_length=50)

    class Meta:
        db_table = 'tb_oauth_qq'
