import math
import time

monthdays = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def leapyear(year):
    """ Determine if a year is a leap year """
    if year % 4 == 0 and year % 100 != 0:
        return 1
    if year % 400 == 0:
        return 1
    return 0


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
    mjd = 0.0
    if mon <= 2:
        mon += 12
        year -= 1
    mjd = 365.25 * year - 365.25 * year % 1.0 - 679006.0
    mjd += math.floor(30.6001 * (mon + 1)) + 2.0 - math.floor(
        year / 100.0) + math.floor(year / 400) + day
    return mjd


def doy2mjd(year, doy):
    """ Change year, day of year to Modified Julian Day """
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
        if leapyear(year) == 0:
            yday = 365
        else:
            yday = 366
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


class GnssTime:

    def __init__(self):
        self.year = 2019
        self.doy = 100
        self.month = 4
        self.day = 1
        self.mjd = 0
        self.sod = 0.0

    def __add__(self, other):
        """ return a new GNSSTime with time increasing by dsec seconds """
        try:
            time_new = GnssTime()
            time_new.from_mjd(self.mjd, self.sod + float(other))
            return time_new
        except TypeError:
            return NotImplemented

    def __sub__(self, other):
        """ return a new GNSSTime with time decreasing by dsec seconds """
        try:
            time_new = GnssTime()
            time_new.from_mjd(self.mjd, self.sod - float(other))
            return time_new
        except TypeError:
            return NotImplemented

    def __iadd__(self, other):
        self.sod += float(other)
        self.from_mjd(self.mjd, self.sod)
        return self

    def __isub__(self, other):
        self.sod -= float(other)
        self.from_mjd(self.mjd, self.sod)
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

    def __norm_sod(self):
        while True:
            if self.sod >= 86400.0:
                self.sod -= 86400.0
                self.mjd += 1
            elif self.sod < 0:
                self.sod += 86400.0
                self.mjd -= 1
            else:
                break

    def __set_time(self):
        """ set all time according to mjd and seconds of day """
        self.doy, self.year = mjd2ydoy(self.mjd)
        self.month, self.day = doy2ymd(self.year, self.doy)

    def from_ymd(self, year, mon, day, sod=0.0):
        """ set GNSSTime by year, mon, day and seconds of day """
        self.mjd = ymd2mjd(year, mon, day)
        self.sod = float(sod)
        self.__norm_sod()
        self.__set_time()

    def from_ydoy(self, year, doy, sod=0.0):
        """ set GNSSTime from year, day of year and seconds of day """
        year = int(year)
        doy = int(doy)
        if doy <= 0:
            year = year - 1
            if leapyear(year) == 1:
                doy = 366 + doy
            else:
                doy = 365 + doy
        if doy > 365 and leapyear(year) == 0:
            year = year - 1
            doy = doy - 365
        if doy > 366 and leapyear(year) == 1:
            year = year - 1
            doy = doy - 366
        self.mjd = doy2mjd(year, doy)
        self.sod = float(sod)
        self.__norm_sod()
        self.__set_time()

    def from_mjd(self, mjd, sod=0.0):
        """ set GNSSTime from Modified Julian Day and seconds of day """
        self.mjd = int(mjd)
        self.sod = float(sod)
        self.__norm_sod()
        self.__set_time()

    def from_datetime(self, str_date):
        """ set GNSSTime from YYYY-MM-DD HH:MM:SS """
        str_date = str_date.strip()
        year = int(str_date.split()[0].split('-')[0])
        month = int(str_date.split()[0].split('-')[1])
        day = int(str_date.split()[0].split('-')[2])
        hh = int(str_date.split()[1].split(':')[0])
        mm = int(str_date.split()[1].split(':')[1])
        ss = int(str_date.split()[1].split(':')[2])
        sod = hh * 3600 + mm * 60 + ss
        self.from_ymd(year, month, day, sod)
    
    @classmethod
    def today(cls):
        t = time.localtime()
        sod = t.tm_hour*3600 + t.tm_min*60 + t.tm_sec
        gt = cls()
        gt.from_ydoy(t.tm_year, t.tm_yday, sod)
        return gt

    def fmjd(self):
        return self.mjd + self.sod / 86400.0

    def gwkd(self):
        doy, year = mjd2ydoy(self.mjd)
        month, day = doy2ymd(year, doy)
        _, gwkd = ymd2gpsweek(year, month, day)
        return gwkd

    def gwk(self):
        doy, year = mjd2ydoy(self.mjd)
        month, day = doy2ymd(year, doy)
        gwk, _ = ymd2gpsweek(year, month, day)
        return gwk

    def yr(self):
        return int(str(self.year)[2:])

    def datetime(self):
        """ format: 2019-07-19 00:00:00 """
        hh, mm, ss = sod2hms(self.sod)
        msg = f"{self.year:4d}-{self.month:0>2d}-{self.day:0>2d} {hh:0>2d}:{mm:0>2d}:{ss:0>2d}"
        return msg

    def diff(self, other):
        return (self.mjd - other.mjd) * 86400.0 + self.sod - other.sod

    def config_timedic(self):
        """ return a dictionary of time information for config file """
        return {'yyyy': f"{self.year:4d}", 'ddd': f"{self.doy:0>3d}", 'yy': f"{self.yr():0>2d}",
                'mm': f"{self.month:0>2d}", 'gwk': f"{self.gwk():0>4d}", 'gwkd': f"{self.gwk():0>4d}{self.gwkd():1d}"}
