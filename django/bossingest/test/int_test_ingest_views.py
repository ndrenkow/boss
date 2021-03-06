# Copyright 2016 The Johns Hopkins University Applied Physics Laboratory
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import unittest
from rest_framework.test import APITestCase


from rest_framework.test import APITestCase
from django.conf import settings
from bosscore.test.setup_db import SetupTestDB
from bossingest.test.setup import SetupTests
from bossingest.ingest_manager import IngestManager

from ndingest.ndqueue.uploadqueue import UploadQueue
from ndingest.ndqueue.ingestqueue import IngestQueue
from ndingest.ndingestproj.bossingestproj import BossIngestProj

version = settings.BOSS_VERSION


class BossIngestViewTestMixin(object):
    """
    Class to test the manage-data service
    """
    def setUp(self):
        """
        Initialize the database
        :return:
        """
        self.client.force_login(self.user)

    def test_post_new_ingest_job(self):
        """ Test view to create a new ingest job """

        config_data = self.setup_helper.get_ingest_config_data_dict()
        config_data = json.loads(json.dumps(config_data))

        # # Post the data
        url = '/' + version + '/ingest/'
        response = self.client.post(url, data=config_data, format='json')
        print(response.content)
        assert (response.status_code == 201)

        # Check if the queue's exist
        ingest_job = response.json()
        proj_class = BossIngestProj.load()
        nd_proj = proj_class(ingest_job['collection'], ingest_job['experiment'], ingest_job['channel'],
                             0, ingest_job['id'])
        self.nd_proj = nd_proj
        upload_queue = UploadQueue(nd_proj, endpoint_url=None)
        assert (upload_queue is not None)
        ingest_queue = IngestQueue(nd_proj, endpoint_url=None)
        assert (ingest_queue is not None)

        # Test joining the job
        url = '/' + version + '/ingest/{}/'.format(ingest_job['id'])
        response = self.client.get(url)
        assert (response.json()['ingest_job']['id'] == ingest_job['id'])
        assert("credentials" in response.json())

        # # Delete the job
        url = '/' + version + '/ingest/{}/'.format(ingest_job['id'])
        response = self.client.delete(url)
        assert (response.status_code == 204)
        
# TODO: Add test back after fixing ndingest
#class TestIntegrationBossIngestView(BossIngestViewTestMixin, APITestCase):
#
#    @classmethod
#    def setUpTestData(cls):
#        # Set the environment variable for the tests
#        dbsetup = SetupTestDB()
#        cls.user = dbsetup.create_user('testuser')
#        dbsetup.set_user(cls.user)
#        dbsetup.insert_ingest_test_data()
#
#        cls.setup_helper = SetupTests()


