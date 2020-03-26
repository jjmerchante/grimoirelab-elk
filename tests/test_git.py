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
#     Alvaro del Castillo <acs@bitergia.com>
#     Valerio Cosentino <valcos@bitergia.com>
#
import logging
import requests
import time
import unittest

from base import TestBaseBackend
from grimoire_elk.raw.git import GitOcean
from grimoire_elk.enriched.enrich import (logger,
                                          DEMOGRAPHICS_ALIAS)
from grimoire_elk.enriched.utils import REPO_LABELS


HEADER_JSON = {"Content-Type": "application/json"}


class TestGit(TestBaseBackend):
    """Test Git backend"""

    connector = "git"
    ocean_index = "test_" + connector
    ocean_index_anonymized = "test_" + connector + "_anonymized"
    ocean_aliases = ["a", "b", "git-raw"]
    enrich_index = "test_" + connector + "_enrich"
    enrich_index_anonymized = "test_" + connector + "_enrich_anonymized"
    enrich_aliases = ["c", "d", "git"]

    def test_has_identites(self):
        """Test value of has_identities method"""

        enrich_backend = self.connectors[self.connector][2]()
        self.assertTrue(enrich_backend.has_identities())

    def test_items_to_raw(self):
        """Test whether JSON items are properly inserted into ES"""

        result = self._test_items_to_raw()
        self.assertEqual(result['items'], 9)
        self.assertEqual(result['raw'], 9)

        aliases = self.ocean_backend.elastic.list_aliases()
        self.assertListEqual(self.ocean_aliases, list(aliases.keys()))

    def test_raw_to_enrich(self):
        """Test whether the raw index is properly enriched"""

        result = self._test_raw_to_enrich()
        self.assertEqual(result['raw'], 9)
        self.assertEqual(result['enrich'], 9)

        enrich_backend = self.connectors[self.connector][2]()

        item = self.items[0]
        item['origin'] = 'https://admin:admin@gittest'
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['committer_name'], '')

        for item in self.items[1:]:
            eitem = enrich_backend.get_rich_item(item)
            self.assertNotEqual(eitem['committer_name'], 'Unknown')
            self.assertNotEqual(eitem['author_name'], 'Unknown')

        item = self.items[1]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['author_date'], '2012-08-14T14:32:15')
        self.assertEqual(eitem['author_date_weekday'], 2)
        self.assertEqual(eitem['author_date_hour'], 14)
        self.assertEqual(eitem['utc_author_date_weekday'], 2)
        self.assertEqual(eitem['utc_author_date_hour'], 17)

        self.assertEqual(eitem['author_uuid'], 'f3aee5067d4691544f10d915932c9f1d08cb3b36')
        self.assertEqual(eitem['author_domain'], 'gmail.com')
        self.assertEqual(eitem['author_name'], 'Eduardo Morais')

        self.assertEqual(eitem['commit_date'], '2012-08-14T14:32:15')
        self.assertEqual(eitem['commit_date_weekday'], 2)
        self.assertEqual(eitem['commit_date_hour'], 14)
        self.assertEqual(eitem['utc_commit_date_weekday'], 2)
        self.assertEqual(eitem['utc_commit_date_hour'], 17)

        item = self.items[8]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['author_date'], '2014-02-11T22:10:39')
        self.assertEqual(eitem['author_date_weekday'], 2)
        self.assertEqual(eitem['author_date_hour'], 22)
        self.assertEqual(eitem['utc_author_date_weekday'], 3)
        self.assertEqual(eitem['utc_author_date_hour'], 6)

        self.assertEqual(eitem['author_uuid'], '8abda7ad626330d5065d4c3a93fb45029a32bdcb')
        self.assertEqual(eitem['author_domain'], 'gmail.com')
        self.assertEqual(eitem['author_name'], 'Zhongpeng Lin (林中鹏)')

        self.assertEqual(eitem['commit_date'], '2014-02-11T22:10:39')
        self.assertEqual(eitem['commit_date_weekday'], 2)
        self.assertEqual(eitem['commit_date_hour'], 22)
        self.assertEqual(eitem['utc_commit_date_weekday'], 3)
        self.assertEqual(eitem['utc_commit_date_hour'], 6)

        aliases = self.enrich_backend.elastic.list_aliases()
        self.assertListEqual(self.enrich_aliases, list(aliases.keys()))

    def test_enrich_repo_labels(self):
        """Test whether the field REPO_LABELS is present in the enriched items"""

        self._test_raw_to_enrich()
        enrich_backend = self.connectors[self.connector][2]()

        for item in self.items:
            eitem = enrich_backend.get_rich_item(item)
            self.assertIn(REPO_LABELS, eitem)

    def test_raw_to_enrich_sorting_hat(self):
        """Test enrich with SortingHat"""

        result = self._test_raw_to_enrich(sortinghat=True)
        self.assertEqual(result['raw'], 9)
        self.assertEqual(result['enrich'], 9)

        enrich_backend = self.connectors[self.connector][2]()
        enrich_backend.sortinghat = True

        item = self.items[0]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['committer_name'], '')
        self.assertEqual(eitem['Commit_name'], '-- UNDEFINED --')
        self.assertEqual(eitem['Commit_user_name'], '-- UNDEFINED --')
        self.assertEqual(eitem['Commit_org_name'], '-- UNDEFINED --')
        self.assertEqual(eitem['Commit_multi_org_names'], ['-- UNDEFINED --'])

        self.assertEqual(eitem['author_name'], 'Eduardo Morais')
        self.assertEqual(eitem['Author_name'], 'Eduardo Morais')
        self.assertEqual(eitem['Author_user_name'], 'Unknown')
        self.assertEqual(eitem['Author_multi_org_names'], ['Unknown'])

    def test_raw_to_enrich_projects(self):
        """Test enrich with Projects"""

        result = self._test_raw_to_enrich(projects=True)
        self.assertEqual(result['raw'], 9)
        self.assertEqual(result['enrich'], 9)
        enrich_backend = self.connectors[self.connector][2]()
        url = self.es_con + "/" + self.enrich_index + "/_search"
        response = enrich_backend.requests.get(url, verify=False).json()

        for hit in response['hits']['hits']:
            source = hit['_source']
            if 'author_uuid' in source:
                self.assertIn('author_date', source)
                self.assertIn('author_date_weekday', source)
                self.assertIn('author_date_hour', source)
                self.assertIn('utc_author_date_weekday', source)
                self.assertIn('utc_author_date_hour', source)
                self.assertIn('author_uuid', source)
                self.assertIn('author_domain', source)
                self.assertIn('author_name', source)
                self.assertIn('commit_date', source)
                self.assertIn('commit_date_weekday', source)
                self.assertIn('commit_date_hour', source)
                self.assertIn('utc_commit_date_weekday', source)
                self.assertIn('utc_commit_date_hour', source)
                self.assertIn('project', source)
                self.assertIn('project_1', source)
                self.assertEqual(source['project'], 'Main')
                self.assertEqual(source['project_1'], 'Main')

    def test_refresh_identities(self):
        """Test refresh identities"""

        result = self._test_refresh_identities()
        # ... ?

    def test_refresh_project(self):
        """Test refresh project field for all sources"""

        result = self._test_refresh_project()
        # ... ?

    def test_demography_study(self):
        """ Test that the demography study works correctly """

        study, ocean_backend, enrich_backend = self._test_study('enrich_demography')

        with self.assertLogs(logger, level='INFO') as cm:

            if study.__name__ == "enrich_demography":
                study(ocean_backend, enrich_backend, date_field="utc_commit")

            self.assertEqual(cm.output[0], 'INFO:grimoire_elk.enriched.enrich:[git] Demography '
                                           'starting study %s/test_git_enrich'
                             % enrich_backend.elastic.anonymize_url(self.es_con))
            self.assertEqual(cm.output[-1], 'INFO:grimoire_elk.enriched.enrich:[git] Demography '
                                            'end %s/test_git_enrich'
                             % enrich_backend.elastic.anonymize_url(self.es_con))

        time.sleep(5)  # HACK: Wait until git enrich index has been written
        for item in enrich_backend.fetch():
            self.assertTrue('demography_min_date' in item.keys())
            self.assertTrue('demography_max_date' in item.keys())

        r = enrich_backend.elastic.requests.get(enrich_backend.elastic.index_url + "/_alias",
                                                headers=HEADER_JSON, verify=False)
        self.assertIn(DEMOGRAPHICS_ALIAS, r.json()[enrich_backend.elastic.index]['aliases'])

    def test_extra_study(self):
        """ Test that the extra study works correctly """

        study, ocean_backend, enrich_backend = self._test_study('enrich_extra_data')

        with self.assertLogs(logger, level='INFO') as cm:

            if study.__name__ == "enrich_extra_data":
                study(ocean_backend, enrich_backend,
                      json_url="https://gist.githubusercontent.com/valeriocos/893f55c28c4bd8fa7a217c4e201f4698/raw/"
                               "ba298a6fb09558e68c5e4ec6ae23b1c89fe920ef/test_extra_study.txt")

        time.sleep(5)  # HACK: Wait until git enrich index has been written
        for item in enrich_backend.fetch():
            self.assertTrue('extra_secret_repo' in item.keys())

    def test_enrich_forecast_activity(self):
        """ Test that the forecast activity study works correctly """

        study, ocean_backend, enrich_backend = self._test_study('enrich_forecast_activity')

        with self.assertLogs(logger, level='INFO') as cm:

            if study.__name__ == "enrich_forecast_activity":
                study(ocean_backend, enrich_backend, out_index='git_study_forecast_activity', observations=2)

                self.assertEqual(cm.output[0], 'INFO:grimoire_elk.enriched.enrich:'
                                               '[enrich-forecast-activity] Start study')
                self.assertEqual(cm.output[-1], 'INFO:grimoire_elk.enriched.enrich:'
                                                '[enrich-forecast-activity] End study')

        time.sleep(5)  # HACK: Wait until git enrich index has been written
        url = self.es_con + "/git_study_forecast_activity/_search"
        response = enrich_backend.requests.get(url, verify=False).json()
        for hit in response['hits']['hits']:
            source = hit['_source']
            self.assertIn('uuid', source)
            self.assertIn('origin', source)
            self.assertIn('repository', source)
            self.assertIn('interval_months', source)
            self.assertIn('from_date', source)
            self.assertIn('to_date', source)
            self.assertIn('study_creation_date', source)
            self.assertIn('grimoire_creation_date', source)
            self.assertIn('is_git_survived', source)
            self.assertIn('author_uuid', source)
            self.assertIn('author_name', source)
            self.assertIn('author_bot', source)
            self.assertIn('author_user_name', source)
            self.assertIn('author_org_name', source)
            self.assertIn('author_domain', source)
            self.assertIn('prediction_05', source)
            self.assertIn('prediction_07', source)
            self.assertIn('prediction_09', source)
            self.assertIn('next_activity_05', source)
            self.assertIn('next_activity_07', source)
            self.assertIn('next_activity_09', source)
            self.assertIn('metadata__gelk_version', source)
            self.assertIn('metadata__gelk_backend_name', source)
            self.assertIn('metadata__enriched_on', source)

        delete_survival = self.es_con + "/git_study_forecast_activity"
        requests.delete(delete_survival, verify=False)

    def test_onion_study(self):
        """ Test that the onion study works correctly """

        study, ocean_backend, enrich_backend = self._test_study('enrich_onion')
        study(ocean_backend, enrich_backend, in_index='test_git_enrich')

        url = self.es_con + "/_aliases"
        response = requests.get(url, verify=False).json()
        self.assertTrue('git_onion-enriched' in response)

        time.sleep(1)

        url = self.es_con + "/git_onion-enriched/_count"
        response = requests.get(url, verify=False).json()

        self.assertGreater(response['count'], 0)

        delete_onion = self.es_con + "/git_onion-enriched"
        requests.delete(delete_onion, verify=False)

    def test_enrich_areas_of_code(self):
        """ Test that areas of code works correctly"""

        study, ocean_backend, enrich_backend = self._test_study('enrich_areas_of_code')

        projects_json_repo = "/tmp/perceval_mc84igfc/gittest"
        projects_json = {
            "project": {
                "git": [
                    "/tmp/perceval_mc84igfc/gittest"
                ]
            }
        }
        prjs_map = {
            "git": {
                "/tmp/perceval_mc84igfc/gittest": "project"
            }
        }

        enrich_backend.json_projects = projects_json
        enrich_backend.projects_json_repo = projects_json_repo
        enrich_backend.prjs_map = prjs_map
        study(ocean_backend, enrich_backend, in_index='test_git')
        time.sleep(5)  # HACK: Wait until git area of code has been written
        url = self.es_con + "/git_aoc-enriched/_search"
        response = enrich_backend.requests.get(url, verify=False).json()
        for hit in response['hits']['hits']:
            source = hit['_source']
            self.assertIn('addedlines', source)
            self.assertIn('author_bot', source)
            self.assertIn('author_domain', source)
            self.assertIn('author_id', source)
            self.assertIn('author_name', source)
            self.assertIn('author_org_name', source)
            self.assertIn('author_multi_org_names', source)
            self.assertIn('author_user_name', source)
            self.assertIn('author_uuid', source)
            self.assertIn('committer', source)
            self.assertIn('committer_date', source)
            self.assertIn('date', source)
            self.assertIn('eventtype', source)
            self.assertIn('fileaction', source)
            self.assertIn('filepath', source)
            self.assertIn('files', source)
            self.assertIn('filetype', source)
            self.assertIn('file_name', source)
            self.assertIn('file_ext', source)
            self.assertIn('file_dir_name', source)
            self.assertIn('file_path_list', source)
            self.assertIn('git_author_domain', source)
            self.assertIn('grimoire_creation_date', source)
            self.assertIn('hash', source)
            self.assertIn('id', source)
            self.assertIn('message', source)
            self.assertIn('metadata__enriched_on', source)
            self.assertIn('metadata__timestamp', source)
            self.assertIn('metadata__updated_on', source)
            self.assertIn('origin', source)
            self.assertIn('owner', source)
            self.assertIn('perceval_uuid', source)
            self.assertIn('project', source)
            self.assertIn('project_1', source)
            self.assertIn('removedlines', source)
            self.assertIn('repository', source)
            self.assertIn('uuid', source)

        delete_survival = self.es_con + "/git_aoc-enriched"
        requests.delete(delete_survival, verify=False)

    def test_perceval_params(self):
        """Test the extraction of perceval params from an URL"""

        url = "https://github.com/grimoirelab/perceval"
        expected_params = [
            'https://github.com/grimoirelab/perceval'
        ]
        self.assertListEqual(GitOcean.get_perceval_params_from_url(url), expected_params)

        url = "https://github.com/grimoirelab/perceval /tmp/perceval-repo"
        expected_params = [
            'https://github.com/grimoirelab/perceval'
        ]
        self.assertListEqual(GitOcean.get_perceval_params_from_url(url), expected_params)

    def test_items_to_raw_anonymized(self):
        """Test whether JSON items are properly inserted into ES anonymized"""

        result = self._test_items_to_raw_anonymized()

        self.assertGreater(result['items'], 0)
        self.assertGreater(result['raw'], 0)
        self.assertEqual(result['items'], result['raw'])

        item = self.items[0]['data']
        self.assertEqual(item['Author'], 'e2ea52f7f782fe08109b762e474ff20656a51f47 <xxxxxx@gmail.com>')
        self.assertEqual(item['Commit'], '')

        item = self.items[1]['data']
        self.assertEqual(item['Author'], 'e2ea52f7f782fe08109b762e474ff20656a51f47 <xxxxxx@gmail.com>')
        self.assertEqual(item['Commit'], 'e2ea52f7f782fe08109b762e474ff20656a51f47 <xxxxxx@gmail.com>')

        item = self.items[6]['data']
        self.assertEqual(item['Author'], 'abe1a5515d468ed258124c4c946ceb34ef7ffbda <xxxxxx@gmail.com>')
        self.assertEqual(item['Commit'], 'abe1a5515d468ed258124c4c946ceb34ef7ffbda <xxxxxx@gmail.com>')

    def test_raw_to_enrich_anonymized(self):
        """Test whether the raw index is properly enriched"""

        result = self._test_raw_to_enrich_anonymized()

        self.assertGreater(result['raw'], 0)
        self.assertGreater(result['enrich'], 0)
        self.assertEqual(result['raw'], result['enrich'])

        enrich_backend = self.connectors[self.connector][2]()

        item = self.items[0]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['author_uuid'], '5fe609e6ddadd19697e69832ac1889bb942cccfb')
        self.assertEqual(eitem['author_domain'], 'gmail.com')
        self.assertEqual(eitem['author_name'], 'e2ea52f7f782fe08109b762e474ff20656a51f47')
        self.assertIsNone(eitem['committer_domain'])
        self.assertEqual(eitem['committer_name'], '')

        item = self.items[1]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['author_uuid'], '5fe609e6ddadd19697e69832ac1889bb942cccfb')
        self.assertEqual(eitem['author_domain'], 'gmail.com')
        self.assertEqual(eitem['author_name'], 'e2ea52f7f782fe08109b762e474ff20656a51f47')
        self.assertEqual(eitem['committer_domain'], 'gmail.com')
        self.assertEqual(eitem['committer_name'], 'e2ea52f7f782fe08109b762e474ff20656a51f47')

        item = self.items[6]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['author_uuid'], '221aa5305c73e6574dbba1865ccc930eaa6f59a8')
        self.assertEqual(eitem['author_domain'], 'gmail.com')
        self.assertEqual(eitem['author_name'], 'abe1a5515d468ed258124c4c946ceb34ef7ffbda')
        self.assertEqual(eitem['committer_domain'], 'gmail.com')
        self.assertEqual(eitem['committer_name'], 'abe1a5515d468ed258124c4c946ceb34ef7ffbda')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    unittest.main(warnings='ignore')
