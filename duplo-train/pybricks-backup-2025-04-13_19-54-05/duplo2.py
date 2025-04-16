from pybricks.iodevices import LWP3Device
from pybricks.parameters import Color
from pybricks.tools import wait, StopWatch, run_task

# Device identifier for the Duplo Hub.
DUPLO_TRAIN_ID = 0x20
DUPLO_TRAIN_ID2 = 0x21
PORT_COLOR_SENSOR = const(0x12)
PORT_SPEAKER = const(0x01)
PORT_LIGHTS = const(0x11)
PORT_MOTOR = const(0x00)

MODE_RGB = const(0x03)
PORT_VALUE_MSG = const(0x45)

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
    "starpurple": ColorCodes(name = "starpurple", rgb = [3,2,3]),
    "clockorange": ColorCodes(name = "clockorange", rgb = [6,0,0]),
    "brightred": ColorCodes(name = "brightred", rgb = [4,0,0], lightcolor = Color.RED),
    "darkgreen": ColorCodes(name = "darkgreen", rgb = [0,2,0]),
    "wrenchyellow": ColorCodes(name = "wrenchyellow", rgb = [6,2,0]),
    "brightyellow": ColorCodes(name = "brightyellow", rgb = [6,3,0]),
    "electricgreen": ColorCodes(name = "electricgreen", rgb = [0,3,1]),
    "newwaterblue": ColorCodes(name = "newwaterblue", rgb = [0,2,4]),
}

class DuploTrain():
    """Class to connect to the Duplo train and send commands to it."""

    def __init__(self):
        """Scans for a train, connect, and prepare it to receive commands."""
        print("Searching for the train. Make sure it is on and blinking its front light.")
        self.device = LWP3Device(DUPLO_TRAIN_ID2, name=None, timeout=10000)

        # # Allows speaker to be used (3.17.1. Format of Port Input Format Setup (Single))
        # self.device.write(bytes([
        #     0x0a, 0x00, MSG_TYPES["Port Input Format Setup (Single)"], # Header: Length, HubID (not used), Message Type
        #     PORT_SPEAKER, 0x01,                         # Port ID, Mode
        #     0x01, 0x00, 0x00, 0x00,             # Delta Interval
        #     0x01                                # Notification enabled
        #     ]))
        
        # # # Reads from color sensor (3.17.1. Format of Port Input Format Setup (Single))
        # self.device.write(bytes([
        #     0x0a, 0x00, MSG_TYPES["Port Input Format Setup (Single)"], # Header: Length, HubID (not used), Message Type
        #     PORT_COLOR_SENSOR, MODE_RGB,        # Port ID, Mode
        #     0x01, 0x00, 0x00, 0x00,             # Delta Interval
        #     0x01                                # Notification enabled
        #     ]))

        # State values so we can avoid updating the speed too often.
        self.last_power = 0
        self.drivetimer = StopWatch()
        self.readtimer = StopWatch()

        print("Connected! to " + self.device.name())
        wait(500)

    def play_sound(self, sound=None, duration=None):
        """Plays the specified sound."""
        try:
            index = SOUNDS[sound.lower()]
        except:
            index = int(sound)
        return self.device.write(bytes([
            0x08, 0x00, MSG_TYPES["Port Output Command"], # Header: Length, HubID (not used), Message Type
            PORT_SPEAKER,       # Port ID
            0x11,               # startup and completion info
            0x51,               # Sub Command:  WriteDirectModeData() 
            0x01, index
            ]))

    def set_light(self, color):
        """Turns on the train light at the requested color."""
        if color not in COLORS:
            print("unknown color ", color)
            return awaitable() if run_task() else None
        return self.device.write(bytes([
            0x08, 0x00, MSG_TYPES["Port Output Command"], # Header: Length, HubID (not used), Message Type
            PORT_LIGHTS,        # Port ID
            0x11,               # startup and completion info
            0x51,               # Sub Command:  WriteDirectModeData() 
            0x00, COLORS[color] # Mode and Color Number
            ]))

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
        return self.device.write(bytes([
            0x08, 0x00, MSG_TYPES["Port Output Command"], # Header: Length, HubID (not used), Message Type
            PORT_MOTOR,             # Port ID
            0x01,                   # startup and completion info
            0x51,                   # Sub Command:  WriteDirectModeData()
            0x00, power_send        # MOTOR/OUTPUT Commands encoded as WriteDirectModeData (Cmd 0x81, Sub Cmd 0x51)
            ]))

    def stop_driving(self):
        """Stops driving."""
        return self.start_driving(0)

    def read(self):
        """Reads."""
        if self.readtimer.time() < 200:
            return awaitable() if run_task() else None
        self.readtimer.reset()
        return self.device.read()


# Extra "functions" that allow us to call methods of the train object using
# block coding, which currently does not have a method call block.
def start_driving(train: DuploTrain, power):
    return train.start_driving(power)

def set_light(train: DuploTrain, color):
    return train.set_light(color)

def play_sound(train: DuploTrain, sound):
    return train.play_sound(sound)

def read(train: DuploTrain):
    msg = train.read()
    print(msg)
    try:
        kind = msg[2]
        port = msg[3]
        
        if kind != PORT_VALUE_MSG:
            return
        
        if port == PORT_COLOR_SENSOR:
            red = msg[4]
            green = msg[6]
            blue = msg[8]
            print("red: ", red, "green: ", green, "blue: ", blue)
        elif port == PORT_LIGHTS:
            print("lights")
        elif port == PORT_MOTOR:
            print("motor")
        elif port == PORT_SPEAKER:
            print("speaker")
        else:
            print(port)
    except:
        return     

    return None

def get_color(train: DuploTrain, updatelight=False):
    msg = train.read()
    try:
        kind = msg[2]
        port = msg[3]
        
        if kind != PORT_VALUE_MSG and port != PORT_COLOR_SENSOR:
            return None
        
        red = msg[5]
        green = msg[7]
        blue = msg[9]
        # for element in msg:
        #     print(element)
        # print("red: ", red, "green: ", green, "blue: ", blue)

        for item in COLORCODES.values():
            if item.rgb == [red, green, blue]:
                print(item.name)
                if updatelight and item.lightcolor:
                    train.set_light(item.lightcolor)
                return(item.name)
                break
        # if [red, green, blue] == COLORCODES['white'].rgb: 
        #     print("white")
        # elif red == 0 and green == 1 and blue == 3: 
        #     print("brightblue")
        # elif red == 2 and green == 2 and blue == 0: 
        #     print("treegreen")
        # elif red == 5 and green == 5 and blue == 6: 
        #     print("housesalmon")
        # elif red == 3 and green == 2 and blue == 3: 
        #     print("starpurple")
        # elif red == 6 and green == 0 and blue == 0: 
        #     print("clockorange")
        # elif red == 4 and green == 0 and blue == 0: 
        #     print("brightred")
        # elif red == 0 and green == 2 and blue == 0: 
        #     print("darkgreen")
        # elif red == 6 and green == 2 and blue == 0: 
        #     print("wrenchyellow")
        # elif red == 6 and green == 3 and blue == 0: 
        #     print("brightyellow")
        # elif red == 0 and green == 3 and blue == 1: 
        #     print("electricgreen")
        # elif red == 0 and green == 2 and blue == 4: 
        #     print("newwaterblue")

    except:
        return None

        
    return None