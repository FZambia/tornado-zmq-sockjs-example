# -*- coding: utf-8 -*-

import tornado.ioloop
import tornado.web
import sockjs.tornado
import logging
import zmq
from zmq.eventloop import ioloop
from zmq.eventloop.zmqstream import ZMQStream

# Install ZMQ ioloop instead of a tornado ioloop
# http://zeromq.github.com/pyzmq/eventloop.html
ioloop.install()


logging.getLogger().setLevel(logging.DEBUG)


TORNADO_PORT = 8001
ZMQ_PORT = 5556

context = zmq.Context()
publisher = context.socket(zmq.PUB)
publisher.bind("tcp://*:%s" % str(ZMQ_PORT))
publish_stream = ZMQStream(publisher)


class IndexHandler(tornado.web.RequestHandler):

    def get(self, *args, **kwargs):
        self.render('index.html')


class SocketConnection(sockjs.tornado.SockJSConnection):

    clients = set()

    def on_open(self, request):
        self.clients.add(self)

        subscriber = context.socket(zmq.SUB)
        subscriber.connect("tcp://localhost:%s" % str(ZMQ_PORT))
        subscriber.setsockopt(zmq.SUBSCRIBE, '')
        self.subscribe_stream = ZMQStream(subscriber)
        self.subscribe_stream.on_recv(self.on_message_published)

    def on_message(self, message):
        logging.info(
            'message received, publish it to %d clients' % len(self.clients)
        )
        publish_stream.send_unicode(message)

    def on_message_published(self, message):
        logging.info('client received new published message')
        self.send(message)

    def on_close(self):
        self.clients.remove(self)
        # Properly close ZMQ socket
        self.subscribe_stream.close()


def run():

    SocketRouter = sockjs.tornado.SockJSRouter(SocketConnection, '/socket')

    app = tornado.web.Application(
        [(r'/', IndexHandler), ] + SocketRouter.urls,
        debug=True,
    )

    app.listen(TORNADO_PORT)

    logging.info("app started, visit http://localhost:%s" % TORNADO_PORT)

    tornado.ioloop.IOLoop.instance().start()


def main():
    try:
        run()
    except KeyboardInterrupt:
        pass
    finally:
        publish_stream.close()


if __name__ == '__main__':
    main()
