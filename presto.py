"""Prestodoctor OAuth on Authomatic implementation."""
from argparse import Namespace
import time

from authomatic.core import json_qs_parser
from authomatic.providers.oauth2 import OAuth2

from websauna.system.model import now
from websauna.system.user.social import EmailSocialLoginMapper, \
    NotSatisfiedWithData

from trees.models import UserMedia


__author__ = "Mikko Ohtamaa <mikko@opensourcehacker.com>"
__license__ = "AGPL"


class PrestodoctorAuthomatic(OAuth2):
    """Prestodoctor Authomatic OAuth2 implementation.

    * Docs: https://github.com/PrestoDoctor/omniauth-prestodoctor/blob/master/lib/omniauth/strategies/prestodoctor.rb
    """

    user_authorization_url = 'https://prestodoctor.com/oauth/authorize'
    access_token_url = 'https://prestodoctor.com/oauth/token'
    user_info_url = 'https://prestodoctor.com/api/v1/user'
    info_base_url = "https://prestodoctor.com/api/v1/user"

    #: Comes from config file
    user_info_scope = []

    def _x_scope_parser(self, scope):
        """Space separated scopes"""
        return 'user_info recommendation photo_id'

    def _update_or_create_user(self, data, credentials=None, content=None):
        """Fetch user info from Prestodoctor specific endpoints."""
        super(PrestodoctorAuthomatic, self)._update_or_create_user(data, credentials, content)

        self.user.base_data = self.access(self.info_base_url, content_parser=json_qs_parser).data
        # Recommendation data might be empty if the user has not done medical evaluation yet
        self.user.recommendation_data = self.access(self.info_base_url + "/recommendation", content_parser=json_qs_parser).data or {}
        self.user.photo_data = self.access(self.info_base_url + "/photo_id", content_parser=json_qs_parser).data or {}
        return self.user

