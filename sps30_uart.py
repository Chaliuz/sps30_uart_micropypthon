from machine import UART
import time, struct
import uasyncio as asyncio

class SPS30Uart:

    def __init__(self, rx, tx, baudrate=115200):
        """
        """
        self.rx = rx
        self.tx = tx

        self.uart = UART(2, baudrate, tx=self.tx, rx=self.rx)

        self.rx_buffer = bytearray()
        self.sensor_started = False


    def _send_cmd(self, cmd, data=b''):
        frame = bytearray()
        frame.append(0x7E)
        frame.append(0x00)          # ADDRESS
        frame.append(cmd)
        frame.append(len(data))
        frame.extend(data)
    
        chk = self._checksum(frame[1:])  # sin 0x7E
        frame.append(chk)
        frame.append(0x7E)
    
        self.uart.write(frame)

    def _checksum(self, data):
        return (~(sum(data) & 0xFF)) & 0xFF

    def _unstuff(self, data):
        out = bytearray()
        i = 0
        while i < len(data):
            if data[i] == 0x7D:
                i += 1
                if data[i] == 0x5E: out.append(0x7E)
                elif data[i] == 0x5D: out.append(0x7D)
                elif data[i] == 0x31: out.append(0x11)
                elif data[i] == 0x33: out.append(0x13)
            else:
                out.append(data[i])
            i += 1
            time.sleep(0.01)
        return out

    def _find_7E(self, buf, start=0):
        for i in range(start, len(buf)):
            if buf[i] == 0x7E:
                return i
        return -1

    def _read_frame(self):
        # global rx_buffer
    
        data = self.uart.read()
        if data:
            self.rx_buffer.extend(data)
    
        start = self._find_7E(self.rx_buffer, 0)
        if start == -1:
            return None
    
        end = self._find_7E(self.rx_buffer, start + 1)
        if end == -1:
            return None
    
        raw = self.rx_buffer[start+1:end]
        self.rx_buffer = self.rx_buffer[end+1:]
    
        frame = self._unstuff(raw)
    
        if len(frame) < 6:
            return None
    
        adr = frame[0]
        cmd = frame[1]
        state = frame[2]
        length = frame[3]
        payload = frame[4:4+length]
        chk_rx = frame[4+length]
    
        # checksum incluye ADR, CMD, STATE, LEN y DATA
        if self._checksum(frame[:-1]) != chk_rx:
            print("Checksum error")
            return None
    
        # opcional: verificar errores del sensor
        if state != 0x00:
            print("Sensor error state:", state)
            return None
    
        return payload

    def _parse_measurement(self, data):
        values = struct.unpack('>10f', data)
        return {
            "1.0": round(values[0],2),
            "2.5": round(values[1],2),
            "4.0": round(values[2],2),
            "10":  round(values[3],2)
        }

    async def start_continuous_measurements(self):
        self._send_cmd(0x00, b'\x01\x03')
        # time.sleep(1.5)   # tiempo real de arranque
        await asyncio.sleep(1.5)
        self.sensor_started = True
        print("iniciando medición continua...")


    async def stop_continuous_measurement(self): 
        self._send_cmd(0x01)  
        # time.sleep(0.2)
        await asyncio.sleep(0.2)
        self.sensor_started = False
        print("medida continua detenida...")

    # def read_measure(self):
    async def read_measure(self):

        """
        it returns a dict like this:
        {
            "PM1.0": round(values[0],2),
            "PM2.5": round(values[1],2),
            "PM4.0": round(values[2],2),
            "PM10":  round(values[3],2)
        }
        """
        if not self.sensor_started:
            print("iniciando sensor...")
            # self.start_continuous_measurements()
            await self.start_continuous_measurements()

        self._send_cmd(0x03)  # READ MEASUREMENT
        # time.sleep(0.3)
        await asyncio.sleep(0.3)

        data = self._read_frame()
        if data:
            response = self._parse_measurement(data)
            # print("response: ", response)
            return response
        else: 
            return None

    async def clean_fan(self): 
        if not self.sensor_started:
            # self.start_continuous_measurements()
            await self.start_continuous_measurements()

        self._send_cmd(0x56)  
        # time.sleep(0.2)
        await asyncio.sleep(0.3)

        data = self._read_frame()
        if data:
            status = (data[0] << 8) | data[1]
            print("Status:", hex(status))

