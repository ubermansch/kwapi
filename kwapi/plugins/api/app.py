# Author: François Rossigneux <francois.rossigneux@inria.fr>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Set up the API server application instance."""

import sys
import thread

import flask
from oslo.config import cfg

from kwapi.openstack.common import log
from kwapi.plugins import listen
import acl
from collector import Collector
import v1

LOG = log.getLogger(__name__)

app_opts = [
    cfg.BoolOpt('acl_enabled',
                required=True,
                ),
    cfg.IntOpt('api_port',
               required=True,
               ),
]

cfg.CONF.register_opts(app_opts)


def make_app():
    """Instantiates Flask app, attaches collector database, installs acl."""
    LOG.info('Starting API')
    app = flask.Flask(__name__)
    app.register_blueprint(v1.blueprint, url_prefix='/v1')

    collector = Collector()
    collector.clean()

    thread.start_new_thread(listen, (collector.add,))

    @app.before_request
    def attach_config():
        flask.request.collector = collector
        collector.lock.acquire()

    @app.after_request
    def unlock(response):
        collector.lock.release()
        return response

    # Install the middleware wrapper
    if cfg.CONF.acl_enabled:
        acl.install(app, cfg.CONF)

    return app


def start():
    """Starts Kwapi API."""
    cfg.CONF(sys.argv[1:],
             project='kwapi',
             default_config_files=['/etc/kwapi/api.conf']
             )
    log.setup('kwapi')
    root = make_app()
    root.run(host='0.0.0.0', port=cfg.CONF.api_port)
