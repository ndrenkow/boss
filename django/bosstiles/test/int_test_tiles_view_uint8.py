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

from django.conf import settings
from django.test.utils import override_settings
import time
import redis
import random

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework.test import force_authenticate

from bosstiles.test.tiles_view_uint8 import ImageInterfaceViewTestMixin, TileInterfaceViewTestMixin

from bosscore.test.setup_db import SetupTestDB
from bossspatialdb.views import Cutout

import bossutils
from spdb.spatialdb.test.setup import SetupTests
from botocore.exceptions import ClientError

import numpy as np
from PIL import Image
import blosc

version = settings.BOSS_VERSION

config = bossutils.configuration.BossConfig()
KVIO_SETTINGS = {"cache_host": config['aws']['cache'],
                 "cache_db": 1,
                 "read_timeout": 86400}

# state settings
STATEIO_CONFIG = {"cache_state_host": config['aws']['cache-state'],
                  "cache_state_db": 1}

# object store settings
OBJECTIO_CONFIG = {"s3_flush_queue": None,
                   "cuboid_bucket": "intTest{}.{}".format(random.randint(0, 9999), config['aws']['cuboid_bucket']),
                   "page_in_lambda_function": config['lambda']['page_in_function'],
                   "page_out_lambda_function": config['lambda']['flush_function'],
                   "s3_index_table": "intTest.{}".format(config['aws']['s3-index-table']),
                   "id_index_table": config['aws']['id-index-table'],
                   "id_count_table": config['aws']['id-count-table']
                   }

config = bossutils.configuration.BossConfig()
_, domain = config['aws']['cuboid_bucket'].split('.', 1)

FLUSH_QUEUE_NAME = "intTest.S3FlushQueue.{}".format(domain).replace('.', '-')


@override_settings(KVIO_SETTINGS=KVIO_SETTINGS)
@override_settings(STATEIO_CONFIG=STATEIO_CONFIG)
@override_settings(OBJECTIO_CONFIG=OBJECTIO_CONFIG)
class ImageViewIntegrationTests(ImageInterfaceViewTestMixin, APITestCase):
    def setUp(self):
        """Setup to run before every test"""
        self.client.force_login(self.user)

    def tearDown(self):
        """Clean kv store in between tests"""
        client = redis.StrictRedis(host=settings.KVIO_SETTINGS["cache_host"],
                                   port=6379, db=1, decode_responses=False)
        client.flushdb()
        client = redis.StrictRedis(host=settings.STATEIO_CONFIG["cache_state_host"],
                                   port=6379, db=1, decode_responses=False)
        client.flushdb()

    @classmethod
    def setUpTestData(cls):
        """ get_some_resource() is slow, to avoid calling it for each test use setUpClass()
            and store the result as class variable
        """
        # Setup the helper to create temporary AWS resources
        cls.setup_helper = SetupTests()
        cls.setup_helper.mock = False

        # Create a user in django
        dbsetup = SetupTestDB()
        cls.user = dbsetup.create_user('testuser')
        dbsetup.add_role('resource-manager')
        dbsetup.set_user(cls.user)

        # Populate django models DB
        dbsetup.insert_spatialdb_test_data()

        try:
            cls.setup_helper.create_index_table(OBJECTIO_CONFIG["s3_index_table"], cls.setup_helper.DYNAMODB_SCHEMA)
        except ClientError:
            cls.setup_helper.delete_index_table(OBJECTIO_CONFIG["s3_index_table"])
            cls.setup_helper.create_index_table(OBJECTIO_CONFIG["s3_index_table"], cls.setup_helper.DYNAMODB_SCHEMA)

        try:
            cls.setup_helper.create_cuboid_bucket(OBJECTIO_CONFIG["cuboid_bucket"])
        except ClientError:
            cls.setup_helper.delete_cuboid_bucket(OBJECTIO_CONFIG["cuboid_bucket"])
            cls.setup_helper.create_cuboid_bucket(OBJECTIO_CONFIG["cuboid_bucket"])

        try:

            OBJECTIO_CONFIG["s3_flush_queue"] = cls.setup_helper.create_flush_queue(FLUSH_QUEUE_NAME)
        except ClientError:
            try:
                cls.setup_helper.delete_flush_queue(OBJECTIO_CONFIG["s3_flush_queue"])
            except:
                pass
            time.sleep(61)
            OBJECTIO_CONFIG["s3_flush_queue"] = cls.setup_helper.create_flush_queue(FLUSH_QUEUE_NAME)

        # load some data for reading
        cls.test_data_8 = np.random.randint(1, 254, (16, 1024, 1024), dtype=np.uint8)
        bb = blosc.compress(cls.test_data_8, typesize=8)

        # Post data to the database
        factory = APIRequestFactory()
        request = factory.post('/' + version + '/cutout/col1/exp1/channel1/0/0:1024/0:1024/0:16/', bb,
                               content_type='application/blosc')
        force_authenticate(request, user=cls.user)
        _ = Cutout.as_view()(request, collection='col1', experiment='exp1', channel='channel1',
                             resolution='0', x_range='0:1024', y_range='0:1024', z_range='0:16', t_range=None)

    @classmethod
    def tearDownClass(cls):
        super(ImageViewIntegrationTests, cls).tearDownClass()
        try:
            cls.setup_helper.delete_index_table(OBJECTIO_CONFIG["s3_index_table"])
        except Exception as e:
            print("Failed to cleanup S3 Index Table: {}".format(e))
            pass

        try:
            cls.setup_helper.delete_cuboid_bucket(OBJECTIO_CONFIG["cuboid_bucket"])
        except Exception as e:
            print("Failed to cleanup S3 bucket: {}".format(e))
            pass

        try:
            cls.setup_helper.delete_flush_queue(OBJECTIO_CONFIG["s3_flush_queue"])
        except Exception as e:
            print("Failed to cleanup S3 flush queue: {}".format(e))
            pass


@override_settings(KVIO_SETTINGS=KVIO_SETTINGS)
@override_settings(STATEIO_CONFIG=STATEIO_CONFIG)
@override_settings(OBJECTIO_CONFIG=OBJECTIO_CONFIG)
class TileViewIntegrationTests(TileInterfaceViewTestMixin, APITestCase):
    def setUp(self):
        """Setup to run before every test"""
        self.client.force_login(self.user)

    def tearDown(self):
        """Clean kv store in between tests"""
        client = redis.StrictRedis(host=settings.KVIO_SETTINGS["cache_host"],
                                   port=6379, db=1, decode_responses=False)
        client.flushdb()
        client = redis.StrictRedis(host=settings.STATEIO_CONFIG["cache_state_host"],
                                   port=6379, db=1, decode_responses=False)
        client.flushdb()

    @classmethod
    def setUpTestData(cls):
        """ get_some_resource() is slow, to avoid calling it for each test use setUpClass()
            and store the result as class variable
        """
        # Setup the helper to create temporary AWS resources
        cls.setup_helper = SetupTests()
        cls.setup_helper.mock = False

        # Create a user in django
        dbsetup = SetupTestDB()
        cls.user = dbsetup.create_user('testuser')
        dbsetup.add_role('resource-manager')
        dbsetup.set_user(cls.user)

        # Populate django models DB
        dbsetup.insert_spatialdb_test_data()

        try:
            cls.setup_helper.create_index_table(OBJECTIO_CONFIG["s3_index_table"], cls.setup_helper.DYNAMODB_SCHEMA)
        except ClientError:
            cls.setup_helper.delete_index_table(OBJECTIO_CONFIG["s3_index_table"])
            cls.setup_helper.create_index_table(OBJECTIO_CONFIG["s3_index_table"], cls.setup_helper.DYNAMODB_SCHEMA)

        try:
            cls.setup_helper.create_cuboid_bucket(OBJECTIO_CONFIG["cuboid_bucket"])
        except ClientError:
            cls.setup_helper.delete_cuboid_bucket(OBJECTIO_CONFIG["cuboid_bucket"])
            cls.setup_helper.create_cuboid_bucket(OBJECTIO_CONFIG["cuboid_bucket"])

        try:

            OBJECTIO_CONFIG["s3_flush_queue"] = cls.setup_helper.create_flush_queue(FLUSH_QUEUE_NAME)
        except ClientError:
            try:
                cls.setup_helper.delete_flush_queue(OBJECTIO_CONFIG["s3_flush_queue"])
            except:
                pass
            time.sleep(61)
            OBJECTIO_CONFIG["s3_flush_queue"] = cls.setup_helper.create_flush_queue(FLUSH_QUEUE_NAME)

        # load some data for reading
        cls.test_data_8 = np.random.randint(1, 254, (16, 1024, 1024), dtype=np.uint8)
        bb = blosc.compress(cls.test_data_8, typesize=8)

        # Post data to the database
        factory = APIRequestFactory()
        request = factory.post('/' + version + '/cutout/col1/exp1/channel1/0/0:1024/0:1024/0:16/', bb,
                               content_type='application/blosc')
        force_authenticate(request, user=cls.user)
        _ = Cutout.as_view()(request, collection='col1', experiment='exp1', channel='channel1',
                             resolution='0', x_range='0:1024', y_range='0:1024', z_range='0:16', t_range=None)

    @classmethod
    def tearDownClass(cls):
        super(TileViewIntegrationTests, cls).tearDownClass()

        try:
            cls.setup_helper.delete_index_table(OBJECTIO_CONFIG["s3_index_table"])
        except Exception as e:
            print("Failed to cleanup S3 Index Table: {}".format(e))
            pass

        try:
            cls.setup_helper.delete_cuboid_bucket(OBJECTIO_CONFIG["cuboid_bucket"])
        except Exception as e:
            print("Failed to cleanup S3 bucket: {}".format(e))
            pass

        try:
            cls.setup_helper.delete_flush_queue(OBJECTIO_CONFIG["s3_flush_queue"])
        except Exception as e:
            print("Failed to cleanup S3 flush queue: {}".format(e))
            pass

