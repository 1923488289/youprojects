from flask import current_app
from flask_restful import Resource, inputs
from flask_restful.reqparse import RequestParser
from . import constants
from models.news import Article
from cache import article as cache_article


class SearchResource(Resource):

    def get(self):
        # 检验参数
        qs_parser = RequestParser()
        qs_parser.add_argument('q', type=inputs.regex(r'^.{1,50}$'), required=True, location='args')
        qs_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_SEARCH_PER_PAGE_MIN,
                                                                 constants.DEFAULT_SEARCH_PER_PAGE_MAX, 'per_page'),
                               required=False, location='args')
        req = qs_parser.parse_args()
        q = req.q
        page = 1 if not req.page else req.page
        per_page = constants.DEFAULT_SEARCH_PER_PAGE_MIN if not req.per_page else req.per_page

        query_dict = {
            "from": per_page * (page - 1),
            "size": per_page,
            "_source": ["article_id", "title"],
            "query": {
                "bool": {
                    "must": {
                        "match": {
                            "_all": q
                        }
                    },
                    "filter": {
                        "term": {
                            "status": Article.STATUS.APPROVED
                        }
                    }
                }
            }
        }

        ret = current_app.es.search(index='articles', doc_type='article', body=query_dict)

        total_count = ret['hits']['total']
        results = []
        for item in ret['hits']['hits']:
            # article_id = item['_source']['article_id']
            article_id = item['_id']
            article_dict = cache_article.ArticleInfoCache(article_id).get()
            if article_dict:
                results.append(article_dict)

        # 返回接口
        # {
        # 	"message": "OK",
        # 	"data": {
        # 		"page": xx,
        # 		"per_page": xx,
        # 		"total_count": xx,
        # 		"results": [
        # 			{
        # 				"article_id":xx,
        # 				"title": xx,
        # 				"cover": xx
        # 			},
        # 			...
        # 		]
        # 	}
        # }

        return {"page": page,
                "per_page": per_page,
                "total_count": total_count,
                "results": results
                }


