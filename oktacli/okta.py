import enum
import json

import requests


class REST(enum.Enum):
    get = "get"
    post = "post"


class Okta:

    def __init__(self, url, token):
        self.token = token
        self.path_base = "/api/v1"
        self.url = url + self.path_base

        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type':  'application/json',
            'Accept':        'application/json',
            'Authorization': 'SSWS ' + token,
        })

    def _call_okta(self, path, method, params={}, body_obj=None):
        call_method = getattr(self.session, method.value)
        call_params = {
            "params": params,
        }
        if method == REST.post and body_obj:
            call_params["data"] = json.dumps(body_obj)
        rsp = call_method(self.url + path, **call_params)
        rv = rsp.json()
        # NOW, we either have a SINGLE DICT in the rv variable,
        #     *OR*
        # a list.
        while True:
            # raise if there was an error
            if rsp.status_code >= 400:
                raise requests.HTTPError(json.dumps(rsp.json()))
            # now, let's get all the "next" links. if we do NOT have a list,
            # we do not have "next" links :) . handy!
            url = rsp.links.get("next", {"url": ""})["url"]
            if not url:
                break
            rsp = self.session.get(url)
            # now the += operation is safe, cause we have a list.
            # this is a liiiitle bit implicit, but should work smoothly.
            rv += rsp.json()
        # filter out _links items from the final result list
        if isinstance(rv, list):
            rv = list(filter(lambda x: x.pop("_links", None), rv))
        elif isinstance(rv, dict):
            rv.pop("_links", None)
        return rv

    def list_groups(self, query="", filter=""):
        params = {}
        if query:
            params["query"] = query
        if filter:
            params["filter"] = filter
        return self._call_okta("/groups", REST.get, params=params)

    def list_users(self, filter_query="", search_query=""):
        if filter_query:
            params = {"filter": filter_query}
        elif search_query:
            params = {"search": search_query}
        else:
            params = {}
        return self._call_okta("/users", REST.get, params=params)

    def add_user(self, query_params, body_object):
        body = json.dumps(body_object).encode("utf-8")
        rsp = self.session.post(self.url + "users/",
                                params=query_params,
                                data=body)
        if rsp.status_code >= 400:
            raise requests.HTTPError(json.dumps(rsp.json()))
        return rsp.json()

    def update_user(self, user_id, body_object):
        body = json.dumps(body_object).encode("utf-8")
        rsp = self.session.post(self.url + "users/" + user_id,
                                data=body)
        if rsp.status_code >= 400:
            raise requests.HTTPError(json.dumps(rsp.json()))
        return rsp.json()

    def reset_password(self, user_id, *, send_email=True):
        url = self.url + f"users/{user_id}/lifecycle/reset_password"
        rsp = self.session.post(
                url,
                params={'sendEmail': f"{str(send_email).lower()}"}
        )
        if rsp.status_code >= 400:
            raise requests.HTTPError(json.dumps(rsp.json()))
        return rsp.json()

