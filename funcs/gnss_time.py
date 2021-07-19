import math
import time
from datetime import datetime

monthdays = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def leapyear(year):
    """ Determine if a year is a leap year """
    if year % 4 == 0 and year % 100 != 0:
        return 1
    if year % 400 == 0:
        return 1
    return 0


def norm_doy(year, doy):
    while True:
        if doy <= 0:
            year -= 1
            doy += (365 + leapyear(year))
        elif doy > 365 + leapyear(year):
            doy -= (365 - leapyear(year))
            year += 1
        else:
            break
    return year, doy


def doy2ymd(year, doy):
    """ Change year,day of year to year,month,day """
    day = doy
    mon = 0
    for i in range(13):
        monthday = monthdays[i]
        if i == 2 and leapyear(year) == 1:
            monthday += 1
        if day > monthday:
            day -= monthday
        else:
            mon = i
            break
    return mon, day


def ymd2doy(year, mon, day):
    """ Change year,month,day to year,day of year """
    doy = day
    for i in range(1, mon):
        doy += monthdays[i]
    if mon > 2:
        doy += leapyear(year)
    return doy


def ymd2mjd(year, mon, day):
    """ Change year,month,day to Modified Julian Day """
    if mon <= 2:
        mon += 12
        year -= 1
    mjd = 365.25 * year - 365.25 * year % 1.0 - 679006.0
    mjd += math.floor(30.6001 * (mon + 1)) + 2.0 - math.floor(
        year / 100.0) + math.floor(year / 400) + day
    return mjd


def doy2mjd(year, doy):
    """ Change year, day of year to Modified Julian Day """
    year, doy = norm_doy(year, doy)
    mon, day = doy2ymd(year, doy)
    return ymd2mjd(year, mon, day)


def ymd2gpsweek(year, mon, day):
    """ Change year,month,day to GPS weeks """
    mjd = ymd2mjd(year, mon, day)
    week = int((mjd - 44244.0) / 7.0)
    day = math.floor(mjd - 44244.0 - week * 7.0)
    return week, day


def mjd2ydoy(mjd):
    """ Change Modified Julian Day to year, day of year """
    """ The input date must after 1952.0 """
    year = 1952
    dd = mjd + 1 - 34012
    yday = 366
    while dd > yday:
        dd -= yday
        year += 1
        yday = 365 + leapyear(year)
    return int(dd), int(year)


def sod2hms(sod):
    """ Change seconds of day to hours, minutes and seconds """
    sod = float(sod)
    hh = math.floor(sod / 3600)
    mm = math.floor((sod - hh * 3600) / 60.0)
    ss = int(sod - hh * 3600 - mm * 60)
    return hh, mm, ss


def hms2sod(hh, mm=0, ss=0.0):
    """ Change hours:minutes:seconds to seconds of day """
    return int(hh)*3600 + int(mm)*60 + float(ss)


_formats = {
    'ymd': '{d.year:0>4d}-{d.month:0>2d}-{d.day:0>2d}',
    'mdy': '{d.month:0>2d}/{d.day:0>2d}/{d.year:0>4d}',
    'dmy': '{d.day:0>2d}/{d.month:0>2d}/{d.year:0>4d}',
    'ydoy': '{d.year:0>4d}{d.doy:0>3d}',
    'gwkd': '{d.gwk:0>4d}{d.gwkd:1d}'
    }


class GnssTime:
    __slots__ = ['_mjd', '_sod', '_year', '_month', '_day', '_doy', '_gwk', '_gwkd']

    def __init__(self, mjd, sod=0.0):
        self._mjd = mjd
        self._sod = sod
        self.__set_time()

    def __norm_sod(self):
        while True:
            if self._sod >= 86400.0:
                self._sod -= 86400.0
                self._mjd += 1
            elif self._sod < 0:
                self._sod += 86400.0
                self._mjd -= 1
            else:
                break

    def __set_time(self):
        """ set all time according to mjd and seconds of day """
        self.__norm_sod()
        self._doy, self._year = mjd2ydoy(self._mjd)
        self._month, self._day = doy2ymd(self._year, self._doy)
        self._gwk, self._gwkd = ymd2gpsweek(self._year, self._month, self._day)

    # only readable as no @XXX.setter
    @property
    def mjd(self):
        return self._mjd

    @property
    def sod(self):
        return self._sod

    @property
    def year(self):
        return self._year

    @property
    def doy(self):
        return self._doy

    @property
    def month(self):
        return self._month

    @property
    def day(self):
        return self._day

    @property
    def gwk(self):
        return self._gwk

    @property
    def gwkd(self):
        return self._gwkd

    @property
    def yr(self):
        return int(str(self.year)[2:])

    @property
    def fmjd(self):
        return self.mjd + self.sod / 86400.0

    @classmethod
    def from_ydoy(cls, year, doy, sod=0.0):
        """ set GNSSTime from year, day of year and seconds of day """
        year, doy = norm_doy(int(year), int(doy))
        mjd = doy2mjd(year, doy)
        return cls(mjd, float(sod))

    @classmethod
    def from_ymd(cls, year, mon, day, sod=0.0):
        """ set GNSSTime by year, mon, day and seconds of day """
        mjd = ymd2mjd(int(year), int(mon), int(day))
        return cls(mjd, float(sod))

    @classmethod
    def from_datetime(cls, dt: datetime):
        """ set GNSSTime by datetime """
        return cls.from_str(dt.strftime('%Y-%m-%d %H:%M:%S'))

    @classmethod
    def now(cls):
        t_loc = time.localtime()
        mjd = ymd2mjd(t_loc.tm_year, t_loc.tm_mon, t_loc.tm_mday)
        sod = t_loc.tm_hour * 3600 + t_loc.tm_min * 60 + t_loc.tm_sec
        sod += time.timezone  # from local time to UTC
        return cls(mjd, sod)

    @classmethod
    def from_str(cls, str_time):
        """ set GNSSTime from YYYY-MM-DD HH:MM:SS """
        dd = str_time.strip().split()
        year, mon, day = dd[0].split('-')
        if len(dd) > 1:
            hh, mm, ss = dd[1].split(':')
            sod = int(hh) * 3600 + int(mm) * 60 + int(ss)
        else:
            sod = 0
        mjd = ymd2mjd(int(year), int(mon), int(day))
        return cls(mjd, float(sod))

    def __str__(self):
        """ format: 2019-07-19 00:00:00 """
        hh, mm, ss = sod2hms(self.sod)
        return f"{self.year:4d}-{self.month:0>2d}-{self.day:0>2d} {hh:0>2d}:{mm:0>2d}:{ss:0>2d}"

    def __repr__(self):
        hh, mm, ss = sod2hms(self.sod)
        return f"GnssTime({self.year:4d}-{self.month:0>2d}-{self.day:0>2d} {hh:0>2d}:{mm:0>2d}:{ss:0>2d})"

    def __format__(self, code):
        if code == '':
            code = 'ymd'
        fmt = _formats[code]
        return fmt.format(d=self)

    def __add__(self, other):
        """ return a new GNSSTime with time increasing by dsec seconds """
        try:
            dsec = float(other)
        except ValueError:
            return NotImplemented
        return GnssTime(self.mjd, self.sod + dsec)

    def __sub__(self, other):
        """ return a new GNSSTime with time decreasing by dsec seconds """
        try:
            dsec = float(other)
        except ValueError:
            return NotImplemented
        return GnssTime(self.mjd, self.sod - dsec)

    def __iadd__(self, other):
        try:
            dsec = float(other)
        except ValueError:
            return NotImplemented
        self._sod += dsec
        self.__set_time()
        return self

    def __isub__(self, other):
        try:
            dsec = float(other)
        except ValueError:
            return NotImplemented
        self._sod -= dsec
        self.__set_time()
        return self

    def __eq__(self, other):
        return (self.mjd == other.mjd) and (self.sod == other.sod)

    def __ne__(self, other):
        return (self.mjd != other.mjd) or (self.sod != other.sod)

    def __lt__(self, other):
        return (self.mjd < other.mjd) or (self.mjd == other.mjd and self.sod < other.sod)

    def __le__(self, other):
        return (self.mjd < other.mjd) or (self.mjd == other.mjd and self.sod <= other.sod)

    def __gt__(self, other):
        return (self.mjd > other.mjd) or (self.mjd == other.mjd and self.sod > other.sod)

    def __ge__(self, other):
        return (self.mjd > other.mjd) or (self.mjd == other.mjd and self.sod >= other.sod)

    def datetime(self) -> datetime:
        hh, mm, ss = sod2hms(int(self.sod))
        ms = 1000*(int(self.sod - int(self.sod)))
        return datetime(self.year, self.month, self.day, hh, mm, ss, ms)

    def diff(self, other):
        if not isinstance(other, GnssTime):
            raise TypeError("Expected a GnssTime()")
        return (self.mjd - other.mjd) * 86400.0 + self.sod - other.sod

    def config_timedic(self):
        """ return a dictionary of time information for config file """
        return {'yyyy': f"{self.year:4d}", 'ddd': f"{self.doy:0>3d}", 'yy': f"{self.yr:0>2d}",
                'mm': f"{self.month:0>2d}", 'hh': f'{math.floor(self.sod / 3600):0>2d}',
                'gwk': f"{self.gwk:0>4d}", 'gwkd': f"{self:gwkd}"}


__all__ = ['doy2mjd', 'doy2ymd', 'ymd2doy', 'ymd2mjd', 'ymd2gpsweek', 'mjd2ydoy', 'sod2hms', 'hms2sod', 'GnssTime']