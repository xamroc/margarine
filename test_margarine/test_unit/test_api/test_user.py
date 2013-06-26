# Copyright (C) 2013 by Alex Brandt <alex.brandt@rackspace.com>
#
# margarine is freely distributable under the terms of an MIT-style license.
# See COPYING or http://www.opensource.org/licenses/mit-license.php.

import unittest2
import logging
import mock

from margarine.api import information
from margarine.api import MARGARINE_API

logger = logging.getLogger(__name__)

class BaseUserTest(unittest2.TestCase):
    def setUp(self):
        MARGARINE_API.config["TESTING"] = True
        self.application = MARGARINE_API.test_client()

        self.account_name = "test_user"

        self.url = "/{i.API_VERSION}/users/{username}"
        self.url = self.url.format(username = self.account_name, i = information)

class UserCreationTest(BaseUserTest):
    def setUp(self):
        super().setUp()

        patcher = mock.patch("margarine.api.user.get_channel")
        mock_get_channel = patcher.start()

        self.addCleanup(patcher.stop)

        mock_get_channel.return_value = mock.MagicMock()

    def test_nonexsitent_user_creation_request(self):
        """Create a new (non-existent) user."""

        # TODO Mock user retrieval (non-existent user).

        response = self.application.put(self.url, data = {
            "email": "test@example.com",
            })

        self.assertIn("202", response.status)

        # Ensure publish has a routing_key parameter of users.create.

    def test_existing_user_creation_request(self):
        """Create an existing user."""

        # TODO Mock user retrieval (existing user).

        response = self.application.put(self.url, data = {
            "email": "test@example.com",
            })

        self.assertIn("401", response.status)

class UserReadTest(BaseUserTest):
    def setUp(self):
        super().setUp()

        patcher = mock.patch("margarine.api.user.get_collection")
        mock_get_collection = patcher.start()

        self.addCleanup(patcher.stop)

        mock_get_collection.return_value = mock.MagickMock()

    def test_existing_user_read_request(self):
        """Read an existing user."""

        # TODO Mock user retrieval (existing user).

        response = self.application.get(self.url)

        self.assertIn("200", response.status)

    def test_nonexistent_user_read_request(self):
        """Read a non-existent user."""

        # TODO Mock user retrieval (non-existent user).

        resposne = self.application.get(self.url)

        self.assertIn("404", response.status)

class UserUpdateTest(BaseUserTest):
    def setUp(self):
        super(UserUpdateTest, self).setUp()

        patcher = mock.patch("margarine.api.user.get_collection")
        mock_get_collection = patcher.start()

        self.addCleanup(patcher.stop)

        mock_get_collection.return_value = mock.MagicMock()

        self.token = "c2d52150-08d1-4ae3-b19c-323c9e37813d"

        patcher = mock.patch("margarine.api.user.get_keyspace")
        mock_get_keyspace = patcher.start()

        self.addCleanup(patcher.stop)

        self.mock_keyspace = mock.MagicMock()
        mock_get_keyspace.return_value = self.mock_keyspace
        self.mock_keyspace.get.return_value = self.account_name

        patcher = mock.patch("margarine.api.user.get_channel")
        mock_get_channel = patcher.start()

        self.addCleanup(patcher.stop)

        self.mock_channel = mock.MagicMock()
        mock_get_channel.return_value = self.mock_channel

    def test_user_update_request(self):
        """Update an existing user."""

        response = self.application.put(self.url,
                headers = {
                    "X-Auth-Token": self.token,
                    },
                data = {
                    "email": "test@example.com",
                    "name": "Test User",
                    })

        self.mock_keyspace.get.assert_called_with(self.token)

        self.mock_channel.basic_publish.assert_called_once_with(
                body = '{"username": "test_user", "password": null, "email": "test@example.com", "name": "Test User"}',
                exchange = 'margarine.users.topic',
                properties = mock.ANY,
                routing_key = 'users.update'
                )

        self.assertIn("202", response.status)

class UserDeleteTest(BaseUserTest):
    def setUp(self):
        super().setUp()

    def test_user_delete_request(self):
        """Delete an existing user."""

        # TODO Mock user retrieval.

        response = self.application.delete(self.url)

        self.assertIn("200", response.status)

        # And again to prove idempotency:

        response = self.application.delete(self.url)

        self.assertIn("200", response.status)
