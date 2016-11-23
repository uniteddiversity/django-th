# coding: utf-8
import requests

# django classes
from django.utils.log import getLogger
from django.core.cache import caches

# django_th classes
from django_th.services.services import ServicesMgr
from django_th.models import TriggerService
from th_slack.models import Slack

logger = getLogger('django_th.trigger_happy')

cache = caches['th_slack']


class ServiceSlack(ServicesMgr):
    """
        Service Slack
    """
    def __init__(self, token=None, **kwargs):
        super(ServiceSlack, self).__init__(token, **kwargs)

    def read_data(self, **kwargs):
        """
            get the data from the service

            :param kwargs: contain keyword args : trigger_id and model name
            :type kwargs: dict
            :rtype: dict
        """
        trigger_id = kwargs.get('trigger_id')
        kwargs['model_name'] = 'Slack'

        # get the URL from the trigger id
        data = super(ServiceSlack, self).read_data(**kwargs)
        cache.set('th_slack_' + str(trigger_id), data)
        # return the data
        return data

    def save_data(self, trigger_id, **data):
        """
            get the data from the service

            :param trigger_id: id of the trigger
            :params data, dict
            :rtype: dict
        """
        status = False
        slack = Slack.objects.get(trigger_id=trigger_id)
        title = self.set_title(data)
        service = TriggerService.objects.get(id=trigger_id)
        # set the bot username of Slack to the name of the
        # provider service
        username = service.provider.name.name.split('Service')[1]
        # 'build' a link
        title_link = '<' + data.get('link') + '|' + title + '>'
        data = service.description + ': ' + title_link

        payload = {'username': username,
                   'text': data}

        r = requests.post(slack.webhook_url, json=payload)

        if r.status_code == requests.codes.ok:
            status = True
        # return the data
        return status
