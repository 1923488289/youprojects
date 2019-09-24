from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# 定义flask对象
app = Flask(__name__)


# 配置
class Config(object):
    SQLALCHEMY_DATABASE_URI = 'mysql://root:mysql@127.0.0.1:3306/toutiao'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True


# 加载配置
app.config.from_object(Config)

# 声明sqlalchemy对象
# 方式一
db = SQLAlchemy(app)


# 方式二
# db = SQLAlchemy()
# db.init_app(app)
# 区别
# 方式2在flask程序运行之外使用时 需要把数据库操作的语句放到flask应用上下文环境之下 with app.app_context():


# 声明要操作的模型类
class User(db.Model):
    """
    用户基本信息
    """
    __tablename__ = 'user_basic'

    class STATUS:
        ENABLE = 1
        DISABLE = 0

    id = db.Column('user_id', db.Integer, primary_key=True, doc='用户ID')
    mobile = db.Column(db.String, doc='手机号')
    password = db.Column(db.String, doc='密码')
    name = db.Column('user_name', db.String, doc='昵称')
    profile_photo = db.Column(db.String, doc='头像')
    last_login = db.Column(db.DateTime, doc='最后登录时间')
    is_media = db.Column(db.Boolean, default=False, doc='是否是自媒体')
    is_verified = db.Column(db.Boolean, default=False, doc='是否实名认证')
    introduction = db.Column(db.String, doc='简介')
    certificate = db.Column(db.String, doc='认证')
    article_count = db.Column(db.Integer, default=0, doc='发帖数')
    following_count = db.Column(db.Integer, default=0, doc='关注的人数')
    fans_count = db.Column(db.Integer, default=0, doc='被关注的人数（粉丝数）')
    like_count = db.Column(db.Integer, default=0, doc='累计点赞人数')
    read_count = db.Column(db.Integer, default=0, doc='累计阅读人数')

    account = db.Column(db.String, doc='账号')
    email = db.Column(db.String, doc='邮箱')
    status = db.Column(db.Integer, default=1, doc='状态，是否可用')

    # 两种方法都可以
    # followings = db.relationship('Relation', primaryjoin='User.id==Relation.user_id')
    followings = db.relationship('Relation', foreign_keys='Relation.user_id')

    # 为了方便关联查询到另外表的数据，所以额外自己补充的属性
    # 我们知道对应一个用户基本信息表的对象（user1) 在UserProfile用户详细信息表中 只有一条数据与之对应，是一对一的关系，所以在获取这个关联属性的数据时
    # 也只会返回一个UserProfile对象，使用uselist=False 表示对于这一个对象 不使用列表返回，直接返回对象
    # profile = db.relationship('UserProfile', uselist=False)
    profile = db.relationship('UserProfile', primaryjoin='User.id==foreign(UserProfile.id)', uselist=False)


class UserProfile(db.Model):
    """
    用户资料表
    """
    __tablename__ = 'user_profile'

    class GENDER:
        MALE = 0
        FEMALE = 1

    # id = db.Column('user_id', db.Integer, db.ForeignKey('user_basic.user_id'), primary_key=True, doc='用户ID') # 关联查询方式1
    id = db.Column('user_id', db.Integer, primary_key=True, doc='用户ID')
    gender = db.Column(db.Integer, default=0, doc='性别')
    birthday = db.Column(db.Date, doc='生日')
    real_name = db.Column(db.String, doc='真实姓名')
    id_number = db.Column(db.String, doc='身份证号')
    id_card_front = db.Column(db.String, doc='身份证正面')
    id_card_back = db.Column(db.String, doc='身份证背面')
    id_card_handheld = db.Column(db.String, doc='手持身份证')
    ctime = db.Column('create_time', db.DateTime, default=datetime.now, doc='创建时间')
    utime = db.Column('update_time', db.DateTime, default=datetime.now, onupdate=datetime.now, doc='更新时间')
    register_media_time = db.Column(db.DateTime, doc='注册自媒体时间')

    area = db.Column(db.String, doc='地区')
    company = db.Column(db.String, doc='公司')
    career = db.Column(db.String, doc='职业')

    followings = db.relationship('Relation', foreign_keys='Relation.user_id')


class Relation(db.Model):
    """
    用户关系表
    """
    __tablename__ = 'user_relation'

    class RELATION:
        DELETE = 0
        FOLLOW = 1
        BLACKLIST = 2

    id = db.Column('relation_id', db.Integer, primary_key=True, doc='主键ID')
    user_id = db.Column(db.Integer, db.ForeignKey('user_basic.user_id'), db.ForeignKey('user_profile.user_id'),
                        doc='用户ID')
    target_user_id = db.Column(db.Integer, db.ForeignKey('user_basic.user_id'), doc='目标用户ID')
    relation = db.Column(db.Integer, doc='关系')
    ctime = db.Column('create_time', db.DateTime, default=datetime.now, doc='创建时间')
    utime = db.Column('update_time', db.DateTime, default=datetime.now, onupdate=datetime.now, doc='更新时间')


# sys.path.extend(['/home/python/TouTiaoWeb/Flask-develop'])
# from db_SQLAlchemy import User
# from db_SQLAlchemy import UserProfile


@app.route('/')
def index():
    user = User(mobile='18911111122', name='itniubi')
    db.session.add(user)
    db.session.flush()  # 将db.session记录的sql传到数据库中执行
    profile = UserProfile(id=user.id)
    db.session.add(profile)
    db.session.commit()
    return 'ok'


if __name__ == '__main__':
    app.run(host='0.0.0.0')
