from libraries.sps30_uart import SPS30Uart
import uasyncio as asyncio

seconds = 0
sps30 = SPS30Uart(tx=16,rx=17)


async def main():

    # await sps30.clean_fan()

    seconds = 0
    while True:
        " start continuous measurement if not already initialized "
        current_measure = await sps30.read_measure()
        print("current_measure: ", current_measure)

        if seconds >= 8:
            await sps30.stop_continuous_measurement()
            break

        await asyncio.sleep(2)
        seconds += 2

asyncio.run(main())

