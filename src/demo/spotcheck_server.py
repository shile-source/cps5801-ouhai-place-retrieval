"""Collect only the real60 sampled human decisions; no whole-batch acceptance."""
from http.server import ThreadingHTTPServer
from src.demo.adjudication_server import ROOT,handler
from src.evaluation.assisted_review import AssistedReview


if __name__=='__main__':
    review=AssistedReview(ROOT/'data/labels/user30_activity151_spotcheck_v1_20261127',ROOT)
    server=ThreadingHTTPServer(('127.0.0.1',8778),handler(review,ROOT/'src/demo/spotcheck.html'))
    print('http://127.0.0.1:8778/ human spotcheck only',flush=True)
    server.serve_forever()
