""" Simple Python class to access the Tesla JSON API
https://github.com/gglockner/teslajson
new auth and MFA-login by
https://github.com/enode-engineering/tesla-oauth2

The Tesla JSON API is described at:
http://docs.timdorr.apiary.io/

Example:

import teslajson
c = teslajson.Connection('youremail', 'yourpassword')
v = c.vehicles[0]
v.wake_up()
v.data_request('charge_state')
v.command('charge_start')
"""

try: # Python 3
    from urllib.parse import urlencode
    from urllib.request import Request, build_opener
    from urllib.request import ProxyHandler, HTTPBasicAuthHandler, HTTPHandler
except: # Python 2
    from urllib import urlencode
    from urllib2 import Request, build_opener
    from urllib2 import ProxyHandler, HTTPBasicAuthHandler, HTTPHandler
import json
import datetime
import calendar
import base64
import hashlib
import os
import re
import random
import time
from urllib.parse import parse_qs
import requests

class Connection(object):
    """Connection to Tesla Motors API"""
    def __init__(self,
            email='',
            password='',
            access_token='',
            proxy_url = '',
            proxy_user = '',
            proxy_password = ''):
        """Initialize connection object
        
        Sets the vehicles field, a list of Vehicle objects
        associated with your account

        Required parameters:
        email: your login for teslamotors.com
        password: your password for teslamotors.com
        
        Optional parameters:
        access_token: API access token
        proxy_url: URL for proxy server
        proxy_user: username for proxy server
        proxy_password: password for proxy server
        id and secret taken from https://www.teslaapi.io/authentication/oauth
        """
        self.proxy_url = proxy_url
        self.proxy_user = proxy_user
        self.proxy_password = proxy_password
        self.baseurl = "https://owner-api.teslamotors.com"
        self.api = "/api/1/"
        self.debug = False
        if access_token:
            self.__sethead(access_token)
        else:
            self.email = email
            self.password = password
            self.expiration = 0 # force refresh
        self.vehicles = [Vehicle(v, self) for v in self.get('vehicles')['response']]
    
    def get(self, command):
        """Utility command to get data from API"""
        return self.post(command, None)
    
    def post(self, command, data={}):
        """Utility command to post data to API"""
        now = calendar.timegm(datetime.datetime.now().timetuple())
        if now > self.expiration:
            auth = self.__login()
            self.__sethead(auth['access_token'],
                           auth['created_at'] + auth['expires_in'] - 86400)
        return self.__open("%s%s" % (self.api, command), headers=self.head, data=data)
    
    def __sethead(self, access_token, expiration=float('inf')):
        """Set HTTP header"""
        self.access_token = access_token
        self.expiration = expiration
        self.head = {"Authorization": "Bearer %s" % access_token}
    
    def __open(self, url, headers={}, data=None, baseurl=""):
        """Raw urlopen command"""
        if not baseurl:
            baseurl = self.baseurl
        req = Request("%s%s" % (baseurl, url), headers=headers)
        try:
            req.data = urlencode(data).encode('utf-8') # Python 3
        except:
            try:
                req.add_data(urlencode(data)) # Python 2
            except:
                pass

        # Proxy support
        if self.proxy_url:
            if self.proxy_user:
                proxy = ProxyHandler({'https': 'https://%s:%s@%s' % (self.proxy_user,
                                                                     self.proxy_password,
                                                                     self.proxy_url)})
                auth = HTTPBasicAuthHandler()
                opener = build_opener(proxy, auth, HTTPHandler)
            else:
                handler = ProxyHandler({'https': self.proxy_url})
                opener = build_opener(handler)
        else:
            opener = build_opener()
        resp = opener.open(req)
        charset = resp.info().get('charset', 'utf-8')
        return json.loads(resp.read().decode(charset))
    
    def __login(self):
        """login with MFA if necessary"""
        MAX_ATTEMPTS = 10
        CLIENT_ID = "81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384"
        UA = "Mozilla/5.0 (Linux; Android 10; Pixel 3 Build/QQ2A.200305.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/85.0.4183.81 Mobile Safari/537.36"
        X_TESLA_USER_AGENT = "TeslaApp/3.10.9-433/adff2e065/android/10"

        headers = {
            "User-Agent": UA,
            "x-tesla-user-agent": X_TESLA_USER_AGENT,
            "X-Requested-With": "com.teslamotors.tesla",
        }

        for attempt in range(MAX_ATTEMPTS):
            verifier_bytes = os.urandom(86)
            code_verifier = base64.urlsafe_b64encode(verifier_bytes).rstrip(b"=")
            code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier).digest()).rstrip(b"=")
            state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode("utf-8")

            params = (
                ("client_id", "ownerapi"),
                ("code_challenge", code_challenge),
                ("code_challenge_method", "S256"),
                ("redirect_uri", "https://auth.tesla.com/void/callback"),
                ("response_type", "code"),
                ("scope", "openid email offline_access"),
                ("state", state),
            )

            session = requests.Session()
            resp = session.get("https://auth.tesla.com/oauth2/v3/authorize", headers=headers, params=params)

            if resp.ok and "<title>" in resp.text:
                if self.debug:
                    print(f"Get auth form success - {attempt + 1} attempt(s).")
                break
            time.sleep(3)
        else:
            raise ValueError(f"Didn't get auth form in {MAX_ATTEMPTS} attempts.")

        csrf = re.search(r'name="_csrf".+value="([^"]+)"', resp.text).group(1)
        transaction_id = re.search(r'name="transaction_id".+value="([^"]+)"', resp.text).group(1)

        data = {
            "_csrf": csrf,
            "_phase": "authenticate",
            "_process": "1",
            "transaction_id": transaction_id,
            "cancel": "",
            "identity": self.email,
            "credential": self.password,
        }

        for attempt in range(MAX_ATTEMPTS):
            resp = session.post(
                "https://auth.tesla.com/oauth2/v3/authorize", headers=headers, params=params, data=data, allow_redirects=False
            )
            if resp.ok and (resp.status_code == 302 or "<title>" in resp.text):
                if self.debug:
                    print(f"Post auth form success - {attempt + 1} attempt(s).")
                break
            time.sleep(3)
        else:
            raise ValueError(f"Didn't post auth form in {MAX_ATTEMPTS} attempts.")

        # Determine if user has MFA enabled
        # In that case there is no redirect to `https://auth.tesla.com/void/callback` and app shows new form with Passcode / Backup Passcode field
        is_mfa = True if resp.status_code == 200 and "/mfa/verify" in resp.text else False

        if is_mfa:
            resp = session.get(
                f"https://auth.tesla.com/oauth2/v3/authorize/mfa/factors?transaction_id={transaction_id}", headers=headers,
            )
            print(resp.text)
            factor_id = resp.json()["data"][0]["id"]

            # Can use Passcode
            data = {"transaction_id": transaction_id, "factor_id": factor_id, "passcode": "YOUR_PASSCODE"}
            resp = session.post("https://auth.tesla.com/oauth2/v3/authorize/mfa/verify", headers=headers, json=data)
            if "error" in resp.text or not resp.json()["data"]["approved"] or not resp.json()["data"]["valid"]:
                raise ValueError("Invalid passcode.")

            data = {"transaction_id": transaction_id}

            for attempt in range(MAX_ATTEMPTS):
                resp = session.post(
                    "https://auth.tesla.com/oauth2/v3/authorize",
                    headers=headers,
                    params=params,
                    data=data,
                    allow_redirects=False,
                )
                if resp.headers.get("location"):
                    print(f"Got location in {attempt + 1} attempt(s).")
                    break
            else:
                raise ValueError(f"Didn't get location in {MAX_ATTEMPTS} attempts.")

        code = parse_qs(resp.headers["location"])["https://auth.tesla.com/void/callback?code"]
        headers = {"user-agent": UA, "x-tesla-user-agent": X_TESLA_USER_AGENT}
        payload = {
            "grant_type": "authorization_code",
            "client_id": "ownerapi",
            "code_verifier": code_verifier.decode("utf-8"),
            "code": code,
            "redirect_uri": "https://auth.tesla.com/void/callback",
        }

        resp = session.post("https://auth.tesla.com/oauth2/v3/token", headers=headers, json=payload)
        access_token = resp.json()["access_token"]

        headers["authorization"] = "bearer " + access_token
        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_id": CLIENT_ID,
        }
        resp = session.post("https://owner-api.teslamotors.com/oauth/token", headers=headers, json=payload)
        return resp.json()
            
            
            
class Vehicle(dict):
    """Vehicle class, subclassed from dictionary.
    
    There are 3 primary methods: wake_up, data_request and command.
    data_request and command both require a name to specify the data
    or command, respectively. These names can be found in the
    Tesla JSON API."""
    def __init__(self, data, connection):
        """Initialize vehicle class
        
        Called automatically by the Connection class
        """
        super(Vehicle, self).__init__(data)
        self.connection = connection
    
    def state(self):
        """Get vehicle data"""
        return self['state']
    
    def data_request(self, name):
        """Get vehicle data"""
        result = self.get('data_request/%s' % name)
        return result['response']
    
    def vehicle_data(self):
        """Get vehicle data"""
        result = self.get('vehicle_data')
        return result['response']
    
    def wake_up(self):
        """Wake the vehicle"""
        return self.post('wake_up')
    
    def charge_start(self):
        """Start Charging"""
        return self.post("charge_start")
    
    def command(self, name, data={}):
        """Run the command for the vehicle"""
        return self.post('command/%s' % name, data)
    
    def get(self, command):
        """Utility command to get data from API"""
        return self.connection.get('vehicles/%i/%s' % (self['id'], command))
    
    def post(self, command, data={}):
        """Utility command to post data to API"""
        return self.connection.post('vehicles/%i/%s' % (self['id'], command), data)

