#!/usr/bin/env python3

# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.


import time

from ha.monitor.k8s.error import NotSupportedObjectError
from ha.monitor.k8s.const import K8SEventsConst
from ha.monitor.k8s.const import AlertStates
from ha.monitor.k8s.const import EventStates
from ha.monitor.k8s.alert import K8sAlert

from cortx.utils.log import Log

class ObjectParser:
    def __init__(self):
        pass

    def parse(self, an_event, cached_state):
        pass


class NodeEventParser(ObjectParser):
    def __init__(self):
        super().__init__()
        self._type = 'host'

    def parse(self, an_event, cached_state):
        alert = K8sAlert()
        alert.resource_type = self._type
        alert.timestamp = str(int(time.time()))
        raw_object = an_event[K8SEventsConst.RAW_OBJECT]

        if K8SEventsConst.TYPE in an_event:
            alert.event_type = an_event[K8SEventsConst.TYPE]
        if K8SEventsConst.NAME in raw_object[K8SEventsConst.METADATA]:
            alert.resource_name = raw_object[K8SEventsConst.METADATA][K8SEventsConst.NAME]

        ready_status = None
        try:
            for a_condition in raw_object[K8SEventsConst.STATUS][K8SEventsConst.CONDITIONS]:
                if a_condition[K8SEventsConst.TYPE] == K8SEventsConst.READY:
                    ready_status = a_condition[K8SEventsConst.STATUS]
        except Exception as e:
            Log.debug(f"Exception received during parsing {e}")

        if ready_status is None:
            Log.debug(f"ready_status is None for node resource {alert.resource_name}")
            cached_state[alert.resource_name] = ready_status
            return None

        if alert.event_type == EventStates.ADDED:
            cached_state[alert.resource_name] = ready_status.lower()
            if ready_status.lower() == K8SEventsConst.true:
                alert.event_type = AlertStates.ONLINE
                return alert
            else:
                Log.debug(f"[EventStates ADDED] No change detected for node resource {alert.resource_name}")
                return None

        if alert.event_type == EventStates.MODIFIED:
            if alert.resource_name in cached_state:
                if cached_state[alert.resource_name] != K8SEventsConst.true and ready_status.lower() == K8SEventsConst.true:
                    cached_state[alert.resource_name] = ready_status.lower()
                    alert.event_type = AlertStates.ONLINE
                    return alert
                elif cached_state[alert.resource_name] == K8SEventsConst.true and ready_status.lower() != K8SEventsConst.true:
                    cached_state[alert.resource_name] = ready_status.lower()
                    alert.event_type = AlertStates.FAILED
                    return alert
                else:
                    Log.debug(f"[EventStates MODIFIED] No change detected for node resource {alert.resource_name}")
                    return None
            else:
                Log.debug(f"[EventStates MODIFIED] No cached state detected for node resource {alert.resource_name}")
                return None

        # Handle DELETED event - Not required for Cortx

        return None


class PodEventParser(ObjectParser):
    def __init__(self):
        super().__init__()

        # Note: The below type is not a Kubernetes 'node'.
        #       in cortx cluster the pod is called or considered as a node.
        #       hence while sending alert to cortx, below type is set to 'node'.
        self._type = 'node'

    def parse(self, an_event, cached_state):
        alert = K8sAlert()
        alert.resource_type = self._type
        alert.timestamp = str(int(time.time()))
        raw_object = an_event[K8SEventsConst.RAW_OBJECT]

        labels = raw_object[K8SEventsConst.METADATA][K8SEventsConst.LABELS]
        if K8SEventsConst.MACHINEID in labels:
            alert.resource_name = labels[K8SEventsConst.MACHINEID]
        if K8SEventsConst.TYPE in an_event:
            alert.event_type = an_event[K8SEventsConst.TYPE]
        if K8SEventsConst.NODE_NAME in raw_object[K8SEventsConst.SPEC]:
            alert.node = raw_object[K8SEventsConst.SPEC][K8SEventsConst.NODE_NAME]
        if K8SEventsConst.NAME in raw_object[K8SEventsConst.METADATA]:
            alert.generation_id = raw_object[K8SEventsConst.METADATA][K8SEventsConst.NAME]

        ready_status = None
        try:
            for a_condition in raw_object[K8SEventsConst.STATUS][K8SEventsConst.CONDITIONS]:
                if a_condition[K8SEventsConst.TYPE] == K8SEventsConst.READY:
                    ready_status = a_condition[K8SEventsConst.STATUS]
        except Exception as e:
            Log.debug(f"Exception received during parsing {e}")

        if ready_status is None:
            Log.debug(f"ready_status is None for pod resource {alert.resource_name}")
            cached_state[alert.resource_name] = ready_status
            return None

        if an_event[K8SEventsConst.TYPE] == EventStates.ADDED:
            cached_state[alert.resource_name] = ready_status.lower()
            if ready_status.lower() != K8SEventsConst.true:
                Log.debug(f"[EventStates ADDED] No change detected for pod resource {alert.resource_name}")
                return None
            else:
                alert.event_type = AlertStates.ONLINE
                return alert

        if alert.event_type == EventStates.MODIFIED:
            if alert.resource_name in cached_state:
                if cached_state[alert.resource_name] != K8SEventsConst.true and ready_status.lower() == K8SEventsConst.true:
                    cached_state[alert.resource_name] = ready_status.lower()
                    alert.event_type = AlertStates.ONLINE
                    return alert
                elif cached_state[alert.resource_name] == K8SEventsConst.true and ready_status.lower() != K8SEventsConst.true:
                    cached_state[alert.resource_name] = ready_status.lower()
                    alert.event_type = AlertStates.FAILED
                    return alert
                else:
                    Log.debug(f"[EventStates MODIFIED] No change detected for pod resource {alert.resource_name}")
                    return None
            else:
                Log.debug(f"[EventStates MODIFIED] No cached state detected for pod resource {alert.resource_name}")
                return None

        # Handle DELETED event - Not required for Cortx

        return None


class EventParser:
    parser_map = {
        'node': NodeEventParser(),
        'pod': PodEventParser()
    }

    @staticmethod
    def parse(k_object, an_event, cached_state):
        if k_object in EventParser.parser_map:
            object_event_parser = EventParser.parser_map[k_object]
            return object_event_parser.parse(an_event, cached_state)

        raise NotSupportedObjectError(f"object = {k_object}")

