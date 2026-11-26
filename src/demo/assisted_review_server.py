"""Only collect individual human reviews of explicit AI-rule suggestions."""
from http.server import ThreadingHTTPServer
from src.demo.adjudication_server import ROOT, handler
from src.evaluation.assisted_review import AssistedReview


if __name__ == '__main__':
    review = AssistedReview(ROOT / 'data/labels/assisted_ai30_76_v1_20261126', ROOT)
    server = ThreadingHTTPServer(('127.0.0.1', 8777), handler(review, ROOT / 'src/demo/assisted_review.html'))
    print('Assisted human review http://127.0.0.1:8777/; no model routes', flush=True)
    server.serve_forever()
