"""API for JupyterHub's proxy.

Custom proxy implementations can subclass :class:`Proxy`
and register in JupyterHub config:

.. sourcecode:: python

    from mymodule import MyProxy
    c.JupyterHub.proxy_class = MyProxy

Route Specification:

- A routespec is a URL prefix ([host]/path/), e.g.
  'host.tld/path/' for host-based routing or '/path/' for default routing.
- Route paths should be normalized to always start and end with '/'
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import traceback
import asyncio
import json
import time
import os
from functools import wraps

from tornado import gen
from tornado.httpclient import HTTPError

from jupyterhub import orm
from jupyterhub.metrics import CHECK_ROUTES_DURATION_SECONDS
from jupyterhub.objects import Server

from jupyterhub.proxy import ConfigurableHTTPProxy

def _one_at_a_time(method):
    """decorator to limit an async method to be called only once

    If multiple concurrent calls to this method are made,
    queue them instead of allowing them to be concurrently outstanding.
    """
    method._lock = asyncio.Lock()

    @wraps(method)
    async def locked_method(*args, **kwargs):
        async with method._lock:
            return await method(*args, **kwargs)

    return locked_method

class J4J_Proxy(ConfigurableHTTPProxy):
    async def delete_route(self, routespec):
        path = self._routespec_to_chp_path(routespec)
        try:
            await self.api_request(path, method='DELETE')
        except HTTPError as e:
            if e.code == 404:
                # Warn about 404s because something might be wrong
                # but don't raise because the route is gone,
                # which is the goal.
                self.log.debug("Route %s already deleted", routespec)
            else:
                raise

    async def add_user(self, user, server_name='', client=None):
        """Add a user's server to the proxy table."""
        # It happens that the HDFCloud JupyterLab answers, before the J4J_Proxy can find the Docker Container in the network. Because of this we wait one second (in this async function), before we add a user to the proxy. This delays the spawn for one second, but gives the Docker network time to establish the new hostname in the network.
        time.sleep(1)
        spawner = user.spawners[server_name]
        self.log.debug(
            "Adding user %s to proxy %s => %s",
            user.name,
            spawner.proxy_spec,
            spawner.server.host,
        )

        if spawner.pending and spawner.pending != 'spawn':
            raise RuntimeError(
                "%s is pending %s, shouldn't be added to the proxy yet!"
                % (spawner._log_name, spawner.pending)
            )

        await self.add_route(
            spawner.proxy_spec,
            spawner.server.host,
            {'user': user.name, 'server_name': server_name},
        )


    @_one_at_a_time
    async def check_routes(self, user_dict, service_dict, routes=None):
        """Check that all users are properly routed on the proxy."""
        start = time.perf_counter()  # timer starts here when user is created
        for user in user_dict.values():
            if user.authenticator.multiple_instances:
                await user.authenticator.update_mem(user, "Proxy - check_routes")
        if not routes:
            self.log.debug("Fetching routes to check")
            routes = await self.get_all_routes()
        # log info-level that we are starting the route-checking
        # this may help diagnose performance issues,
        # as we are about
        self.log.debug("Checking routes")
        user_routes = {path for path, r in routes.items() if 'user' in r['data']}
        futures = []

        good_routes = {self.app.hub.routespec}

        hub = self.hub
        if self.app.hub.routespec not in routes:
            futures.append(self.add_hub_route(hub))
        else:
            route = routes[self.app.hub.routespec]
            if route['target'] != hub.host:
                self.log.warning(
                    "Updating default route %s → %s", route['target'], hub.host
                )
                futures.append(self.add_hub_route(hub))
        for user in user_dict.values():
            for name, spawner in user.spawners.items():
                if spawner.ready:
                    spec = spawner.proxy_spec
                    good_routes.add(spec)
                    if spec not in user_routes:
                        self.log.warning(
                            "Adding missing route for %s (%s)", spec, spawner.server
                        )
                        futures.append(self.add_user(user, name))
                    else:
                        route = routes[spec]
                        if route['target'] != spawner.server.host:
                            self.log.warning(
                                "Updating route for %s (%s → %s)",
                                spec,
                                route['target'],
                                spawner.server,
                            )
                            futures.append(self.add_user(user, name))
                elif spawner.pending:
                    # don't consider routes stale if the spawner is in any pending event
                    # wait until after the pending state clears before taking any actions
                    # they could be pending deletion from the proxy!
                    good_routes.add(spawner.proxy_spec)

        # check service routes
        service_routes = {
            r['data']['service']: r for r in routes.values() if 'service' in r['data']
        }
        for service in service_dict.values():
            if service.server is None:
                continue
            good_routes.add(service.proxy_spec)
            if service.name not in service_routes:
                self.log.warning(
                    "Adding missing route for %s (%s)", service.name, service.server
                )
                futures.append(self.add_service(service))
            else:
                route = service_routes[service.name]
                if route['target'] != service.server.host:
                    self.log.warning(
                        "Updating route for %s (%s → %s)",
                        route['routespec'],
                        route['target'],
                        service.server.host,
                    )
                    futures.append(self.add_service(service))

        # Now delete the routes that shouldn't be there
        for routespec in routes:
            if routespec not in good_routes:
                route_as_list = list(filter(None, routespec.split('/')))
                route_user = None
                route_servername = None
                spawn_skip = False
                try:
                    #self.log.debug("Route as List: {}".format(route_as_list))
                    if route_as_list[0] == 'integration':
                        if route_as_list[1] == 'hub':
                            if route_as_list[2] == 'api':
                                if route_as_list[3] in ['cancel', 'jobstatus', 'token', 'uxnotification']:
                                    route_user = route_as_list[4]
                                    route_servername = route_as_list[5]
                                elif route_as_list[3] == 'users':
                                    route_user = route_as_list[4]
                                    route_servername = route_as_list[6]
                            elif route_as_list[2] == 'spawn-pending' or route_as_list[2] == 'spawn':
                                route_user = route_as_list[3]
                                route_servername = route_as_list[4]
                                spawn_skip = True
                        elif route_as_list[1] in ['user', 'spawn']:
                            route_user = route_as_list[2]
                            route_servername = route_as_list[3]
                            try:
                                # skip /tree and /lab , that's the routes we want to deny for dashboards
                                if route_as_list[1] == 'user' and route_as_list[4] not in ['lab', 'tree']:
                                    spawn_skip = True
                            except:
                                spawn_skip = True
                    else:
                        if route_as_list[0] == 'hub':
                            if route_as_list[1] == 'api':
                                if route_as_list[2] in ['cancel', 'jobstatus', 'token', 'uxnotification']:
                                    route_user = route_as_list[3]
                                    route_servername = route_as_list[4]
                                elif route_as_list[2] == 'users':
                                    route_user = route_as_list[3]
                                    route_servername = route_as_list[5]
                            elif route_as_list[1] == 'spawn-pending' or route_as_list[1] == 'spawn':
                                route_user = route_as_list[2]
                                route_servername = route_as_list[3]
                                spawn_skip = True
                        elif route_as_list[0] in ['user', 'spawn']:
                            route_user = route_as_list[1]
                            route_servername = route_as_list[2]
                            try:
                                # skip /tree and /lab , that's the routes we want to deny for dashboards
                                if route_as_list[0] == 'user' and route_as_list[4] not in ['lab', 'tree']:
                                    spawn_skip = True
                            except:
                                spawn_skip = True
                except:
                    self.log.debug("Err: {}".format(traceback.format_exc()))
                    route_user = None
                    route_servername = None
                    pass
                delete = False
                db_spawner = None
                if route_user:
                    db_user = self.db.query(orm.User).filter(orm.User.name == route_user).first()
                    if db_user:
                        self.db.refresh(db_user)
                        db_spawner = self.db.query(orm.Spawner).filter(orm.Spawner.user_id == db_user.id).filter(orm.Spawner.name == route_servername).first()
                        if db_spawner:
                            self.db.refresh(db_spawner)
                        if (not spawn_skip) and (not db_spawner or not db_spawner.server_id):
                            delete = True
                    else:
                        delete = True
                else:
                    delete = True
                if delete:
                    self.log.debug("Deleting stale route %s", routespec)
                    futures.append(self.delete_route(routespec))
                else:
                    if db_spawner:
                        db_server = self.db.query(orm.Server).filter(orm.Server.id == db_spawner.server_id).first()
                        if db_server:
                            self.db.refresh(db_server)
                        if route_user and user_dict.get(route_user) and db_server:
                            self.log.debug("Add Server to memory spawner %s", routespec)
                            user_dict.get(route_user).spawners[db_spawner.name].server = Server(orm_server=db_server)
        await gen.multi(futures)
        stop = time.perf_counter()  # timer stops here when user is deleted
        CHECK_ROUTES_DURATION_SECONDS.observe(stop - start)  # histogram metric

    def _reformat_routespec(self, routespec, chp_data):
        """Reformat CHP data format to JupyterHub's proxy API."""
        target = chp_data.pop('target')
        if 'jupyterhub' in chp_data:
            chp_data.pop('jupyterhub')
        return {'routespec': routespec, 'target': target, 'data': chp_data}

    async def get_all_routes(self, client=None):
        """Fetch the proxy's routes."""
        resp = await self.api_request('', client=client)
        chp_routes = json.loads(resp.body.decode('utf8', 'replace'))
        all_routes = {}
        all_server_dict = {}
        all_db_server = self.db.query(orm.Server).all()
        for db_server in all_db_server:
            self.db.refresh(db_server)
            if db_server.base_url:
                l = list(filter(None, db_server.base_url.split("/")))
                all_server_dict[l[1]] = l[2]
        for chp_path, chp_data in chp_routes.items():
            routespec = self._routespec_from_chp_path(chp_path)
            if 'jupyterhub' not in chp_data:
                # exclude routes not associated with JupyterHub
                is_running = False
                for user, server_name in all_server_dict.items():
                    if user in routespec and server_name in routespec:
                        is_running = True
                        break
                if is_running:
                    #self.log.debug("Omitting non-jupyterhub route %r", routespec)
                    continue
            all_routes[routespec] = self._reformat_routespec(routespec, chp_data)
        return all_routes
