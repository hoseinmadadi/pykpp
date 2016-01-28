__all__ = ['interp_updater', 'Update_RCONST', 'Update_SUN', 'Update_THETA', 'Update_M', 'add_time_interpolated', 'add_time_interpolated_from_csv', 'code_updater', 'add_code_updater', 'func_updater', 'solar_declination']
from numpy import *
from scipy.constants import *
from warnings import warn

class updater:
    def __init__(self, *args, **kwds):
        self.reset()
    
    def __call__(self, mech, world, force = False):
        return False

    def reset(self):
        self.last = -inf
    
    def updatenow(self, t, force = False):
        tsince = t - self.last
        if (not force) and tsince < self.incr:
            return False
        else:
            self.last = t
            return True
            
class interp_updater(updater):
    def __init__(self, time, incr, verbose = False, **props):
        self.last = -inf
        self.verbose = verbose
        self.time = time
        self.incr = incr
        self.props = props
    
    def __call__(self, mech, world, force = False):
        t = world['t']
        update = self.updatenow(t, force = force)
        if update:
            if self.verbose:
                print "Updating %s: %s" % (', '.join(self.props.keys()), self.last)
            for k, vs in self.props.iteritems():
                world[k] = interp(t, self.time, vs)
        
        return update

class func_updater(updater):
    def __init__(self, func, incr, verbose = False):
        self.last = -inf
        self.verbose = verbose
        self.incr = incr
        self.func = func
    
    def __call__(self, mech, world, force = False):
        t = world['t']
        update = self.updatenow(t, force = force)
        if update:
            if self.verbose:
                print "Updating %s: %s" % (str(self.func).split(' ')[1], self.last)
            self.func(mech, world)
        
        return update

class code_updater(updater):
    def __init__(self, code, incr, verbose = False, message = 'code'):
        self.verbose = verbose
        self.block = compile(code, '<user>', 'exec')
        self.incr = incr
        self.message = message
        self.reset()
    
    def __call__(self, mech, world, force = False):
        last = self.last
        t = world['t']
        update = self.updatenow(t, force = force)
        if update:
            if self.verbose:
                print "Updating %s: %s" % (self.message, self.last)
            
            exec self.block in globals(), world
        
        return update

def add_time_interpolated(time, incr = 0, verbose = False, **props):
    add_world_updater(interp_updater(time = time, incr = incr, verbose = verbose, **props))

def add_time_interpolated_from_csv(path, timekey, incr = 0):
    names = map(lambda x: x.strip(), file(path).read().split('\n')[0].split(','))
    
    data = csv2rec(path)
    datadict = dict([(newkey, data[k]) for k, newkey in zip(data.dtype.names, names)])
    time = datadict.pop(timekey)
    add_time_interpolated(time = time, incr = incr, **datadict)

def add_code_updater(code, incr = 0, verbose = False, message = 'code'):
    add_world_updater(code_updater(code = code, incr = incr, verbose = verbose, message = message))


#def add_world_updater(func, incr = 0, verbose = False):
#    """
#    Add func to be called with mech and world
#    to update the world environment
#    """
#    Update_World.add(func_updater(func = func, incr = incr, verbose = verbose))

#add_func_updater = add_world_updater

def Update_RCONST(mech, world = None):
    for rconst in mech._parsed['RCONST']:
        exec(rconst, None, world)

def Update_SUN(mech, world):
    """
    Updates world dectionary to contain
      SUN - scaling variable between 0 and 1 (following Sandu et al.)

    if t < SunRise or t > SunSet: SUN = 0.
    
    hour = time since noon
    squared = abs(hour) * hour
    
    """
    t = world['t']
    SunRise = world['SunRise']
    SunSet  = world['SunSet']
    Thour = t/3600.0
    Tlocal = Thour % 24.

    if (Tlocal >= SunRise) and (Tlocal <= SunSet):
        Ttmp = (2.0 * Tlocal - SunRise - SunSet) / (SunSet - SunRise)
        if (Ttmp > 0.):
            Ttmp =  Ttmp * Ttmp
        else:
            Ttmp = -Ttmp * Ttmp
        
        SUN = ( 1.0 + cos(pi * Ttmp) )/2.0
    else:
        SUN = 0.0
    world['SUN'] = SUN

def solar_declination(N):
    """
    N - julian day 1-365 (1 = Jan 1; 365 = Dec 31)
    Returns solar declination in radians
    
    wikipedia.org/wiki/Declination_of_the_Sun
    dec_degrees = -23.44 * cos_degrees(360./365 * (N + 10))
    dec_radians = pi / 180. * -23.44) * cos_radians(pi / 180. * 360./365 * (N + 10))
    """
    return -0.40910517666747087 * cos(0.017214206321039961 * (N + 10.))


def Update_THETA(mech, world):
    """
    Adds solar zenith angle (THETA; angle from solar noon) in degrees
    to the world dictionary based on time
    
    THETA = arccos(sin(lat) * sin(dec) + cos(lat) * cos(dec) * cos(houra))
    """
    phi = world['Latitude_Radians']
    t = world['t']
    if 'SolarDeclination_Radians' in world:
        dec = world['SolarDeclination_Radians']
    else:
        StartJday = world['StartJday']
        N = StartJday + (t / 3600.) // 24
        dec = solar_declination(N)
    Tlocal = (t / 3600.) % 24.
    houra = radians((Tlocal - 12.) * 15.)
    THETA = arccos(sin(phi) * sin(dec) + cos(phi) * cos(dec) * cos(houra))
    world['THETA'] = degrees(THETA)

def Update_M(mech, world):
    """
    Adds concentrations (molecules/cm3) to world namespace for:
        M (air),
        O2 (0.20946 M),
        N2 (0.78084 M), and 
        H2 (500 ppb)
    based on:
        Pressure (P in Pascals),
        Temperature (TEMP in Kelvin), and 
        R is provided in m**3 * Pascals/K/mol
        
    TEMP and P must be defined either in world or in stdfuncs
    """
    try:
        M = eval('P / (R / centi**3) / TEMP * Avogadro', None, world)
    except:
        M = float(world['M'])
    world['M'] = M
    world['O2'] = 0.20946 * M
    world['N2'] = 0.78084 * M
    world['H2'] = 0.00000055 * M
