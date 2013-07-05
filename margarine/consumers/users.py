# -*- coding: UTF-8 -*-
#
# Copyright (C) 2013 by Alex Brandt <alex.brandt@rackspace.com>
#
# margarine is freely distributable under the terms of an MIT-style license.
# See COPYING or http://www.opensource.org/licenses/mit-license.php.

import hashlib
import logging
import json
import uuid
import datetime
import pymongo

from margarine.api import information
from margarine.aggregates import get_collection
from margarine.keystores import get_keyspace
from margarine.communication import send_user_email

logger = logging.getLogger(__name__)

def create_user_consumer(channel, method, header, body):
    """Create a user—completing the bottom half of user creation.

    This takes the meta-information passed through the message queue and
    performs the following operations:

    * Add User to DataStore
    * Reset the user's password

    """
    
    user = json.loads(body)

    try:
        get_collection("users").insert(user) # TODO Fix race condition of multiple sign-ups.
    except (pymongo.errors.DuplicateKeyError) as e:
        logger.exception(e)
        logger.error("Duplicate user request ignored!")

    try:
        password_email_consumer(channel, method, header, body)
    except (RuntimeError) as e:
        logger.exception(e)
        get_collection("users").remove({ "username": user["username"] })

def password_email_consumer(channel, method, header, body):
    """Send a user the link to reset their password.

    This takes the information passed through the queue and creates a
    verification token to email to the user for resetting their password.

    * Record the Verification URL in the Token Store
    * Email the Verification URL to the User

    """

    user = json.loads(body)

    user = get_collection("users").find_one({ "username": user["username"] })

    verification = uuid.uuid4()

    get_keyspace("verifications").setex(verification, user["username"], datetime.timedelta(hours = 6))

    send_user_email(user, verification)

    channel.basic_ack(delivery_tag = method.delivery_tag)

def password_change_consumer(channel, method, header, body):
    """Change the password—completing the bottom half of verification.

    This takes the meta-information passed through a message queue and performs
    the following operations:

    * create password hash
    * store password hash
    * remove verification token
   
    """

    user = json.loads(body)

    h = hashlib.md5("{0}:{1}:{2}".format(user["username"], information.AUTHENTICATION_REALM, user["password"])).hexdigest()

    get_collection("users").update({ "username": user["username"] }, { "$set": { "hash": h } }, upsert = True)

    get_keyspace("verifications").delete(verification) # TODO Move to successful password reset request.

    channel.basic_ack(delivery_tag = method.delivery_tag)

def register(channel):
    """Register the user worker functions on the passed channel.

    Declare exchange, queue, and consumption for the user backend processes.

    Parameters
    ----------

    :channel: The channel to setup the queue over.
    
    """

    channel.exchange_declare(exchange = "margarine.users.topic", type = "topic", auto_delete = False)

    channel.queue_declare(queue = "margarine.users.create", auto_delete = False)
    channel.queue_bind(queue = "margarine.users.create", exchange = "margarine.users.topic", routing_key = "users.create")

    channel.basic_consume(create_user_consumer, queue = "margarine.users.create", no_ack = False, consumer_tag = "create")

    channel.queue_declare(queue = "margarine.users.email", auto_delete = False)
    channel.queue_bind(queue = "margarine.users.email", exchange = "margarine.users.topic", routing_key = "users.email")

    channel.basic_consume(password_email_consumer, queue = "margarine.users.email", no_ack = False, consumer_tag = "email")

    channel.queue_declare(queue = "margarine.users.password", auto_delete = False)
    channel.queue_bind(queue = "margarine.users.password", exchange = "margarine.users.topic", routing_key = "users.password")

    channel.basic_consume(password_change_consumer, queue = "margarine.users.password", no_ack = False, consumer_tag = "password")

