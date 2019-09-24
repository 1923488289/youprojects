from flask import g, current_app
from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from models import db
from utils.decorators import login_required
from utils.parser import check_image
from utils.qiniu_storage import upload
from models.user import User
from cache import user as cache_user
from cache import statistic as cache_stastistic


class PhotoResource(Resource):
    """更新用户的头像"""

    method_decorators = [login_required]

    def patch(self):
        # 接受
        # 校验
        rp = RequestParser()
        rp.add_argument('photo', type=check_image, required=True, location="files")
        req = rp.parse_args()
        image_file = req.photo
        # 处理
        # 上传图片
        image_name = upload(image_file.read())
        # 将文件地址保存到数据库
        User.query.filter(User.id == g.user_id).update({'profile_photo': image_name})
        db.session.commit()  # 如果更新数据库出错，flask-sqlalchemy是可以自动回滚的
        # 返回
        photo_url = current_app.config['QINIU_DOMAIN'] + image_name
        return {'photo_url': photo_url}, 201


class UserResource(Resource):
    """用户资料接口"""

    # /users/<user_id>
    def get(self, user_id):
        # 接受
        # 校验
        cache_tool = cache_user.UserProfileCache(user_id)
        if not cache_tool.determine_user_exists():
            # 用户不存在
            return {'message': 'User does not exits'}, 400
        # 处理
        user_dict = cache_tool.get()
        # 可获得参数
        #       'mobile': user.mobile,
        #       'name': user.name,
        #       'photo': user.profile_photo,
        #       'intro': user.introduction,
        #       'certi': user.certificate
        # 需要返回的数据
        # 	    "user_id": xx,
        # 		"name": xx,
        # 		"photo": xx,
        # 		"intro": xx,
        # 		"certi": xxx,
        # 		"article_count": xxx,
        # 		"follows_count": xxx,
        # 		"fans_count": xx,
        # 		"liking_count": xxx
        # 依据以上修改构建返回数据
        del user_dict['mobile']
        user_dict['user_id'] = user_id
        user_dict['photo'] = current_app.config['QINIU_DOMAIN'] + user_dict['photo']

        user_dict['article_count'] = cache_stastistic.UserArticlesCountStorage.get(user_id)
        user_dict['follows_count'] = cache_stastistic.UserFollowingsCountStorage.get(user_id)
        user_dict['fans_count'] = cache_stastistic.UserFansCountStorage.get(user_id)
        user_dict['liking_count'] = cache_stastistic.UserLikingCountStorage.get(user_id)

        # 返回
        return user_dict
