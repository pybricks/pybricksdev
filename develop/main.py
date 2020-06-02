
import asyncio
from pybricks_tools.ble import PybricksHubConnection


# Main function, to be replaced with an argparser
async def main():

    async with PybricksHubConnection(debug=True) as hub:
        await asyncio.sleep(2.0)
        await hub.write(b'    ')
        await asyncio.sleep(2.0)


asyncio.run(main())
