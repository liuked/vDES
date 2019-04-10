from datetime import datetime
import time
import logging, coloredlogs

coloredlogs.install(level='DEBUG')
logger = logging.getLogger(__file__.split('/')[-1])
logger.level = logging.DEBUG


class Feature:

    def __init__(self, _name, _value, _units, _last_updated, _max_time_gap):
        self.name = _name
        self.value = _value
        self.units = _units
        self.last_updated = _last_updated
        self.max_time_gap = _max_time_gap

    def __add__(self, other):
        try:
            last_datetime = None
            assert (isinstance(other, Feature))
            last_datetime = max(self.__timestamp_from_date(), other.__timestamp_from_date())
            assert(self.__is_summable(other))
            return Feature(self.name, self.value+other.value, self.units, datetime.fromtimestamp(last_datetime).strftime("%y-%m-%dT%H:%M:%S"), self.max_time_gap)

        except AssertionError:
            logger.error("{} and {} are not summable".format(self.to_json(), other.to_json()))
            # return the most recent feature
            if last_datetime is not None and last_datetime == self.__timestamp_from_date():
                return self
            else:
                return other


    def __timestamp_from_date(self):
        return time.mktime(datetime.strptime(self.last_updated, "%y-%m-%dT%H:%M:%S").timetuple())

    def __is_summable(self, other):
        last_timestamp = self.__timestamp_from_date()
        other_last_timestamp = other.__timestamp_from_date()
        logging.debug("self {} {}, other {} {}".format(self.last_updated, last_timestamp, other.last_updated, other_last_timestamp))
        samename = (self.name == other.name)
        sameunit = (self.units == other.units)
        timegap = abs(last_timestamp - other_last_timestamp)
        sametime = (timegap < self.max_time_gap)
        logger.debug("[{}] samename? {}; sameunit? {}; sametime? {}(gap{})".format(self.name, samename, sameunit,sametime,timegap))
        return (samename and sameunit and sametime)

    def to_json(self):
        return {
            "name": self.name,
            "value": self.value,
            "units": self.units,
            "last_updated": self.last_updated
        }