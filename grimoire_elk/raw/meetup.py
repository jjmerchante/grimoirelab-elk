# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2019 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#   Alvaro del Castillo San Felix <acs@bitergia.com>
#

import hashlib

from .elastic import ElasticOcean
from ..elastic_mapping import Mapping as BaseMapping


class Mapping(BaseMapping):

    @staticmethod
    def get_elastic_mappings(es_major):
        """Get Elasticsearch mapping.

        :param es_major: major version of Elasticsearch, as string
        :returns:        dictionary with a key, 'items', with the mapping
        """

        mapping = '''
         {
            "dynamic":true,
                "properties": {
                    "data": {
                        "properties": {
                            "comments": {
                                "properties": {
                                    "comment": {
                                        "type": "text",
                                        "index": true
                                    },
                                    "member": {
                                        "properties": {
                                            "bio": {
                                                "type": "text",
                                                "index": true
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
        }
        '''

        return {"items": mapping}


class MeetupOcean(ElasticOcean):
    """Git Ocean feeder"""

    mapping = Mapping

    @classmethod
    def get_perceval_params_from_url(cls, url):
        params = []

        # The URL is directly the meetup group so use it as the tag
        params.append('--tag')
        params.append(url)
        # Add the group as the last param for perceval
        params.append(url)

        return params

    def _hash(self, name):
        sha1 = hashlib.sha1(name.encode('UTF-8', errors="surrogateescape"))
        return sha1.hexdigest()

    def _anonymize_item(self, item):
        """ Remove or hash the fields that contain personal information """
        item = item['data']

        if 'event_hosts' in item:
            for i, host in enumerate(item['event_hosts']):
                item['event_hosts'][i] = {
                    'id': host['id'],
                    'name': self._hash(host['name']),
                }

        if 'rsvps' in item:
            for rsvp in item['rsvps']:
                rsvp['member'] = {
                    'id': rsvp['member']['id'],
                    'name': self._hash(rsvp['member']['name']),
                    'event_context': {'host': rsvp['member']['event_context']['host']}
                }

        if 'comments' in item:
            for comment in item['comments']:
                comment['member'] = {
                    'id': comment['member']['id'],
                    'name': self._hash(comment['member']['name'])
                }
