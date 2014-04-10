#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import datetime
import time
import arrow
import asyncio

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_th.settings")

from django.conf import settings
from django_th.services import default_provider
from django_th.models import TriggerService
from django.utils.log import getLogger

# create logger
logger = getLogger('django_th.trigger_happy')

q = asyncio.Queue(maxsize=0)
q2 = asyncio.Queue(maxsize=0)


def to_datetime(data):
    """
        convert Datetime 9-tuple to the date and time format
        feedparser provides this 9-tuple
    """
    my_date_time = None

    if 'published_parsed' in data:
        my_date_time = datetime.datetime.fromtimestamp(
            time.mktime(data.published_parsed))
    elif 'updated_parsed' in data:
        my_date_time = datetime.datetime.fromtimestamp(
            time.mktime(data.updated_parsed))

    return my_date_time


@asyncio.coroutine
def update_trigger(service):
    """
        update the date when occurs the trigger
    """
    my_count = yield from q2.get()
    if my_count > 0:

        logger.info("user: {} - provider: {} - consumer: {} - {} = {} new data".format(
            service.user, service.provider.name.name, service.consumer.name.name, service.description, my_count))

        trigger = TriggerService.objects.get(id=service.id)
        if trigger:
            # set the current datetime
            now = arrow.utcnow().to(
                settings.TIME_ZONE).format('YYYY-MM-DD HH:mm:ss')
            trigger.date_triggered = now
            trigger.save()
    else:
        logger.info("user: {} - provider: {} - consumer: {} - {} nothing new".format(
            service.user, service.provider.name.name, service.consumer.name.name, service.description))
    asyncio.get_event_loop().stop()


@asyncio.coroutine
def my_dummy_provider():
    yield from q.put(1)


@asyncio.coroutine
def my_provider(service_provider, token, service_id, date_triggered):
    """
        service_provider : the name of the class to trigger the service
        token : is the token of the service provider from the database
        service_id : is the service id from the database
        date_triggered : date_triggered is the data from the database
        :rtype provider class object
    """
    datas = getattr(service_provider, 'process_data')(
        token, service_id, date_triggered)

    for data in datas:
        yield from q.put(data)


@asyncio.coroutine
def my_consumer(service_consumer, token_consumer, service_id, date_triggered):
    """
        service_provider : the name of the class to trigger the service
        token : is the token of the service provider from the database
        service_id : is the service id from the database
        date_triggered : date_triggered is the data from the database
        service_consumer : the name of the class to trigger the target
        :rtype boolean
    """
    count_new_data = 0
    proceed = False
    while q.empty() is not True:
        data = yield from q.get()

        consumer = getattr(service_consumer, 'save_data')

        published = ''
        which_date = ''

        # flag to know if we can push data to the consumer

        # 2) for each one
        # if in a pool of data once of them does not have
        # a date, will take the previous date for this one
        # if it's the first one, set it to 00:00:00
        # let's try to determine the date contained in the data...
        published = to_datetime(data)
        if published is not None:
            # get the published date of the provider
            published = arrow.get(str(published), 'YYYY-MM-DD HH:mm:ss')
            # store the date for the next loop
            # if published became 'None'
            which_date = published
        #... otherwise set it to 00:00:00 of the current date
        if which_date == '':
            # current date
            which_date = arrow.utcnow().replace(
                hour=0, minute=0, second=0)
            published = which_date
        if published is None and which_date != '':
            published = which_date
        # 3) check if the previous trigger is older than the
        # date of the data we retreived
        # if yes , process the consumer

        # add the TIME_ZONE settings
        my_date_triggered = arrow.get(
            str(date_triggered), 'YYYY-MM-DD HH:mm:ss').to(settings.TIME_ZONE)

        # if the published date if greater or equal to the last
        # triggered event ... :
        if my_date_triggered is not None and published is not None and published.date() >= my_date_triggered.date():
            # if date are the same ...
            if published.date() == my_date_triggered.date():
                # ... compare time and proceed if needed
                if published.time() >= my_date_triggered.time():
                    proceed = True
            # not same date so proceed !
            else:
                proceed = True
            if proceed:
                if 'title' in data:
                    logger.info("date {} >= date triggered {} title {}".format(
                        published, date_triggered, data['title']))
                else:
                    logger.info(
                        "date {} >= date triggered {} ".format(published, my_date_triggered))

                consumer(token_consumer, service_id, **data)

                count_new_data += 1
        # otherwise do nothing
        else:
            if 'title' in data:
                logger.debug(
                    "data outdated skiped : [{}] {}".format(published, data['title']))
            else:
                logger.debug(
                    "data outdated skiped : [{}] ".format(published))

    else:
        yield from q2.put(count_new_data)


default_provider.load_services()
trigger = TriggerService.objects.filter(status=True)
if trigger:
    for service in trigger:

        # provider - the service that offer datas
        service_name = str(service.provider.name.name)
        service_provider = default_provider.get_service(service_name)

        # consumer - the service which uses the data
        service_name = str(service.consumer.name.name)
        service_consumer = default_provider.get_service(service_name)

        # First run
        if service.date_triggered is None:
            logger.debug("first run for %s => %s " % (str(
                service.provider.name), str(service.consumer.name.name)))

            asyncio.get_event_loop().run_until_complete(my_dummy_provider)

        # another run
        else:
            asyncio.get_event_loop().run_until_complete(
                my_provider(service_provider, service.provider.token, service.id, service.date_triggered))

        # process done in every case
        asyncio.get_event_loop().run_until_complete(
            my_consumer(service_consumer, service.consumer.token, service.id, service.date_triggered))
        asyncio.get_event_loop().run_until_complete(update_trigger(service))
        asyncio.get_event_loop().run_forever()

else:
    print("No trigger set by any user")
