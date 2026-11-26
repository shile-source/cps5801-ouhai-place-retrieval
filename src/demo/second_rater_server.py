"""Loopback-only second-rater collection, separate storage and no evaluation route."""
from http.server import ThreadingHTTPServer
import json
from src.demo.annotation_server import handler
from src.evaluation.second_rater import SAMPLED_SESSION as SESSION,prepare_second_rater,SecondRaterPilot,make_page


def main():
    prepare_second_rater(session=SESSION,sample_per_query=10)
    page=SESSION/'annotation_second.html'
    page.write_text(make_page(total=80,sampled=True),encoding='utf-8')
    service=ThreadingHTTPServer(('127.0.0.1',8772),handler(SecondRaterPilot(SESSION),page_path=page,allow_evaluation=False))
    print(json.dumps({'url':'http://127.0.0.1:8772/','session':str(SESSION),'model_calls_enabled':False,'ratings_prefilled':False}),flush=True)
    service.serve_forever()


if __name__=='__main__':main()
