from pybricks.iodevices import LWP3Device
from pybricks.parameters import Color
from pybricks.tools import wait, StopWatch, run_task


MODE_RGB = const(0x03)
PORT_VALUE_MSG = const(0x45)
DEBUG = True

# Device identifier for the Duplo Hub.
DUPLO_TRAIN_ID = {
    'old': 0x20,
    'new': 0x21,
}

class Ports():
    def __init__(self, color_sensor = None, speaker = None, lights = None, motor = None):
        self.color_sensor = color_sensor
        self.speaker = speaker
        self.lights = lights
        self.motor = motor

train_ports = {
    DUPLO_TRAIN_ID['old']: Ports(color_sensor = 0x12, speaker = 0x01, lights = 0x11, motor = 0x29),
}

Color.LIGHTRED = Color.RED * 1.2
Color.LIGHTBLUE = Color.BLUE * 1.2

# Mapping that converts colors to LEGO color identifiers.
COLORS = {
    Color.NONE: 0,
    Color.LIGHTRED: 1,
    Color.MAGENTA: 2,
    Color.BLUE: 3,
    Color.LIGHTBLUE: 4,
    Color.CYAN: 5,
    Color.GREEN: 6,
    Color.YELLOW: 7,
    Color.ORANGE: 8,
    Color.RED: 9,
    Color.WHITE: 10,
}

MSG_TYPES = {
    "Port Input Format Setup (Single)": 0x41,
    "Port Output Command": 0x81,
}

# Mapping that converts sound names to indexes.
SOUNDS = {
    "brake": 3,
    "depart": 5,
    "water": 7,
    "horn": 9,
    "steam": 10
}

async def awaitable(value=None):
    return value

class ColorCodes():
    def __init__(self, name, rgb, lightcolor = None):
        self.name = name
        self.rgb = rgb
        self.lightcolor = lightcolor

COLORCODES = {
    "white": ColorCodes(name = "white", rgb = [6,5,5], lightcolor = Color.WHITE),
    "brightblue": ColorCodes(name = "brightblue", rgb = [0,1,3], lightcolor=Color.BLUE), 
    "treegreen": ColorCodes(name = "treegreen", rgb = [2,2,0], lightcolor=Color.GREEN),
    "housesalmon": ColorCodes(name = "housesalmon", rgb = [5,5,6], lightcolor=Color.LIGHTRED),
    "starpurple": ColorCodes(name = "starpurple", rgb = [3,2,3], lightcolor=Color.LIGHTBLUE),
    "clockorange": ColorCodes(name = "clockorange", rgb = [6,0,0], lightcolor=Color.ORANGE),
    "brightred": ColorCodes(name = "brightred", rgb = [4,0,0], lightcolor = Color.RED),
    "darkgreen": ColorCodes(name = "darkgreen", rgb = [0,2,0], lightcolor=Color.GREEN),
    "wrenchyellow": ColorCodes(name = "wrenchyellow", rgb = [6,2,0], lightcolor=Color.YELLOW),
    "brightyellow": ColorCodes(name = "brightyellow", rgb = [6,3,0], lightcolor=Color.YELLOW),
    "electricgreen": ColorCodes(name = "electricgreen", rgb = [0,3,1], lightcolor=Color.GREEN),
    "newwaterblue": ColorCodes(name = "newwaterblue", rgb = [0,2,4], lightcolor=Color.BLUE),
}

class DuploTrain():
    """Class to connect to the Duplo train and send commands to it."""

    def __init__(self, model='old'):
        """Scans for a train, connect, and prepare it to receive commands."""
        print("Searching for the train. Make sure it is on and blinking its front light.")
        self.trainid = DUPLO_TRAIN_ID[model]
        self.ports = train_ports[self.trainid]

        self.device = LWP3Device(self.trainid, name=None, timeout=10000)
        wait(500)

        self.setup_input(port = self.ports.speaker)
        self.setup_input(port = self.ports.color_sensor, mode = 0x03)

        # State values so we can avoid updating the speed too often.
        self.last_power = 0
        self.drivetimer = StopWatch()
        self.readtimer = StopWatch()

        print("Connected! to " + self.device.name())


    def play_sound(self, sound=None, duration=None):
        """Plays the specified sound."""
        try:
            index = SOUNDS[sound.lower()]
        except:
            index = int(sound)
        return self.write_direct(port=self.ports.speaker, value = index, mode = 0x01)

    def set_light(self, color):
        """Turns on the train light at the requested color."""
        if color not in COLORS:
            print("unknown color ", color)
            return awaitable() if run_task() else None
        
        return self.write_direct(port = self.ports.lights, value = COLORS[color])

    def start_driving(self, power):
        """Drives at a given "power" level between -100 and 100."""

        # Cap the power value and cut off values below -25% which won't move
        # the train, only make noise.
        power = max(-100, min(power, 100))
        if abs(power) < 25:
            power = 0

        # If the speed has hardly changed and we recently sent that value,
        # don't send now to avoid overloading the BLE link.
        if abs(power - self.last_power) <= 5 and self.drivetimer.time() < 200:
            return awaitable() if run_task() else None

        # Update power state and send the value.
        self.last_power = power
        self.drivetimer.reset()
        power_send = power + 256 if power < 0 else power  
        return self.write_direct(port = self.ports.motor, value = power_send)

    def stop_driving(self):
        """Stops driving."""
        return self.start_driving(0)

    def read(self):
        """Reads."""
        if self.readtimer.time() < 200:
            return awaitable() if run_task() else None
        self.readtimer.reset()
        return self.device.read()
    
    def getcolor(self, updatelight = False):
        msg = self.read()
        if msg != None and DEBUG and False:
            print(msg)
        try:
            kind = msg[2]
            port = msg[3]
            
            if kind != PORT_VALUE_MSG and port != self.ports.color_sensor:
                return None
            
            red = msg[5]
            green = msg[7]
            blue = msg[9]

            for item in COLORCODES.values():
                if item.rgb == [red, green, blue]:
                    if DEBUG:
                        print(item.name)
                    if updatelight and item.lightcolor:
                        self.set_light(item.lightcolor)
                    return(item.name)
                    break
                elif DEBUG and False:
                    print(red, green, blue)

        except:
            return None

    def testports(self, port = None, value = None, mode = 0x01):
        if port != None and value != None:
            result = self.write(port = port, value = value)
        elif value != None:
            for i in range(0x20):
                result = self.write_direct(port = i, value = value, mode = mode)
                wait(500)
        elif port != None:
            for i in range(0x50):
                result = self.write_direct(port = port, value = i, mode = mode)
                wait(500)
        else:
            for i in range(0x50):
                print("port:", i)
                for j in range(0x10):
                    for k in range(0x8):
                        result = self.write_direct(port = i, value = j, mode = k)
                        wait(100)
        return

    def testinputs(self, port = None, mode = None):
        if port != None and mode != None:
            result = self.setup_input(port = port, mode = mode)
        elif mode != None:
            for i in range(0x20):
                result = self.setup_input(port = i, mode = mode)
                wait(500)
        elif port != None:
            for i in range(0x50):
                result = self.setup_input(port = port, mode = i)
                wait(500)
        else:
            for i in range(0x50):
                print("port:", i)
                for j in range(0x10):
                    result = self.setup_input(port = i, mode = j)
                    wait(100)
        return

    def setup_input(self, port, mode = 0x01, notification = 0x01):
        try:
            self.device.write(bytes([
                0x0a, 0x00, MSG_TYPES["Port Input Format Setup (Single)"], # Header: Length, HubID (not used), Message Type
                port, mode,      # Port ID, Mode
                0x01, 0x00, 0x00, 0x00,                 # Delta Interval
                notification                                    # Notification enabled
                ]))
            if DEBUG:
                print(port, ":", mode, "worked")
        except Exception as e:
            if not DEBUG:
                print("Port ", port, " not initialized")
                print(getattr(e, 'message', repr(e)))
                print(e)

        wait(500)

    def write_direct(self, port, value, mode = 0x00):
        try: 
            return self.device.write(bytes([
                            0x08, 0x00, MSG_TYPES["Port Output Command"], # Header: Length, HubID (not used), Message Type
                            port,        # Port ID
                            0x11,               # startup and completion info
                            0x51,               # Sub Command:  WriteDirectModeData() 
                            mode, value # Mode and Value
                            ]))
            if DEBUG:
                print(port, ":", value, ":", mode, "worked")
        except Exception as e:
            if not DEBUG:
                print("Port ", port, " not written to")
                print(getattr(e, 'message', repr(e)))
                print(e)
            return



# Extra "functions" that allow us to call methods of the train object using
# block coding, which currently does not have a method call block.
def start_driving(train: DuploTrain, power):
    return train.start_driving(power)

def set_light(train: DuploTrain, color):
    return train.set_light(color)

def play_sound(train: DuploTrain, sound):
    print("playing ", sound)
    return train.play_sound(sound)

def read(train: DuploTrain):
    msg = train.read()
    if msg != None:
        print(', '.join(map(hex, msg)))

    try:
        kind = msg[2]
        port = msg[3]
        
        if kind != PORT_VALUE_MSG:
            return
        
        if port == train.ports.color_sensor:
            red = msg[4]
            green = msg[6]
            blue = msg[8]
            # print("red: ", red, "green: ", green, "blue: ", blue)
        elif port == train.ports.lights:
            print("lights")
        elif port == train.ports.motor:
            print("motor")
        elif port == train.ports.speaker:
            print("speaker")
        else:
            print(port)
    except:
        return     

    return None

def get_color(train: DuploTrain, updatelight=False):
    return train.getcolor(updatelight = updatelight)

def testports(train: DuploTrain, port = None, value = None, mode = 0x00):
    return train.testports(port, value, mode)

def testinputs(train: DuploTrain, port = None, mode = None):
    return train.testinputs(port = port, mode = mode)
